"""
Document Preview Service
========================

Generates previews and thumbnails for documents.

Supported formats:
- PDF: First page as thumbnail
- Images: Resized thumbnail, full preview
- DOCX/DOC: Text extraction preview
- TXT: Direct text preview

Caching:
- Thumbnails stored in cache directory
- Preview metadata in overlay system
- Cache invalidation on document update
"""

import io
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from app.core.id_gen import make_id
from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class PreviewType(str, Enum):
    """Types of previews."""
    THUMBNAIL = "thumbnail"  # Small image (200x200)
    PREVIEW = "preview"        # Medium image (800x600)
    FULL = "full"             # Full resolution


class FileCategory(str, Enum):
    """Document category for preview handling."""
    PDF = "pdf"
    IMAGE = "image"
    DOCX = "docx"
    DOC = "doc"
    TXT = "text"
    UNKNOWN = "unknown"


@dataclass
class PreviewResult:
    """Result of preview generation."""
    success: bool
    preview_id: str
    preview_type: PreviewType
    mime_type: str
    data: Optional[bytes] = None
    width: Optional[int] = None
    height: Optional[int] = None
    text_content: Optional[str] = None  # For text-based previews
    error_message: Optional[str] = None
    cached: bool = False


@dataclass
class PreviewMetadata:
    """Metadata about a preview."""
    preview_id: str
    document_id: str
    document_hash: str
    preview_type: PreviewType
    mime_type: str
    width: int
    height: int
    file_size: int
    created_at: str
    expires_at: Optional[str] = None


