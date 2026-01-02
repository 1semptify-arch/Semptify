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

import os
import logging
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.modules.document_converter import (
    DocumentConverter,
    DocumentMetadata,
    DocumentStyle,
    markdown_to_docx,
    markdown_to_html,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/convert", tags=["Document Converter"])

# Output directory for converted files
CONVERT_OUTPUT_DIR = Path("data/converted_documents")
CONVERT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# REQUEST MODELS
# =============================================================================

class ConvertRequest(BaseModel):
    """Request model for text conversion"""
    markdown_text: str
    title: Optional[str] = None
    case_number: Optional[str] = None
    court: Optional[str] = None
    parties: Optional[str] = None
    author: Optional[str] = None
    style: Optional[str] = "legal_brief"  # legal_brief, court_filing, standard, memo
    linked_documents: Optional[Dict[str, str]] = None
    filename: Optional[str] = None


class ConvertFilePathRequest(BaseModel):
    """Request model for file path conversion"""
    file_path: str
    output_format: str = "both"  # docx, html, both
    title: Optional[str] = None
    case_number: Optional[str] = None
    court: Optional[str] = None
    parties: Optional[str] = None
    style: Optional[str] = "legal_brief"
    linked_documents: Optional[Dict[str, str]] = None


class ConvertResponse(BaseModel):
    """Response model for conversion"""
    success: bool
    message: str
    docx_path: Optional[str] = None
    html_path: Optional[str] = None
    download_url: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_style(style_name: str) -> DocumentStyle:
    """Convert style string to enum"""
    style_map = {
        "legal_brief": DocumentStyle.LEGAL_BRIEF,
        "court_filing": DocumentStyle.COURT_FILING,
        "standard": DocumentStyle.STANDARD,
        "memo": DocumentStyle.MEMO,
    }
    return style_map.get(style_name, DocumentStyle.LEGAL_BRIEF)


def build_metadata(request: ConvertRequest) -> Optional[DocumentMetadata]:
    """Build metadata from request"""
    if any([request.title, request.case_number, request.court, request.parties]):
        return DocumentMetadata(
            title=request.title or "Document",
            case_number=request.case_number,
            court=request.court,
            parties=request.parties,
            author=request.author,
            date=datetime.now().strftime("%B %d, %Y"),
        )
    return None


def generate_filename(request: ConvertRequest) -> str:
    """Generate output filename"""
    if request.filename:
        return request.filename.rsplit('.', 1)[0]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if request.case_number:
        safe_case = request.case_number.replace(' ', '_').replace('/', '_')
        return f"document_{safe_case}_{timestamp}"
    return f"document_{timestamp}"


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/docx", response_model=ConvertResponse)
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
        result_path = converter.convert_text_to_docx(
            request.markdown_text,
            output_path,
            metadata
        )
        
        return ConvertResponse(
            success=True,
            message="Document converted to DOCX successfully",
            docx_path=result_path,
            download_url=f"/api/convert/download/{filename}.docx"
        )
        
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="python-docx package not installed. Run: pip install python-docx"
        )
    except Exception as e:
        logger.error(f"DOCX conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/html", response_model=ConvertResponse)
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
            request.markdown_text,
            output_path,
            metadata,
            request.linked_documents
        )
        
        return ConvertResponse(
            success=True,
            message="Document converted to HTML successfully",
            html_path=result_path,
            download_url=f"/api/convert/download/{filename}.html"
        )
        
    except Exception as e:
        logger.error(f"HTML conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/both", response_model=ConvertResponse)
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
        converter.convert_text_to_html(
            request.markdown_text,
            html_path,
            metadata,
            request.linked_documents
        )
        
        return ConvertResponse(
            success=True,
            message="Document converted to both DOCX and HTML successfully",
            docx_path=docx_path,
            html_path=html_path,
            download_url=f"/api/convert/download/{filename}"
        )
        
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/file")
async def convert_file(
    file: UploadFile = File(...),
    output_format: str = Form("both"),
    title: Optional[str] = Form(None),
    case_number: Optional[str] = Form(None),
    court: Optional[str] = Form(None),
    style: str = Form("legal_brief")
):
    """
    Convert an uploaded markdown file to DOCX and/or HTML
    
    Upload a .md file and get converted documents back.
    """
    if not file.filename.endswith('.md'):
        raise HTTPException(
            status_code=400,
            detail="Only .md (Markdown) files are supported"
        )
    
    try:
        # Read uploaded file
        content = await file.read()
        markdown_text = content.decode('utf-8')
        
        # Build request
        request = ConvertRequest(
            markdown_text=markdown_text,
            title=title,
            case_number=case_number,
            court=court,
            style=style,
            filename=file.filename.rsplit('.', 1)[0]
        )
        
        # Convert based on format
        if output_format == "docx":
            return await convert_to_docx(request)
        elif output_format == "html":
            return await convert_to_html(request)
        else:
            return await convert_to_both(request)
            
    except Exception as e:
        logger.error(f"File conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/path")
async def convert_from_path(request: ConvertFilePathRequest):
    """
    Convert a markdown file from a file path
    
    Useful for converting case documents already in the system.
    """
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(request.file_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
        
        convert_request = ConvertRequest(
            markdown_text=markdown_text,
            title=request.title,
            case_number=request.case_number,
            court=request.court,
            style=request.style,
            linked_documents=request.linked_documents,
            filename=Path(request.file_path).stem
        )
        
        if request.output_format == "docx":
            return await convert_to_docx(convert_request)
        elif request.output_format == "html":
            return await convert_to_html(convert_request)
        else:
            return await convert_to_both(convert_request)
            
    except Exception as e:
        logger.error(f"Path conversion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a converted document
    """
    file_path = CONVERT_OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    if filename.endswith('.docx'):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif filename.endswith('.html'):
        media_type = "text/html"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename
    )


@router.get("/list")
async def list_converted_documents():
    """
    List all converted documents
    """
    documents = []
    
    for file_path in CONVERT_OUTPUT_DIR.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            documents.append({
                "filename": file_path.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "download_url": f"/api/convert/download/{file_path.name}"
            })
    
    return {
        "count": len(documents),
        "documents": sorted(documents, key=lambda x: x["created"], reverse=True)
    }


@router.delete("/cleanup")
async def cleanup_old_documents(days_old: int = Query(7, ge=1, le=365)):
    """
    Clean up converted documents older than specified days
    """
    cutoff = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    deleted = []
    
    for file_path in CONVERT_OUTPUT_DIR.iterdir():
        if file_path.is_file() and file_path.stat().st_mtime < cutoff:
            file_path.unlink()
            deleted.append(file_path.name)
    
    return {
        "deleted_count": len(deleted),
        "deleted_files": deleted
    }
