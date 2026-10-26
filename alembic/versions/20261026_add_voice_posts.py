"""Add voice_posts table — Your Voice public question/opinion board.

Public, org-facing content: anonymous questions and opinions submitted
from /your-voice about the housing bill draft and renter issues,
published with answers after review. No user linkage, no PII columns,
by design — same boundary as tool_requests.

Revision ID: 20261026_voice_posts
Revises: 20261025_tool_requests
Create Date: 2026-10-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261026_voice_posts"
down_revision: Union[str, Sequence[str], None] = "20261025_tool_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_posts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="question"),
        sa.Column("post_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("responder_label", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_voice_posts_kind", "voice_posts", ["kind"])
    op.create_index("ix_voice_posts_status", "voice_posts", ["status"])
    op.create_index("ix_voice_posts_is_published", "voice_posts", ["is_published"])
    op.create_index("ix_voice_posts_created_at", "voice_posts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_voice_posts_created_at", table_name="voice_posts")
    op.drop_index("ix_voice_posts_is_published", table_name="voice_posts")
    op.drop_index("ix_voice_posts_status", table_name="voice_posts")
    op.drop_index("ix_voice_posts_kind", table_name="voice_posts")
    op.drop_table("voice_posts")
