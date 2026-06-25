"""merge_heads_before_context_engine

Revision ID: e8e919671d1a
Revises: 20260615_add_module_registry, 20260624_add_legal_sub_role
Create Date: 2026-06-24 18:52:13.570058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8e919671d1a'
down_revision: Union[str, Sequence[str], None] = ('20260615_add_module_registry', '20260624_add_legal_sub_role')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
