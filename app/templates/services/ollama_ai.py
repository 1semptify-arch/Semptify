"""
Semptify - Ollama AI Service
Free, private, local AI for document classification and extraction.
Runs entirely on your machine - data never leaves.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import get_settings


@dataclass
class OllamaAnalysisResult:
    """Result from Ollama document analysis."""
    doc_type: str
    confidence: float
    title: str
    summary: str
    key_dates: list[dict]
    key_parties: list[dict]
    key_amounts: list[dict]
    key_terms: list[str]
    issues_detected: list[dict]
    analyzed_at: datetime


class OllamaAIService:
    """
    Ollama AI client for document processing.
    Runs locally - completely free and private.
    """

    def __init__(self):
        settings = get_settings()
        self.base_url = getattr(settings, 'ollama_base_url', 'http://localhost:11434')
        self.model = getattr(settings, 'ollama_model', 'llama3.2')
        self._available: Optional[bool] = None

    @property
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        if self._available is not None:
            return self._available
        
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                r = client.get(f"{self.base_url}/api/tags")
                self._available = r.status_code == 200
        except Exception:
            self._available = False
        
        return self._available

    async def check_available(self) -> bool:
        """Async check if Ollama is running."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                self._available = r.status_code == 200
                return self._available
        except Exception:
            self._available = False
            return False

    async def analyze_document(
        self,
        text: str,
        filename: str,
        doc_hint: Optional[str] = None
    ) -> OllamaAnalysisResult:
        """
        Analyze a document using local Ollama.
        
        Args:
            text: The extracted text from the document
            filename: Original filename
            doc_hint: Optional hint about document type
            
        Returns:
            OllamaAnalysisResult with classification and extracted data
        """
        if not await self.check_available():
            return self._fallback_analysis(text, filename)

        prompt = self._build_analysis_prompt(text, filename, doc_hint)
        
        try:
            result = await self._call_ollama(prompt)
            return self._parse_result(result)
        except Exception as e:
            print(f"Ollama analysis failed: {e}")
            return self._fallback_analysis(text, filename)

    def _build_analysis_prompt(
        self,
        text: str,
        filename: str,
        doc_hint: Optional[str] = None
    ) -> str:
        """Build the analysis prompt."""
        
        # Truncate for smaller local models
        max_chars = 3000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... document truncated ...]"

        hint_text = f"\nHint: This might be a {doc_hint}." if doc_hint else ""

        return f"""Analyze this legal document for a tenant. Extract key information.{hint_text}

Filename: {filename}

Document:
---
{text}
---

Respond with ONLY valid JSON (no other text):
{{
    "doc_type": "eviction_notice|court_summons|lease|notice_to_quit|rent_increase|repair_request|receipt|inspection|security_deposit|correspondence|other",
    "confidence": 0.0 to 1.0,
    "title": "Brief title",
    "summary": "2-3 sentence plain-English summary for the tenant",
    "key_dates": [{{"date": "YYYY-MM-DD", "description": "what it means", "is_deadline": true/false}}],
    "key_parties": [{{"name": "Name", "role": "landlord|tenant|attorney|court|other"}}],
    "key_amounts": [{{"amount": 1234.56, "description": "what this is for"}}],
    "key_terms": ["term1", "term2"],
    "issues_detected": [{{"severity": "critical|high|medium|low", "title": "Issue", "description": "Details"}}]
}}

Important: Flag any illegal eviction threats (lockouts, utility shutoffs). Check notice periods (14 days for non-payment in MN)."""

    async def _call_ollama(self, prompt: str) -> dict:
        """Make API call to local Ollama."""
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_predict": 1500,
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for local
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result.get("response", "{}")
            
            # Clean up response - sometimes models add extra text
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)

    def _parse_result(self, data: dict) -> OllamaAnalysisResult:
        """Parse Ollama response into result object."""
        return OllamaAnalysisResult(
            doc_type=data.get("doc_type", "other"),
            confidence=float(data.get("confidence", 0.5)),
            title=data.get("title", "Document"),
            summary=data.get("summary", ""),
            key_dates=data.get("key_dates", []),
            key_parties=data.get("key_parties", []),
            key_amounts=data.get("key_amounts", []),
            key_terms=data.get("key_terms", []),
            issues_detected=data.get("issues_detected", []),
            analyzed_at=datetime.now(timezone.utc)
        )

    def _fallback_analysis(self, text: str, filename: str) -> OllamaAnalysisResult:
        """Rule-based fallback when Ollama is unavailable."""
        text_lower = text.lower()

        doc_type = "other"
        confidence = 0.5

        if any(w in text_lower for w in ["eviction", "evict", "unlawful detainer"]):
            doc_type = "eviction_notice"
            confidence = 0.85
        elif any(w in text_lower for w in ["summons", "court date", "appear in court"]):
            doc_type = "court_summons"
            confidence = 0.85
        elif any(w in text_lower for w in ["lease agreement", "rental agreement"]):
            doc_type = "lease"
            confidence = 0.9
        elif any(w in text_lower for w in ["notice to quit", "vacate"]):
            doc_type = "notice_to_quit"
            confidence = 0.85
        elif any(w in text_lower for w in ["rent increase"]):
            doc_type = "rent_increase"
            confidence = 0.8
        elif any(w in text_lower for w in ["receipt", "payment received"]):
            doc_type = "receipt"
            confidence = 0.8

        return OllamaAnalysisResult(
            doc_type=doc_type,
            confidence=confidence,
            title=filename,
            summary="Analyzed using rule-based classification (Ollama not running)",
            key_dates=[],
            key_parties=[],
            key_amounts=[],
            key_terms=[],
            issues_detected=[],
            analyzed_at=datetime.now(timezone.utc)
        )

    async def quick_classify(self, text: str) -> tuple[str, float]:
        """Quick classification without full extraction."""
        if not await self.check_available():
            result = self._fallback_analysis(text, "")
            return result.doc_type, result.confidence

        prompt = f"""Classify this document. Return ONLY JSON:
{{"doc_type": "eviction_notice|court_summons|lease|notice_to_quit|rent_increase|repair_request|receipt|other", "confidence": 0.0-1.0}}

Text (first 500 chars):
{text[:500]}"""

        try:
            result = await self._call_ollama(prompt)
            return result.get("doc_type", "other"), result.get("confidence", 0.5)
        except Exception:
            return "other", 0.3

    async def summarize_for_tenant(self, text: str, doc_type: str) -> str:
        """Generate a plain-English summary."""
        if not await self.check_available():
            return "AI summary unavailable. Please review the document carefully."

        prompt = f"""Summarize this {doc_type.replace('_', ' ')} for a tenant in 2-3 simple sentences.
Explain what it means and any action needed.

Document:
{text[:2000]}

Summary:"""

        try:
            url = f"{self.base_url}/api/generate"
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 200}
                })
                
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
                    
        except Exception as e:
            print(f"Summary failed: {e}")
            
        return "Unable to generate summary."


# Singleton instance
_ollama_service: Optional[OllamaAIService] = None


def get_ollama_ai() -> OllamaAIService:
    """Get or create Ollama AI service instance."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaAIService()
    return _ollama_service
