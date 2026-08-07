"""add context_facts and tenant_stories tables for Context Engine

Creates the two PostgreSQL tables backing the Context Engine module:

- context_facts: cached verified facts from external sources
  (MN Revisor, HUD, EPA ECHO, CourtListener, MN Courts, etc.)
  Every fact has a source_url — no hallucination.
  Facts expire after 7 days (configurable via DEFAULT_TTL_DAYS in cache.py).

- tenant_stories: moderated tenant stories
  Anonymized by default. Surfaces after task completion.
  Story frame: `avoided_court` is the hero, not "I won".
  Pending moderation — not published until admin reviews.

Both tables are declared on the SQLAlchemy Base.metadata in
app/modules/context_engine/models.py. Local dev creates them via
Base.metadata.create_all(), but production runs alembic migrations
exclusively, so this migration is required for Render.

Revision ID: 20260624_add_context_engine
Revises: e8e919671d1a
Create Date: 2026-06-24

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260624_add_context_engine"
down_revision: str | Sequence[str] | None = "e8e919671d1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create context_facts and tenant_stories tables."""
    # context_facts — verified fact cache
    op.create_table(
        "context_facts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subject", sa.String(length=50), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False, server_default="MN"),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("citation", sa.Text(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("verified_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_context_facts_subject", "context_facts", ["subject"])
    op.create_index("ix_context_facts_jurisdiction", "context_facts", ["jurisdiction"])
    op.create_index("ix_context_facts_expires_at", "context_facts", ["expires_at"])
    op.create_index("ix_context_facts_subject_jur", "context_facts", ["subject", "jurisdiction"])

    # tenant_stories — moderated tenant stories
    op.create_table(
        "tenant_stories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subject", sa.String(length=50), nullable=False),
        sa.Column("jurisdiction", sa.String(length=10), nullable=False, server_default="MN"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(length=50), nullable=False, server_default="avoided_court"),
        sa.Column("is_anonymized", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_moderated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("submitted_by", sa.String(length=128), nullable=True),
        sa.Column("moderated_by", sa.String(length=128), nullable=True),
        sa.Column("moderated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_stories_subject", "tenant_stories", ["subject"])
    op.create_index("ix_tenant_stories_jurisdiction", "tenant_stories", ["jurisdiction"])
    op.create_index("ix_tenant_stories_is_moderated", "tenant_stories", ["is_moderated"])
    op.create_index("ix_tenant_stories_is_published", "tenant_stories", ["is_published"])
    op.create_index("ix_tenant_stories_subject_pub", "tenant_stories", ["subject", "is_published"])


def downgrade() -> None:
    """Drop context_facts and tenant_stories tables."""
    op.drop_index("ix_tenant_stories_subject_pub", table_name="tenant_stories")
    op.drop_index("ix_tenant_stories_is_published", table_name="tenant_stories")
    op.drop_index("ix_tenant_stories_is_moderated", table_name="tenant_stories")
    op.drop_index("ix_tenant_stories_jurisdiction", table_name="tenant_stories")
    op.drop_index("ix_tenant_stories_subject", table_name="tenant_stories")
    op.drop_table("tenant_stories")

    op.drop_index("ix_context_facts_subject_jur", table_name="context_facts")
    op.drop_index("ix_context_facts_expires_at", table_name="context_facts")
    op.drop_index("ix_context_facts_jurisdiction", table_name="context_facts")
    op.drop_index("ix_context_facts_subject", table_name="context_facts")
    op.drop_table("context_facts")
