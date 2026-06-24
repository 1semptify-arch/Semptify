"""add legal_sub_role and bar_license_number to users

Merges the two existing heads (20260618_add_admin_error_queue and
20260615_add_module_registry) and adds the two columns that the User
model in app/models/models.py already declares but that were never
migrated on the production database:

- users.legal_sub_role : VARCHAR(20), nullable, indexed
- users.bar_license_number : VARCHAR(50), nullable, indexed

Both columns are nullable because they are only meaningful when
default_role == 'legal'. Existing rows get NULL, which is the correct
value for non-legal users.

Revision ID: 20260624_add_legal_sub_role
Revises: 20260618_add_admin_error_queue, 20260615_add_module_registry
Create Date: 2026-06-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260624_add_legal_sub_role'
down_revision: Union[str, Sequence[str], None] = (
    '20260618_add_admin_error_queue',
    '20260615_add_module_registry',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add legal_sub_role and bar_license_number columns to users."""
    op.add_column(
        'users',
        sa.Column('legal_sub_role', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('bar_license_number', sa.String(length=50), nullable=True),
    )
    op.create_index(
        'ix_users_legal_sub_role',
        'users',
        ['legal_sub_role'],
        unique=False,
    )
    op.create_index(
        'ix_users_bar_license_number',
        'users',
        ['bar_license_number'],
        unique=False,
    )


def downgrade() -> None:
    """Remove legal_sub_role and bar_license_number columns from users."""
    op.drop_index('ix_users_bar_license_number', table_name='users')
    op.drop_index('ix_users_legal_sub_role', table_name='users')
    op.drop_column('users', 'bar_license_number')
    op.drop_column('users', 'legal_sub_role')
