"""Local keyword-based document classifier for filedored AI sorting.

A deterministic, zero-dependency classifier used as the local-model fallback for
`app.services.filedored_service.ai_classify_document()`. It returns one of the
canonical `AI_CLASSIFICATION_MAP` labels:

    lease, notice, evidence, photo, invoice, communication, unknown

The classifier scores documents by matching keywords against the filename and a
small sample of extracted text. It is intentionally simple and fast so it can run
synchronously during upload post-processing without requiring cloud calls or
heavy model inference.
"""

import io
import logging

logger = logging.getLogger(__name__)

MAX_CONTENT_SAMPLE = 8000

_FILENAME_KEYWORDS: dict[str, list[str]] = {
    "lease": ["lease", "rental agreement", "tenancy agreement"],
    "notice": [
        "notice",
        "notice to quit",
        "notice to vacate",
        "eviction notice",
        "14-day",
        "30-day",
        "rent increase",
        "late fee",
    ],
    "invoice": ["invoice", "bill", "receipt", "payment", "ledger", "deposit"],
    "communication": [
        "email",
        "letter",
        "message",
        "text",
        "correspondence",
    ],
    "evidence": [
        "repair",
        "maintenance",
        "inspection",
        "violation",
        "evidence",
        "complaint",
    ],
    "photo": [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        "photo",
        "image",
        "picture",
        "screenshot",
    ],
}

_CONTENT_KEYWORDS: dict[str, list[str]] = {
    "lease": [
        "lease agreement",
        "rental agreement",
        "landlord and tenant",
        "term of lease",
        "leased premises",
        "monthly rent",
    ],
    "notice": [
        "notice to quit",
        "notice to vacate",
        "notice to pay rent",
        "eviction notice",
        "you must vacate",
        "termination of tenancy",
        "rent is due",
        "late fee",
    ],
    "invoice": [
        "invoice",
        "amount due",
        "payment received",
        "rent receipt",
        "total due",
        "balance due",
        "please pay",
        "invoice number",
    ],
    "communication": [
        "dear",
        "sincerely",
        "regards",
        "email from",
        "subject:",
        "to:",
        "from:",
        "cc:",
    ],
    "evidence": [
        "repair request",
        "maintenance request",
        "inspection report",
        "housing inspector",
        "code violation",
        "unsafe",
        "habitability",
        "damage",
        "mold",
        "leak",
        "broken",
    ],
    "photo": [],
}

_LABEL_ORDER = ("lease", "notice", "invoice", "communication", "evidence", "photo")


def _decode_text(content: bytes) -> str:
    """Decode text-ish bytes; return empty string if content is not text."""
    if not content:
        return ""

    # Fast path: content is entirely printable ASCII / common whitespace.
    if all(byte >= 0x09 and byte <= 0x7E or byte in (0x0A, 0x0D) for byte in content[:512]):
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return content.decode(encoding)[:MAX_CONTENT_SAMPLE]
            except UnicodeDecodeError:
                continue
    return ""


def _extract_text_sample(content: bytes, filename: str) -> str:
    """Return a small text sample from binary content, best effort."""
    if not content:
        return ""

    lower_name = filename.lower()

    # PDFs: try to extract text with PyPDF2 when available.
    if lower_name.endswith(".pdf"):
        try:
            import PyPDF2

            reader = PyPDF2.PdfReader(io.BytesIO(content))
            parts: list[str] = []
            for page in reader.pages[:3]:
                text = page.extract_text() or ""
                if text:
                    parts.append(text)
                if len("".join(parts)) >= MAX_CONTENT_SAMPLE:
                    break
            extracted = "\n\n".join(parts)[:MAX_CONTENT_SAMPLE]
            if extracted:
                return extracted
        except Exception as exc:
            logger.debug("PyPDF2 extraction failed for local classifier: %s", exc)
        # Fall back to decoding the bytes as plain text (useful for test fixtures
        # and malformed/non-PDF inputs).
        return _decode_text(content)

    # Plain text / common text-based formats: decode directly.
    if lower_name.endswith((".txt", ".md", ".rtf", ".csv", ".json", ".xml", ".html", ".htm")):
        return _decode_text(content)

    # Unknown binary: only decode if it looks like text.
    return _decode_text(content)


def _score_against(text: str, keywords: list[str]) -> int:
    """Count keyword matches in a lowercased text string."""
    if not text or not keywords:
        return 0
    score = 0
    for keyword in keywords:
        score += text.count(keyword)
    return score


def _score_document(content: bytes | None, filename: str) -> dict[str, int]:
    """Return the raw keyword scores for a document."""
    if not filename:
        return dict.fromkeys(_LABEL_ORDER, 0)

    filename_lower = filename.lower()
    sample = _extract_text_sample(content or b"", filename).lower()

    scores: dict[str, int] = dict.fromkeys(_LABEL_ORDER, 0)
    for label in _LABEL_ORDER:
        filename_score = _score_against(filename_lower, _FILENAME_KEYWORDS[label])
        content_score = _score_against(sample, _CONTENT_KEYWORDS[label])
        # Filename matches are weighted more heavily because filenames are
        # usually intentionally descriptive.
        scores[label] = filename_score * 2 + content_score

    return scores


def predict(content: bytes | None, filename: str) -> str:
    """
    Predict a filedored AI label for a document using filename and content.

    Args:
        content: Raw file bytes (may be None).
        filename: Original filename.

    Returns:
        One of: lease, notice, evidence, photo, invoice, communication, unknown.
    """
    scores = _score_document(content, filename)
    best_label = max(_LABEL_ORDER, key=lambda label: scores[label])
    if scores[best_label] > 0:
        return best_label
    return "unknown"


def predict_with_confidence(content: bytes | None, filename: str) -> tuple[str, float]:
    """
    Predict a label and return a confidence score.

    Confidence is derived from the gap between the best and runner-up scores,
    scaled so that a single weak match is not reported with unwarranted certainty.

    Returns:
        (label, confidence) where confidence is in [0.0, 0.99].
    """
    scores = _score_document(content, filename)
    best_label = max(_LABEL_ORDER, key=lambda label: scores[label])
    best_score = scores[best_label]

    if best_score <= 0:
        return "unknown", 0.0

    runner_up = max(scores[label] for label in _LABEL_ORDER if label != best_label)
    confidence = (best_score - runner_up) / (best_score + 1.0)
    return best_label, round(max(0.0, min(0.99, confidence)), 2)
