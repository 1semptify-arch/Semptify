"""Pass 0 — layout segmentation for overlay-first intake.

Spec: handoffs/overlay-first-intake-spec-2026-09-20.md (decisions locked:
fixed pass cap of 3, low-confidence regions flagged for manual review).

Rule-based only — no AI/ML, consistent with the locked OCR path
(ADR-0007 own-engine constraint). Segmentation runs over the already-
extracted structure: word boxes for scans, paragraph blocks for text-layer
docs. Regions are ranked by field-relevance confidence and processed in
passes — high-confidence regions first, then progressively looser, up to
the fixed cap. Anything left unattributed is flagged for manual review.

Regions are derived artifacts of the intake overlay — the original vault
document is never touched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.id_gen import make_id

__all__ = [
    "PASS_CAP",
    "Region",
    "segment",
    "rank_regions",
    "mark_region_resolved",
    "finalize_region_status",
]

PASS_CAP = 3

_STATUS_PENDING = "pending"
_STATUS_RESOLVED = "resolved"
_STATUS_NO_DATA = "no_data"
_STATUS_MANUAL_REVIEW = "manual_review"

# Confidence thresholds for pass assignment. Pass 1 gets the regions that
# clearly carry checklist data; each later pass accepts weaker signal.
_PASS_THRESHOLDS = (0.5, 0.2, 0.0)

_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2})\b",
    re.IGNORECASE,
)
_CURRENCY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?", re.IGNORECASE)


@dataclass
class Region:
    """One candidate data region on the document's overlay copy."""

    region_id: str
    label: str
    text: str
    confidence: float = 0.0
    pass_number: int = 1
    status: str = _STATUS_PENDING
    field_names: list[str] = field(default_factory=list)
    page: int | None = None
    bbox: dict | None = None            # {left, top, width, height} — scans
    char_span: tuple[int, int] | None = None  # into full text — text-layer docs
    word_indices: list[int] = field(default_factory=list)  # into word_boxes — scans

    def to_dict(self) -> dict:
        return {
            "region_id": self.region_id,
            "label": self.label,
            "confidence": round(self.confidence, 3),
            "pass_number": self.pass_number,
            "status": self.status,
            "field_names": self.field_names,
            "page": self.page,
            "bbox": self.bbox,
            "char_span": list(self.char_span) if self.char_span else None,
            "preview": self.text[:80],
        }


# ---------------------------------------------------------------------------
# Segmentation — word-box clustering for scans, paragraph blocks for text
# ---------------------------------------------------------------------------


