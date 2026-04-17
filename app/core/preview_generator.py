"""
Document Preview Generator - Multi-format Preview System
====================================================

Generates previews and thumbnails for various document formats.
"""

import logging
import os
import io
import tempfile
import subprocess
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import base64
import hashlib
import asyncio
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF for PDF processing
import magic  # python-magic for file type detection

logger = logging.getLogger(__name__)

class PreviewType(Enum):
    """Preview generation types."""
    THUMBNAIL = "thumbnail"
    PREVIEW = "preview"
    FULL_TEXT = "full_text"
    METADATA = "metadata"

class SupportedFormat(Enum):
    """Supported document formats."""
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"

@dataclass
class PreviewConfig:
    """Preview generation configuration."""
    thumbnail_size: Tuple[int, int] = (200, 300)
    preview_size: Tuple[int, int] = (800, 1200)
    quality: int = 85
    format: str = "JPEG"
    max_text_length: int = 10000
    max_pages: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PreviewResult:
    """Preview generation result."""
    document_id: str
    preview_type: PreviewType
    content: Union[str, bytes, Dict[str, Any]]
    format: str
    size_bytes: int
    generated_at: datetime
    cache_key: str
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "preview_type": self.preview_type.value,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "generated_at": self.generated_at.isoformat(),
            "cache_key": self.cache_key,
            "metadata": self.metadata
        }

