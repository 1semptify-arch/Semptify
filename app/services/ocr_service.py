"""
OCR Integration Service
=======================
Extracts text from images and scanned documents using:
1. Azure Document Intelligence (if API key configured)
2. Tesseract OCR (local fallback)
3. Basic image-to-text (emergency fallback)

Supports: PDF, JPG, PNG, TIFF, BMP, GIF, HEIC
"""

import asyncio
import logging
import os
import io
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class OCRResult:
    """Result of OCR processing."""
    
    def __init__(
        self,
        text: str,
        confidence: float = 0.0,
        method: str = "unknown",
        pages: int = 1,
        words: int = 0,
        processing_time_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.text = text
        self.confidence = confidence
        self.method = method
        self.pages = pages
        self.words = len(text.split()) if text else 0
        self.processing_time_ms = processing_time_ms
        self.metadata = metadata or {}
        self.success = bool(text and len(text.strip()) > 10)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "method": self.method,
            "pages": self.pages,
            "words": self.words,
            "processing_time_ms": self.processing_time_ms,
            "success": self.success,
            "metadata": self.metadata,
        }


class OCRService:
    """
    Multi-method OCR service with automatic fallback.
    
    Priority:
    1. Azure Document Intelligence (best quality, requires API key)
    2. Tesseract (good quality, requires local install)
    3. PDF text extraction (for text-based PDFs)
    """
    
    def __init__(self):
        self.azure_available = self._check_azure()
        self.tesseract_available = self._check_tesseract()
        logger.info(f"OCR Service initialized: Azure={self.azure_available}, Tesseract={self.tesseract_available}")
    
    def _check_azure(self) -> bool:
        """Check if Azure Document Intelligence is configured."""
        endpoint = os.getenv("AZURE_DOCUMENT_ENDPOINT") or os.getenv("AZURE_AI_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_KEY") or os.getenv("AZURE_AI_KEY")
        return bool(endpoint and key)
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is installed."""
        try:
            import pytesseract
            # Try to get version
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    async def extract_text(
        self,
        file_path: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        filename: str = "document",
        prefer_method: Optional[str] = None,
    ) -> OCRResult:
        """
        Extract text from document using best available method.
        
        Args:
            file_path: Path to file on disk
            file_bytes: Raw file bytes
            filename: Original filename (for type detection)
            prefer_method: Force specific method (azure, tesseract, pdf)
            
        Returns:
            OCRResult with extracted text and metadata
        """
        import time
        start_time = time.time()
        
        # Get file bytes if path provided
        if file_path and not file_bytes:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
        
        if not file_bytes:
            return OCRResult(text="", method="error", metadata={"error": "No file provided"})
        
        # Detect file type
        file_ext = Path(filename).suffix.lower()
        is_pdf = file_ext == '.pdf'
        is_image = file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif', '.heic']
        
        # Try methods in order
        methods_to_try = []
        
        if prefer_method:
            methods_to_try = [prefer_method]
        else:
            if is_pdf:
                # For PDFs, try text extraction first (faster for text PDFs)
                methods_to_try = ["pdf_text", "azure", "tesseract"]
            else:
                # For images, OCR is required
                methods_to_try = ["azure", "tesseract"]
        
        last_error = None
        for method in methods_to_try:
            try:
                if method == "azure" and self.azure_available:
                    result = await self._extract_azure(file_bytes, filename)
                    if result.success:
                        result.processing_time_ms = int((time.time() - start_time) * 1000)
                        return result
                        
                elif method == "tesseract" and self.tesseract_available:
                    result = await self._extract_tesseract(file_bytes, filename)
                    if result.success:
                        result.processing_time_ms = int((time.time() - start_time) * 1000)
                        return result
                        
                elif method == "pdf_text" and is_pdf:
                    result = await self._extract_pdf_text(file_bytes)
                    if result.success:
                        result.processing_time_ms = int((time.time() - start_time) * 1000)
                        return result
                        
            except Exception as e:
                last_error = str(e)
                logger.warning(f"OCR method {method} failed: {e}")
                continue
        
        # All methods failed
        processing_time = int((time.time() - start_time) * 1000)
        return OCRResult(
            text="",
            method="failed",
            processing_time_ms=processing_time,
            metadata={"error": last_error or "All OCR methods failed"},
        )
    
    async def _extract_azure(self, file_bytes: bytes, filename: str) -> OCRResult:
        """Extract text using Azure Document Intelligence."""
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
            from azure.core.credentials import AzureKeyCredential
        except ImportError:
            return OCRResult(text="", method="azure", metadata={"error": "azure-ai-documentintelligence not installed"})
        
        endpoint = os.getenv("AZURE_DOCUMENT_ENDPOINT") or os.getenv("AZURE_AI_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_KEY") or os.getenv("AZURE_AI_KEY")
        
        if not endpoint or not key:
            return OCRResult(text="", method="azure", metadata={"error": "Azure credentials not configured"})
        
        try:
            client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
            
            # Use prebuilt-read model for general document reading
            poller = client.begin_analyze_document(
                "prebuilt-read",
                AnalyzeDocumentRequest(bytes_source=file_bytes),
            )
            result = poller.result()
            
            # Extract text from all pages
            text_parts = []
            page_count = 0
            total_confidence = 0
            word_count = 0
            
            for page in result.pages:
                page_count += 1
                for line in page.lines:
                    text_parts.append(line.content)
                for word in page.words:
                    word_count += 1
                    total_confidence += word.confidence if word.confidence else 0.8
            
            text = "\n".join(text_parts)
            avg_confidence = total_confidence / word_count if word_count > 0 else 0.0
            
            return OCRResult(
                text=text,
                confidence=avg_confidence,
                method="azure",
                pages=page_count,
                metadata={
                    "model": "prebuilt-read",
                    "api_version": "2024-02-29-preview",
                },
            )
            
        except Exception as e:
            logger.error(f"Azure OCR error: {e}")
            return OCRResult(text="", method="azure", metadata={"error": str(e)})
    
    async def _extract_tesseract(self, file_bytes: bytes, filename: str) -> OCRResult:
        """Extract text using Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return OCRResult(text="", method="tesseract", metadata={"error": "pytesseract or PIL not installed"})
        
        try:
            file_ext = Path(filename).suffix.lower()
            
            # Handle PDFs by converting to images
            if file_ext == '.pdf':
                try:
                    import pdf2image
                    images = pdf2image.convert_from_bytes(file_bytes)
                except ImportError:
                    return OCRResult(text="", method="tesseract", metadata={"error": "pdf2image not installed for PDF OCR"})
            else:
                # Load image directly
                images = [Image.open(io.BytesIO(file_bytes))]
            
            # Extract text from all pages
            text_parts = []
            for i, img in enumerate(images):
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get text with confidence data
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                
                page_text = pytesseract.image_to_string(img)
                text_parts.append(page_text)
            
            text = "\n\n--- Page Break ---\n\n".join(text_parts)
            
            return OCRResult(
                text=text,
                confidence=0.75,  # Tesseract doesn't provide reliable confidence
                method="tesseract",
                pages=len(images),
                metadata={"engine": "tesseract"},
            )
            
        except Exception as e:
            logger.error(f"Tesseract OCR error: {e}")
            return OCRResult(text="", method="tesseract", metadata={"error": str(e)})
    
    async def _extract_pdf_text(self, file_bytes: bytes) -> OCRResult:
        """Extract text from text-based PDFs."""
        try:
            import PyPDF2
        except ImportError:
            try:
                import pypdf as PyPDF2
            except ImportError:
                return OCRResult(text="", method="pdf_text", metadata={"error": "PyPDF2/pypdf not installed"})
        
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text_parts = []
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            full_text = "\n\n".join(text_parts)
            
            # Check if we got meaningful text (not just whitespace/garbage)
            meaningful_words = len([w for w in full_text.split() if len(w) > 2])
            
            return OCRResult(
                text=full_text,
                confidence=0.95 if meaningful_words > 20 else 0.5,
                method="pdf_text",
                pages=len(pdf_reader.pages),
                metadata={"extraction_type": "native_pdf"},
            )
            
        except Exception as e:
            logger.error(f"PDF text extraction error: {e}")
            return OCRResult(text="", method="pdf_text", metadata={"error": str(e)})
    
    def get_status(self) -> Dict[str, Any]:
        """Get OCR service status."""
        return {
            "azure_available": self.azure_available,
            "tesseract_available": self.tesseract_available,
            "pdf_text_available": True,  # Always available with PyPDF2
            "best_method": "azure" if self.azure_available else ("tesseract" if self.tesseract_available else "pdf_text"),
            "recommendations": self._get_recommendations(),
        }
    
    def _get_recommendations(self) -> List[str]:
        """Get recommendations for improving OCR."""
        recs = []
        
        if not self.azure_available:
            recs.append("Set AZURE_DOCUMENT_ENDPOINT and AZURE_DOCUMENT_KEY for best OCR quality")
        
        if not self.tesseract_available:
            recs.append("Install Tesseract OCR: pip install pytesseract; and install tesseract-ocr system package")
        
        if not recs:
            recs.append("OCR is fully configured with Azure Document Intelligence")
        
        return recs


# Singleton instance
ocr_service = OCRService()


# Convenience function
async def extract_text_from_file(
    file_path: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    filename: str = "document",
) -> OCRResult:
    """Extract text from a file using best available OCR method."""
    return await ocr_service.extract_text(file_path, file_bytes, filename)
