"""
Add invite_codes table for Advocate/Legal role validation

Revision ID: 20250424_add_invite_codes
Revises: 20250422_unified_timeline_view
Create Date: 2026-04-24

This migration adds the invite_codes table for managing invite-based
role validation for Advocate and Legal users.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250424_add_invite_codes'
down_revision: Union[str, None] = '20250422_unified_timeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create invite_codes table."""
    op.create_table(
        'invite_codes',
        sa.Column('code', sa.String(32), primary_key=True),
        sa.Column('created_by', sa.String(24), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('organization_id', sa.String(50), nullable=True, index=True),
        sa.Column('organization_name', sa.String(100), nullable=True),
        sa.Column('role', sa.String(20), nullable=False, default='advocate'),
        sa.Column('max_uses', sa.Integer, nullable=False, default=1),
        sa.Column('uses_count', sa.Integer, nullable=False, default=0),
        sa.Column('used_by', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=list),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for common queries
    op.create_index('ix_invite_codes_role', 'invite_codes', ['role'])
    op.create_index('ix_invite_codes_is_active', 'invite_codes', ['is_active'])
    op.create_index('ix_invite_codes_expires_at', 'invite_codes', ['expires_at'])


def downgrade() -> None:
    """Drop invite_codes table."""
    op.drop_table('invite_codes')
