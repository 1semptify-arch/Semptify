"""
Semptify Document Converter API
===============================

REST API for converting Markdown documents to:
- Microsoft Word (.docx)
- Interactive HTML with footnotes

Endpoints:
- POST /api/convert/docx - Convert markdown to DOCX
- POST /api/convert/html - Convert markdown to interactive HTML
- POST /api/convert/both - Convert to both formats
- POST /api/convert/file/{format} - Convert uploaded file
"""
# Migrated from app/routers/document_converter.py into the document_converter SDK module.
# All imports remain absolute since document_converter is a CORE module.

import logging
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.security import green_access, rate_limit_dependency
from app.core.utc import utc_now
from app.modules.document_converter.converter import (
    DOCUMENT_STYLES,
    DocumentConverter,
    DocumentMetadata,
    DocumentStyle,
)

logger = logging.getLogger(__name__)

# All conversion endpoints require an authenticated app user (green: valid
# signed cookie). They were previously unauthenticated — that left /list
# enumerating every converted document and /path reading server files.
router = APIRouter(
    prefix="/api/convert",
    tags=["Document Converter"],
    dependencies=[Depends(green_access)],
)

# Output directory for converted files
CONVERT_OUTPUT_DIR = Path("data/converted_documents")
CONVERT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Server-side bounds — conversion endpoints were unauthenticated with no
# caps, a CPU/disk exhaustion surface.
MAX_MARKDOWN_CHARS = 2_000_000  # ~2 MB of markdown text
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB uploaded .md file
MAX_OUTPUT_BYTES = 25 * 1024 * 1024  # refuse to serve files larger than this

# Repo root — /path conversions are confined inside it so the endpoint can't
# be turned into an arbitrary file read.
_BASE_DIR = Path(__file__).resolve().parents[3]

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_stem(name: str | None) -> str:
    """Reduce a user-supplied filename to a safe stem (no dirs/separators)."""
    stem = Path(name or "document").name.rsplit(".", 1)[0]
    stem = _SAFE_FILENAME_RE.sub("_", stem).strip("._-")
    return stem[:100] or "document"


# =============================================================================
# REQUEST MODELS
# =============================================================================


class ConvertRequest(BaseModel):
    """Request model for text conversion"""

    markdown_text: str = Field(..., max_length=MAX_MARKDOWN_CHARS)
    title: str | None = Field(None, max_length=500)
    case_number: str | None = Field(None, max_length=200)
    court: str | None = Field(None, max_length=500)
    parties: str | None = Field(None, max_length=2000)
    author: str | None = Field(None, max_length=500)
    style: str | None = "legal_brief"  # legal_brief, court_filing, standard, memo
    linked_documents: dict[str, str] | None = None
    filename: str | None = Field(None, max_length=255)


class ConvertFilePathRequest(BaseModel):
    """Request model for file path conversion"""

    file_path: str
    output_format: str = "both"  # docx, html, both
    title: str | None = None
    case_number: str | None = None
    court: str | None = None
    parties: str | None = None
    style: str | None = "legal_brief"
    linked_documents: dict[str, str] | None = None


class ConvertResponse(BaseModel):
    """Response model for conversion"""

    success: bool
    message: str
    docx_path: str | None = None
    html_path: str | None = None
    download_url: str | None = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_style(style_name: str) -> DocumentStyle:
    """Convert style string to DocumentStyle instance"""
    return DOCUMENT_STYLES.get(style_name, DOCUMENT_STYLES["legal_brief"])


def build_metadata(request: ConvertRequest) -> DocumentMetadata | None:
    """Build metadata from request"""
    if any([request.title, request.case_number, request.court, request.parties]):
        return DocumentMetadata(
            title=request.title or "Document",
            case_number=request.case_number,
            court=request.court,
            parties=request.parties,
            author=request.author,
            date=utc_now().strftime("%B %d, %Y"),
        )
    return None