class PreviewGenerator:
    """Document preview and thumbnail generator."""
    
    def __init__(self, config: PreviewConfig = None):
        self.config = config or PreviewConfig()
        
        # Supported formats mapping
        self.mime_types = {
            "application/pdf": SupportedFormat.PDF,
            "image/jpeg": SupportedFormat.IMAGE,
            "image/png": SupportedFormat.IMAGE,
            "image/gif": SupportedFormat.IMAGE,
            "image/bmp": SupportedFormat.IMAGE,
            "image/tiff": SupportedFormat.IMAGE,
            "text/plain": SupportedFormat.TEXT,
            "text/html": SupportedFormat.TEXT,
            "text/css": SupportedFormat.TEXT,
            "text/javascript": SupportedFormat.TEXT,
            "application/msword": SupportedFormat.WORD,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": SupportedFormat.WORD,
            "application/vnd.ms-excel": SupportedFormat.EXCEL,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": SupportedFormat.EXCEL,
            "application/vnd.ms-powerpoint": SupportedFormat.POWERPOINT,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": SupportedFormat.POWERPOINT,
        }
        
        # Preview cache
        self.preview_cache: Dict[str, PreviewResult] = {}
        
        # Statistics
        self.stats = {
            "previews_generated": 0,
            "thumbnails_generated": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0
        }
    
    def detect_format(self, file_path: str) -> Optional[SupportedFormat]:
        """Detect document format from file."""
        try:
            mime_type = magic.from_file(file_path, mime=True)
            return self.mime_types.get(mime_type)
        except Exception as e:
            logger.error(f"Format detection failed: {e}")
            return None
    
    def generate_cache_key(self, document_id: str, preview_type: PreviewType, 
                          file_path: str = None) -> str:
        """Generate cache key for preview."""
        key_data = f"{document_id}:{preview_type.value}"
        
        if file_path and os.path.exists(file_path):
            # Include file modification time for cache invalidation
            mtime = os.path.getmtime(file_path)
            key_data += f":{mtime}"
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def generate_thumbnail(self, document_id: str, file_path: str, 
                               page_number: int = 1) -> Optional[PreviewResult]:
        """Generate thumbnail for document."""
        try:
            cache_key = self.generate_cache_key(document_id, PreviewType.THUMBNAIL, file_path)
            
            # Check cache first
            if cache_key in self.preview_cache:
                self.stats["cache_hits"] += 1
                return self.preview_cache[cache_key]
            
            self.stats["cache_misses"] += 1
            
            # Detect format
            doc_format = self.detect_format(file_path)
            if not doc_format:
                raise ValueError(f"Unsupported document format: {file_path}")
            
            # Generate thumbnail based on format
            if doc_format == SupportedFormat.PDF:
                thumbnail_data = await self._generate_pdf_thumbnail(file_path, page_number)
            elif doc_format == SupportedFormat.IMAGE:
                thumbnail_data = await self._generate_image_thumbnail(file_path)
            elif doc_format == SupportedFormat.TEXT:
                thumbnail_data = await self._generate_text_thumbnail(file_path)
            else:
                thumbnail_data = await self._generate_generic_thumbnail(file_path, doc_format)
            
            # Create preview result
            result = PreviewResult(
                document_id=document_id,
                preview_type=PreviewType.THUMBNAIL,
                content=thumbnail_data,
                format=self.config.format,
                size_bytes=len(thumbnail_data) if isinstance(thumbnail_data, bytes) else 0,
                generated_at=datetime.now(timezone.utc),
                cache_key=cache_key,
                metadata={
                    "page_number": page_number,
                    "size": self.config.thumbnail_size,
                    "format": doc_format.value
                }
            )
            
            # Cache result
            self.preview_cache[cache_key] = result
            self.stats["thumbnails_generated"] += 1
            
            logger.info(f"Generated thumbnail for {document_id}")
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Thumbnail generation failed for {document_id}: {e}")
            return None
    
    async def generate_preview(self, document_id: str, file_path: str, 
                              max_pages: int = None) -> Optional[PreviewResult]:
        """Generate full preview for document."""
        try:
            cache_key = self.generate_cache_key(document_id, PreviewType.PREVIEW, file_path)
            
            # Check cache first
            if cache_key in self.preview_cache:
                self.stats["cache_hits"] += 1
                return self.preview_cache[cache_key]
            
            self.stats["cache_misses"] += 1
            
            # Detect format
            doc_format = self.detect_format(file_path)
            if not doc_format:
                raise ValueError(f"Unsupported document format: {file_path}")
            
            max_pages = max_pages or self.config.max_pages
            
            # Generate preview based on format
            if doc_format == SupportedFormat.PDF:
                preview_data = await self._generate_pdf_preview(file_path, max_pages)
            elif doc_format == SupportedFormat.IMAGE:
                preview_data = await self._generate_image_preview(file_path)
            elif doc_format == SupportedFormat.TEXT:
                preview_data = await self._generate_text_preview(file_path)
            else:
                preview_data = await self._generate_generic_preview(file_path, doc_format)
            
            # Create preview result
            result = PreviewResult(
                document_id=document_id,
                preview_type=PreviewType.PREVIEW,
                content=preview_data,
                format="json",
                size_bytes=len(str(preview_data).encode()),
                generated_at=datetime.now(timezone.utc),
                cache_key=cache_key,
                metadata={
                    "max_pages": max_pages,
                    "format": doc_format.value,
                    "size": self.config.preview_size
                }
            )
            
            # Cache result
            self.preview_cache[cache_key] = result
            self.stats["previews_generated"] += 1
            
            logger.info(f"Generated preview for {document_id}")
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Preview generation failed for {document_id}: {e}")
            return None
    
    async def _generate_pdf_thumbnail(self, file_path: str, page_number: int) -> bytes:
        """Generate thumbnail from PDF."""
        try:
            doc = fitz.open(file_path)
            
            if page_number > len(doc):
                page_number = 1
            
            page = doc.load_page(page_number - 1)
            
            # Get page dimensions
            pix = page.get_pixmap()
            
            # Create thumbnail
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Resize to thumbnail size
            img.thumbnail(self.config.thumbnail_size, Image.Resampling.LANCZOS)
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format=self.config.format, quality=self.config.quality)
            
            doc.close()
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"PDF thumbnail generation failed: {e}")
            raise
    
    async def _generate_image_thumbnail(self, file_path: str) -> bytes:
        """Generate thumbnail from image."""
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to thumbnail size
                img.thumbnail(self.config.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Convert to bytes
                img_buffer = io.BytesIO()
                img.save(img_buffer, format=self.config.format, quality=self.config.quality)
                
                return img_buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Image thumbnail generation failed: {e}")
            raise
    
    async def _generate_text_thumbnail(self, file_path: str) -> bytes:
        """Generate thumbnail from text file."""
        try:
            # Read first few lines of text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[:10]
                text = ''.join(lines)
            
            # Create image with text
            width, height = self.config.thumbnail_size
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Try to use a default font
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
            
            # Draw text
            y_offset = 10
            for line in lines[:15]:  # Max 15 lines
                if y_offset > height - 20:
                    break
                
                # Truncate long lines
                display_line = line[:50] + "..." if len(line) > 50 else line
                draw.text((10, y_offset), display_line, fill='black', font=font)
                y_offset += 15
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format=self.config.format, quality=self.config.quality)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Text thumbnail generation failed: {e}")
            raise
    
    async def _generate_generic_thumbnail(self, file_path: str, doc_format: SupportedFormat) -> bytes:
        """Generate generic thumbnail for unsupported formats."""
        try:
            width, height = self.config.thumbnail_size
            img = Image.new('RGB', (width, height), color='#f0f0f0')
            draw = ImageDraw.Draw(img)
            
            # Try to use a default font
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # Draw format icon/text
            format_text = doc_format.value.upper()
            bbox = draw.textbbox((0, 0), format_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            draw.text((x, y), format_text, fill='#666666', font=font)
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format=self.config.format, quality=self.config.quality)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Generic thumbnail generation failed: {e}")
            raise
    
    async def _generate_pdf_preview(self, file_path: str, max_pages: int) -> Dict[str, Any]:
        """Generate preview from PDF."""
        try:
            doc = fitz.open(file_path)
            
            preview_data = {
                "type": "pdf",
                "pages": [],
                "metadata": {
                    "page_count": len(doc),
                    "title": doc.metadata.get('title', ''),
                    "author": doc.metadata.get('author', ''),
                    "subject": doc.metadata.get('subject', ''),
                    "creator": doc.metadata.get('creator', ''),
                    "producer": doc.metadata.get('producer', ''),
                    "creation_date": doc.metadata.get('creationDate', ''),
                    "modification_date": doc.metadata.get('modDate', '')
                }
            }
            
            # Generate preview for each page
            for page_num in range(min(len(doc), max_pages)):
                page = doc.load_page(page_num)
                
                # Extract text
                text = page.get_text()
                
                # Generate page image
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Resize to preview size
                img.thumbnail(self.config.preview_size, Image.Resampling.LANCZOS)
                
                # Convert to base64
                img_buffer = io.BytesIO()
                img.save(img_buffer, format=self.config.format, quality=self.config.quality)
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                
                preview_data["pages"].append({
                    "page_number": page_num + 1,
                    "text": text[:self.config.max_text_length],
                    "image": f"data:image/{self.config.format.lower()};base64,{img_base64}",
                    "dimensions": {
                        "width": pix.width,
                        "height": pix.height
                    }
                })
            
            doc.close()
            return preview_data
            
        except Exception as e:
            logger.error(f"PDF preview generation failed: {e}")
            raise
    
    async def _generate_image_preview(self, file_path: str) -> Dict[str, Any]:
        """Generate preview from image."""
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get image info
                preview_data = {
                    "type": "image",
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "metadata": {
                        "width": img.width,
                        "height": img.height,
                        "format": img.format
                    }
                }
                
                # Generate preview image
                preview_img = img.copy()
                preview_img.thumbnail(self.config.preview_size, Image.Resampling.LANCZOS)
                
                # Convert to base64
                img_buffer = io.BytesIO()
                preview_img.save(img_buffer, format=self.config.format, quality=self.config.quality)
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                
                preview_data["preview"] = f"data:image/{self.config.format.lower()};base64,{img_base64}"
                
                return preview_data
                
        except Exception as e:
            logger.error(f"Image preview generation failed: {e}")
            raise
    
    async def _generate_text_preview(self, file_path: str) -> Dict[str, Any]:
        """Generate preview from text file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(self.config.max_text_length)
            
            preview_data = {
                "type": "text",
                "content": content,
                "metadata": {
                    "encoding": "utf-8",
                    "length": len(content),
                    "truncated": len(content) == self.config.max_text_length
                }
            }
            
            return preview_data
            
        except Exception as e:
            logger.error(f"Text preview generation failed: {e}")
            raise
    
    async def _generate_generic_preview(self, file_path: str, doc_format: SupportedFormat) -> Dict[str, Any]:
        """Generate preview for unsupported formats."""
        try:
            file_size = os.path.getsize(file_path)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path), timezone.utc)
            
            preview_data = {
                "type": "generic",
                "format": doc_format.value,
                "metadata": {
                    "file_size": file_size,
                    "file_size_human": self._format_file_size(file_size),
                    "modified_time": file_mtime.isoformat(),
                    "supported": False
                },
                "message": f"Preview not available for {doc_format.value} files"
            }
            
            return preview_data
            
        except Exception as e:
            logger.error(f"Generic preview generation failed: {e}")
            raise
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def get_preview(self, document_id: str, preview_type: PreviewType) -> Optional[PreviewResult]:
        """Get cached preview."""
        for key, result in self.preview_cache.items():
            if result.document_id == document_id and result.preview_type == preview_type:
                self.stats["cache_hits"] += 1
                return result
        
        self.stats["cache_misses"] += 1
        return None
    
    def clear_cache(self, document_id: str = None):
        """Clear preview cache."""
        if document_id:
            # Clear specific document previews
            keys_to_remove = [key for key, result in self.preview_cache.items() 
                            if result.document_id == document_id]
            for key in keys_to_remove:
                del self.preview_cache[key]
        else:
            # Clear all cache
            self.preview_cache.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get preview generation statistics."""
        return {
            "cache_size": len(self.preview_cache),
            "previews_generated": self.stats["previews_generated"],
            "thumbnails_generated": self.stats["thumbnails_generated"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_hit_rate": (
                self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"])
                if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0
            ),
            "errors": self.stats["errors"]
        }

