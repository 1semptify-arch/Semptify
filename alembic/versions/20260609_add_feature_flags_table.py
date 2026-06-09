"""Add feature_flags table

Revision ID: 20260609_add_feature_flags
Revises: 20260601_add_provider_file_id_vault_index
Create Date: 2026-06-09 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260609_add_feature_flags'
down_revision = '20260601_add_provider_file_id_vault_index'
branch_labels = None
depends_on = None


def upgrade():
    # Create feature_flags table
    op.create_table(
        'feature_flags',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('flag_name', sa.String(length=100), nullable=False),
        sa.Column('flag_type', sa.String(length=20), nullable=False, server_default='boolean'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rollout_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('allowed_roles', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('allowed_states', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('updated_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flag_name', name='uq_feature_flags_flag_name')
    )
    
    # Create index on flag_name for fast lookups
    op.create_index(
        'ix_feature_flags_flag_name',
        'feature_flags',
        ['flag_name'],
        unique=False
    )
    
    # Create index on enabled for filtering active flags
    op.create_index(
        'ix_feature_flags_enabled',
        'feature_flags',
        ['enabled'],
        unique=False
    )
    
    # Insert default feature flags
    op.execute("""
        INSERT INTO feature_flags (flag_name, flag_type, enabled, description, created_by) VALUES
        ('eviction_defense_nd', 'boolean', true, 'Enable eviction defense in North Dakota', 'system'),
        ('counterclaim_builder', 'boolean', false, 'Enable counterclaim builder (legal only)', 'system'),
        ('advanced_analytics', 'boolean', false, 'Enable advanced analytics dashboard', 'system'),
        ('new_ui_theme', 'boolean', false, 'Enable new UI theme (gradual rollout)', 'system'),
        ('batch_operations', 'boolean', false, 'Enable admin batch operations', 'system')
    """)


def downgrade():
    op.drop_index('ix_feature_flags_enabled', table_name='feature_flags')
    op.drop_index('ix_feature_flags_flag_name', table_name='feature_flags')
    op.drop_table('feature_flags')
