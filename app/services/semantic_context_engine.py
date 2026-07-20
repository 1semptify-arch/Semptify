"""
Semantic Context Engine — Deep OCR Pass 2.

Takes raw OCR text (and an optional document type) and turns date mentions into
labeled, confidence-scored semantic results.  It never re-scans an image; it
works entirely on the text produced by Pass 1 (Light Intake / OCR).

Date roles (Category A intrinsic dates):
    created, signed, issued, effective, claimed_service, deadline, period

Output shape per result:
    {
        "raw_text": "January 15, 2024",
        "date": "2024-01-15",
        "semantic_label": "deadline",
        "trigger_phrase": "must respond by",
        "confidence": 0.95,
        "bounding_box": null  # reserved for future OCR bbox passthrough
    }

The engine is rule-based/regex first.  An LLM fallback is reserved for
ambiguous cases, but is only invoked when an OpenAI-compatible endpoint and
key are configured; otherwise the highest-confidence rule label is returned.
"""

import logging
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SemanticDateResult:
    """A single date classified by semantic role."""

    raw_text: str
    date: str
    semantic_label: str
    trigger_phrase: str
    confidence: float
    bounding_box: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SemanticContextEngine:
    """Classify dates and entities in OCR text using tenancy domain schema."""

    # Date formats we look for.  Each tuple is (regex, strptime format, confidence bump).
    DATE_PATTERNS: list[tuple[str, str, float]] = [
        # MM/DD/YYYY or MM-DD-YYYY
        (r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", "%m/%d/%Y", 0.0),
        # Month DD, YYYY
        (
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b",
            "Month DD, YYYY",
            0.05,
        ),
        # DD Month YYYY
        (
            r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
            "DD Month YYYY",
            0.05,
        ),
        # YYYY-MM-DD (ISO)
        (r"\b(\d{4})-(\d{2})-(\d{2})\b", "%Y-%m-%d", 0.0),
    ]

    MONTH_MAP: dict[str, int] = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    # Domain schema: exact phrases earn the highest confidence; keywords are a softer signal.
    DATE_ROLE_TRIGGERS: dict[str, dict[str, list[str]]] = {
        "created": {
            "exact": ["dated this", "date of this", "created on", "prepared on", "date prepared", "date:"],
            "keyword": ["dated", "created", "prepared", "date of"],
        },
        "signed": {
            "exact": [
                "signed this",
                "signed on",
                "executed on",
                "signature date",
                "date signed",
                "signed by",
            ],
            "keyword": ["signed", "executed", "signature"],
        },
        "issued": {
            "exact": [
                "issued on",
                "issued this",
                "notice is dated",
                "notice date",
                "issued by",
            ],
            "keyword": ["issued", "notice", "served"],
        },
        "effective": {
            "exact": [
                "effective as of",
                "effective date",
                "commencement date",
                "lease begins",
                "term begins",
                "lease effective",
                "effective immediately",
            ],
            "keyword": ["effective", "commencement", "begins", "starts", "start date", "term"],
        },
        "claimed_service": {
            "exact": [
                "claimed on",
                "claimed service date",
                "date of service",
                "service date of",
                "service requested on",
                "incident date",
                "date of loss",
                "repair requested on",
            ],
            "keyword": ["claimed", "service", "incident", "loss", "repair", "requested"],
        },
        "deadline": {
            "exact": [
                "must respond by",
                "no later than",
                "due by",
                "deadline is",
                "must vacate",
                "vacate by",
                "must pay by",
                "appear by",
                "hearing date",
                "court date",
                "respond by",
                "pay by",
            ],
            "keyword": [
                "deadline",
                "due",
                "must",
                "hearing",
                "court",
                "vacate",
                "respond",
                "appear",
                "pay",
            ],
        },
        "period": {
            "exact": [
                "for the period",
                "rent period",
                "billing period",
                "lease term",
                "month of",
                "rent for",
                "through",
            ],
            "keyword": ["period", "term", "month of", "through", "from", "to"],
        },
    }

    # Document-type hints: certain labels are more/less likely per document type.
    DOC_TYPE_HINTS: dict[str, dict[str, float]] = {
        "lease": {"effective": 0.05, "signed": 0.05, "period": 0.03},
        "lease_amendment": {"effective": 0.05, "signed": 0.05},
        "eviction_notice": {"deadline": 0.08, "issued": 0.05},
        "notice_to_quit": {"deadline": 0.08, "issued": 0.05},
        "rent_increase_notice": {"effective": 0.05, "issued": 0.05},
        "late_fee_notice": {"deadline": 0.05, "issued": 0.05},
        "repair_request": {"claimed_service": 0.08, "created": 0.03},
        "repair_response": {"deadline": 0.05, "issued": 0.05},
        "court_summons": {"deadline": 0.08, "hearing": 0.05, "issued": 0.03},
        "court_filing": {"deadline": 0.05, "issued": 0.03, "created": 0.03},
        "payment_record": {"period": 0.05, "created": 0.03},
        "receipt": {"period": 0.05, "created": 0.03},
    }

    def extract(self, text: str, doc_type: str | None = None) -> list[SemanticDateResult]:
        """Extract and classify all date mentions in `text`."""
        if not text:
            return []

        doc_type = (doc_type or "").lower().strip()
        results: list[SemanticDateResult] = []

        for regex, fmt, fmt_bump in self.DATE_PATTERNS:
            for match in re.finditer(regex, text, flags=re.IGNORECASE):
                raw = match.group(0)
                dt = self._parse_date(raw, fmt)
                if not dt:
                    continue

                # Use the line/sentence containing the date as the classification
                # context so triggers from neighboring dates do not contaminate
                # this candidate.
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                if line_end == -1:
                    line_end = len(text)
                context = text[line_start:line_end]
                context_lower = context.lower()
                date_span = (match.start() - line_start, match.end() - line_start)

                label, trigger, confidence = self._classify_date(
                    context, context_lower, date_span, doc_type
                )

                confidence = min(0.99, confidence + fmt_bump)

                results.append(
                    SemanticDateResult(
                        raw_text=raw,
                        date=dt.date().isoformat(),
                        semantic_label=label,
                        trigger_phrase=trigger,
                        confidence=round(confidence, 3),
                    )
                )

        return results

    def _parse_date(self, raw: str, fmt: str) -> datetime | None:
        """Parse a single raw date string into a timezone-aware datetime."""
        try:
            if fmt == "%m/%d/%Y":
                # Handles both / and - separators from the shared MM/DD/YYYY regex.
                parts = re.split(r"[/-]", raw)
                if len(parts) != 3:
                    return None
                month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                return datetime(year, month, day, tzinfo=UTC)

            if fmt == "%Y-%m-%d":
                parts = raw.split("-")
                if len(parts) != 3:
                    return None
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                return datetime(year, month, day, tzinfo=UTC)

            if fmt == "Month DD, YYYY":
                m = re.match(
                    r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", raw, flags=re.IGNORECASE
                )
                if not m:
                    return None
                month = self.MONTH_MAP[m.group(1).lower()]
                day = int(m.group(2))
                year = int(m.group(3))
                return datetime(year, month, day, tzinfo=UTC)

            if fmt == "DD Month YYYY":
                m = re.match(
                    r"(\d{1,2})\s+(\w+)\s+(\d{4})", raw, flags=re.IGNORECASE
                )
                if not m:
                    return None
                day = int(m.group(1))
                month = self.MONTH_MAP[m.group(2).lower()]
                year = int(m.group(3))
                return datetime(year, month, day, tzinfo=UTC)

        except (ValueError, KeyError):
            logger.debug("Failed to parse date: %s", raw)

        return None

    def _classify_date(
        self,
        context: str,
        context_lower: str,
        date_span: tuple[int, int],
        doc_type: str,
    ) -> tuple[str, str, float]:
        """Classify a single date candidate.  Returns (label, trigger, confidence)."""
        date_center = (date_span[0] + date_span[1]) / 2
        scores: dict[str, float] = {}
        triggers: dict[str, str] = {}

        for label, triggers_cfg in self.DATE_ROLE_TRIGGERS.items():
            best_score = 0.0
            best_trigger = ""

            # Exact phrases are strong signals; reward proximity to the date.
            for phrase in triggers_cfg["exact"]:
                for m in re.finditer(re.escape(phrase), context_lower):
                    if self._overlap(date_span, (m.start(), m.end())):
                        continue
                    dist = abs(((m.start() + m.end()) / 2) - date_center)
                    weight = 1.0 / (1.0 + dist / 40.0)
                    score = 1.0 * weight
                    if score > best_score:
                        best_score = score
                        best_trigger = context[m.start() : m.end()]

            # Keywords are softer signals; also reward proximity.
            for keyword in triggers_cfg["keyword"]:
                for m in re.finditer(rf"\b{re.escape(keyword)}\b", context_lower):
                    if self._overlap(date_span, (m.start(), m.end())):
                        continue
                    dist = abs(((m.start() + m.end()) / 2) - date_center)
                    weight = 1.0 / (1.0 + dist / 40.0)
                    score = 0.7 * weight
                    if score > best_score:
                        best_score = score
                        best_trigger = context[m.start() : m.end()]

            scores[label] = best_score
            triggers[label] = best_trigger

        # Apply document-type hints.
        for label, delta in self.DOC_TYPE_HINTS.get(doc_type, {}).items():
            if label in scores:
                scores[label] += delta

        # Ambiguity check: if top two labels are too close, ask for disambiguation.
        sorted_labels = sorted(scores, key=lambda k: scores[k], reverse=True)
        if not sorted_labels or scores[sorted_labels[0]] <= 0.0:
            return "mentioned", "", 0.5

        top_label = sorted_labels[0]
        top_score = scores[top_label]

        if len(sorted_labels) > 1:
            second_score = scores[sorted_labels[1]]
            if top_score - second_score < 0.15 and top_score < 0.85:
                resolved = self._resolve_ambiguity(context, sorted_labels[:2])
                if resolved and resolved in scores:
                    top_label = resolved
                    top_score = scores[top_label]

        confidence = self._score_to_confidence(top_score)
        return top_label, triggers[top_label] or top_label, confidence

    @staticmethod
    def _overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
        """Return True if two spans overlap."""
        return a[0] < b[1] and b[0] < a[1]

    def _score_to_confidence(self, score: float) -> float:
        """Map a classification score to a calibrated confidence."""
        if score >= 1.0:
            return 0.95
        if score >= 0.75:
            return 0.85
        if score >= 0.45:
            return 0.72
        if score > 0.0:
            return 0.58
        return 0.5

    def _resolve_ambiguity(self, context: str, candidates: list[str]) -> str | None:
        """Resolve ambiguous date roles.  Rule-based fallback; optional LLM reserved."""
        context_lower = context.lower()

        # Deadlines often contain explicit obligation words.
        if "deadline" in candidates and any(
            w in context_lower for w in ("must", "deadline", "due", "vacate", "respond")
        ):
            return "deadline"

        # A lease context strongly favors effective dates.
        if "effective" in candidates and ("lease" in context_lower or "tenant" in context_lower):
            return "effective"

        # Court/summons contexts favor hearing/deadline dates.
        if "deadline" in candidates and any(
            w in context_lower for w in ("court", "hearing", "summons")
        ):
            return "deadline"

        # Notices are usually issued dates.
        if "notice" in context_lower and "issued" in candidates:
            return "issued"

        # Without a stronger signal, keep the rule-based best guess.
        return None


