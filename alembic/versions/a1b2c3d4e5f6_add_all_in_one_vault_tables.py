"""
Add ALL-IN-ONE unified evidence vault tables.

This migration creates the unified evidence vault architecture with:
- vault_items: Central evidence storage with three-timestamp model
- incidents: Case/incident grouping for organizing related evidence
- vault_audit_logs: Comprehensive audit trail with before/after states

Revision ID: a1b2c3d4e5f6
Revises: 81c36d8f2466
Create Date: 2026-04-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '20250424_add_search_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create ALL-IN-ONE vault tables with three-timestamp model.
    
    Three-Timestamp Model (NON-NEGOTIABLE):
    - event_time: Factual time of event occurrence
    - record_time: When evidence was created/recorded
    - semptify_entry_time: When added to Semptify system
    """
    
    # ==========================================================================
    # INCIDENTS TABLE (Case grouping)
    # ==========================================================================
    op.create_table(
        'incidents',
        sa.Column('incident_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=24), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('incident_type', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('incident_id')
    )
    
    # Indexes for incidents
    op.create_index('idx_incidents_user_id', 'incidents', ['user_id'])
    op.create_index('idx_incidents_status', 'incidents', ['status'])
    op.create_index('idx_incidents_type', 'incidents', ['incident_type'])
    
    # ==========================================================================
    # VAULT_ITEMS TABLE (Unified evidence storage)
    # ==========================================================================
    op.create_table(
        'vault_items',
        sa.Column('item_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=24), nullable=False),
        
        # THREE TIMESTAMPS (NON-NEGOTIABLE)
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False,
                  comment='Factual time of event occurrence'),
        sa.Column('record_time', sa.DateTime(timezone=True), nullable=False,
                  comment='When evidence was created/recorded'),
        sa.Column('semptify_entry_time', sa.DateTime(timezone=True), nullable=False,
                  comment='When added to Semptify system'),
        
        # Classification & Organization
        sa.Column('item_type', sa.String(length=50), nullable=False),
        sa.Column('folder', sa.String(length=255), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        
        # Relationships & Context
        sa.Column('related_incident_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        
        # Rich Metadata (JSONB - Deep Searchable)
        sa.Column('location_data', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        
        # Content References
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        
        # Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_incident_id'], ['incidents.incident_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('item_id')
    )
    
    # ==========================================================================
    # GIN INDEXES for JSONB deep search (PostgreSQL-specific)
    # ==========================================================================
    op.create_index('idx_vault_metadata_gin', 'vault_items', 
                    [sa.text('metadata')], 
                    postgresql_using='gin')
    op.create_index('idx_vault_location_gin', 'vault_items', 
                    [sa.text('location_data')], 
                    postgresql_using='gin')
    op.create_index('idx_vault_tags_gin', 'vault_items', 
                    [sa.text('tags')], 
                    postgresql_using='gin')
    
    # ==========================================================================
    # BTREE INDEXES for performance
    # ==========================================================================
    # Three timestamp indexes
    op.create_index('idx_vault_event_time', 'vault_items', ['event_time'])
    op.create_index('idx_vault_record_time', 'vault_items', ['record_time'])
    op.create_index('idx_vault_entry_time', 'vault_items', ['semptify_entry_time'])
    
    # Classification indexes
    op.create_index('idx_vault_user_id', 'vault_items', ['user_id'])
    op.create_index('idx_vault_item_type', 'vault_items', ['item_type'])
    op.create_index('idx_vault_folder', 'vault_items', ['folder'])
    op.create_index('idx_vault_incident_id', 'vault_items', ['related_incident_id'])
    op.create_index('idx_vault_severity', 'vault_items', ['severity'])
    op.create_index('idx_vault_status', 'vault_items', ['status'])
    
    # Composite indexes for common queries
    op.create_index('idx_vault_user_type_time', 'vault_items', 
                    ['user_id', 'item_type', 'event_time'])
    op.create_index('idx_vault_incident_time', 'vault_items', 
                    ['related_incident_id', 'event_time'])
    
    # ==========================================================================
    # VAULT_AUDIT_LOGS TABLE (Comprehensive audit trail)
    # ==========================================================================
    op.create_table(
        'vault_audit_logs',
        sa.Column('log_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=24), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('action_context', sa.String(length=100), nullable=True),
        sa.Column('before_state', postgresql.JSONB(), nullable=True),
        sa.Column('after_state', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        
        sa.ForeignKeyConstraint(['item_id'], ['vault_items.item_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('log_id')
    )
    
    # Audit log indexes
    op.create_index('idx_audit_item_id', 'vault_audit_logs', ['item_id'])
    op.create_index('idx_audit_user_id', 'vault_audit_logs', ['user_id'])
    op.create_index('idx_audit_action', 'vault_audit_logs', ['action'])
    op.create_index('idx_audit_timestamp', 'vault_audit_logs', ['timestamp'])
    op.create_index('idx_audit_item_timestamp', 'vault_audit_logs', 
                    ['item_id', 'timestamp'])


def downgrade() -> None:
    """Remove ALL-IN-ONE vault tables."""
    
    # Drop audit logs first (foreign key dependency)
    op.drop_index('idx_audit_item_timestamp', table_name='vault_audit_logs')
    op.drop_index('idx_audit_timestamp', table_name='vault_audit_logs')
    op.drop_index('idx_audit_action', table_name='vault_audit_logs')
    op.drop_index('idx_audit_user_id', table_name='vault_audit_logs')
    op.drop_index('idx_audit_item_id', table_name='vault_audit_logs')
    op.drop_table('vault_audit_logs')
    
    # Drop vault items
    op.drop_index('idx_vault_incident_time', table_name='vault_items')
    op.drop_index('idx_vault_user_type_time', table_name='vault_items')
    op.drop_index('idx_vault_status', table_name='vault_items')
    op.drop_index('idx_vault_severity', table_name='vault_items')
    op.drop_index('idx_vault_incident_id', table_name='vault_items')
    op.drop_index('idx_vault_folder', table_name='vault_items')
    op.drop_index('idx_vault_item_type', table_name='vault_items')
    op.drop_index('idx_vault_user_id', table_name='vault_items')
    op.drop_index('idx_vault_entry_time', table_name='vault_items')
    op.drop_index('idx_vault_record_time', table_name='vault_items')
    op.drop_index('idx_vault_event_time', table_name='vault_items')
    op.drop_index('idx_vault_tags_gin', table_name='vault_items')
    op.drop_index('idx_vault_location_gin', table_name='vault_items')
    op.drop_index('idx_vault_metadata_gin', table_name='vault_items')
    op.drop_table('vault_items')
    
    # Drop incidents
    op.drop_index('idx_incidents_type', table_name='incidents')
    op.drop_index('idx_incidents_status', table_name='incidents')
    op.drop_index('idx_incidents_user_id', table_name='incidents')
    op.drop_table('incidents')
