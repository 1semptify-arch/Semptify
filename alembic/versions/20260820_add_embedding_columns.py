"""add embedding columns for context_explanation_entries and context_facts

Adds dialect-aware ``AsymmetricVector`` columns so the same code runs on
SQLite (dev) and PostgreSQL + pgvector (production). Embeddings are
pre-computed at authoring time with all-MiniLM-L6-v2.

Revision ID: 20260820_add_embedding_columns
Revises: 7f002a47b44a
Create Date: 2026-08-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.database_types import AsymmetricVector
from app.modules.context_engine.embedding_model import EMBEDDING_DIMENSIONS

revision: str = "20260820_add_embedding_columns"
down_revision: Union[str, Sequence[str], None] = "7f002a47b44a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add embedding columns."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # pgvector must be enabled before a VECTOR column can be created.
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # SQLite does not support plain ALTER TABLE ADD COLUMN with some constructs,
    # but SQLAlchemy's JSON type maps to a TEXT affinity and works with
    # batch_alter_table to avoid reflection issues.
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("context_explanation_entries") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "embedding",
                    AsymmetricVector(EMBEDDING_DIMENSIONS),
                    nullable=True,
                )
            )
        with op.batch_alter_table("context_facts") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "embedding",
                    AsymmetricVector(EMBEDDING_DIMENSIONS),
                    nullable=True,
                )
            )
    else:
        op.add_column(
            "context_explanation_entries",
            sa.Column(
                "embedding",
                AsymmetricVector(EMBEDDING_DIMENSIONS),
                nullable=True,
            ),
        )
        op.add_column(
            "context_facts",
            sa.Column(
                "embedding",
                AsymmetricVector(EMBEDDING_DIMENSIONS),
                nullable=True,
            ),
        )


def downgrade() -> None:
    """Drop embedding columns."""
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("context_explanation_entries") as batch_op:
            batch_op.drop_column("embedding")
        with op.batch_alter_table("context_facts") as batch_op:
            batch_op.drop_column("embedding")
    else:
        op.drop_column("context_explanation_entries", "embedding")
        op.drop_column("context_facts", "embedding")