def generate_filename(request: ConvertRequest) -> str:
    """Generate output filename"""
    if request.filename:
        return _safe_stem(request.filename)

    timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
    if request.case_number:
        safe_case = _safe_stem(request.case_number)
        return f"document_{safe_case}_{timestamp}"
    return f"document_{timestamp}"


# =============================================================================
# API ENDPOINTS
# =============================================================================


@router.post(
    "/docx",
    response_model=ConvertResponse,
    dependencies=[Depends(rate_limit_dependency("doc-convert", window=60, max_requests=10))],
)
async def convert_to_docx(request: ConvertRequest):
    """
    Convert markdown text to Microsoft Word (.docx) format

    Preserves:
    - Headers (H1-H6)
    - Bold, italic, strikethrough
    - Bullet and numbered lists
    - Tables
    - Blockquotes
    - Code blocks
    - Footnotes
    """
    try:
        style = get_style(request.style)
        metadata = build_metadata(request)
        filename = generate_filename(request)
        output_path = str(CONVERT_OUTPUT_DIR / f"{filename}.docx")

        converter = DocumentConverter(style)
        result_path = converter.convert_text_to_docx(request.markdown_text, output_path, metadata)

        return ConvertResponse(
            success=True,
            message="Document converted to DOCX successfully",
            docx_path=result_path,
            download_url=f"/api/convert/download/{filename}.docx",
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="python-docx package not installed. Run: pip install python-docx")
    except Exception as e:
        logger.error(f"DOCX conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/html",
    response_model=ConvertResponse,
    dependencies=[Depends(rate_limit_dependency("doc-convert", window=60, max_requests=10))],
)
async def convert_to_html(request: ConvertRequest):
    """
    Convert markdown text to interactive HTML

    Features:
    - Table of contents with smooth scrolling
    - Footnotes with hover popups
    - Document links with icons
    - Legal brief styling
    - Print-friendly formatting
    """
    try:
        style = get_style(request.style)
        metadata = build_metadata(request)
        filename = generate_filename(request)
        output_path = str(CONVERT_OUTPUT_DIR / f"{filename}.html")

        converter = DocumentConverter(style)
        result_path = converter.convert_text_to_html(
            request.markdown_text, output_path, metadata, request.linked_documents
        )

        return ConvertResponse(
            success=True,
            message="Document converted to HTML successfully",
            html_path=result_path,
            download_url=f"/api/convert/download/{filename}.html",
        )

    except Exception as e:
        logger.error(f"HTML conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/both",
    response_model=ConvertResponse,
    dependencies=[Depends(rate_limit_dependency("doc-convert", window=60, max_requests=10))],
)
async def convert_to_both(request: ConvertRequest):
    """
    Convert markdown text to both DOCX and HTML formats
    """
    try:
        style = get_style(request.style)
        metadata = build_metadata(request)
        filename = generate_filename(request)

        converter = DocumentConverter(style)

        # Convert to DOCX
        docx_path = str(CONVERT_OUTPUT_DIR / f"{filename}.docx")
        converter.convert_text_to_docx(request.markdown_text, docx_path, metadata)

        # Reset converter for HTML (footnote counter)
        converter = DocumentConverter(style)

        # Convert to HTML
        html_path = str(CONVERT_OUTPUT_DIR / f"{filename}.html")
        converter.convert_text_to_html(request.markdown_text, html_path, metadata, request.linked_documents)

        return ConvertResponse(
            success=True,
            message="Document converted to both DOCX and HTML successfully",
            docx_path=docx_path,
            html_path=html_path,
            download_url=f"/api/convert/download/{filename}.docx",
        )

    except Exception as e:
        logger.error(f"Conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/file",
    dependencies=[Depends(rate_limit_dependency("doc-convert", window=60, max_requests=10))],
)
async def convert_file(
    file: UploadFile = File(...),
    output_format: str = Form("both"),
    title: str | None = Form(None),
    case_number: str | None = Form(None),
    court: str | None = Form(None),
    style: str = Form("legal_brief"),
):
    """
    Convert an uploaded markdown file to DOCX and/or HTML

    Upload a .md file and get converted documents back.
    """
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md (Markdown) files are supported")

    declared = file.size if file.size is not None else 0
    if declared > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large — limit is {MAX_UPLOAD_BYTES // 1024 // 1024}MB")

    try:
        # Read uploaded file
        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"File too large — limit is {MAX_UPLOAD_BYTES // 1024 // 1024}MB")
        markdown_text = content.decode("utf-8")

        # Build request
        request = ConvertRequest(
            markdown_text=markdown_text,
            title=title,
            case_number=case_number,
            court=court,
            style=style,
            filename=file.filename.rsplit(".", 1)[0],
        )

        # Convert based on format
        if output_format == "docx":
            return await convert_to_docx(request)
        elif output_format == "html":
            return await convert_to_html(request)
        else:
            return await convert_to_both(request)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/path",
    dependencies=[Depends(rate_limit_dependency("doc-convert", window=60, max_requests=10))],
)
async def convert_from_path(request: ConvertFilePathRequest):
    """
    Convert a markdown file from a file path

    Useful for converting case documents already in the system.
    Confined to .md files inside the application directory — previously any
    readable path on the server was accepted.
    """
    resolved = Path(request.file_path).resolve()
    try:
        resolved.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(status_code=403, detail="Path must be inside the application directory")
    if resolved.suffix.lower() != ".md":
        raise HTTPException(status_code=400, detail="Only .md (Markdown) files are supported")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if resolved.stat().st_size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large — limit is {MAX_UPLOAD_BYTES // 1024 // 1024}MB")

    try:
        with open(resolved, encoding="utf-8") as f:
            markdown_text = f.read()

        convert_request = ConvertRequest(
            markdown_text=markdown_text,
            title=request.title,
            case_number=request.case_number,
            court=request.court,
            style=request.style,
            linked_documents=request.linked_documents,
            filename=resolved.stem,
        )

        if request.output_format == "docx":
            return await convert_to_docx(convert_request)
        elif request.output_format == "html":
            return await convert_to_html(convert_request)
        else:
            return await convert_to_both(convert_request)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Path conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a converted document
    """
    # Confine to the output dir — a bare join allowed ../ traversal.
    safe_name = Path(filename).name
    file_path = (CONVERT_OUTPUT_DIR / safe_name).resolve()
    try:
        file_path.relative_to(CONVERT_OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid filename")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if file_path.stat().st_size > MAX_OUTPUT_BYTES:
        raise HTTPException(status_code=413, detail="File too large to download")

    # Determine media type
    if filename.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif filename.endswith(".html"):
        media_type = "text/html"
    else:
        media_type = "application/octet-stream"

    return FileResponse(path=str(file_path), media_type=media_type, filename=filename)


@router.get("/list")
async def list_converted_documents():
    """
    List all converted documents
    """
    documents = []

    for file_path in CONVERT_OUTPUT_DIR.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            documents.append(
                {
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "download_url": f"/api/convert/download/{file_path.name}",
                }
            )

    return {"count": len(documents), "documents": sorted(documents, key=lambda x: x["created"], reverse=True)}


@router.delete("/cleanup")
async def cleanup_old_documents(days_old: int = Query(7, ge=1, le=365)):
    """
    Clean up converted documents older than specified days
    """
    cutoff = utc_now().timestamp() - (days_old * 24 * 60 * 60)
    deleted = []

    for file_path in CONVERT_OUTPUT_DIR.iterdir():
        if file_path.is_file() and file_path.stat().st_mtime < cutoff:
            file_path.unlink()
            deleted.append(file_path.name)

    return {"deleted_count": len(deleted), "deleted_files": deleted}
