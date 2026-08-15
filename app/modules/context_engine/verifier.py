"""Context Engine verifier — checks that cached facts still resolve and content matches.

A fact is 'verified' if:
- source_url returns HTTP 200
- if extraction_pattern is set, the fetched content contains a match and the matched
  text equals canonical_value
- if canonical_value is not set, extraction is attempted but the fact stays
  unverified and an alert is raised, so a human can confirm the number
- if extraction_pattern is not set, the source still resolves and claim is non-empty

Runs periodically (cron/manual) to mark facts stale and raise freshness alerts.
"""

import io
import logging
import re

import httpx
from sqlalchemy import and_, select

from app.core.database import get_db_session
from app.core.utc import utc_now
from app.modules.context_engine.models import ContextFact

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore

try:
    import pdfplumber
except ImportError:
    pdfplumber = None  # type: ignore

try:
    from app.core.data_freshness_manager import FreshnessType, data_freshness_manager
except Exception:  # pragma: no cover - data_freshness manager may not be available in tests
    data_freshness_manager = None  # type: ignore
    FreshnessType = None  # type: ignore

logger = logging.getLogger(__name__)

VERIFY_TIMEOUT_SECONDS = 30.0
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0.0.0 Safari/537.36"
)


_RE_COLLAPSE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Collapse repeated whitespace for stable comparison."""
    return _RE_COLLAPSE.sub(" ", text.strip())


def _extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF byte stream using pdfplumber if available."""
    if pdfplumber is None:
        raise RuntimeError("pdfplumber is not installed; cannot extract text from PDF")

    text_parts: list[str] = []
    with io.BytesIO(content) as bio:
        with pdfplumber.open(bio) as pdf:
            for i, page in enumerate(pdf.pages):
                # Defensive: stop after 25 pages to keep the check bounded.
                if i >= 25:
                    break
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_text_from_response(response: httpx.Response) -> str:
    """Return normalized plain text from an HTTP response (HTML or PDF)."""
    content_type = response.headers.get("content-type", "").lower()
    if "pdf" in content_type:
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise RuntimeError(f"PDF too large: {len(response.content)} bytes")
        return _extract_text_from_pdf(response.content)

    # For HTML, strip tags and decode entities to get comparable text.
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"Response too large: {len(response.content)} bytes")
    text = response.text
    if BeautifulSoup is not None and ("html" in content_type or text.lstrip().startswith(("<", "<!DOCTYPE"))):
        soup = BeautifulSoup(text, "lxml")
        text = soup.get_text(separator=" ", strip=True)
    return text


async def _fetch_source(url: str) -> httpx.Response:
    """Fetch a source URL with a browser-like User-Agent."""
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    async with httpx.AsyncClient(timeout=VERIFY_TIMEOUT_SECONDS, follow_redirects=True) as client:
        return await client.get(url, headers=headers)


def _create_freshness_alert(fact: ContextFact, severity: str, message: str) -> None:
    """Raise a data-freshness alert for a landing/public fact."""
    if data_freshness_manager is None or FreshnessType is None:
        logger.warning("Freshness manager not available; alert not raised: %s", message)
        return

    data_freshness_manager.create_alert(
        rule_id=f"context_engine_landing_{fact.id}",
        data_type=FreshnessType.MARKETING_CLAIMS,
        severity=severity,
        message=message,
    )


async def verify_fact(fact: ContextFact) -> bool:
    """Check that a fact's source URL still resolves and, if configured,
    that the expected content is still present. Returns True if verified."""
    if not fact.source_url:
        return False

    ok = False
    alert_message: str | None = None
    alert_severity = "warning"

    try:
        resp = await _fetch_source(fact.source_url)
        if resp.status_code >= 400:
            alert_message = f"Source URL returned {resp.status_code} for fact {fact.id}: {fact.source_url}"
            logger.info("Verify failed for fact %s: HTTP %s", fact.id, resp.status_code)
            ok = False
        else:
            text = _extract_text_from_response(resp)
            normalized_text = _normalize(text)

            if not fact.claim:
                alert_message = f"Fact {fact.id} has no claim text"
                ok = False
            elif not fact.extraction_pattern:
                # No configured pattern: source resolves and claim exists is enough.
                ok = True
            else:
                match = re.search(fact.extraction_pattern, normalized_text, re.IGNORECASE)
                if not match:
                    alert_message = (
                        f"Could not extract expected content for fact {fact.id} "
                        f"from {fact.source_url}: pattern {fact.extraction_pattern!r} did not match"
                    )
                    alert_severity = "error"
                    ok = False
                else:
                    extracted = _normalize(match.group(0))
                    if fact.canonical_value is None:
                        # We extracted something, but no canonical value has been set yet.
                        # Keep the fact unverified and flag it for human review.
                        alert_message = (
                            f"Canonical value not set for fact {fact.id}; "
                            f"extracted {extracted!r} from {fact.source_url} — needs human confirmation"
                        )
                        alert_severity = "warning"
                        ok = False
                    else:
                        canonical = _normalize(fact.canonical_value)
                        if extracted == canonical:
                            ok = True
                        else:
                            alert_message = (
                                f"Canonical value mismatch for fact {fact.id}: "
                                f"expected {canonical!r}, got {extracted!r} "
                                f"from {fact.source_url}"
                            )
                            alert_severity = "error"
                            ok = False

    except httpx.RequestError as e:
        alert_message = f"Network error verifying fact {fact.id} ({fact.source_url}): {e}"
        logger.info("Verify failed for fact %s: %s", fact.id, e)
    except RuntimeError as e:
        alert_message = f"Content extraction failed for fact {fact.id} ({fact.source_url}): {e}"
        logger.info("Verify extraction failed for fact %s: %s", fact.id, e)
    except Exception as e:
        alert_message = f"Unexpected error verifying fact {fact.id} ({fact.source_url}): {e}"
        logger.exception("Verify failed for fact %s: %s", fact.id, e)

    if alert_message:
        _create_freshness_alert(fact, alert_severity, alert_message)

    async with get_db_session() as db:
        result = await db.execute(select(ContextFact).where(ContextFact.id == fact.id))
        db_fact = result.scalars().first()
        if db_fact:
            db_fact.is_verified = ok
            db_fact.verified_at = utc_now().replace(tzinfo=None)
            await db.commit()

    return ok


async def verify_subject(subject: str, jurisdiction: str = "MN", limit: int = 20) -> dict:
    """Verify all facts for a subject. Returns summary."""
    async with get_db_session() as db:
        stmt = (
            select(ContextFact)
            .where(
                and_(
                    ContextFact.subject == subject,
                    ContextFact.jurisdiction == jurisdiction,
                )
            )
            .limit(limit)
        )
        result = await db.execute(stmt)
        facts = list(result.scalars().all())

    verified = 0
    failed = 0
    for f in facts:
        ok = await verify_fact(f)
        if ok:
            verified += 1
        else:
            failed += 1
    return {
        "subject": subject,
        "jurisdiction": jurisdiction,
        "total": len(facts),
        "verified": verified,
        "failed": failed,
    }