# Global preview generator instance
_preview_generator: Optional[PreviewGenerator] = None

def get_preview_generator() -> PreviewGenerator:
    """Get the global preview generator instance."""
    global _preview_generator
    
    if _preview_generator is None:
        _preview_generator = PreviewGenerator()
    
    return _preview_generator

# Helper functions
async def generate_document_thumbnail(document_id: str, file_path: str, page_number: int = 1) -> Optional[PreviewResult]:
    """Generate thumbnail for document."""
    generator = get_preview_generator()
    return await generator.generate_thumbnail(document_id, file_path, page_number)

async def generate_document_preview(document_id: str, file_path: str, max_pages: int = None) -> Optional[PreviewResult]:
    """Generate preview for document."""
    generator = get_preview_generator()
    return await generator.generate_preview(document_id, file_path, max_pages)

def get_cached_preview(document_id: str, preview_type: PreviewType) -> Optional[PreviewResult]:
    """Get cached preview."""
    generator = get_preview_generator()
    return generator.get_preview(document_id, preview_type)

def clear_preview_cache(document_id: str = None):
    """Clear preview cache."""
    generator = get_preview_generator()
    generator.clear_cache(document_id)

def get_preview_statistics() -> Dict[str, Any]:
    """Get preview generation statistics."""
    generator = get_preview_generator()
    return generator.get_statistics()
