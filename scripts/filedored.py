"""
filedored_semptify_folder_and_filer.py
Version: 1.0.0
Purpose: Semptify Vault Post‑Processing + AI Classification (SWE 1.6 compatible)
Tier: DEV (safe, optional)
"""

import hashlib
import os
import shutil
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
HASH_ALGO = "sha256"


# -----------------------------
# UTILITIES
# -----------------------------

def ensure_dir(base: Path, rel: str) -> Path:
    """Create folder if missing."""
    target = base / rel
    target.mkdir(parents=True, exist_ok=True)
    return target


def file_hash(path: Path, algo: str = HASH_ALGO) -> str:
    """Compute SHA‑256 hash."""
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# -----------------------------
# AI CLASSIFICATION HOOK
# -----------------------------

def ai_classify_document(path: Path) -> str:
    """
    AI classification hook.
    SWE 1.6 or any local model can call this function.

    Expected return values:
        "lease"
        "notice"
        "evidence"
        "photo"
        "invoice"
        "communication"
        "unknown"

    This is a placeholder — SWE 1.6 will override this.
    """
    # Default fallback
    return "unknown"


def ai_route(base: Path, file_path: Path, label: str) -> Path:
    """Route AI‑classified files into AI folder."""
    target = ensure_dir(base, f"{AI_FOLDER}/{label}")
    return target / file_path.name


# -----------------------------
# MAIN VAULT POST‑PROCESSOR
# -----------------------------

def filedored_run(root_path: str, enable_ai: bool = True) -> dict:
    """
    Main vault post‑processing engine.
    - Sorts documents
    - Deduplicates
    - AI‑classifies (optional)
    """

    root = Path(root_path)
    if not root.exists():
        return {"error": "Root path does not exist"}

    seen = {}
    moved = []
    duplicates = []
    ai_sorted = []

    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            src = Path(dirpath) / name
            rel = src.relative_to(root)

            # Skip internal folders
            if rel.parts[0] in (DUPLICATES_FOLDER, OTHER_FOLDER, AI_FOLDER):
                continue

            ext = src.suffix.lower().lstrip(".")
            h = file_hash(src)

            # Duplicate detection
            if h in seen:
                dup_dir = ensure_dir(root, DUPLICATES_FOLDER)
                dst = dup_dir / name
                shutil.move(str(src), str(dst))
                duplicates.append(str(dst))
                continue
            else:
                seen[h] = src

            # AI classification (optional)
            if enable_ai:
                label = ai_classify_document(src)
                if label != "unknown":
                    dst = ai_route(root, src, label)
                    shutil.move(str(src), str(dst))
                    ai_sorted.append(str(dst))
                    continue

            # Extension‑based routing
            if ext in DOCUMENT_EXTENSIONS:
                target_rel = DOCUMENT_EXTENSIONS[ext]
            else:
                target_rel = OTHER_FOLDER

            target_dir = ensure_dir(root, target_rel)
            dst = target_dir / name
            shutil.move(str(src), str(dst))
            moved.append(str(dst))

    return {
        "sorted": moved,
        "duplicates": duplicates,
        "ai_classified": ai_sorted,
        "status": "complete"
    }


# -----------------------------
# CLI ENTRY (optional)
# -----------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Semptify Vault Post‑Processor")
    parser.add_argument("root", help="Path to vault folder")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI classification")

    args = parser.parse_args()

    result = filedored_run(args.root, enable_ai=not args.no_ai)
    print(result)
