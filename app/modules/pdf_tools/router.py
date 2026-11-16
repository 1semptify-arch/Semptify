"""
PDF Tools Router - Read, View, and Extract pages from PDFs
"""

# Migrated from app/routers/pdf_tools.py into the pdf_tools SDK module.
# All imports remain absolute since pdf_tools is a CORE module.
import base64
import io
import logging
import os
import re
from collections import OrderedDict

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.core.security import green_access, rate_limit_dependency
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

# Every endpoint requires an authenticated app user (green: valid signed
# cookie). These were previously unauthenticated — a public CPU+memory
# exhaustion surface (unbounded cache, CPU-bound PyMuPDF work).
router = APIRouter(
    prefix="/api/pdf",
    tags=["PDF Tools"],
    dependencies=[Depends(green_access)],
)

# Server-side bounds
MAX_PDF_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB per uploaded PDF
MAX_MERGE_FILES = 10
MAX_MERGE_TOTAL_BYTES = 100 * 1024 * 1024  # 100 MB across a merge batch
MIN_ZOOM, MAX_ZOOM = 0.25, 4.0
MIN_THUMB_WIDTH, MAX_THUMB_WIDTH = 32, 1024
MAX_PAGES_PER_SPLIT = 500
PDF_CACHE_TTL_SECONDS = 3600
PDF_CACHE_MAX_ENTRIES = 20
PDF_CACHE_MAX_BYTES = 150 * 1024 * 1024

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str | None, fallback: str = "document.pdf") -> str:
    """Reduce a user-supplied filename to something safe for headers/disk."""
    stem = os.path.basename(name or "")
    stem = _SAFE_FILENAME_RE.sub("_", stem).strip("._-")
    return stem[:200] or fallback


# Store uploaded PDFs temporarily — bounded LRU with TTL. Entries expire
# after PDF_CACHE_TTL_SECONDS and the whole cache is capped by entry count
# and total bytes, so uploads can't grow memory without limit.
pdf_cache: OrderedDict[str, dict] = OrderedDict()


def _cache_prune() -> None:
    """Drop expired entries, then evict oldest until within caps."""
    now = utc_now()
    expired = [
        pid for pid, entry in pdf_cache.items() if (now - entry["stored_at"]).total_seconds() > PDF_CACHE_TTL_SECONDS
    ]
    for pid in expired:
        pdf_cache.pop(pid, None)
    total = sum(len(entry["content"]) for entry in pdf_cache.values())
    while pdf_cache and (len(pdf_cache) > PDF_CACHE_MAX_ENTRIES or total > PDF_CACHE_MAX_BYTES):
        _, evicted = pdf_cache.popitem(last=False)
        total -= len(evicted["content"])


def _cache_put(pdf_id: str, entry: dict) -> None:
    entry["stored_at"] = utc_now()
    pdf_cache[pdf_id] = entry
    _cache_prune()


def _cache_get(pdf_id: str) -> dict | None:
    entry = pdf_cache.get(pdf_id)
    if entry is None:
        return None
    if (utc_now() - entry["stored_at"]).total_seconds() > PDF_CACHE_TTL_SECONDS:
        pdf_cache.pop(pdf_id, None)
        return None
    pdf_cache.move_to_end(pdf_id)
    return entry


def _require_cached(pdf_id: str) -> dict:
    pdf_data = _cache_get(pdf_id)
    if pdf_data is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    return pdf_data


def _check_upload_size(file: UploadFile, content: bytes) -> None:
    """Reject oversized uploads — checked on declared size and actual bytes."""
    declared = file.size if file.size is not None else 0
    if declared > MAX_PDF_UPLOAD_BYTES or len(content) > MAX_PDF_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF too large — limit is 25MB")


