"""
PDF Tools Router - Read, View, and Extract pages from PDFs
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional
import fitz  # PyMuPDF
import io
import base64
import os
import tempfile
from datetime import datetime

router = APIRouter(prefix="/api/pdf", tags=["PDF Tools"])

# Store uploaded PDFs temporarily
pdf_cache = {}


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file for processing"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    content = await file.read()
    
    try:
        # Open and validate PDF
        doc = fitz.open(stream=content, filetype="pdf")
        page_count = len(doc)
        
        # Generate unique ID
        pdf_id = f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content) & 0xFFFFFF:06x}"
        
        # Store in cache
        pdf_cache[pdf_id] = {
            "filename": file.filename,
            "content": content,
            "page_count": page_count,
            "uploaded_at": datetime.now().isoformat()
        }
        
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
                "modification_date": metadata.get("modDate", "")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF file: {str(e)}")


@router.get("/info/{pdf_id}")
async def get_pdf_info(pdf_id: str):
    """Get information about an uploaded PDF"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_data = pdf_cache[pdf_id]
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    
    pages_info = []
    for i, page in enumerate(doc):
        rect = page.rect
        pages_info.append({
            "page_number": i + 1,
            "width": rect.width,
            "height": rect.height,
            "rotation": page.rotation
        })
    
    doc.close()
    
    return {
        "pdf_id": pdf_id,
        "filename": pdf_data["filename"],
        "page_count": pdf_data["page_count"],
        "uploaded_at": pdf_data["uploaded_at"],
        "pages": pages_info
    }


@router.get("/page/{pdf_id}/{page_num}")
async def get_page_image(pdf_id: str, page_num: int, zoom: float = 1.5):
    """Get a page as an image (PNG)"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_data = pdf_cache[pdf_id]
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
        headers={"Content-Disposition": f"inline; filename=page_{page_num}.png"}
    )


@router.get("/page-base64/{pdf_id}/{page_num}")
async def get_page_base64(pdf_id: str, page_num: int, zoom: float = 1.5):
    """Get a page as base64-encoded PNG"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_data = pdf_cache[pdf_id]
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    
    if page_num < 1 or page_num > len(doc):
        doc.close()
        raise HTTPException(status_code=400, detail=f"Invalid page number. PDF has {len(doc)} pages.")
    
    page = doc[page_num - 1]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    img_bytes = pix.tobytes("png")
    base64_img = base64.b64encode(img_bytes).decode('utf-8')
    doc.close()
    
    return {
        "page_number": page_num,
        "image": f"data:image/png;base64,{base64_img}"
    }


@router.get("/text/{pdf_id}/{page_num}")
async def get_page_text(pdf_id: str, page_num: int):
    """Extract text from a specific page"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_data = pdf_cache[pdf_id]
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    
    if page_num < 1 or page_num > len(doc):
        doc.close()
        raise HTTPException(status_code=400, detail=f"Invalid page number. PDF has {len(doc)} pages.")
    
    page = doc[page_num - 1]
    text = page.get_text()
    doc.close()
    
    return {
        "page_number": page_num,
        "text": text
    }


@router.get("/text-all/{pdf_id}")
async def get_all_text(pdf_id: str):
    """Extract text from all pages"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_data = pdf_cache[pdf_id]
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    
    pages_text = []
    for i, page in enumerate(doc):
        pages_text.append({
            "page_number": i + 1,
            "text": page.get_text()
        })
    
    doc.close()
    
    return {
        "pdf_id": pdf_id,
        "filename": pdf_data["filename"],
        "pages": pages_text
    }


@router.post("/extract")
async def extract_pages(
    pdf_id: str = Form(...),
    pages: str = Form(...)  # Comma-separated page numbers or ranges like "1,3,5-8"
):
    """Extract specific pages into a new PDF"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_data = pdf_cache[pdf_id]
    
    # Parse page selection
    page_numbers = parse_page_selection(pages, pdf_data["page_count"])
    
    if not page_numbers:
        raise HTTPException(status_code=400, detail="No valid pages selected")
    
    # Create new PDF with selected pages
    src_doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    new_doc = fitz.open()
    
    for page_num in page_numbers:
        new_doc.insert_pdf(src_doc, from_page=page_num-1, to_page=page_num-1)
    
    # Save to bytes
    output = io.BytesIO()
    new_doc.save(output)
    output.seek(0)
    
    new_doc.close()
    src_doc.close()
    
    # Generate filename
    original_name = os.path.splitext(pdf_data["filename"])[0]
    new_filename = f"{original_name}_pages_{pages.replace(',', '-').replace(' ', '')}.pdf"
    
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={new_filename}"}
    )


@router.post("/extract-base64")
async def extract_pages_base64(
    pdf_id: str = Form(...),
    pages: str = Form(...)
):
    """Extract specific pages and return as base64"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_data = pdf_cache[pdf_id]
    
    # Parse page selection
    page_numbers = parse_page_selection(pages, pdf_data["page_count"])
    
    if not page_numbers:
        raise HTTPException(status_code=400, detail="No valid pages selected")
    
    # Create new PDF with selected pages
    src_doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    new_doc = fitz.open()
    
    for page_num in page_numbers:
        new_doc.insert_pdf(src_doc, from_page=page_num-1, to_page=page_num-1)
    
    # Save to bytes
    pdf_bytes = new_doc.tobytes()
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    new_doc.close()
    src_doc.close()
    
    original_name = os.path.splitext(pdf_data["filename"])[0]
    new_filename = f"{original_name}_pages_{pages.replace(',', '-').replace(' ', '')}.pdf"
    
    return {
        "filename": new_filename,
        "page_count": len(page_numbers),
        "extracted_pages": page_numbers,
        "pdf_base64": f"data:application/pdf;base64,{base64_pdf}"
    }


