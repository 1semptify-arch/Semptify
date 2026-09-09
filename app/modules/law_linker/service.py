"""
Law Linker Service
==================
Resolves a free-text citation to its official source and, where supported,
fetches the word-for-word official text so the pop-out can display it.

Caching is a simple in-memory TTL cache per worker process. Official law text
is public, and Semptify does not store user data here, so a short-lived cache
is acceptable and avoids hammering government servers.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.core.law_source_registry import (
    LawSource,
    build_official_url,
    resolve_source,
)
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600
_cache: dict[str, tuple[dict, float]] = {}


def _cache_key(citation: str) -> str:
    return citation.strip().lower()


def _get_cached(citation: str) -> dict | None:
    key = _cache_key(citation)
    if key in _cache:
        data, ts = _cache[key]
        if utc_now().timestamp() - ts < CACHE_TTL_SECONDS:
            return data
        del _cache[key]
    return None


def _set_cached(citation: str, data: dict) -> None:
    _cache[_cache_key(citation)] = (data, utc_now().timestamp())


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _extract_mn_statute_text(html: str) -> str:
    """Extract the word-for-word statute text from a revisor.mn.gov page."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        statute = soup.find(class_="statute")
        if not statute:
            return ""
        # Remove script/style tags and collapse whitespace
        for tag in statute.find_all(["script", "style"]):
            tag.decompose()
        text = statute.get_text(separator="\n", strip=True)
        # Normalize runs of blank lines
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text
    except Exception as exc:
        logger.warning("Failed to extract Minnesota statute text: %s", exc)
        return ""


async def _fetch_mn_statute_text(citation: str, source: LawSource) -> str:
    """Fetch the official Minnesota statute text from the Revisor of Statutes."""
    url = build_official_url(citation)
    if not url:
        return ""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            text = _extract_mn_statute_text(resp.text)
            if text:
                return text
            # If extraction fails, log and return empty so UI falls back to link
            logger.warning("No .statute text extracted from %s", url)
    except httpx.HTTPError as exc:
        logger.warning("Could not fetch Minnesota statute text from %s: %s", url, exc)
    except Exception as exc:
        logger.error("Unexpected error fetching statute text: %s", exc)
    return ""


async def resolve_and_fetch(citation: str) -> dict:
    """
    Resolve a citation and, where possible, fetch the official source text.

    Returns a dict with:
        citation, official_url, source_name, jurisdiction, last_verified,
        verified_date, title, text, disclaimer
    """
    cached = _get_cached(citation)
    if cached:
        return cached

    source = resolve_source(citation)
    if not source:
        return {
            "citation": citation,
            "official_url": None,
            "source_name": None,
            "jurisdiction": None,
            "last_verified": None,
            "verified_date": None,
            "title": None,
            "text": None,
            "disclaimer": (
                "This information is for educational purposes only and does not "
                "constitute legal advice. Always verify current law at the official source."
            ),
        }

    official_url = build_official_url(citation)
    text = ""

    # Minnesota Statutes are the first supported live-fetch source.
    if source.source_name == "Minnesota Revisor of Statutes":
        text = await _fetch_mn_statute_text(citation, source)

    # For other sources, the pop-out links to the official source and shows
    # source metadata; we do not yet fetch their full text.
    title = citation.strip()
    if not text:
        text = None

    result = {
        "citation": citation,
        "official_url": official_url,
        "source_name": source.source_name,
        "jurisdiction": source.jurisdiction,
        "last_verified": source.last_verified,
        "verified_date": _now_date() if text else None,
        "title": title,
        "text": text,
        "disclaimer": (
            "This information is for educational purposes only and does not "
            "constitute legal advice. Laws change frequently — always verify "
            "current statutes at the official source."
        ),
    }

    # Only cache successful fetches or successful resolutions.
    _set_cached(citation, result)
    return result
