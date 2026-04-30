"""
Semptify 5.0 - Azure AI Service
Document Intelligence + OpenAI integration for document analysis.
"""

import asyncio
import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import httpx

from app.core.config import get_settings


class DocumentType(str, Enum):
    """Types of documents in a tenancy."""
    LEASE = "lease"
    NOTICE = "notice"
    RECEIPT = "receipt"
    LETTER = "letter"
    PHOTO = "photo"
    COURT_FILING = "court_filing"
    INSPECTION = "inspection"
    REPAIR_REQUEST = "repair_request"
    PAYMENT_RECORD = "payment_record"
    COMMUNICATION = "communication"
    UNKNOWN = "unknown"


@dataclass
class ExtractedDocument:
    """Result of document analysis."""
    doc_type: DocumentType
    confidence: float
    title: str
    summary: str
    key_dates: list[dict]  # [{date, description}]
    key_parties: list[dict]  # [{name, role}]
    key_amounts: list[dict]  # [{amount, description}]
    key_terms: list[str]
    full_text: str
    raw_response: dict
    analyzed_at: datetime


class AzureAIService:
    """
    Azure AI client for document processing.
    Uses Document Intelligence for OCR and structure extraction.
    Uses OpenAI for classification and understanding.
    """

    def __init__(self):
        settings = get_settings()
        self.endpoint = settings.azure_ai_endpoint.rstrip('/')
        self.api_key = settings.azure_ai_key1
        self.region = settings.azure_ai_region
        
        # Document Intelligence API
        self.doc_intel_url = f"{self.endpoint}/documentintelligence"
        
    async def analyze_document(
        self,
        content: bytes,
        filename: str,
        mime_type: str = "application/pdf"
    ) -> ExtractedDocument:
        """
        Full document analysis pipeline:
        1. Text extraction (local PDF extraction or Azure OCR)
        2. Classification with AI (Groq/Ollama/Azure)
        3. Extract key information
        """
        full_text = ""
        raw_result = {}
        
        # For text files, use content directly
        if mime_type in ("text/plain", "text/csv", "text/markdown") or filename.endswith(('.txt', '.csv', '.md')):
            try:
                full_text = content.decode('utf-8')
            except UnicodeDecodeError:
                full_text = content.decode('latin-1', errors='replace')
            raw_result = {"content": full_text, "source": "direct_text"}
        
        # For PDFs, use local extraction first
        elif mime_type == "application/pdf" or filename.lower().endswith('.pdf'):
            try:
                from app.services.pdf_extractor import get_pdf_extractor
                extractor = get_pdf_extractor()
                
                # Try local extraction first (fast, no API calls)
                result = extractor.extract(content)
                full_text = result.text
                raw_result = {
                    "content": full_text,
                    "source": result.method_used,
                    "page_count": result.page_count,
                    "has_images": result.has_images,
                    "confidence": result.confidence
                }
                
                # If extraction failed or got very little text, try Azure OCR
                if len(full_text.strip()) < 50 and self.api_key:
                    print(f"Local extraction got {len(full_text)} chars, trying Azure OCR...")
                    ocr_result = extractor.extract_with_ocr(
                        content,
                        azure_endpoint=self.endpoint,
                        azure_key=self.api_key
                    )
                    if ocr_result.text.strip():
                        full_text = ocr_result.text
                        raw_result = {
                            "content": full_text,
                            "source": ocr_result.method_used,
                            "page_count": ocr_result.page_count,
                            "confidence": ocr_result.confidence
                        }
            except Exception as e:
                print(f"PDF extraction error: {e}, falling back to Azure")
                # Fallback to Azure Document Intelligence
                raw_result = await self._extract_with_doc_intelligence(content, mime_type)
                full_text = self._get_text_from_result(raw_result)
        
        # For images, use Azure Document Intelligence (OCR)
        elif mime_type.startswith("image/") or filename.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp')):
            raw_result = await self._extract_with_doc_intelligence(content, mime_type)
            full_text = self._get_text_from_result(raw_result)
        
        # Other file types - try to decode as text
        else:
            try:
                full_text = content.decode('utf-8')
            except:
                full_text = content.decode('latin-1', errors='replace')
            raw_result = {"content": full_text, "source": "text_decode"}

        # Step 2: Classify and extract with AI
        analysis = await self._classify_and_extract(full_text, filename)

        return ExtractedDocument(
            doc_type=DocumentType(analysis.get("doc_type", "unknown")),
            confidence=analysis.get("confidence", 0.0),
            title=analysis.get("title", filename),
            summary=analysis.get("summary", ""),
            key_dates=analysis.get("key_dates", []),
            key_parties=analysis.get("key_parties", []),
            key_amounts=analysis.get("key_amounts", []),
            key_terms=analysis.get("key_terms", []),
            full_text=full_text,
            raw_response=raw_result,
            analyzed_at=datetime.now(timezone.utc)
        )

    async def _extract_with_doc_intelligence(
        self,
        content: bytes,
        mime_type: str
    ) -> dict:
        """Use Azure Document Intelligence to extract text and structure."""
        
        # Use prebuilt-read model for general document OCR
        url = f"{self.doc_intel_url}/documentModels/prebuilt-read:analyze?api-version=2024-02-29-preview"
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": mime_type,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Submit for analysis
            response = await client.post(url, headers=headers, content=content)
            
            if response.status_code == 202:
                # Async operation - poll for result
                operation_url = response.headers.get("Operation-Location")
                return await self._poll_operation(client, operation_url)
            elif response.status_code == 200:
                return response.json()
            else:
                # Return error info for debugging
                return {
                    "error": True,
                    "status": response.status_code,
                    "message": response.text
                }

    async def _poll_operation(
        self,
        client: httpx.AsyncClient,
        operation_url: str,
        max_attempts: int = 30
    ) -> dict:
        """Poll async operation until complete."""
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        
        for _ in range(max_attempts):
            response = await client.get(operation_url, headers=headers)
            result = response.json()
            
            status = result.get("status", "")
            if status == "succeeded":
                return result.get("analyzeResult", result)
            elif status == "failed":
                return {"error": True, "message": result.get("error", "Analysis failed")}
            
            await asyncio.sleep(1)
        
        return {"error": True, "message": "Operation timed out"}

    def _get_text_from_result(self, result: dict) -> str:
        """Extract plain text from Document Intelligence result."""
        if result.get("error"):
            return ""
        
        # Try different result structures
        if "content" in result:
            return result["content"]
        
        if "pages" in result:
            texts = []
            for page in result["pages"]:
                for line in page.get("lines", []):
                    texts.append(line.get("content", ""))
            return "\n".join(texts)
        
        return ""

    async def _classify_and_extract(
        self,
        text: str,
        filename: str
    ) -> dict:
        """Use AI to classify document and extract key information."""
        
        if not text.strip():
            return {
                "doc_type": "unknown",
                "confidence": 0.0,
                "title": filename,
                "summary": "Could not extract text from document",
                "key_dates": [],
                "key_parties": [],
                "key_amounts": [],
                "key_terms": []
            }

        # Build classification prompt
        prompt = f"""Analyze this document from a tenant's records. Extract key information.

Document filename: {filename}
Document text:
{text[:4000]}  # Limit to avoid token limits

Respond in JSON format:
{{
    "doc_type": "lease|notice|receipt|letter|photo|court_filing|inspection|repair_request|payment_record|communication|unknown",
    "confidence": 0.0-1.0,
    "title": "descriptive title",
    "summary": "2-3 sentence summary",
    "key_dates": [{{"date": "YYYY-MM-DD", "description": "what this date means"}}],
    "key_parties": [{{"name": "person/company name", "role": "landlord|tenant|court|other"}}],
    "key_amounts": [{{"amount": "dollar amount", "description": "what it's for"}}],
    "key_terms": ["important terms or clauses"]
}}"""

        # Call Azure OpenAI
        return await self._call_openai(prompt)

    async def _call_openai(self, prompt: str) -> dict:
        """
        Call AI for text analysis.
        
        Priority order (free/local first):
        1. Ollama - FREE, private, local (no API costs)
        2. Rule-based - FREE, instant, no API needed
        3. Groq - FREE tier: 14,400 req/day, then ~$0.59/M tokens
        4. Azure OpenAI - Pay per use (~$1-3/1K docs)
        """
        settings = get_settings()

        # 1. Try Ollama FIRST (completely free, local, private)
        try:
            result = await self._call_ollama(prompt, settings)
            if result:
                print("✓ Using Ollama (free, local)")
                return result
        except Exception as e:
            pass  # Silent fail, try next

        # 2. Try Groq (free tier: 14,400 requests/day)
        if settings.groq_api_key:
            try:
                result = await self._call_groq(prompt, settings)
                print("✓ Using Groq (free tier)")
                return result
            except Exception as e:
                print(f"Groq failed: {e}")

        # 3. Try Azure OpenAI (paid, but you may have free credits)
        if settings.azure_openai_endpoint and settings.azure_openai_api_key:
            try:
                result = await self._call_azure_openai(prompt, settings)
                if result:
                    print("✓ Using Azure OpenAI")
                    return result
            except Exception as e:
                print(f"Azure OpenAI failed: {e}")

        # 4. Fall back to rule-based (always free, always works)
        print("✓ Using rule-based classification (free)")
        return self._rule_based_classify(prompt)

    async def _call_azure_openai(self, prompt: str, settings) -> Optional[dict]:
        """Call Azure OpenAI for text analysis."""
        url = f"{settings.azure_openai_endpoint}/openai/deployments/{settings.azure_openai_deployment}/chat/completions?api-version=2024-02-15-preview"

        headers = {
            "api-key": settings.azure_openai_api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "messages": [
                {"role": "system", "content": "You are a document analysis assistant for tenant rights. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
            else:
                return None

    async def _call_groq(self, prompt: str, settings) -> dict:
        """Call Groq API for fast, affordable text analysis."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": settings.groq_model or "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a document analysis assistant for tenant rights. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
            else:
                raise Exception(f"Groq API error: {response.status_code}")

    async def _call_ollama(self, prompt: str, settings) -> Optional[dict]:
        """Call local Ollama for free, private text analysis."""
        base_url = settings.ollama_base_url or "http://localhost:11434"
        model = settings.ollama_model or "llama3.2"
        
        # Quick check if Ollama is running
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{base_url}/api/tags")
                if r.status_code != 200:
                    return None
        except Exception:
            return None

        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": f"You are a document analysis assistant. Respond with valid JSON only.\n\n{prompt}",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_predict": 1000,
            }
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "{}")
                # Clean up
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                return json.loads(content.strip())
            else:
                raise Exception(f"Ollama error: {response.status_code}")

    def _rule_based_classify(self, text: str) -> dict:
        """
        World-class document recognition using multi-layered analysis:
        1. Structural Analysis - Document layout, headers, signatures
        2. Contextual Analysis - Surrounding text, document flow  
        3. Keyword Pattern Matching - Legal terminology with weights
        4. Reasoning Logic - Cross-referencing signals for confidence
        5. Entity Extraction - Parties, dates, amounts with context
        
        Specifically tuned for Minnesota tenant/eviction court documents.
        """
        import re
        from app.services.document_recognition import recognize_document, DocumentType as NewDocType
        
        # Extract from the full prompt text (includes filename)
        filename_match = re.search(r'Document filename:\s*(.+)', text)
        filename = filename_match.group(1).strip() if filename_match else ""
        
        # Get document text section
        text_section_match = re.search(r'Document text:\s*(.+)', text, re.DOTALL)
        doc_text = text_section_match.group(1) if text_section_match else text
        
        # ======================================================================
        # USE NEW ADVANCED RECOGNITION ENGINE
        # ======================================================================
        try:
            result = recognize_document(doc_text, filename)
            
            # Map new document types to legacy format
            type_mapping = {
                NewDocType.SUMMONS: "court_filing",
                NewDocType.COMPLAINT: "court_filing",
                NewDocType.EVICTION_FILING: "court_filing",
                NewDocType.MOTION: "court_filing",
                NewDocType.COURT_ORDER: "court_filing",
                NewDocType.JUDGMENT: "court_filing",
                NewDocType.WRIT: "court_filing",
                NewDocType.SUBPOENA: "court_filing",
                NewDocType.ANSWER: "court_filing",
                NewDocType.AFFIDAVIT: "court_filing",
                NewDocType.LEASE: "lease",
                NewDocType.EVICTION_NOTICE: "notice",
                NewDocType.RENT_INCREASE: "notice",
                NewDocType.NOTICE_TO_QUIT: "notice",
                NewDocType.LATE_NOTICE: "notice",
                NewDocType.LEASE_VIOLATION: "notice",
                NewDocType.NON_RENEWAL: "notice",
                NewDocType.ENTRY_NOTICE: "notice",
                NewDocType.RECEIPT: "receipt",
                NewDocType.INVOICE: "receipt",
                NewDocType.LEDGER: "receipt",
                NewDocType.DEPOSIT_STATEMENT: "receipt",
                NewDocType.INSPECTION: "inspection",
                NewDocType.CONDITION_REPORT: "inspection",
                NewDocType.REPAIR_REQUEST: "repair_request",
                NewDocType.WORK_ORDER: "repair_request",
                NewDocType.LETTER: "letter",
                NewDocType.EMAIL: "letter",
                NewDocType.TEXT_MESSAGE: "communication",
                NewDocType.PHOTO: "photo",
                NewDocType.VIDEO: "photo",
                NewDocType.UNKNOWN: "unknown",
            }
            
            doc_type = type_mapping.get(result.doc_type, "unknown")
            confidence = result.confidence
            title = result.title
            summary = result.summary
            
            # Convert entities to legacy format
            key_dates = result.to_dict().get("key_dates", [])
            key_parties = result.to_dict().get("key_parties", [])
            key_amounts = result.to_dict().get("key_amounts", [])
            key_terms = result.key_terms
            
            # Log reasoning chain for debugging
            if result.reasoning_chain:
                logger.debug(f"Recognition reasoning: {result.reasoning_chain}")
            
            # Add urgency info to summary if critical
            if result.urgency_level in ("critical", "high"):
                if result.has_deadline and result.days_to_respond is not None:
                    if result.days_to_respond < 0:
                        summary = f"⚠️ URGENT: Deadline has PASSED! {summary}"
                    elif result.days_to_respond <= 3:
                        summary = f"⚠️ CRITICAL: Only {result.days_to_respond} days to respond! {summary}"
                    elif result.days_to_respond <= 7:
                        summary = f"⚠️ URGENT: {result.days_to_respond} days to respond. {summary}"
            
            return {
                "doc_type": doc_type,
                "confidence": confidence,
                "title": title,
                "summary": summary,
                "key_dates": key_dates[:10],
                "key_parties": key_parties[:5],
                "key_amounts": key_amounts[:10],
                "key_terms": key_terms[:10],
                "detailed_type": result.doc_type.value,
                "category": result.category.value,
                "urgency_level": result.urgency_level,
                "reasoning": result.reasoning_chain[:5] if result.reasoning_chain else [],
            }
            
        except Exception as e:
            logger.warning(f"Advanced recognition failed, using legacy fallback: {e}")
            # Fall through to legacy classification below
        
        # ======================================================================
        # LEGACY FALLBACK (kept for safety)
        # ======================================================================
        text_lower = text.lower()
        filename_lower = filename.lower()
        doc_text_lower = doc_text.lower()

        # Initialize results
        doc_type = "unknown"
        confidence = 0.3
        title = "Document"
        summary = ""
        key_dates = []
        key_parties = []
        key_amounts = []
        key_terms = []
        
        # =================================================================
        # COURT DOCUMENT DETECTION (HIGH PRIORITY)
        # =================================================================
        court_indicators = {
            "summons": ["summons", "you are hereby summoned", "you are being sued", "you must respond"],
            "complaint": ["complaint", "plaintiff", "defendant", "cause of action", "wherefore"],
            "eviction_action": ["unlawful detainer", "eviction", "recovery of premises", "writ of restitution"],
            "motion": ["motion to", "motion for", "moves the court", "hereby moves"],
            "order": ["it is ordered", "hereby ordered", "order of court", "court order"],
            "judgment": ["judgment", "judgment is entered", "judgment for", "default judgment"],
            "answer": ["answer to complaint", "defendant answers", "admits", "denies"],
            "notice_of_hearing": ["hearing", "appear before", "scheduled for hearing"],
        }
        
        # Check for court filing indicators
        is_court_doc = False
        court_doc_subtype = ""
        
        # Minnesota court identifiers
        if any(x in doc_text_lower for x in ["district court", "state of minnesota", "county of", "case no", "court file"]):
            is_court_doc = True
            confidence = 0.7
            
        # Check specific court document types
        for subtype, keywords in court_indicators.items():
            if any(kw in doc_text_lower for kw in keywords):
                is_court_doc = True
                court_doc_subtype = subtype
                confidence = 0.85
                break
        
        if is_court_doc:
            doc_type = "court_filing"
            
            # Generate specific title based on subtype
            if court_doc_subtype == "summons":
                title = "Court Summons"
                summary = "This is a court summons requiring you to respond to a lawsuit. You must respond within the time limit specified."
            elif court_doc_subtype == "complaint":
                title = "Civil Complaint"
                summary = "This is a legal complaint filed against you. It outlines the claims being made."
            elif court_doc_subtype == "eviction_action":
                title = "Eviction Action"
                summary = "This is an eviction lawsuit. The landlord is seeking to remove you from the property through court action."
            elif court_doc_subtype == "motion":
                title = "Court Motion"
                summary = "This is a motion filed with the court requesting specific action."
            elif court_doc_subtype == "order":
                title = "Court Order"
                summary = "This is a court order. You must comply with its terms."
            elif court_doc_subtype == "judgment":
                title = "Court Judgment"
                summary = "This is a judgment from the court. It may require payment or action."
            else:
                title = "Court Filing"
                summary = "This is a court document related to legal proceedings."
                
            # Extract case number
            case_patterns = [
                r'(?:case\s*(?:no\.?|number|#)?|file\s*(?:no\.?|number))\s*[:.]?\s*([A-Z0-9\-]+)',
                r'(\d{2}[A-Z]{2}-[A-Z]{2}-\d{2,4}-\d+)',  # Minnesota format: 19AV-CV-25-3477
                r'([A-Z]+\d+[-/]\d+)',
            ]
            for pattern in case_patterns:
                match = re.search(pattern, doc_text, re.IGNORECASE)
                if match:
                    key_terms.append(f"Case: {match.group(1)}")
                    break
        
        # =================================================================
        # LEASE/RENTAL AGREEMENT
        # =================================================================
        elif any(w in doc_text_lower for w in [
            "lease agreement", "rental agreement", "tenancy agreement",
            "residential lease", "month-to-month", "term of lease",
            "landlord agrees to rent", "tenant agrees to rent"
        ]):
            doc_type = "lease"
            confidence = 0.9
            title = "Lease Agreement"
            summary = "This is a rental/lease agreement outlining the terms of your tenancy."
            
        # =================================================================
        # NOTICE DOCUMENTS
        # =================================================================
        elif any(w in doc_text_lower for w in [
            "notice to quit", "eviction notice", "notice to vacate",
            "pay or quit", "notice to terminate", "cure or quit",
            "notice of termination", "three day notice", "14 day notice",
            "30 day notice", "notice of non-renewal"
        ]):
            doc_type = "notice"
            confidence = 0.9
            title = "Landlord Notice"
            
            # Determine notice type
            if any(w in doc_text_lower for w in ["pay or quit", "pay rent", "rent due"]):
                title = "Pay or Quit Notice"
                summary = "This is a notice to pay overdue rent or vacate the premises."
            elif any(w in doc_text_lower for w in ["cure or quit", "violation", "breach"]):
                title = "Cure or Quit Notice"
                summary = "This is a notice to correct a lease violation or vacate."
            elif "non-renewal" in doc_text_lower:
                title = "Non-Renewal Notice"
                summary = "This is a notice that your lease will not be renewed."
            else:
                summary = "This is a notice from your landlord regarding tenancy."
                
        # =================================================================
        # RECEIPT/PAYMENT
        # =================================================================
        elif any(w in doc_text_lower for w in [
            "receipt", "payment received", "amount paid", "paid in full",
            "rent payment", "deposit received"
        ]):
            doc_type = "receipt"
            confidence = 0.8
            title = "Payment Receipt"
            summary = "This is a receipt for payment made."
            
        # =================================================================
        # REPAIR REQUEST
        # =================================================================
        elif any(w in doc_text_lower for w in [
            "repair request", "maintenance request", "work order",
            "needs repair", "broken", "not working", "please fix"
        ]):
            doc_type = "repair_request"
            confidence = 0.8
            title = "Repair Request"
            summary = "This is a maintenance or repair request."
            
        # =================================================================
        # INSPECTION REPORT
        # =================================================================
        elif any(w in doc_text_lower for w in [
            "inspection", "walkthrough", "condition report",
            "move-in inspection", "move-out inspection"
        ]):
            doc_type = "inspection"
            confidence = 0.8
            title = "Inspection Report"
            summary = "This is a property inspection or condition report."
            
        # =================================================================
        # COMMUNICATION/LETTER
        # =================================================================
        elif any(w in doc_text_lower for w in [
            "dear tenant", "dear landlord", "to whom it may concern",
            "regarding your", "this letter"
        ]):
            doc_type = "letter"
            confidence = 0.7
            title = "Correspondence"
            summary = "This is correspondence related to your tenancy."
        
        # =================================================================
        # EXTRACT DATES
        # =================================================================
        date_patterns = [
            # Full dates: December 3, 2025 or Dec 3, 2025
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', 'long'),
            # Short dates: 12/3/2025
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', 'short'),
            # ISO dates: 2025-12-03
            (r'(\d{4})-(\d{2})-(\d{2})', 'iso'),
        ]
        
        month_map = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12'
        }
        
        found_dates = set()
        for pattern, fmt in date_patterns:
            for match in re.finditer(pattern, doc_text, re.IGNORECASE):
                try:
                    if fmt == 'long':
                        month = month_map[match.group(1).lower()]
                        day = match.group(2).zfill(2)
                        year = match.group(3)
                        date_str = f"{year}-{month}-{day}"
                    elif fmt == 'short':
                        month = match.group(1).zfill(2)
                        day = match.group(2).zfill(2)
                        year = match.group(3)
                        date_str = f"{year}-{month}-{day}"
                    else:  # iso
                        date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    
                    if date_str not in found_dates:
                        found_dates.add(date_str)
                        # Get context for description
                        start = max(0, match.start() - 50)
                        end = min(len(doc_text), match.end() + 50)
                        context = doc_text[start:end].lower()
                        
                        desc = "Date mentioned"
                        if any(w in context for w in ["filed", "filing"]):
                            desc = "Filing date"
                        elif any(w in context for w in ["hearing", "appear", "court date"]):
                            desc = "Court hearing date"
                        elif any(w in context for w in ["deadline", "must", "by", "before"]):
                            desc = "Deadline"
                        elif any(w in context for w in ["vacate", "move out", "quit"]):
                            desc = "Move-out date"
                        elif any(w in context for w in ["lease", "term", "begin", "start"]):
                            desc = "Lease term date"
                        elif any(w in context for w in ["due", "payment", "rent"]):
                            desc = "Payment due date"
                            
                        key_dates.append({"date": date_str, "description": desc})
                except:
                    continue
        
        # =================================================================
        # EXTRACT PARTIES
        # =================================================================
        party_patterns = [
            (r'(?:plaintiff|petitioner)[:\s]+([A-Z][A-Za-z\s,\.]+?)(?:\n|$|vs|v\.)', 'landlord'),
            (r'(?:defendant|respondent)[:\s]+([A-Z][A-Za-z\s,\.]+?)(?:\n|$)', 'tenant'),
            (r'(?:landlord|lessor|property owner)[:\s]+([A-Z][A-Za-z\s,\.]+?)(?:\n|$)', 'landlord'),
            (r'(?:tenant|lessee|renter)[:\s]+([A-Z][A-Za-z\s,\.]+?)(?:\n|$)', 'tenant'),
        ]
        
        for pattern, role in party_patterns:
            match = re.search(pattern, doc_text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip().rstrip(',.')
                if len(name) > 2 and len(name) < 100:
                    key_parties.append({"name": name, "role": role})
        
        # =================================================================
        # EXTRACT AMOUNTS
        # =================================================================
        amount_patterns = [
            (r'\$\s*([\d,]+\.?\d*)', None),
            (r'([\d,]+\.?\d*)\s*dollars?', None),
        ]
        
        found_amounts = set()
        for pattern, _ in amount_patterns:
            for match in re.finditer(pattern, doc_text, re.IGNORECASE):
                try:
                    amount_str = match.group(1).replace(',', '')
                    amount = float(amount_str)
                    if amount > 0 and amount < 1000000 and amount not in found_amounts:
                        found_amounts.add(amount)
                        
                        # Get context for description
                        start = max(0, match.start() - 50)
                        end = min(len(doc_text), match.end() + 50)
                        context = doc_text[start:end].lower()
                        
                        desc = "Amount"
                        if any(w in context for w in ["rent", "monthly"]):
                            desc = "Rent amount"
                        elif any(w in context for w in ["deposit", "security"]):
                            desc = "Security deposit"
                        elif any(w in context for w in ["fee", "late"]):
                            desc = "Late fee"
                        elif any(w in context for w in ["damage", "repair"]):
                            desc = "Damages"
                        elif any(w in context for w in ["owe", "owed", "due", "balance"]):
                            desc = "Amount owed"
                        elif any(w in context for w in ["judgment", "award"]):
                            desc = "Judgment amount"
                            
                        key_amounts.append({"amount": f"${amount:,.2f}", "description": desc})
                except:
                    continue
        
        # =================================================================
        # EXTRACT KEY TERMS
        # =================================================================
        legal_terms = [
            "unlawful detainer", "writ of restitution", "default judgment",
            "summary judgment", "service of process", "statute of limitations",
            "covenant", "warranty of habitability", "constructive eviction",
            "security deposit", "reasonable notice", "quiet enjoyment",
            "tenant rights", "landlord obligations", "breach of lease"
        ]
        
        for term in legal_terms:
            if term in doc_text_lower:
                key_terms.append(term.title())
        
        # Set default title from filename if still generic
        if title == "Document" and filename:
            # Clean up filename for display
            clean_name = filename.replace('_', ' ').replace('-', ' ')
            clean_name = re.sub(r'\.(pdf|jpg|png|doc|docx|txt)$', '', clean_name, flags=re.IGNORECASE)
            if len(clean_name) > 5:
                title = clean_name[:50]
        
        # Generate summary if empty
        if not summary:
            summary = f"Analyzed document with {len(key_dates)} dates, {len(key_parties)} parties, and {len(key_amounts)} amounts detected."

        return {
            "doc_type": doc_type,
            "confidence": confidence,
            "title": title,
            "summary": summary,
            "key_dates": key_dates[:10],  # Limit to 10
            "key_parties": key_parties[:5],
            "key_amounts": key_amounts[:10],
            "key_terms": key_terms[:10]
        }
    
    async def quick_classify(self, text: str) -> tuple[DocumentType, float]:
        """Quick classification without full extraction."""
        result = self._rule_based_classify(text)
        return DocumentType(result["doc_type"]), result["confidence"]


# Singleton instance
_azure_ai: Optional[AzureAIService] = None


def get_azure_ai() -> AzureAIService:
    """Get or create Azure AI service instance."""
    global _azure_ai
    if _azure_ai is None:
        _azure_ai = AzureAIService()
    return _azure_ai
