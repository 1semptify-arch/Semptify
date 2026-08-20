"""Singleton all-MiniLM-L6-v2 embedding model for the Context Engine.

The model is loaded once — either at application startup or on first use —
and reused for every query and every authored entry. This keeps retrieval
latency low and memory predictable.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import cast

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSIONS: int = 384

# The sentence-transformers / huggingface libraries are chatty at INFO.
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

_model: "SentenceTransformer | None" = None
_load_lock = threading.Lock()


def _load_model() -> "SentenceTransformer | None":
    """Synchronously load the sentence-transformer model."""
    try:
        from sentence_transformers import SentenceTransformer

        local_files_only = (
            os.getenv("EMBEDDING_MODEL_LOCAL_FILES_ONLY", "false").lower() == "true"
        )
        logger.info(
            "Loading embedding model %s (local_files_only=%s)...",
            MODEL_NAME,
            local_files_only,
        )
        model = SentenceTransformer(
            MODEL_NAME, device="cpu", local_files_only=local_files_only
        )
        logger.info("Embedding model %s loaded", MODEL_NAME)
        return cast("SentenceTransformer", model)
    except Exception as e:
        logger.warning("Could not load embedding model %s: %s", MODEL_NAME, e)
        return None


def get_embedding_model() -> "SentenceTransformer | None":
    """Return the singleton embedding model, loading it if necessary."""
    global _model
    if _model is not None:
        return _model
    with _load_lock:
        if _model is not None:
            return _model
        _model = _load_model()
    return _model


def load_embedding_model() -> "SentenceTransformer | None":
    """Eagerly load the singleton embedding model.

    Called from ``app.main:lifespan`` so the first request does not pay the
    model-load cost.
    """
    return get_embedding_model()


def _encode_sync(text: str) -> list[float] | None:
    """Encode a single string into a 384-dim embedding vector."""
    model = get_embedding_model()
    if model is None:
        return None
    try:
        embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return np.asarray(embedding, dtype=float).tolist()
    except Exception as e:
        logger.warning("Embedding encoding failed for text: %s", e)
        return None


async def embed_text(text: str) -> list[float] | None:
    """Async wrapper around ``_encode_sync``.

    Encoding is CPU-bound and blocks the event loop, so it runs in the
    default thread pool.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _encode_sync, text)


__all__ = [
    "MODEL_NAME",
    "EMBEDDING_DIMENSIONS",
    "get_embedding_model",
    "load_embedding_model",
    "embed_text",
]