@router.delete("/{pdf_id}")
async def delete_pdf(pdf_id: str):
    """Remove a PDF from cache"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    del pdf_cache[pdf_id]
    return {"success": True, "message": "PDF removed from cache"}


@router.get("/thumbnails/{pdf_id}")
async def get_thumbnails(pdf_id: str, max_width: int = 150):
    """Get thumbnails of all pages"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_data = pdf_cache[pdf_id]
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    
    thumbnails = []
    for i, page in enumerate(doc):
        # Calculate zoom to fit max_width
        rect = page.rect
        zoom = max_width / rect.width
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        img_bytes = pix.tobytes("png")
        base64_img = base64.b64encode(img_bytes).decode('utf-8')
        
        thumbnails.append({
            "page_number": i + 1,
            "width": pix.width,
            "height": pix.height,
            "thumbnail": f"data:image/png;base64,{base64_img}"
        })
    
    doc.close()
    
    return {
        "pdf_id": pdf_id,
        "filename": pdf_data["filename"],
        "thumbnails": thumbnails
    }


def parse_page_selection(selection: str, max_pages: int) -> List[int]:
    """Parse page selection string like '1,3,5-8,10' into list of page numbers"""
    pages = set()
    parts = selection.replace(' ', '').split(',')
    
    for part in parts:
        if '-' in part:
            # Range like "5-8"
            try:
                start, end = part.split('-')
                start = int(start)
                end = int(end)
                for p in range(max(1, start), min(max_pages, end) + 1):
                    pages.add(p)
            except:
                continue
        else:
            # Single page
            try:
                p = int(part)
                if 1 <= p <= max_pages:
                    pages.add(p)
            except:
                continue
    
    return sorted(list(pages))


@router.post("/split")
async def split_pdf(
    pdf_id: str = Form(...),
    pages_per_file: int = Form(default=1)
):
    """Split PDF into multiple files"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_data = pdf_cache[pdf_id]
    src_doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    
    total_pages = len(src_doc)
    original_name = os.path.splitext(pdf_data["filename"])[0]
    
    splits = []
    for start in range(0, total_pages, pages_per_file):
        end = min(start + pages_per_file, total_pages)
        
        new_doc = fitz.open()
        new_doc.insert_pdf(src_doc, from_page=start, to_page=end-1)
        
        pdf_bytes = new_doc.tobytes()
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        splits.append({
            "filename": f"{original_name}_part_{start+1}-{end}.pdf",
            "start_page": start + 1,
            "end_page": end,
            "page_count": end - start,
            "pdf_base64": f"data:application/pdf;base64,{base64_pdf}"
        })
        
        new_doc.close()
    
    src_doc.close()
    
    return {
        "original_filename": pdf_data["filename"],
        "total_pages": total_pages,
        "split_count": len(splits),
        "files": splits
    }


@router.post("/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    """Merge multiple PDFs into one"""
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 PDFs to merge")
    
    merged_doc = fitz.open()
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            continue
        
        content = await file.read()
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            merged_doc.insert_pdf(doc)
            doc.close()
        except Exception as e:
            continue
    
    if len(merged_doc) == 0:
        raise HTTPException(status_code=400, detail="No valid PDFs to merge")
    
    pdf_bytes = merged_doc.tobytes()
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    merged_doc.close()
    
    return {
        "filename": "merged.pdf",
        "page_count": len(merged_doc),
        "pdf_base64": f"data:application/pdf;base64,{base64_pdf}"
    }


@router.post("/rotate")
async def rotate_pages(
    pdf_id: str = Form(...),
    pages: str = Form(...),
    rotation: int = Form(...)  # 90, 180, 270, or -90
):
    """Rotate specific pages"""
    if pdf_id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    if rotation not in [90, 180, 270, -90]:
        raise HTTPException(status_code=400, detail="Rotation must be 90, 180, 270, or -90")
    
    pdf_data = pdf_cache[pdf_id]
    page_numbers = parse_page_selection(pages, pdf_data["page_count"])
    
    doc = fitz.open(stream=pdf_data["content"], filetype="pdf")
    
    for page_num in page_numbers:
        page = doc[page_num - 1]
        page.set_rotation((page.rotation + rotation) % 360)
    
    pdf_bytes = doc.tobytes()
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # Update cache
    pdf_cache[pdf_id]["content"] = pdf_bytes
    
    doc.close()
    
    return {
        "success": True,
        "rotated_pages": page_numbers,
        "rotation": rotation,
        "pdf_base64": f"data:application/pdf;base64,{base64_pdf}"
    }
