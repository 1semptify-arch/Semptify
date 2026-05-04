"""drop_user_display_name_avatar_url

Remove display_name and avatar_url from users table.
These fields are fetched from the OAuth provider at login time — not stored on our servers.

Revision ID: 20250504_drop_display
Revises: 81c36d8f2466
Create Date: 2026-05-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250504_drop_display'
down_revision: Union[str, Sequence[str], None] = '81c36d8f2466'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop display_name and avatar_url from users — fetched from provider at login, not stored."""
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'avatar_url')


def downgrade() -> None:
    """Restore display_name and avatar_url if rolling back."""
    op.add_column('users', sa.Column('display_name', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(500), nullable=True))
