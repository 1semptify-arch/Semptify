"""
Semptify - Groq AI Service
Fast, affordable AI for document classification and extraction.
Uses Llama 3.1 70B via Groq's ultra-fast inference.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import get_settings


@dataclass
class GroqAnalysisResult:
    """Result from Groq document analysis."""
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


class GroqAIService:
    """
    Groq AI client for document processing.
    Uses Llama 3.1 70B for fast, accurate document analysis.
    """

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    # Model options (sorted by capability)
    MODELS = {
        "fast": "llama-3.1-8b-instant",      # Fastest, good for simple tasks
        "balanced": "llama-3.3-70b-versatile", # Best balance of speed/quality
        "best": "llama-3.3-70b-versatile",     # Highest quality
    }

    def __init__(self):
        settings = get_settings()
        self.api_key = getattr(settings, 'groq_api_key', None)
        self.model = self.MODELS["balanced"]  # Default to 70B
        
    @property
    def is_available(self) -> bool:
        """Check if Groq is configured."""
        return bool(self.api_key)

    async def analyze_document(
        self,
        text: str,
        filename: str,
        doc_hint: Optional[str] = None
    ) -> GroqAnalysisResult:
        """
        Analyze a document using Groq AI.
        
        Args:
            text: The extracted text from the document
            filename: Original filename (helps with classification)
            doc_hint: Optional hint about document type
            
        Returns:
            GroqAnalysisResult with classification and extracted data
        """
        if not self.is_available:
            return self._fallback_analysis(text, filename)

        prompt = self._build_analysis_prompt(text, filename, doc_hint)
        
        try:
            result = await self._call_groq(prompt)
            return self._parse_result(result)
        except Exception as e:
            print(f"Groq analysis failed: {e}")
            return self._fallback_analysis(text, filename)

    def _build_analysis_prompt(
        self,
        text: str,
        filename: str,
        doc_hint: Optional[str] = None
    ) -> str:
        """Build the analysis prompt for Groq."""
        
        # Truncate text if too long (Groq has 8K context for most models)
        max_chars = 6000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... document truncated ...]"

        hint_text = f"\nHint: This might be a {doc_hint}." if doc_hint else ""

        return f"""You are a legal document analyst specializing in tenant rights and housing law.
Analyze this document and extract key information.{hint_text}

Document filename: {filename}

Document text:
---
{text}
---

Respond ONLY with valid JSON in this exact format:
{{
    "doc_type": "eviction_notice|court_summons|lease|notice_to_quit|rent_increase|repair_request|receipt|inspection|security_deposit|correspondence|other",
    "confidence": 0.0 to 1.0,
    "title": "Brief descriptive title for this document",
    "summary": "2-3 sentence plain-English summary of what this document says and means for the tenant",
    "key_dates": [
        {{"date": "YYYY-MM-DD", "description": "what this date means", "is_deadline": true/false}}
    ],
    "key_parties": [
        {{"name": "Person or Company Name", "role": "landlord|tenant|attorney|court|property_manager|other"}}
    ],
    "key_amounts": [
        {{"amount": 1234.56, "description": "what this amount is for"}}
    ],
    "key_terms": ["important term 1", "important term 2"],
    "issues_detected": [
        {{
            "severity": "critical|high|medium|low",
            "title": "Issue title",
            "description": "What the issue is and why it matters",
            "legal_basis": "Relevant law citation if applicable"
        }}
    ]
}}

Important:
- For eviction notices, check if notice periods comply with Minnesota law (14 days for non-payment, 30 days for month-to-month)
- Flag any illegal self-help eviction threats (lockouts, utility shutoffs)
- Identify upcoming deadlines that require tenant action
- Note any potentially unenforceable clauses"""

    async def _call_groq(self, prompt: str) -> dict:
        """Make API call to Groq."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a legal document analyst. Always respond with valid JSON only, no other text."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low temp for consistent extraction
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Groq API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)

    def _parse_result(self, data: dict) -> GroqAnalysisResult:
        """Parse Groq response into GroqAnalysisResult."""
        return GroqAnalysisResult(
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

    def _fallback_analysis(self, text: str, filename: str) -> GroqAnalysisResult:
        """Rule-based fallback when Groq is unavailable."""
        text_lower = text.lower()
        filename_lower = filename.lower()

        # Determine document type by keywords
        doc_type = "other"
        confidence = 0.5

        if any(w in text_lower for w in ["eviction", "evict", "unlawful detainer"]):
            doc_type = "eviction_notice"
            confidence = 0.85
        elif any(w in text_lower for w in ["summons", "court date", "appear in court", "hearing"]):
            doc_type = "court_summons"
            confidence = 0.85
        elif any(w in text_lower for w in ["lease agreement", "rental agreement", "tenancy agreement"]):
            doc_type = "lease"
            confidence = 0.9
        elif any(w in text_lower for w in ["notice to quit", "vacate", "terminate tenancy"]):
            doc_type = "notice_to_quit"
            confidence = 0.85
        elif any(w in text_lower for w in ["rent increase", "new rent amount"]):
            doc_type = "rent_increase"
            confidence = 0.8
        elif any(w in text_lower for w in ["receipt", "payment received", "amount paid"]):
            doc_type = "receipt"
            confidence = 0.8
        elif any(w in text_lower for w in ["repair", "maintenance request", "work order"]):
            doc_type = "repair_request"
            confidence = 0.8
        elif any(w in text_lower for w in ["security deposit", "itemization", "deductions"]):
            doc_type = "security_deposit"
            confidence = 0.8

        return GroqAnalysisResult(
            doc_type=doc_type,
            confidence=confidence,
            title=filename,
            summary="Document analyzed using rule-based classification (AI unavailable)",
            key_dates=[],
            key_parties=[],
            key_amounts=[],
            key_terms=[],
            issues_detected=[],
            analyzed_at=datetime.now(timezone.utc)
        )

    async def quick_classify(self, text: str) -> tuple[str, float]:
        """Quick classification without full extraction."""
        if not self.is_available:
            result = self._fallback_analysis(text, "")
            return result.doc_type, result.confidence

        prompt = f"""Classify this legal document. Respond with JSON only:
{{"doc_type": "eviction_notice|court_summons|lease|notice_to_quit|rent_increase|repair_request|receipt|inspection|security_deposit|correspondence|other", "confidence": 0.0-1.0}}

Text (first 1000 chars):
{text[:1000]}"""

        try:
            result = await self._call_groq(prompt)
            return result.get("doc_type", "other"), result.get("confidence", 0.5)
        except Exception:
            return "other", 0.3

    async def summarize_for_tenant(self, text: str, doc_type: str) -> str:
        """Generate a plain-English summary for the tenant."""
        if not self.is_available:
            return "AI summary unavailable. Please review the document carefully."

        prompt = f"""You are helping a tenant understand a legal document.
This is a {doc_type.replace('_', ' ')}.

Document text:
{text[:3000]}

Write a 2-3 sentence summary in simple, plain English explaining:
1. What this document is
2. What it means for the tenant
3. Any action the tenant needs to take

Be direct and helpful. Don't use legal jargon."""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self.API_URL,
                    headers=headers,
                    json={
                        "model": self.MODELS["fast"],  # Use fast model for summaries
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 300
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"].strip()
                    
        except Exception as e:
            print(f"Summary generation failed: {e}")
            
        return "Unable to generate summary. Please review the document."


# Singleton instance
_groq_service: Optional[GroqAIService] = None


def get_groq_ai() -> GroqAIService:
    """Get or create Groq AI service instance."""
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqAIService()
    return _groq_service