@router.get("/test")
async def test_pdf_tools():
    """Test endpoint to verify PDF tools are working."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")
    return {"status": "PDF tools available", "pymupdf_version": fitz.__version__}


@router.post(
    "/upload",
    dependencies=[Depends(rate_limit_dependency("pdf-upload", window=60, max_requests=10))],
)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file for processing"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")
    filename = _safe_filename(file.filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    content = await file.read()
    _check_upload_size(file, content)

    try:
        # Open and validate PDF
        doc = fitz.open(stream=content, filetype="pdf")
        page_count = len(doc)

        # Generate unique ID
        pdf_id = f"pdf_{utc_now().strftime('%Y%m%d_%H%M%S')}_{hash(content) & 0xFFFFFF:06x}"

        # Store in cache
        _cache_put(
            pdf_id,
            {
                "filename": filename,
                "content": content,
                "page_count": page_count,
                "uploaded_at": utc_now().isoformat(),
            },
        )

        # Get metadata
        metadata = doc.metadata
        doc.close()

        return {
            "success": True,
            "pdf_id": pdf_id,
            "filename": file.filename,
            "page_count": page_count,
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
            },
        }
    except Exception:
        logger.exception("Invalid PDF file")
        raise HTTPException(status_code=400, detail="Invalid PDF file")


@router.get("/info/{pdf_id}")
async def get_pdf_info(pdf_id: str):
    """Get information about an uploaded PDF"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    pdf_data = _require_cached(pdf_id)
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")

    pages_info = []
    for i, page in enumerate(doc):
        rect = page.rect
        pages_info.append({"page_number": i + 1, "width": rect.width, "height": rect.height, "rotation": page.rotation})

    doc.close()

    return {
        "pdf_id": pdf_id,
        "filename": pdf_data["filename"],
        "page_count": pdf_data["page_count"],
        "uploaded_at": pdf_data["uploaded_at"],
        "pages": pages_info,
    }


@router.get("/page/{pdf_id}/{page_num}")
async def get_page_image(pdf_id: str, page_num: int, zoom: float = Query(1.5, ge=MIN_ZOOM, le=MAX_ZOOM)):
    """Get a page as an image (PNG)"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    pdf_data = _require_cached(pdf_id)
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")

    if page_num < 1 or page_num > len(doc):
        doc.close()
        raise HTTPException(status_code=400, detail=f"Invalid page number. PDF has {len(doc)} pages.")

    page = doc[page_num - 1]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_bytes = pix.tobytes("png")
    doc.close()

    return StreamingResponse(
        io.BytesIO(img_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=page_{page_num}.png"},
    )


@router.get("/page-base64/{pdf_id}/{page_num}")
async def get_page_base64(pdf_id: str, page_num: int, zoom: float = Query(1.5, ge=MIN_ZOOM, le=MAX_ZOOM)):
    """Get a page as base64-encoded PNG"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    pdf_data = _require_cached(pdf_id)
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")

    if page_num < 1 or page_num > len(doc):
        doc.close()
        raise HTTPException(status_code=400, detail=f"Invalid page number. PDF has {len(doc)} pages.")

    page = doc[page_num - 1]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_bytes = pix.tobytes("png")
    base64_img = base64.b64encode(img_bytes).decode("utf-8")
    doc.close()

    return {"page_number": page_num, "image": f"data:image/png;base64,{base64_img}"}


@router.get("/text/{pdf_id}/{page_num}")
async def get_page_text(pdf_id: str, page_num: int):
    """Extract text from a specific page"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    pdf_data = _require_cached(pdf_id)
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")

    if page_num < 1 or page_num > len(doc):
        doc.close()
        raise HTTPException(status_code=400, detail=f"Invalid page number. PDF has {len(doc)} pages.")

    page = doc[page_num - 1]
    text = page.get_text()
    doc.close()

    return {"page_number": page_num, "text": text}


@router.get("/text-all/{pdf_id}")
async def get_all_text(pdf_id: str):
    """Extract text from all pages"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    pdf_data = _require_cached(pdf_id)
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")

    pages_text = []
    for i, page in enumerate(doc):
        pages_text.append({"page_number": i + 1, "text": page.get_text()})

    doc.close()

    return {"pdf_id": pdf_id, "filename": pdf_data["filename"], "pages": pages_text}


