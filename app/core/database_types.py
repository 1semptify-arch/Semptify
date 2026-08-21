"""Dialect-aware database types for Semptify.

`AsymmetricVector` uses pgvector's `VECTOR` type on PostgreSQL and a JSON
blob on SQLite. This lets the same model run in local dev (SQLite) and
Render production (PostgreSQL) without code branches in retrieval logic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import JSON, TypeDecorator

logger = logging.getLogger(__name__)

try:
    from pgvector.sqlalchemy import VECTOR as PgVector
except ImportError:  # pragma: no cover
    PgVector = None
    logger.warning("pgvector package not installed; vector columns will fall back to JSON")


class AsymmetricVector(TypeDecorator):
    """Vector type that is pgvector(384) on PostgreSQL and JSON on SQLite.

    Values are normalized to plain ``list[float]`` on the way in and out,
    so callers always see a normal Python list regardless of dialect.
    """

    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int = 384, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect: Any) -> Any:
        if PgVector is not None and dialect.name == "postgresql":
            return PgVector(self.dimensions)
        return JSON()

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            return [float(v) for v in value]
        if isinstance(value, str):
            # Allow JSON-encoded vectors to be passed directly.
            return json.loads(value)
        raise ValueError(f"AsymmetricVector expects a list of floats, got {type(value).__name__}")

    def process_result_value(self, value: Any, dialect: Any) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, list):
            return [float(v) for v in value]
        if isinstance(value, str):
            return [float(v) for v in json.loads(value)]
        raise ValueError(f"AsymmetricVector result was not a list, got {type(value).__name__}")
