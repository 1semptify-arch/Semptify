"""
Document Preview API - Multi-format Preview Generation
===================================================

Provides document preview and thumbnail generation capabilities.
"""

import logging
import os
import tempfile
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.security import require_user, StorageUser
from app.core.preview_generator import (
    get_preview_generator, PreviewType, PreviewResult,
    generate_document_thumbnail, generate_document_preview,
    get_cached_preview, clear_preview_cache, get_preview_statistics
)
from app.core.database import get_db_session
from app.models.models import Document as DocumentModel
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# Schemas
# =============================================================================

class PreviewRequest(BaseModel):
    """Preview generation request."""
    document_id: str = Field(..., description="Document ID")
    preview_type: str = Field("preview", description="Preview type: thumbnail, preview")
    page_number: int = Field(1, ge=1, description="Page number for PDF thumbnails")
    max_pages: int = Field(10, ge=1, le=50, description="Max pages for preview")

class PreviewResponse(BaseModel):
    """Preview generation response."""
    success: bool
    document_id: str
    preview_type: str
    preview_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None

# =============================================================================
# Preview Endpoints
# =============================================================================

@router.post("/generate")
async def generate_preview_endpoint(
    request: PreviewRequest,
    user: StorageUser = Depends(require_user)
):
    """
    Generate preview or thumbnail for a document.
    
    Supports:
    - PDF documents (multi-page)
    - Images (JPEG, PNG, GIF, BMP, TIFF)
    - Text files (plain text, HTML, CSS, JS)
    - Office documents (fallback preview)
    """
    try:
        # Get document from database
        async with get_db_session() as session:
            doc_query = select(DocumentModel).where(
                DocumentModel.id == request.document_id,
                DocumentModel.user_id == user.user_id
            )
            result = await session.execute(doc_query)
            doc = result.scalar_one_or_none()
            
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            
            if not doc.file_path or not os.path.exists(doc.file_path):
                raise HTTPException(status_code=404, detail="Document file not found")
            
            # Determine preview type
            preview_type = PreviewType.THUMBNAIL if request.preview_type == "thumbnail" else PreviewType.PREVIEW
            
            # Check cache first
            cached_preview = get_cached_preview(request.document_id, preview_type)
            if cached_preview:
                return PreviewResponse(
                    success=True,
                    document_id=request.document_id,
                    preview_type=request.preview_type,
                    preview_url=f"/preview/serve/{cached_preview.cache_key}",
                    metadata=cached_preview.metadata,
                    message="Preview retrieved from cache"
                )
            
            # Generate preview
            if preview_type == PreviewType.THUMBNAIL:
                preview_result = await generate_document_thumbnail(
                    request.document_id, 
                    doc.file_path, 
                    request.page_number
                )
            else:
                preview_result = await generate_document_preview(
                    request.document_id, 
                    doc.file_path, 
                    request.max_pages
                )
            
            if not preview_result:
                raise HTTPException(status_code=500, detail="Preview generation failed")
            
            return PreviewResponse(
                success=True,
                document_id=request.document_id,
                preview_type=request.preview_type,
                preview_url=f"/preview/serve/{preview_result.cache_key}",
                metadata=preview_result.metadata,
                message="Preview generated successfully"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview generation error: {e}")
        raise HTTPException(status_code=500, detail="Preview generation failed")

@router.get("/serve/{cache_key}")
async def serve_preview(cache_key: str):
    """
    Serve generated preview content.
    
    Returns the actual preview data (image or JSON).
    """
    try:
        generator = get_preview_generator()
        
        # Find preview in cache
        preview_result = None
        for key, result in generator.preview_cache.items():
            if result.cache_key == cache_key:
                preview_result = result
                break
        
        if not preview_result:
            raise HTTPException(status_code=404, detail="Preview not found")
        
        # Serve based on preview type and format
        if preview_result.preview_type == PreviewType.THUMBNAIL:
            # Serve image
            if isinstance(preview_result.content, bytes):
                media_type = f"image/{preview_result.format.lower()}"
                return Response(
                    content=preview_result.content,
                    media_type=media_type,
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Content-Disposition": f"inline; filename=thumbnail_{preview_result.document_id}.{preview_result.format.lower()}"
                    }
                )
        
        elif preview_result.preview_type == PreviewType.PREVIEW:
            # Serve JSON data
            return Response(
                content=str(preview_result.content),
                media_type="application/json",
                headers={
                    "Cache-Control": "public, max-age=3600"
                }
            )
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported preview type")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview serving error: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve preview")

