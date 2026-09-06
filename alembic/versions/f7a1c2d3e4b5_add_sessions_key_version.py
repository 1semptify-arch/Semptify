"""add key_version to sessions for versioned SECRET_KEY rotation

Revision ID: f7a1c2d3e4b5
Revises: 0890abd391b2
Create Date: 2026-09-06 21:45:00.000000

Spec: handoffs/vault-security-pair-spec-2026-09-06.md (Scope A).
NULL rows = written before key versioning; decrypt falls back through
SECRET_KEY_HISTORY during the 60-day grace window.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a1c2d3e4b5'
down_revision: Union[str, Sequence[str], None] = '0890abd391b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('key_version', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'key_version')
