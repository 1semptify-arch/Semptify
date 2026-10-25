"""Add tool_requests table — anonymous public tool-request forum.

Public, org-facing content: requests submitted anonymously from
/tool-requests, published with our responses after review. No user
linkage, no PII columns, by design.

Revision ID: 20261025_tool_requests
Revises: 20261020_settlement_awareness
Create Date: 2026-10-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261025_tool_requests"
down_revision: Union[str, Sequence[str], None] = "20261020_settlement_awareness"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tool_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tool_requests_status", "tool_requests", ["status"])
    op.create_index("ix_tool_requests_is_published", "tool_requests", ["is_published"])
    op.create_index("ix_tool_requests_created_at", "tool_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_tool_requests_created_at", table_name="tool_requests")
    op.drop_index("ix_tool_requests_is_published", table_name="tool_requests")
    op.drop_index("ix_tool_requests_status", table_name="tool_requests")
    op.drop_table("tool_requests")
