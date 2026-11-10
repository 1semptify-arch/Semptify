"""Add Executive Administration tables — the organization's books and records.

Org-level data only (the nonprofit's own ledger, board, meetings, filings).
No tenant data, no user linkage.

Revision ID: 20261108_executive_admin
Revises: 20261026_voice_posts
Create Date: 2026-11-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261108_executive_admin"
down_revision: Union[str, Sequence[str], None] = "20261026_voice_posts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exec_ledger_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("functional_class", sa.String(length=30), nullable=True),
        sa.Column("fund", sa.String(length=80), nullable=False, server_default="unrestricted"),
        sa.Column("counterparty", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("goods_services_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("acknowledged_on", sa.Date(), nullable=True),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exec_ledger_entries_entry_date", "exec_ledger_entries", ["entry_date"])
    op.create_index("ix_exec_ledger_entries_kind", "exec_ledger_entries", ["kind"])

    op.create_table(
        "exec_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exec_records_kind", "exec_records", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_exec_records_kind", table_name="exec_records")
    op.drop_table("exec_records")
    op.drop_index("ix_exec_ledger_entries_kind", table_name="exec_ledger_entries")
    op.drop_index("ix_exec_ledger_entries_entry_date", table_name="exec_ledger_entries")
    op.drop_table("exec_ledger_entries")
