"""add case_overlay_id to incidents

Adds the overlay pointer so case_builder content can live in the user's
cloud storage instead of Postgres incident_metadata.

Revision ID: 20260820_add_case_overlay_id
Revises: 20260820_add_embedding_columns
Create Date: 2026-08-20
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_add_case_overlay_id"
down_revision: str | Sequence[str] | None = "20260820_add_embedding_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add case_overlay_id column to incidents."""
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("incidents") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "case_overlay_id",
                    sa.String(36),
                    nullable=True,
                )
            )
    else:
        op.add_column(
            "incidents",
            sa.Column(
                "case_overlay_id",
                sa.String(36),
                nullable=True,
            ),
        )


def downgrade() -> None:
    """Drop case_overlay_id column from incidents."""
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("incidents") as batch_op:
            batch_op.drop_column("case_overlay_id")
    else:
        op.drop_column("incidents", "case_overlay_id")
