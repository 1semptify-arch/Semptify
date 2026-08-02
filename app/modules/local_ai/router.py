"""
Local AI Router — Minimal stub.

The local_ai module provides a self-contained local AI integration (Ollama, LM Studio, etc.).
This router creates the API endpoints for chat, analysis, summarization, and health checks.

Note: This module is dev_only and not registered in product_manifest.py.
It is kept as a skeleton for future integration when local AI is needed.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.local_ai.config import LocalAIConfig

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    context: str | None = None


class ChatResponse(BaseModel):
    response: str
    model: str
    tokens_used: int = 0


class AnalyzeRequest(BaseModel):
    text: str
    analysis_type: str = "general"


class SummarizeRequest(BaseModel):
    text: str
    max_length: int = 500


def create_router(config: LocalAIConfig) -> APIRouter:
    """Create and return the local AI router with all endpoints."""
    router = APIRouter(prefix=config.route_prefix, tags=["Local AI"])

    @router.get("/health")
    async def health():
        return {
            "status": "ok",
            "module": "local_ai",
            "product": config.product_name,
            "model": config.model_name,
            "endpoint": config.api_endpoint,
        }

    @router.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        if not config.is_feature_enabled("chat"):
            raise HTTPException(status_code=503, detail="Chat feature not enabled")
        return ChatResponse(
            response="Local AI chat is not yet connected to a model backend.",
            model=config.model_name,
            tokens_used=0,
        )

    @router.post("/analyze")
    async def analyze(request: AnalyzeRequest):
        if not config.is_feature_enabled("analysis"):
            raise HTTPException(status_code=503, detail="Analysis feature not enabled")
        return {
            "status": "ok",
            "analysis_type": request.analysis_type,
            "summary": "Local AI analysis is not yet connected to a model backend.",
            "model": config.model_name,
        }

    @router.post("/summarize")
    async def summarize(request: SummarizeRequest):
        if not config.is_feature_enabled("summarization"):
            raise HTTPException(status_code=503, detail="Summarization feature not enabled")
        return {
            "status": "ok",
            "summary": "Local AI summarization is not yet connected to a model backend.",
            "model": config.model_name,
            "original_length": len(request.text),
        }

    return router
