"""
Semptify - PDF Text Extraction Service
Robust PDF text extraction with multiple fallback methods.

Methods (in order of preference):
1. pdfplumber - Best for text-based PDFs with tables
2. PyMuPDF (fitz) - Fast, handles most PDFs well
3. PyPDF2 - Fallback for simple PDFs
4. Azure Document Intelligence - For scanned/image PDFs (uses OCR)
"""

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of PDF text extraction."""
    text: str
    page_count: int
    method_used: str
    has_images: bool = False
    confidence: float = 1.0
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PDFExtractor:
    """
    Multi-method PDF text extractor.
    Tries multiple extraction methods to get the best results.
    """

    def __init__(self):
        self._check_available_methods()

    def _check_available_methods(self):
        """Check which extraction libraries are available."""
        self.has_pdfplumber = False
        self.has_pymupdf = False
        self.has_pypdf2 = False

        try:
            import pdfplumber
            self.has_pdfplumber = True
        except ImportError:
            pass

        try:
            import fitz  # PyMuPDF
            self.has_pymupdf = True
        except ImportError:
            pass

        try:
            import PyPDF2
            self.has_pypdf2 = True
        except ImportError:
            pass

        logger.info(f"PDF methods: pdfplumber={self.has_pdfplumber}, "
                   f"pymupdf={self.has_pymupdf}, pypdf2={self.has_pypdf2}")

    def extract(
        self,
        content: Union[bytes, Path, str],
        prefer_ocr: bool = False
    ) -> ExtractionResult:
        """
        Extract text from a PDF file.
        
        Args:
            content: PDF bytes, file path, or path string
            prefer_ocr: If True, use OCR even for text PDFs
            
        Returns:
            ExtractionResult with extracted text
        """
        # Convert to bytes if needed
        if isinstance(content, (str, Path)):
            content = Path(content).read_bytes()

        # Try methods in order of preference
        result = None
        
        # Method 1: pdfplumber (best for tables and structured docs)
        if self.has_pdfplumber and not result:
            result = self._extract_pdfplumber(content)
            if result and len(result.text.strip()) > 50:
                return result

        # Method 2: PyMuPDF (fast and reliable)
        if self.has_pymupdf and not result:
            result = self._extract_pymupdf(content)
            if result and len(result.text.strip()) > 50:
                return result

        # Method 3: PyPDF2 (fallback)
        if self.has_pypdf2:
            result = self._extract_pypdf2(content)
            if result and len(result.text.strip()) > 50:
                return result

        # If we got some text but it's short, still return it
        if result and result.text.strip():
            result.confidence = 0.5  # Low confidence for short extractions
            return result

        # No text extracted - likely a scanned PDF
        return ExtractionResult(
            text="",
            page_count=self._get_page_count(content),
            method_used="none",
            has_images=True,
            confidence=0.0,
            metadata={"needs_ocr": True}
        )

    def _extract_pdfplumber(self, content: bytes) -> Optional[ExtractionResult]:
        """Extract text using pdfplumber."""
        try:
            import pdfplumber
            
            texts = []
            page_count = 0
            has_images = False
            
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                page_count = len(pdf.pages)
                
                for page in pdf.pages:
                    # Extract text
                    text = page.extract_text() or ""
                    texts.append(text)
                    
                    # Check for images
                    if page.images:
                        has_images = True
                    
                    # Also try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            for row in table:
                                if row:
                                    texts.append(" | ".join(str(cell or "") for cell in row))

            full_text = "\n\n".join(texts)
            
            return ExtractionResult(
                text=full_text,
                page_count=page_count,
                method_used="pdfplumber",
                has_images=has_images,
                confidence=0.95 if len(full_text) > 100 else 0.7
            )
            
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            return None

    def _extract_pymupdf(self, content: bytes) -> Optional[ExtractionResult]:
        """Extract text using PyMuPDF (fitz)."""
        try:
            import fitz  # PyMuPDF
            
            texts = []
            has_images = False
            
            doc = fitz.open(stream=content, filetype="pdf")
            page_count = len(doc)
            
            for page in doc:
                # Extract text with better formatting
                text = page.get_text("text")
                texts.append(text)
                
                # Check for images
                images = page.get_images()
                if images:
                    has_images = True

            doc.close()
            full_text = "\n\n".join(texts)
            
            return ExtractionResult(
                text=full_text,
                page_count=page_count,
                method_used="pymupdf",
                has_images=has_images,
                confidence=0.9 if len(full_text) > 100 else 0.6
            )
            
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
            return None

    def _extract_pypdf2(self, content: bytes) -> Optional[ExtractionResult]:
        """Extract text using PyPDF2."""
        try:
            import PyPDF2
            
            texts = []
            
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            page_count = len(reader.pages)
            
            for page in reader.pages:
                text = page.extract_text() or ""
                texts.append(text)

            full_text = "\n\n".join(texts)
            
            return ExtractionResult(
                text=full_text,
                page_count=page_count,
                method_used="pypdf2",
                has_images=False,  # PyPDF2 doesn't easily detect images
                confidence=0.8 if len(full_text) > 100 else 0.5
            )
            
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")
            return None

    def _get_page_count(self, content: bytes) -> int:
        """Get page count using any available method."""
        try:
            if self.has_pymupdf:
                import fitz
                doc = fitz.open(stream=content, filetype="pdf")
                count = len(doc)
                doc.close()
                return count
        except:
            pass
        
        try:
            if self.has_pypdf2:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                return len(reader.pages)
        except:
            pass
        
        return 0

    def extract_with_ocr(
        self,
        content: bytes,
        azure_endpoint: Optional[str] = None,
        azure_key: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract text from a scanned PDF using OCR.
        Uses Azure Document Intelligence if configured, otherwise attempts local OCR.
        
        Args:
            content: PDF file bytes
            azure_endpoint: Azure Document Intelligence endpoint
            azure_key: Azure API key
            
        Returns:
            ExtractionResult with OCR-extracted text
        """
        # First try normal extraction
        result = self.extract(content)
        
        # If we got good text, return it
        if result.text.strip() and result.confidence > 0.7:
            return result
        
        # Need OCR - try Azure if configured
        if azure_endpoint and azure_key:
            ocr_result = self._azure_ocr(content, azure_endpoint, azure_key)
            if ocr_result:
                return ocr_result
        
        # Try local image extraction + OCR
        local_result = self._local_ocr(content)
        if local_result:
            return local_result
        
        # Return original result (even if empty)
        result.metadata["ocr_attempted"] = True
        result.metadata["ocr_failed"] = True
        return result

    def _azure_ocr(
        self,
        content: bytes,
        endpoint: str,
        key: str
    ) -> Optional[ExtractionResult]:
        """Use Azure Document Intelligence for OCR."""
        try:
            import httpx
            import asyncio
            
            async def do_ocr():
                url = f"{endpoint.rstrip('/')}/documentintelligence/documentModels/prebuilt-read:analyze?api-version=2024-02-29-preview"
                
                headers = {
                    "Ocp-Apim-Subscription-Key": key,
                    "Content-Type": "application/pdf",
                }
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    # Submit for analysis
                    response = await client.post(url, headers=headers, content=content)
                    
                    if response.status_code == 202:
                        # Poll for result
                        operation_url = response.headers.get("Operation-Location")
                        
                        for _ in range(30):
                            await asyncio.sleep(1)
                            result = await client.get(
                                operation_url,
                                headers={"Ocp-Apim-Subscription-Key": key}
                            )
                            data = result.json()
                            
                            if data.get("status") == "succeeded":
                                # Extract text from result
                                analyze_result = data.get("analyzeResult", {})
                                content_text = analyze_result.get("content", "")
                                pages = analyze_result.get("pages", [])
                                
                                return ExtractionResult(
                                    text=content_text,
                                    page_count=len(pages),
                                    method_used="azure_ocr",
                                    has_images=True,
                                    confidence=0.95,
                                    metadata={"ocr_provider": "azure"}
                                )
                            elif data.get("status") == "failed":
                                return None
                        
                    elif response.status_code == 200:
                        # Synchronous result
                        data = response.json()
                        content_text = data.get("content", "")
                        return ExtractionResult(
                            text=content_text,
                            page_count=1,
                            method_used="azure_ocr",
                            has_images=True,
                            confidence=0.95,
                            metadata={"ocr_provider": "azure"}
                        )
                
                return None
            
            return asyncio.run(do_ocr())
            
        except Exception as e:
            logger.warning(f"Azure OCR failed: {e}")
            return None

    def _local_ocr(self, content: bytes) -> Optional[ExtractionResult]:
        """
        Attempt local OCR using pdf2image + pytesseract.
        Requires Tesseract OCR to be installed on the system.
        """
        try:
            # Convert PDF pages to images
            if not self.has_pymupdf:
                return None
                
            import fitz
            
            doc = fitz.open(stream=content, filetype="pdf")
            texts = []
            page_count = len(doc)
            
            # Check if pytesseract is available
            try:
                import pytesseract
                from PIL import Image
                has_tesseract = True
            except ImportError:
                has_tesseract = False
            
            for page_num, page in enumerate(doc):
                # Try to get text first
                text = page.get_text("text").strip()
                
                if text:
                    texts.append(text)
                elif has_tesseract:
                    # Render page to image and OCR it
                    try:
                        pix = page.get_pixmap(dpi=200)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        ocr_text = pytesseract.image_to_string(img)
                        texts.append(ocr_text)
                    except Exception as e:
                        logger.warning(f"Page {page_num} OCR failed: {e}")
            
            doc.close()
            full_text = "\n\n".join(texts)
            
            if full_text.strip():
                return ExtractionResult(
                    text=full_text,
                    page_count=page_count,
                    method_used="local_ocr" if has_tesseract else "pymupdf",
                    has_images=True,
                    confidence=0.8 if has_tesseract else 0.6,
                    metadata={"ocr_provider": "tesseract" if has_tesseract else "none"}
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Local OCR failed: {e}")
            return None


# Singleton instance
_extractor: Optional[PDFExtractor] = None


def get_pdf_extractor() -> PDFExtractor:
    """Get or create PDF extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = PDFExtractor()
    return _extractor


# Convenience function
def extract_pdf_text(content: Union[bytes, Path, str]) -> str:
    """
    Quick function to extract text from a PDF.
    
    Args:
        content: PDF bytes or file path
        
    Returns:
        Extracted text string
    """
    extractor = get_pdf_extractor()
    result = extractor.extract(content)
    return result.text