@router.post("/extract")
async def extract_pages(
    pdf_id: str = Form(...),
    pages: str = Form(...),  # Comma-separated page numbers or ranges like "1,3,5-8"
):
    """Extract specific pages into a new PDF"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    pdf_data = _require_cached(pdf_id)

    # Parse page selection
    page_numbers = parse_page_selection(pages, pdf_data["page_count"])

    if not page_numbers:
        raise HTTPException(status_code=400, detail="No valid pages selected")

    # Create new PDF with selected pages
    src_doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    new_doc = fitz.open()

    for page_num in page_numbers:
        new_doc.insert_pdf(src_doc, from_page=page_num - 1, to_page=page_num - 1)

    # Save to bytes
    output = io.BytesIO()
    new_doc.save(output)
    output.seek(0)

    new_doc.close()
    src_doc.close()

    # Generate filename — sanitize; both inputs are user-controlled and this
    # string lands in a Content-Disposition header.
    original_name = os.path.splitext(_safe_filename(pdf_data["filename"]))[0]
    safe_pages = re.sub(r"[^0-9-]", "-", pages).strip("-")[:50]
    new_filename = f"{original_name}_pages_{safe_pages}.pdf"

    return StreamingResponse(
        output, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={new_filename}"}
    )


@router.post("/extract-base64")
async def extract_pages_base64(pdf_id: str = Form(...), pages: str = Form(...)):
    """Extract specific pages and return as base64"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    pdf_data = _require_cached(pdf_id)

    # Parse page selection
    page_numbers = parse_page_selection(pages, pdf_data["page_count"])

    if not page_numbers:
        raise HTTPException(status_code=400, detail="No valid pages selected")

    # Create new PDF with selected pages
    src_doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    new_doc = fitz.open()

    for page_num in page_numbers:
        new_doc.insert_pdf(src_doc, from_page=page_num - 1, to_page=page_num - 1)

    # Save to bytes
    pdf_bytes = new_doc.tobytes()
    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    new_doc.close()
    src_doc.close()

    original_name = os.path.splitext(_safe_filename(pdf_data["filename"]))[0]
    safe_pages = re.sub(r"[^0-9-]", "-", pages).strip("-")[:50]
    new_filename = f"{original_name}_pages_{safe_pages}.pdf"

    return {
        "filename": new_filename,
        "page_count": len(page_numbers),
        "extracted_pages": page_numbers,
        "pdf_base64": f"data:application/pdf;base64,{base64_pdf}",
    }


@router.delete("/{pdf_id}")
async def delete_pdf(pdf_id: str):
    """Remove a PDF from cache"""
    if _cache_get(pdf_id) is None:
        raise HTTPException(status_code=404, detail="PDF not found")

    del pdf_cache[pdf_id]
    return {"success": True, "message": "PDF removed from cache"}


