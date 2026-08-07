"""add deep_ocr_status to documents and document_pipeline_index

Revision ID: 573f2a9e816f
Revises: 20260624_add_context_engine
Create Date: 2026-07-19 21:05:18.753426

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "573f2a9e816f"
down_revision: str | Sequence[str] | None = "20260624_add_context_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add deep_ocr_status column to Document and DocumentPipelineIndex."""
    op.add_column(
        "documents",
        sa.Column("deep_ocr_status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
    )
    op.add_column(
        "document_pipeline_index",
        sa.Column("deep_ocr_status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
    )


def downgrade() -> None:
    """Remove deep_ocr_status columns."""
    op.drop_column("document_pipeline_index", "deep_ocr_status")
    op.drop_column("documents", "deep_ocr_status")