def _cluster_word_boxes(word_boxes: list) -> list[Region]:
    """Group word boxes into lines, then merge lines into block regions."""
    if not word_boxes:
        return []

    pages: dict[int, list[tuple[int, object]]] = {}
    for i, wb in enumerate(word_boxes):
        pages.setdefault(wb.page or 0, []).append((i, wb))

    regions: list[Region] = []
    for page, entries in sorted(pages.items()):
        entries.sort(key=lambda e: (e[1].top, e[1].left))
        median_h = sorted(e[1].height for e in entries if e[1].height > 0)
        line_h = median_h[len(median_h) // 2] if median_h else 12

        # Lines: same row when vertical centers sit within half a line height.
        lines: list[list[tuple[int, object]]] = []
        for entry in entries:
            wb = entry[1]
            center = wb.top + wb.height / 2
            placed = False
            for line in lines:
                l_center = sum(w.top + w.height / 2 for _, w in line) / len(line)
                if abs(center - l_center) <= max(line_h * 0.6, 4):
                    line.append(entry)
                    placed = True
                    break
            if not placed:
                lines.append([entry])
        lines.sort(key=lambda line: min(w.top for _, w in line))

        # Blocks: merge consecutive lines while the vertical gap is small.
        blocks: list[list[tuple[int, object]]] = []
        prev_bottom = None
        for line in lines:
            top = min(w.top for _, w in line)
            bottom = max(w.top + w.height for _, w in line)
            if prev_bottom is not None and top - prev_bottom > line_h * 1.8:
                blocks.append([])
            if not blocks:
                blocks.append([])
            blocks[-1].extend(line)
            prev_bottom = bottom

        for n, block in enumerate(blocks, 1):
            block.sort(key=lambda e: (e[1].top, e[1].left))
            left = min(w.left for _, w in block)
            top = min(w.top for _, w in block)
            right = max(w.left + w.width for _, w in block)
            bottom = max(w.top + w.height for _, w in block)
            regions.append(
                Region(
                    region_id=make_id("reg"),
                    label=f"page {page + 1} · block {n}",
                    text=" ".join(w.text for _, w in block if w.text),
                    page=page,
                    bbox={
                        "left": left,
                        "top": top,
                        "width": right - left,
                        "height": bottom - top,
                    },
                    word_indices=[i for i, _ in block],
                )
            )
    return regions


def _split_text_blocks(text: str) -> list[Region]:
    """Paragraph-block segmentation for text-layer documents."""
    regions: list[Region] = []
    pos = 0
    n = 0
    for chunk in re.split(r"\n\s*\n", text):
        start = text.find(chunk, pos)
        if start < 0:
            continue
        pos = start + len(chunk)
        if not chunk.strip():
            continue
        n += 1
        regions.append(
            Region(
                region_id=make_id("reg"),
                label=f"block {n}",
                text=chunk.strip(),
                char_span=(start, start + len(chunk)),
            )
        )
    if not regions and text.strip():
        regions.append(
            Region(
                region_id=make_id("reg"),
                label="block 1",
                text=text.strip(),
                char_span=(0, len(text)),
            )
        )
    return regions


def segment(text: str, word_boxes: list | None, has_text_layer: bool) -> list[Region]:
    """Segment extracted content into candidate data regions."""
    if word_boxes:
        return _cluster_word_boxes(word_boxes)
    return _split_text_blocks(text)


# ---------------------------------------------------------------------------
# Ranking + pass assignment — high-confidence regions first, fixed cap
# ---------------------------------------------------------------------------


def _region_confidence(region: Region, keywords: set[str]) -> float:
    hay = region.text.lower()
    hits = sum(1 for kw in keywords if kw in hay)
    hits += len(_DATE_RE.findall(region.text))
    hits += len(_CURRENCY_RE.findall(region.text))
    # Blend in mean word-box confidence when present via caller — here the
    # signal is field-relevance density only. "Keyword + its value in one
    # region" (2 hits) is already a confident data region.
    return min(1.0, hits / 3.0)


def rank_regions(regions: list[Region], doc_type_def: dict, pass_cap: int = PASS_CAP) -> None:
    """Score regions and assign pass numbers in place."""
    keywords: set[str] = set()
    for fdef in doc_type_def.get("fields", []):
        for kw in re.split(r"[,/]", fdef.get("ocr_target", "").lower()):
            kw = kw.strip()
            if len(kw) >= 3:
                keywords.add(kw)

    for r in regions:
        r.confidence = _region_confidence(r, keywords)
        # First threshold the region clears is its pass — high-confidence
        # regions process in pass 1, weaker signal waits for a later pass.
        r.pass_number = pass_cap
        for i, threshold in enumerate(_PASS_THRESHOLDS[:pass_cap], 1):
            if r.confidence >= threshold:
                r.pass_number = i
                break


def mark_region_resolved(region: Region, field_name: str) -> None:
    if field_name not in region.field_names:
        region.field_names.append(field_name)
    region.status = _STATUS_RESOLVED


def finalize_region_status(regions: list[Region]) -> None:
    """Settle every region still pending after the pass cap.

    A region that signaled field-relevant content but produced no proposal
    is the spec's "unresolved low-confidence region" — flagged for manual
    review (Brad's call). A region with zero signal was never a candidate
    data region — it settles as no_data, not a flag: flagging plain prose
    would train tenants to ignore the flag that matters.
    """
    for r in regions:
        if r.status == _STATUS_PENDING:
            r.status = _STATUS_MANUAL_REVIEW if r.confidence > 0 else _STATUS_NO_DATA
