"""
filedored_semptify_folder_and_filer.py
Version: 5.0.0 (Timeline Enabled)
Purpose: Semptify Vault Post‑Processing
Features:
    - Sorting
    - Deduplication (SHA‑256)
    - AI Classification (SWE 1.6 hook)
    - OCR Extraction (Tesseract / OCRmyPDF)
    - AI‑sorted folders
    - OCR text output
    - Legal category inference (rule + AI hybrid)
    - Timeline event generation (non-destructive)
Tier: DEV (safe, optional)
"""

import hashlib
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

# -----------------------------
# CONFIG — Semptify‑Safe
# -----------------------------

DOCUMENT_EXTENSIONS = {
    "pdf": "Documents/PDF",
    "doc": "Documents/Word",
    "docx": "Documents/Word",
    "txt": "Documents/Text",
    "rtf": "Documents/Text",
    "xls": "Documents/Spreadsheets",
    "xlsx": "Documents/Spreadsheets",
    "ppt": "Documents/Presentations",
    "pptx": "Documents/Presentations",
    "jpg": "Scans/Images",
    "jpeg": "Scans/Images",
    "png": "Scans/Images",
}

DUPLICATES_FOLDER = "__DUPLICATES__"
OTHER_FOLDER = "__OTHER__"
AI_FOLDER = "__AI_CLASSIFIED__"
OCR_FOLDER = "__OCR_TEXT__"
LEGAL_FOLDER = "__LEGAL_CATEGORIES__"
TIMELINE_FOLDER = "__TIMELINE_EVENTS__"

HASH_ALGO = "sha256"

LEGAL_CATEGORIES = [
    "lease",
    "rent_increase",
    "nonpayment_notice",
    "eviction_notice",
    "repair_request",
    "harassment",
    "utilities",
    "fees_and_charges",
    "court_document",
    "communication_general",
    "other",
]


# -----------------------------
# UTILITIES
# -----------------------------


def ensure_dir(base: Path, rel: str) -> Path:
    target = base / rel
    target.mkdir(parents=True, exist_ok=True)
    return target


def file_hash(path: Path, algo: str = HASH_ALGO) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# -----------------------------
# OCR LAYER
# -----------------------------


def ocr_extract_text(path: Path) -> str | None:
    try:
        import pytesseract
        from PIL import Image

        if path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            img = Image.open(path)
            return pytesseract.image_to_string(img)

        if path.suffix.lower() == ".pdf":
            import subprocess

            temp_txt = path.with_suffix(".txt")
            subprocess.run(["ocrmypdf", "--sidecar", str(temp_txt), str(path), str(path)], check=False)
            if temp_txt.exists():
                return temp_txt.read_text(encoding="utf-8", errors="ignore")

    except Exception:
        return None

    return None


def ocr_save(base: Path, file_path: Path, text: str) -> Path:
    ocr_dir = ensure_dir(base, OCR_FOLDER)
    out = ocr_dir / f"{file_path.stem}.txt"
    out.write_text(text, encoding="utf-8", errors="ignore")
    return out


# -----------------------------
# AI CLASSIFICATION HOOK
# -----------------------------


def ai_classify_document(path: Path, ocr_text: str | None = None) -> str:
    return "unknown"


def ai_route(base: Path, file_path: Path, label: str) -> Path:
    target = ensure_dir(base, f"{AI_FOLDER}/{label}")
    return target / file_path.name


# -----------------------------
# LEGAL CATEGORY INFERENCE
# -----------------------------


def infer_legal_category_from_text(text: str) -> str:
    t = text.lower()

    if "lease" in t or "rental agreement" in t:
        return "lease"
    if "rent increase" in t or "increase your rent" in t:
        return "rent_increase"
    if "pay or quit" in t or "nonpayment" in t or "rent due" in t:
        return "nonpayment_notice"
    if "eviction" in t or "unlawful detainer" in t or "notice to vacate" in t:
        return "eviction_notice"
    if "repair" in t or "maintenance" in t or "habitability" in t:
        return "repair_request"
    if "harass" in t or "harassment" in t or "retaliation" in t:
        return "harassment"
    if "utility" in t or "heat" in t or "water" in t or "electric" in t:
        return "utilities"
    if "late fee" in t or "fee" in t or "charge" in t:
        return "fees_and_charges"
    if "court" in t or "case number" in t or "summons" in t or "complaint" in t:
        return "court_document"
    if "text message" in t or "email" in t or "phone" in t or "conversation" in t:
        return "communication_general"

    return "other"


def legal_category_route(base: Path, file_path: Path, category: str) -> Path:
    if category not in LEGAL_CATEGORIES:
        category = "other"
    target = ensure_dir(base, f"{LEGAL_FOLDER}/{category}")
    return target / file_path.name


