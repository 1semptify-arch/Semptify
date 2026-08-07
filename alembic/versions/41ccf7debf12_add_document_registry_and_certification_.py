"""add document_registry, certification_events, user_relationships tables

Revision ID: 41ccf7debf12
Revises: 20260614_add_fems_tables
Create Date: 2026-06-15 17:25:08.133425

SCOPED: Only creates our 3 new tables. No drops. No unrelated column changes.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "41ccf7debf12"
down_revision: str | Sequence[str] | None = "20260614_add_fems_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "certification_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vault_id", sa.String(length=256), nullable=False),
        sa.Column("user_id", sa.String(length=256), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("failure_detail", sa.String(length=1024), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("source_module", sa.String(length=64), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_certification_events_attempted_at", "certification_events", ["attempted_at"])
    op.create_index("ix_certification_events_result", "certification_events", ["result"])
    op.create_index("ix_certification_events_user_id", "certification_events", ["user_id"])
    op.create_index("ix_certification_events_vault_id", "certification_events", ["vault_id"])

    op.create_table(
        "document_registry",
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=256), nullable=False),
        sa.Column("vault_id", sa.String(length=256), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata_hash", sa.String(length=64), nullable=False),
        sa.Column("combined_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("integrity_status", sa.String(length=32), nullable=False),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False),
        sa.Column("original_document_id", sa.String(length=64), nullable=True),
        sa.Column("forgery_score", sa.Float(), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.Column("case_number", sa.String(length=64), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index("ix_document_registry_case_number", "document_registry", ["case_number"])
    op.create_index("ix_document_registry_content_hash", "document_registry", ["content_hash"])
    op.create_index("ix_document_registry_integrity_status", "document_registry", ["integrity_status"])
    op.create_index("ix_document_registry_status", "document_registry", ["status"])
    op.create_index("ix_document_registry_user_id", "document_registry", ["user_id"])
    op.create_index("ix_document_registry_vault_id", "document_registry", ["vault_id"])

    op.create_table(
        "user_relationships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("from_user_id", sa.String(length=256), nullable=False),
        sa.Column("to_user_id", sa.String(length=256), nullable=False),
        sa.Column("relationship_type", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(
            ["from_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["to_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_relationships_expires_at", "user_relationships", ["expires_at"])
    op.create_index("ix_user_relationships_from_user_id", "user_relationships", ["from_user_id"])
    op.create_index("ix_user_relationships_is_active", "user_relationships", ["is_active"])
    op.create_index("ix_user_relationships_relationship_type", "user_relationships", ["relationship_type"])
    op.create_index("ix_user_relationships_to_user_id", "user_relationships", ["to_user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_relationships_to_user_id", table_name="user_relationships")
    op.drop_index("ix_user_relationships_relationship_type", table_name="user_relationships")
    op.drop_index("ix_user_relationships_is_active", table_name="user_relationships")
    op.drop_index("ix_user_relationships_from_user_id", table_name="user_relationships")
    op.drop_index("ix_user_relationships_expires_at", table_name="user_relationships")
    op.drop_table("user_relationships")
    op.drop_index("ix_document_registry_vault_id", table_name="document_registry")
    op.drop_index("ix_document_registry_user_id", table_name="document_registry")
    op.drop_index("ix_document_registry_status", table_name="document_registry")
    op.drop_index("ix_document_registry_integrity_status", table_name="document_registry")
    op.drop_index("ix_document_registry_content_hash", table_name="document_registry")
    op.drop_index("ix_document_registry_case_number", table_name="document_registry")
    op.drop_table("document_registry")
    op.drop_index("ix_certification_events_vault_id", table_name="certification_events")
    op.drop_index("ix_certification_events_user_id", table_name="certification_events")
    op.drop_index("ix_certification_events_result", table_name="certification_events")
    op.drop_index("ix_certification_events_attempted_at", table_name="certification_events")
    op.drop_table("certification_events")
