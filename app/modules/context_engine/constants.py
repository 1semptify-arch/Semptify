"""Leaf constants for the Context Engine.

Kept dependency-free on purpose: ``models.py`` needs ``EMBEDDING_DIMENSIONS``
at class-definition time, and importing it from ``embedding_model.py`` used to
drag ``numpy`` (and the model machinery) into every ``app.models.models``
import — i.e. into the eager app-startup path.
"""

EMBEDDING_DIMENSIONS: int = 384
