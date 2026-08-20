"""Pure-Python vector math for the SQLite/dev retrieval path.

PostgreSQL uses pgvector's native ``<=>`` cosine-distance operator, but the
local SQLite database has no vector extension, so we compute cosine similarity
in Python after fetching candidate rows.
"""

from __future__ import annotations

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return the cosine similarity of two equal-length vectors.

    Returns ``0.0`` if either vector is empty or has zero magnitude.
    """
    if not a or not b or len(a) != len(b):
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