class PreviewService:
    """
    Service for generating document previews and thumbnails.
    
    Features:
    - PDF to image conversion (first page)
    - Image resizing with aspect ratio preservation
    - Text extraction for documents
    - Caching with hash-based invalidation
    """
    
    # Preview dimensions
    THUMBNAIL_SIZE = (200, 200)
    PREVIEW_SIZE = (800, 600)
    
    # Cache directory
    CACHE_DIR = Path("/tmp/semptify_previews")
    
    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_file_category(self, filename: str, mime_type: Optional[str] = None) -> FileCategory:
        """Determine file category from filename and mime type."""
        name_lower = filename.lower()
        
        if mime_type:
            if 'pdf' in mime_type:
                return FileCategory.PDF
            if 'image' in mime_type:
                return FileCategory.IMAGE
            if 'word' in mime_type or 'docx' in mime_type:
                return FileCategory.DOCX
            if 'text' in mime_type:
                return FileCategory.TXT
        
        # Fallback to extension
        if name_lower.endswith('.pdf'):
            return FileCategory.PDF
        if any(name_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
            return FileCategory.IMAGE
        if name_lower.endswith('.docx'):
            return FileCategory.DOCX
        if name_lower.endswith('.doc'):
            return FileCategory.DOC
        if name_lower.endswith('.txt'):
            return FileCategory.TXT
        
        return FileCategory.UNKNOWN
    
    def _compute_hash(self, data: bytes) -> str:
        """Compute hash for cache invalidation."""
        return hashlib.sha256(data).hexdigest()[:16]
    
    def _get_cache_path(self, document_id: str, preview_type: PreviewType) -> Path:
        """Get cache file path for a preview."""
        return self.CACHE_DIR / f"{document_id}_{preview_type.value}.png"
    
    async def generate_thumbnail(
        self,
        document_id: str,
        filename: str,
        document_data: bytes,
        mime_type: Optional[str] = None
    ) -> PreviewResult:
        """
        Generate thumbnail for a document.
        
        Args:
            document_id: Document identifier
            filename: Original filename
            document_data: Raw document bytes
            mime_type: Optional MIME type hint
            
        Returns:
            PreviewResult with thumbnail data
        """
        category = self._get_file_category(filename, mime_type)
        doc_hash = self._compute_hash(document_data)
        cache_path = self._get_cache_path(f"{document_id}_{doc_hash}", PreviewType.THUMBNAIL)
        
        # Check cache
        if cache_path.exists():
            try:
                cached_data = cache_path.read_bytes()
                return PreviewResult(
                    success=True,
                    preview_id=make_id("thumb"),
                    preview_type=PreviewType.THUMBNAIL,
                    mime_type="image/png",
                    data=cached_data,
                    width=self.THUMBNAIL_SIZE[0],
                    height=self.THUMBNAIL_SIZE[1],
                    cached=True
                )
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
        
        # Generate based on category
        try:
            if category == FileCategory.PDF:
                return await self._generate_pdf_thumbnail(document_id, document_data, cache_path)
            elif category == FileCategory.IMAGE:
                return await self._generate_image_thumbnail(document_id, document_data, cache_path)
            elif category in [FileCategory.DOCX, FileCategory.DOC]:
                return await self._generate_docx_thumbnail(document_id, document_data, filename, cache_path)
            elif category == FileCategory.TXT:
                return await self._generate_text_thumbnail(document_id, document_data, cache_path)
            else:
                return PreviewResult(
                    success=False,
                    preview_id="",
                    preview_type=PreviewType.THUMBNAIL,
                    mime_type="",
                    error_message=f"Unsupported file type: {category}"
                )
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return PreviewResult(
                success=False,
                preview_id="",
                preview_type=PreviewType.THUMBNAIL,
                mime_type="",
                error_message=str(e)
            )
    
    async def generate_preview(
        self,
        document_id: str,
        filename: str,
        document_data: bytes,
        mime_type: Optional[str] = None
    ) -> PreviewResult:
        """
        Generate medium-sized preview for a document.
        
        Args:
            document_id: Document identifier
            filename: Original filename
            document_data: Raw document bytes
            mime_type: Optional MIME type hint
            
        Returns:
            PreviewResult with preview data
        """
        category = self._get_file_category(filename, mime_type)
        doc_hash = self._compute_hash(document_data)
        cache_path = self._get_cache_path(f"{document_id}_{doc_hash}", PreviewType.PREVIEW)
        
        # Check cache
        if cache_path.exists():
            try:
                cached_data = cache_path.read_bytes()
                return PreviewResult(
                    success=True,
                    preview_id=make_id("prev"),
                    preview_type=PreviewType.PREVIEW,
                    mime_type="image/png",
                    data=cached_data,
                    width=self.PREVIEW_SIZE[0],
                    height=self.PREVIEW_SIZE[1],
                    cached=True
                )
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
        
        # Generate based on category
        try:
            if category == FileCategory.PDF:
                return await self._generate_pdf_preview(document_id, document_data, cache_path)
            elif category == FileCategory.IMAGE:
                return await self._generate_image_preview(document_id, document_data, cache_path)
            elif category in [FileCategory.DOCX, FileCategory.DOC, FileCategory.TXT]:
                # Text-based preview
                return await self._generate_text_preview(document_id, document_data, filename, cache_path)
            else:
                return PreviewResult(
                    success=False,
                    preview_id="",
                    preview_type=PreviewType.PREVIEW,
                    mime_type="",
                    error_message=f"Unsupported file type: {category}"
                )
        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            return PreviewResult(
                success=False,
                preview_id="",
                preview_type=PreviewType.PREVIEW,
                mime_type="",
                error_message=str(e)
            )
    
    async def _generate_pdf_thumbnail(
        self,
        document_id: str,
        pdf_data: bytes,
        cache_path: Path
    ) -> PreviewResult:
        """Generate thumbnail from PDF first page."""
        try:
            from pdf2image import convert_from_bytes
            
            # Convert first page to image
            images = convert_from_bytes(pdf_data, first_page=1, last_page=1, dpi=72)
            
            if not images:
                return PreviewResult(
                    success=False,
                    preview_id="",
                    preview_type=PreviewType.THUMBNAIL,
                    mime_type="",
                    error_message="PDF has no pages"
                )
            
            # Resize to thumbnail
            img = images[0]
            img.thumbnail(self.THUMBNAIL_SIZE)
            
            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            data = buffer.getvalue()
            
            # Cache
            cache_path.write_bytes(data)
            
            return PreviewResult(
                success=True,
                preview_id=make_id("thumb"),
                preview_type=PreviewType.THUMBNAIL,
                mime_type="image/png",
                data=data,
                width=img.width,
                height=img.height
            )
            
        except ImportError:
            # pdf2image not available, return placeholder
            return await self._generate_placeholder_thumbnail("PDF", cache_path)
        except Exception as e:
            logger.error(f"PDF thumbnail error: {e}")
            return await self._generate_placeholder_thumbnail("PDF", cache_path)
    
    async def _generate_pdf_preview(
        self,
        document_id: str,
        pdf_data: bytes,
        cache_path: Path
    ) -> PreviewResult:
        """Generate preview from PDF first page."""
        try:
            from pdf2image import convert_from_bytes
            
            images = convert_from_bytes(pdf_data, first_page=1, last_page=1, dpi=150)
            
            if not images:
                return PreviewResult(
                    success=False,
                    preview_id="",
                    preview_type=PreviewType.PREVIEW,
                    mime_type="",
                    error_message="PDF has no pages"
                )
            
            img = images[0]
            img.thumbnail(self.PREVIEW_SIZE)
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            data = buffer.getvalue()
            
            cache_path.write_bytes(data)
            
            return PreviewResult(
                success=True,
                preview_id=make_id("prev"),
                preview_type=PreviewType.PREVIEW,
                mime_type="image/png",
                data=data,
                width=img.width,
                height=img.height
            )
            
        except ImportError:
            return await self._generate_placeholder_preview("PDF", cache_path)
        except Exception as e:
            logger.error(f"PDF preview error: {e}")
            return await self._generate_placeholder_preview("PDF", cache_path)
    
    async def _generate_image_thumbnail(
        self,
        document_id: str,
        image_data: bytes,
        cache_path: Path
    ) -> PreviewResult:
        """Generate thumbnail from image."""
        try:
            from PIL import Image
            
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail(self.THUMBNAIL_SIZE)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            data = buffer.getvalue()
            
            cache_path.write_bytes(data)
            
            return PreviewResult(
                success=True,
                preview_id=make_id("thumb"),
                preview_type=PreviewType.THUMBNAIL,
                mime_type="image/png",
                data=data,
                width=img.width,
                height=img.height
            )
            
        except Exception as e:
            logger.error(f"Image thumbnail error: {e}")
            return await self._generate_placeholder_thumbnail("IMG", cache_path)
    
    async def _generate_image_preview(
        self,
        document_id: str,
        image_data: bytes,
        cache_path: Path
    ) -> PreviewResult:
        """Generate preview from image."""
        try:
            from PIL import Image
            
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail(self.PREVIEW_SIZE)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            data = buffer.getvalue()
            
            cache_path.write_bytes(data)
            
            return PreviewResult(
                success=True,
                preview_id=make_id("prev"),
                preview_type=PreviewType.PREVIEW,
                mime_type="image/png",
                data=data,
                width=img.width,
                height=img.height
            )
            
        except Exception as e:
            logger.error(f"Image preview error: {e}")
            return await self._generate_placeholder_preview("IMG", cache_path)
    
    async def _generate_docx_thumbnail(
        self,
        document_id: str,
        docx_data: bytes,
        filename: str,
        cache_path: Path
    ) -> PreviewResult:
        """Generate thumbnail for DOCX (placeholder with icon)."""
        return await self._generate_placeholder_thumbnail("DOCX", cache_path)
    
    async def _generate_text_thumbnail(
        self,
        document_id: str,
        text_data: bytes,
        cache_path: Path
    ) -> PreviewResult:
        """Generate thumbnail for text file (placeholder with icon)."""
        return await self._generate_placeholder_thumbnail("TXT", cache_path)
    
    async def _generate_text_preview(
        self,
        document_id: str,
        document_data: bytes,
        filename: str,
        cache_path: Path
    ) -> PreviewResult:
        """Generate text preview for documents."""
        try:
            text = document_data.decode('utf-8', errors='ignore')
            
            # Extract first 5000 characters
            preview_text = text[:5000]
            if len(text) > 5000:
                preview_text += "\n\n... [preview truncated]"
            
            return PreviewResult(
                success=True,
                preview_id=make_id("txt"),
                preview_type=PreviewType.PREVIEW,
                mime_type="text/plain",
                text_content=preview_text,
                width=0,
                height=0
            )
            
        except Exception as e:
            logger.error(f"Text preview error: {e}")
            return PreviewResult(
                success=False,
                preview_id="",
                preview_type=PreviewType.PREVIEW,
                mime_type="",
                error_message=str(e)
            )
    
    async def _generate_placeholder_thumbnail(self, label: str, cache_path: Path) -> PreviewResult:
        """Generate placeholder thumbnail with label."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create placeholder image
            img = Image.new('RGB', self.THUMBNAIL_SIZE, color='#f0f0f0')
            draw = ImageDraw.Draw(img)
            
            # Draw border
            draw.rectangle([0, 0, self.THUMBNAIL_SIZE[0]-1, self.THUMBNAIL_SIZE[1]-1], outline='#cccccc')
            
            # Draw label
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            # Center text
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (self.THUMBNAIL_SIZE[0] - text_width) // 2
            y = (self.THUMBNAIL_SIZE[1] - text_height) // 2
            
            draw.text((x, y), label, fill='#666666', font=font)
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            data = buffer.getvalue()
            
            cache_path.write_bytes(data)
            
            return PreviewResult(
                success=True,
                preview_id=make_id("thumb"),
                preview_type=PreviewType.THUMBNAIL,
                mime_type="image/png",
                data=data,
                width=self.THUMBNAIL_SIZE[0],
                height=self.THUMBNAIL_SIZE[1]
            )
            
        except Exception as e:
            logger.error(f"Placeholder error: {e}")
            return PreviewResult(
                success=False,
                preview_id="",
                preview_type=PreviewType.THUMBNAIL,
                mime_type="",
                error_message="Failed to generate placeholder"
            )
    
    async def _generate_placeholder_preview(self, label: str, cache_path: Path) -> PreviewResult:
        """Generate placeholder preview."""
        return await self._generate_placeholder_thumbnail(label, cache_path)
    
    async def clear_cache(self, document_id: str) -> bool:
        """Clear cached previews for a document."""
        try:
            for preview_type in PreviewType:
                cache_path = self._get_cache_path(document_id, preview_type)
                if cache_path.exists():
                    cache_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False


# Global instance
_preview_service: Optional[PreviewService] = None


def get_preview_service() -> PreviewService:
    """Get preview service instance."""
    global _preview_service
    if _preview_service is None:
        _preview_service = PreviewService()
    return _preview_service
