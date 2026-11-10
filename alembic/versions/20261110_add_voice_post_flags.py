"""Add public flag/report state to voice_posts — reader-driven review.

Flag control on /your-voice board posts: anonymous readers report a
published post that breaks the review standard (MODERATION.md), and the
flag feeds the same /admin/public-voice review queue. Reasons are stored
as a {reason_code: count} JSON object — codes only, never free text or
identities, matching the anonymous-by-design boundary on voice_posts.

Revision ID: 20261110_voice_post_flags
Revises: 20261108_executive_admin
Create Date: 2026-11-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261110_voice_post_flags"
down_revision: Union[str, Sequence[str], None] = "20261108_executive_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_posts",
        sa.Column("flag_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "voice_posts",
        sa.Column(
            "flag_reasons",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
    )
    op.add_column(
        "voice_posts",
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("voice_posts", "flagged_at")
    op.drop_column("voice_posts", "flag_reasons")
    op.drop_column("voice_posts", "flag_count")
