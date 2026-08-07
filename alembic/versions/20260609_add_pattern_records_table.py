"""Add pattern_records table

Revision ID: 20260609_add_pattern_records
Revises: 20260609_add_feature_flags
Create Date: 2026-06-09 00:35:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260609_add_pattern_records"
down_revision = "20260609_add_feature_flags"
branch_labels = None
depends_on = None


def upgrade():
    # Create pattern_records table
    op.create_table(
        "pattern_records",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("pattern_id", sa.String(length=50), nullable=False),
        sa.Column("pattern_type", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("case_id", sa.String(length=100), nullable=True),
        sa.Column("source_document_id", sa.String(length=200), nullable=True),
        sa.Column("pattern_data", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("confidence_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_by", sa.String(length=50), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for common queries
    op.create_index("ix_pattern_records_pattern_id", "pattern_records", ["pattern_id"], unique=False)

    op.create_index("ix_pattern_records_user_id", "pattern_records", ["user_id"], unique=False)

    op.create_index("ix_pattern_records_case_id", "pattern_records", ["case_id"], unique=False)

    op.create_index("ix_pattern_records_pattern_type", "pattern_records", ["pattern_type"], unique=False)

    op.create_index("ix_pattern_records_extracted_at", "pattern_records", ["extracted_at"], unique=False)

    op.create_index("ix_pattern_records_verified", "pattern_records", ["verified"], unique=False)

    # Composite index for user + pattern queries
    op.create_index("ix_pattern_records_user_pattern", "pattern_records", ["user_id", "pattern_type"], unique=False)


def downgrade():
    op.drop_index("ix_pattern_records_user_pattern", table_name="pattern_records")
    op.drop_index("ix_pattern_records_verified", table_name="pattern_records")
    op.drop_index("ix_pattern_records_extracted_at", table_name="pattern_records")
    op.drop_index("ix_pattern_records_pattern_type", table_name="pattern_records")
    op.drop_index("ix_pattern_records_case_id", table_name="pattern_records")
    op.drop_index("ix_pattern_records_user_id", table_name="pattern_records")
    op.drop_index("ix_pattern_records_pattern_id", table_name="pattern_records")
    op.drop_table("pattern_records")
