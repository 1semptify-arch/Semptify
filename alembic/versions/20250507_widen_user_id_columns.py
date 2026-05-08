"""Widen all user_id / users.id columns from VARCHAR(24) to VARCHAR(128)

The new stateless user_id format (GUJhGjWAAA.{hmac_hex}) produces IDs of
~66 characters, exceeding the original VARCHAR(24) limit and causing
'value too long' errors on INSERT into sessions and every FK table.

Widens:
  - users.id               (primary key)
  - storage_configs.user_id (primary key)
  - sessions.user_id        (already widened to 100 by cacc26689cdf — extend to 128)
  - All FK columns pointing to users.id (VARCHAR 24 → 128):
      linked_providers, documents, document_pipeline_index,
      timeline_events, rent_payments, calendar_events, complaints,
      witness_statements, certified_mail, fraud_analysis_results,
      press_release_records, research_profiles, contacts,
      contact_interactions, footnote_anchors, vault_items,
      vault_audit_logs, incidents, mndes_exhibit_packages,
      mndes_exhibit_items, vault_index

Revision ID: 20250507_widen_user_id_columns
Revises: cacc26689cdf
Create Date: 2026-05-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20250507_widen_user_id_columns'
down_revision: Union[str, Sequence[str], None] = 'cacc26689cdf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TARGET = sa.String(128)
OLD    = sa.String(24)


def _alter(table: str, column: str, from_len: int = 24) -> None:
    op.alter_column(
        table, column,
        existing_type=sa.String(from_len),
        type_=TARGET,
        existing_nullable=False,
    )


def _alter_nullable(table: str, column: str, from_len: int = 24) -> None:
    op.alter_column(
        table, column,
        existing_type=sa.String(from_len),
        type_=TARGET,
        existing_nullable=True,
    )


def upgrade() -> None:
    """Use raw SQL with IF EXISTS so missing tables never block the migration."""
    # Validate table names to prevent SQL injection
    VALID_TABLES = {
        'users', 'sessions', 'storage_configs', 'linked_providers',
        'documents', 'document_pipeline_index', 'timeline_events',
        'rent_payments', 'calendar_events', 'complaints',
        'witness_statements', 'certified_mail', 'fraud_analysis_results',
        'press_release_records', 'research_profiles', 'contacts',
        'contact_interactions', 'footnote_anchors', 'vault_items',
        'vault_audit_logs', 'incidents', 'mndes_exhibit_packages',
        'mndes_exhibit_items', 'vault_index',
    }

    id_tables = ['users']
    for table in id_tables:
        if table not in VALID_TABLES:
            raise ValueError(f"Invalid table name: {table}")
        op.execute(f"ALTER TABLE IF EXISTS {table} ALTER COLUMN id TYPE VARCHAR(256)")

    user_id_tables = [
        'sessions', 'storage_configs', 'linked_providers', 'documents',
        'document_pipeline_index', 'timeline_events', 'rent_payments',
        'calendar_events', 'complaints', 'witness_statements',
        'certified_mail', 'fraud_analysis_results', 'press_release_records',
        'research_profiles', 'contacts', 'contact_interactions',
        'footnote_anchors', 'vault_items', 'vault_audit_logs', 'incidents',
        'mndes_exhibit_packages', 'mndes_exhibit_items', 'vault_index',
    ]
    for table in user_id_tables:
        if table not in VALID_TABLES:
            raise ValueError(f"Invalid table name: {table}")
        op.execute(f"ALTER TABLE IF EXISTS {table} ALTER COLUMN user_id TYPE VARCHAR(256)")


def downgrade() -> None:
    """Downgrade using raw SQL to match upgrade approach — no existing_type assumptions."""
    VALID_TABLES = {
        'users', 'sessions', 'storage_configs', 'linked_providers',
        'documents', 'document_pipeline_index', 'timeline_events',
        'rent_payments', 'calendar_events', 'complaints',
        'witness_statements', 'certified_mail', 'fraud_analysis_results',
        'press_release_records', 'research_profiles', 'contacts',
        'contact_interactions', 'footnote_anchors', 'vault_items',
        'vault_audit_logs', 'incidents', 'mndes_exhibit_packages',
        'mndes_exhibit_items', 'vault_index',
    }

    id_tables = ['users']
    for table in id_tables:
        if table not in VALID_TABLES:
            raise ValueError(f"Invalid table name: {table}")
        op.execute(f"ALTER TABLE IF EXISTS {table} ALTER COLUMN id TYPE VARCHAR(24)")

    user_id_tables = [
        'sessions', 'storage_configs', 'linked_providers', 'documents',
        'document_pipeline_index', 'timeline_events', 'rent_payments',
        'calendar_events', 'complaints', 'witness_statements',
        'certified_mail', 'fraud_analysis_results', 'press_release_records',
        'research_profiles', 'contacts', 'contact_interactions',
        'footnote_anchors', 'vault_items', 'vault_audit_logs', 'incidents',
        'mndes_exhibit_packages', 'mndes_exhibit_items', 'vault_index',
    ]
    for table in user_id_tables:
        if table not in VALID_TABLES:
            raise ValueError(f"Invalid table name: {table}")
        op.execute(f"ALTER TABLE IF EXISTS {table} ALTER COLUMN user_id TYPE VARCHAR(24)")