@router.get("/info/{document_id}")
async def get_preview_info(
    document_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Get information about available previews for a document.
    """
    try:
        # Verify document ownership
        async with get_db_session() as session:
            doc_query = select(DocumentModel).where(
                DocumentModel.id == document_id,
                DocumentModel.user_id == user.user_id
            )
            result = await session.execute(doc_query)
            doc = result.scalar_one_or_none()
            
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
        
        generator = get_preview_generator()
        
        # Check available previews
        thumbnail = get_cached_preview(document_id, PreviewType.THUMBNAIL)
        preview = get_cached_preview(document_id, PreviewType.PREVIEW)
        
        return {
            "document_id": document_id,
            "available_previews": {
                "thumbnail": {
                    "available": thumbnail is not None,
                    "cache_key": thumbnail.cache_key if thumbnail else None,
                    "url": f"/preview/serve/{thumbnail.cache_key}" if thumbnail else None,
                    "metadata": thumbnail.metadata if thumbnail else None
                },
                "preview": {
                    "available": preview is not None,
                    "cache_key": preview.cache_key if preview else None,
                    "url": f"/preview/serve/{preview.cache_key}" if preview else None,
                    "metadata": preview.metadata if preview else None
                }
            },
            "document_info": {
                "filename": doc.filename,
                "file_type": doc.document_type,
                "file_size": doc.file_size,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview info error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get preview info")

@router.delete("/cache/{document_id}")
async def clear_document_cache(
    document_id: str,
    user: StorageUser = Depends(require_user)
):
    """
    Clear cached previews for a document.
    """
    try:
        # Verify document ownership
        async with get_db_session() as session:
            doc_query = select(DocumentModel).where(
                DocumentModel.id == document_id,
                DocumentModel.user_id == user.user_id
            )
            result = await session.execute(doc_query)
            doc = result.scalar_one_or_none()
            
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
        
        # Clear cache
        clear_preview_cache(document_id)
        
        return {
            "success": True,
            "document_id": document_id,
            "message": "Preview cache cleared successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@router.get("/statistics")
async def get_preview_stats(
    user: StorageUser = Depends(require_user)
):
    """
    Get preview generation statistics.
    """
    try:
        stats = get_preview_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Preview statistics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@router.post("/batch")
async def batch_generate_previews(
    document_ids: list[str],
    preview_type: str = Query("thumbnail", description="Preview type: thumbnail, preview"),
    user: StorageUser = Depends(require_user)
):
    """
    Generate previews for multiple documents.
    """
    try:
        results = []
        
        for document_id in document_ids:
            try:
                # Get document from database
                async with get_db_session() as session:
                    doc_query = select(DocumentModel).where(
                        DocumentModel.id == document_id,
                        DocumentModel.user_id == user.user_id
                    )
                    result = await session.execute(doc_query)
                    doc = result.scalar_one_or_none()
                    
                    if not doc:
                        results.append({
                            "document_id": document_id,
                            "success": False,
                            "error": "Document not found"
                        })
                        continue
                    
                    if not doc.file_path or not os.path.exists(doc.file_path):
                        results.append({
                            "document_id": document_id,
                            "success": False,
                            "error": "Document file not found"
                        })
                        continue
                    
                    # Determine preview type
                    preview_type_enum = PreviewType.THUMBNAIL if preview_type == "thumbnail" else PreviewType.PREVIEW
                    
                    # Generate preview
                    if preview_type_enum == PreviewType.THUMBNAIL:
                        preview_result = await generate_document_thumbnail(document_id, doc.file_path)
                    else:
                        preview_result = await generate_document_preview(document_id, doc.file_path)
                    
                    if preview_result:
                        results.append({
                            "document_id": document_id,
                            "success": True,
                            "preview_url": f"/preview/serve/{preview_result.cache_key}",
                            "metadata": preview_result.metadata
                        })
                    else:
                        results.append({
                            "document_id": document_id,
                            "success": False,
                            "error": "Preview generation failed"
                        })
                        
            except Exception as e:
                logger.error(f"Batch preview error for {document_id}: {e}")
                results.append({
                    "document_id": document_id,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total_documents": len(document_ids),
            "successful": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch preview generation error: {e}")
        raise HTTPException(status_code=500, detail="Batch preview generation failed")

# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/supported-formats")
async def get_supported_formats():
    """
    Get list of supported document formats for preview generation.
    """
    try:
        generator = get_preview_generator()
        
        formats = []
        for mime_type, format_enum in generator.mime_types.items():
            formats.append({
                "mime_type": mime_type,
                "format": format_enum.value,
                "supported": True
            })
        
        return {
            "supported_formats": formats,
            "total_supported": len(formats)
        }
        
    except Exception as e:
        logger.error(f"Supported formats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supported formats")

@router.delete("/cache")
async def clear_all_cache(user: StorageUser = Depends(require_user)):
    """
    Clear all preview cache (admin only or user-specific).
    """
    try:
        # For now, clear all cache (in production, this might be admin-only)
        clear_preview_cache()
        
        return {
            "success": True,
            "message": "All preview cache cleared"
        }
        
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")