@router.get("/thumbnails/{pdf_id}")
async def get_thumbnails(pdf_id: str, max_width: int = Query(150, ge=MIN_THUMB_WIDTH, le=MAX_THUMB_WIDTH)):
    """Get thumbnails of all pages"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    pdf_data = _require_cached(pdf_id)
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")

    thumbnails = []
    for i, page in enumerate(doc):
        # Calculate zoom to fit max_width
        rect = page.rect
        zoom = max_width / rect.width
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img_bytes = pix.tobytes("png")
        base64_img = base64.b64encode(img_bytes).decode("utf-8")

        thumbnails.append(
            {
                "page_number": i + 1,
                "width": pix.width,
                "height": pix.height,
                "thumbnail": f"data:image/png;base64,{base64_img}",
            }
        )

    doc.close()

    return {"pdf_id": pdf_id, "filename": pdf_data["filename"], "thumbnails": thumbnails}


def parse_page_selection(selection: str, max_pages: int) -> list[int]:
    """Parse page selection string like '1,3,5-8,10' into list of page numbers"""
    pages = set()
    parts = selection.replace(" ", "").split(",")

    for part in parts:
        if "-" in part:
            # Range like "5-8"
            try:
                start, end = part.split("-")
                start = int(start)
                end = int(end)
                for p in range(max(1, start), min(max_pages, end) + 1):
                    pages.add(p)
            except Exception:
                continue
        else:
            # Single page
            try:
                p = int(part)
                if 1 <= p <= max_pages:
                    pages.add(p)
            except Exception:
                continue

    return sorted(pages)


@router.post("/split")
async def split_pdf(pdf_id: str = Form(...), pages_per_file: int = Form(default=1)):
    """Split PDF into multiple files"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")
    if pages_per_file < 1 or pages_per_file > MAX_PAGES_PER_SPLIT:
        raise HTTPException(status_code=400, detail=f"pages_per_file must be 1-{MAX_PAGES_PER_SPLIT}")

    pdf_data = _require_cached(pdf_id)
    src_doc = fitz.open(stream=pdf_data["content"], filetype="pdf")

    total_pages = len(src_doc)
    original_name = os.path.splitext(_safe_filename(pdf_data["filename"]))[0]

    splits = []
    for start in range(0, total_pages, pages_per_file):
        end = min(start + pages_per_file, total_pages)

        new_doc = fitz.open()
        new_doc.insert_pdf(src_doc, from_page=start, to_page=end - 1)

        pdf_bytes = new_doc.tobytes()
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        splits.append(
            {
                "filename": f"{original_name}_part_{start + 1}-{end}.pdf",
                "start_page": start + 1,
                "end_page": end,
                "page_count": end - start,
                "pdf_base64": f"data:application/pdf;base64,{base64_pdf}",
            }
        )

        new_doc.close()

    src_doc.close()

    return {
        "original_filename": pdf_data["filename"],
        "total_pages": total_pages,
        "split_count": len(splits),
        "files": splits,
    }


@router.post(
    "/merge",
    dependencies=[Depends(rate_limit_dependency("pdf-merge", window=60, max_requests=10))],
)
async def merge_pdfs(files: list[UploadFile] = File(...)):
    """Merge multiple PDFs into one"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 PDFs to merge")
    if len(files) > MAX_MERGE_FILES:
        raise HTTPException(status_code=400, detail=f"Too many files — limit is {MAX_MERGE_FILES} per merge")

    merged_doc = fitz.open()
    total_bytes = 0

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue

        content = await file.read()
        _check_upload_size(file, content)
        total_bytes += len(content)
        if total_bytes > MAX_MERGE_TOTAL_BYTES:
            merged_doc.close()
            raise HTTPException(status_code=413, detail="Merge batch too large — limit is 100MB total")
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            merged_doc.insert_pdf(doc)
            doc.close()
        except Exception:
            continue

    if len(merged_doc) == 0:
        merged_doc.close()
        raise HTTPException(status_code=400, detail="No valid PDFs to merge")

    merged_page_count = len(merged_doc)
    pdf_bytes = merged_doc.tobytes()
    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    merged_doc.close()

    return {
        "filename": "merged.pdf",
        "page_count": merged_page_count,
        "pdf_base64": f"data:application/pdf;base64,{base64_pdf}",
    }


@router.post("/rotate")
async def rotate_pages(
    pdf_id: str = Form(...),
    pages: str = Form(...),
    rotation: int = Form(...),  # 90, 180, 270, or -90
):
    """Rotate specific pages"""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    if rotation not in [90, 180, 270, -90]:
        raise HTTPException(status_code=400, detail="Rotation must be 90, 180, 270, or -90")

    pdf_data = _require_cached(pdf_id)
    page_numbers = parse_page_selection(pages, pdf_data["page_count"])

    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")

    for page_num in page_numbers:
        page = doc[page_num - 1]
        page.set_rotation((page.rotation + rotation) % 360)

    pdf_bytes = doc.tobytes()
    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    # Update cache
    pdf_cache[pdf_id]["content"] = pdf_bytes
    pdf_cache[pdf_id]["stored_at"] = utc_now()

    doc.close()

    return {
        "success": True,
        "rotated_pages": page_numbers,
        "rotation": rotation,
        "pdf_base64": f"data:application/pdf;base64,{base64_pdf}",
    }