def infer_and_route_legal_category(
    base: Path, file_path: Path, ocr_text: str | None, ai_label: str | None = None
) -> Path | None:
    if not ocr_text:
        return None

    category = infer_legal_category_from_text(ocr_text)

    mapping = {
        "lease": "lease",
        "notice": "eviction_notice",
        "invoice": "fees_and_charges",
        "communication": "communication_general",
    }
    if ai_label in mapping:
        category = mapping[ai_label]

    dst = legal_category_route(base, file_path, category)
    if file_path != dst:
        shutil.copy2(str(file_path), str(dst))
    return dst


# -----------------------------
# TIMELINE EVENT GENERATION
# -----------------------------


def generate_timeline_event(file_path: Path, category: str, ocr_text: str | None) -> dict:
    """
    Creates a Semptify‑compatible timeline event object.
    Does NOT send it to the API — safe, offline, DEV‑tier.
    """
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "category": category,
        "file_name": file_path.name,
        "file_path": str(file_path),
        "summary": (ocr_text[:300] + "...") if ocr_text else "No OCR text",
        "source": "filedored",
    }


def save_timeline_event(base: Path, event: dict) -> Path:
    """
    Saves timeline event JSON into:
        __TIMELINE_EVENTS__/{timestamp}_{file}.json
    """
    import json

    timeline_dir = ensure_dir(base, TIMELINE_FOLDER)
    safe_name = event["file_name"].replace(" ", "_")
    out = timeline_dir / f"{event['timestamp'].replace(':', '-')}_{safe_name}.json"

    out.write_text(json.dumps(event, indent=2), encoding="utf-8")
    return out


# -----------------------------
# MAIN VAULT POST‑PROCESSOR
# -----------------------------


def filedored_run(
    root_path: str,
    enable_ai: bool = True,
    enable_ocr: bool = True,
    enable_legal_inference: bool = True,
    enable_timeline: bool = True,
) -> dict:

    root = Path(root_path)
    if not root.exists():
        return {"error": "Root path does not exist"}

    seen = {}
    moved = []
    duplicates = []
    ai_sorted = []
    ocr_outputs = []
    legal_routed = []
    timeline_events = []

    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            src = Path(dirpath) / name
            rel = src.relative_to(root)

            if rel.parts[0] in (
                DUPLICATES_FOLDER,
                OTHER_FOLDER,
                AI_FOLDER,
                OCR_FOLDER,
                LEGAL_FOLDER,
                TIMELINE_FOLDER,
            ):
                continue

            ext = src.suffix.lower().lstrip(".")
            h = file_hash(src)

            if h in seen:
                dup_dir = ensure_dir(root, DUPLICATES_FOLDER)
                dst = dup_dir / name
                shutil.move(str(src), str(dst))
                duplicates.append(str(dst))
                continue
            else:
                seen[h] = src

            ocr_text = None
            if enable_ocr:
                ocr_text = ocr_extract_text(src)
                if ocr_text:
                    ocr_out = ocr_save(root, src, ocr_text)
                    ocr_outputs.append(str(ocr_out))

            ai_label = None
            if enable_ai:
                ai_label = ai_classify_document(src, ocr_text=ocr_text)
                if ai_label and ai_label != "unknown":
                    dst = ai_route(root, src, ai_label)
                    shutil.move(str(src), str(dst))
                    ai_sorted.append(str(dst))

                    if enable_legal_inference and (ocr_text or ai_label):
                        legal_dst = infer_and_route_legal_category(root, dst, ocr_text, ai_label)
                        if legal_dst:
                            legal_routed.append(str(legal_dst))

                    if enable_timeline:
                        event = generate_timeline_event(dst, ai_label, ocr_text)
                        timeline_events.append(str(save_timeline_event(root, event)))

                    continue

            target_rel = DOCUMENT_EXTENSIONS.get(ext, OTHER_FOLDER)

            target_dir = ensure_dir(root, target_rel)
            dst = target_dir / name
            shutil.move(str(src), str(dst))
            moved.append(str(dst))

            if enable_legal_inference and (ocr_text or ai_label):
                legal_dst = infer_and_route_legal_category(root, dst, ocr_text, ai_label)
                if legal_dst:
                    legal_routed.append(str(legal_dst))

            if enable_timeline:
                category = ai_label or "sorted_document"
                event = generate_timeline_event(dst, category, ocr_text)
                timeline_events.append(str(save_timeline_event(root, event)))

    return {
        "sorted": moved,
        "duplicates": duplicates,
        "ai_classified": ai_sorted,
        "ocr_text_files": ocr_outputs,
        "legal_category_files": legal_routed,
        "timeline_events": timeline_events,
        "status": "complete",
    }


# -----------------------------
# CLI ENTRY
# -----------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Semptify Vault Post‑Processor (ALL FEATURES + Legal + Timeline)")
    parser.add_argument("root", help="Path to vault folder")
    parser.add_argument("--no-ai", action="store_true")
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--no-legal", action="store_true")
    parser.add_argument("--no-timeline", action="store_true")

    args = parser.parse_args()

    result = filedored_run(
        args.root,
        enable_ai=not args.no_ai,
        enable_ocr=not args.no_ocr,
        enable_legal_inference=not args.no_legal,
        enable_timeline=not args.no_timeline,
    )
    print(result)
