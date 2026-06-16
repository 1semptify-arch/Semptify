"""drop FK from certification_events.user_id — audit log must never fail due to missing user

Revision ID: 20260615_drop_cert_events_user_fk
Revises: 41ccf7debf12
Create Date: 2026-06-15

Audit logs must be unconditionally writable. A missing user FK would cause the
compliance record to be silently swallowed, defeating the entire audit purpose.
"""
from typing import Sequence, Union
from alembic import op

revision: str = '20260615_drop_cert_events_user_fk'
down_revision: Union[str, Sequence[str], None] = '41ccf7debf12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('certification_events_user_id_fkey', 'certification_events', type_='foreignkey')


def downgrade() -> None:
    op.create_foreign_key(
        'certification_events_user_id_fkey',
        'certification_events', 'users',
        ['user_id'], ['id'],
    )
