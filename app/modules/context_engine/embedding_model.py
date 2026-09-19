"""Singleton all-MiniLM-L6-v2 embedding model for the Context Engine.

The model is loaded once — either at application startup or on first use —
and reused for every query and every authored entry. This keeps retrieval
latency low and memory predictable.

Two backends, tried in order:

1. ``fastembed`` — ONNX Runtime build of the same model
   (``sentence-transformers/all-MiniLM-L6-v2``). No torch dependency,
   ~3-4x smaller RSS than PyTorch — this is what runs on the Render
   free-tier image (torch is excluded from requirements-render-mvp.txt
   precisely because it does not fit 512 MB). Same weights, same
   384-dim vector space as the torch build, so stored embeddings stay
   compatible.
2. ``sentence_transformers`` — the original torch backend, used in local
   dev where the full requirements.txt is installed.

Set ``EMBEDDING_MODEL_LOCAL_FILES_ONLY=true`` to forbid any network
download at load time (production images bake the weights; see
``EMBEDDING_CACHE_DIR`` in the Dockerfile). ``EMBEDDING_CACHE_DIR``
points fastembed's model cache at a shared path.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any

from app.core.runtime_profile import get_active_profile

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSIONS: int = 384
EMBEDDING_CACHE_DIR: str | None = os.getenv("EMBEDDING_CACHE_DIR") or None

# The sentence-transformers / huggingface libraries are chatty at INFO.
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

_model: Any = None
_load_lock = threading.Lock()


def _local_files_only() -> bool:
    return os.getenv("EMBEDDING_MODEL_LOCAL_FILES_ONLY", "false").lower() == "true"


def _load_fastembed() -> Any:
    """Load the model via fastembed's ONNX backend. Returns None on failure."""
    try:
        if _local_files_only():
            # fastembed has no local_files_only param; HF_HUB_OFFLINE is the
            # equivalent — huggingface_hub then fails fast instead of
            # hitting the network.
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from fastembed import TextEmbedding

        model_name = MODEL_NAME if "/" in MODEL_NAME else f"sentence-transformers/{MODEL_NAME}"
        kwargs: dict = {}
        if EMBEDDING_CACHE_DIR:
            kwargs["cache_dir"] = EMBEDDING_CACHE_DIR
        logger.info("Loading embedding model %s via fastembed (cache_dir=%s)...", model_name, EMBEDDING_CACHE_DIR)
        model = TextEmbedding(model_name=model_name, **kwargs)
        logger.info("Embedding model %s loaded (fastembed)", model_name)
        return ("fastembed", model)
    except Exception as e:
        logger.warning("Could not load embedding model %s via fastembed: %s", MODEL_NAME, e)
        return None


def _load_sentence_transformers() -> Any:
    """Load the model via sentence-transformers (torch backend). Returns None on failure."""
    try:
        from sentence_transformers import SentenceTransformer

        local_files_only = _local_files_only()
        logger.info(
            "Loading embedding model %s via sentence-transformers (local_files_only=%s)...",
            MODEL_NAME,
            local_files_only,
        )
        model = SentenceTransformer(
            MODEL_NAME, device="cpu", local_files_only=local_files_only
        )
        logger.info("Embedding model %s loaded (sentence-transformers)", MODEL_NAME)
        return ("sentence_transformers", model)
    except Exception as e:
        logger.warning("Could not load embedding model %s via sentence-transformers: %s", MODEL_NAME, e)
        return None


def _load_model() -> Any:
    """Synchronously load the embedding model, fastembed first."""
    return _load_fastembed() or _load_sentence_transformers()


def get_embedding_model() -> Any:
    """Return the singleton embedding model, loading it if necessary."""
    global _model
    if _model is not None:
        return _model

    # Honor the runtime profile: in local_dev the embedding model is
    # intentionally off, so the first user request does not pay a model
    # load or a HuggingFace/network timeout.
    if not get_active_profile().embedding_model:
        logger.debug("Embedding model disabled by runtime profile; skipping load")
        return None

    with _load_lock:
        if _model is not None:
            return _model
        _model = _load_model()
    return _model


def load_embedding_model() -> Any:
    """Eagerly load the singleton embedding model.

    Called from ``app.main:lifespan`` so the first request does not pay the
    model-load cost.
    """
    return get_embedding_model()


def _encode_sync(text: str) -> list[float] | None:
    """Encode a single string into a 384-dim embedding vector."""
    loaded = get_embedding_model()
    if loaded is None:
        return None
    backend, model = loaded
    try:
        if backend == "fastembed":
            embedding = next(iter(model.embed([text])))
        else:
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
    "EMBEDDING_CACHE_DIR",
    "get_embedding_model",
    "load_embedding_model",
    "embed_text",
]
