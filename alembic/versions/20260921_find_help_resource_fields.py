"""merge heads + add find-help fields to resources

Revision ID: 20260921_find_help
Revises: 20260921_info_donation, 20260921_vc_device_type
Create Date: 2026-09-21 00:00:00.000000

Merges the two migration heads left by the PR #305/#306 branch merges, then
adds the "find help near me" fields to `resources`:

- state_code / county / city — structured jurisdiction for near-me matching
  (NULL state_code = serves everywhere, e.g. national hotlines)
- subcategory — finer grouping inside a category (food -> meals, food_shelf)
- is_no_charge / is_verified_nonprofit — the public-listing rule: a row only
  surfaces if it charges nothing or is an officially verified nonprofit
- verified_source — what the verification rests on (lsc-grantee, hud-approved,
  gov-registry, state-bar, samhsa, org-official-site)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260921_find_help'
down_revision: Union[str, Sequence[str], None] = ('20260921_info_donation', '20260921_vc_device_type')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS = (
    ('state_code', sa.String(2)),
    ('county', sa.String(120)),
    ('city', sa.String(120)),
    ('subcategory', sa.String(100)),
    ('is_no_charge', sa.Boolean()),
    ('is_verified_nonprofit', sa.Boolean()),
    ('verified_source', sa.String(120)),
)

_NEW_INDEXES = (
    ('ix_resources_state_code', 'state_code'),
    ('ix_resources_county', 'county'),
    ('ix_resources_city', 'city'),
    ('ix_resources_subcategory', 'subcategory'),
    ('ix_resources_is_no_charge', 'is_no_charge'),
    ('ix_resources_is_verified_nonprofit', 'is_verified_nonprofit'),
)


def upgrade() -> None:
    # Idempotent: init_db() runs Base.metadata.create_all during startup and
    # may have already added these columns. Add only what is missing.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'resources' not in set(insp.get_table_names()):
        return
    cols = {c['name'] for c in insp.get_columns('resources')}
    for name, col_type in _NEW_COLUMNS:
        if name not in cols:
            op.add_column('resources', sa.Column(name, col_type, nullable=True))
    indexes = {ix['name'] for ix in insp.get_indexes('resources')}
    for ix_name, col in _NEW_INDEXES:
        if ix_name not in indexes and col in {c['name'] for c in sa.inspect(bind).get_columns('resources')}:
            op.create_index(ix_name, 'resources', [col])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'resources' not in set(insp.get_table_names()):
        return
    indexes = {ix['name'] for ix in insp.get_indexes('resources')}
    for ix_name, _col in _NEW_INDEXES:
        if ix_name in indexes:
            op.drop_index(ix_name, 'resources')
    cols = {c['name'] for c in sa.inspect(bind).get_columns('resources')}
    for name, _col_type in _NEW_COLUMNS:
        if name in cols:
            op.drop_column('resources', name)
