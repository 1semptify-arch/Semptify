"""add incident fca readiness columns

Revision ID: 0890abd391b2
Revises: 20260825_vault_review_catchup
Create Date: 2026-08-26 01:21:35.102888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '0890abd391b2'
down_revision: Union[str, Sequence[str], None] = '20260825_vault_review_catchup'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    """Add FCA readiness score columns to incidents."""
    bind = op.get_bind()

    columns_to_add = [
        ("fca_readiness_score", sa.Integer, {"nullable": True}),
        ("fca_readiness_updated_at", sa.DateTime, {"nullable": True, "kwargs": {"timezone": True}}),
    ]

    for col_name, col_type, options in columns_to_add:
        if _column_exists("incidents", col_name):
            continue

        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("incidents") as batch_op:
                batch_op.add_column(
                    sa.Column(col_name, col_type(**options.get("kwargs", {})), nullable=options.get("nullable", True))
                )
        else:
            op.add_column(
                "incidents",
                sa.Column(col_name, col_type(**options.get("kwargs", {})), nullable=options.get("nullable", True)),
            )


def downgrade() -> None:
    """Remove FCA readiness score columns from incidents."""
    bind = op.get_bind()

    for col_name in ("fca_readiness_score", "fca_readiness_updated_at"):
        if not _column_exists("incidents", col_name):
            continue

        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("incidents") as batch_op:
                batch_op.drop_column(col_name)
        else:
            op.drop_column("incidents", col_name)
