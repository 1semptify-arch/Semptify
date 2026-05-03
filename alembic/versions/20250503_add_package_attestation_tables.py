"""
Add package tracking and attestation persistence tables.

Revision ID: 20250503_add_package_attestation_tables
Revises: a1b2c3d4e5f6
Create Date: 2026-05-03 03:00:00.000000

This migration creates tables to persist:
- packages: Physical mail/packages sent/received with tracking
- package_attestations: Proof of mailing/delivery certificates
- package_events: Carrier tracking event history

Replaces in-memory stores that lose data on server restart.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250503_add_package_attestation_tables'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create package tracking and attestation tables.
    
    These tables replace in-memory storage for:
    - Certified mail tracking numbers
    - Package delivery attestations
    - Evidence custody chain for physical items
    """
    
    # ==========================================================================
    # PACKAGES TABLE - Physical mail/package tracking
    # ==========================================================================
    op.create_table(
        'packages',
        sa.Column('package_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(24), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Tracking information
        sa.Column('tracking_number', sa.String(100), nullable=False, index=True),
        sa.Column('carrier', sa.String(20), nullable=False, server_default='usps'),  # usps, ups, fedex, dhl
        sa.Column('carrier_tracking_url', sa.String(500), nullable=True),
        
        # Package classification
        sa.Column('package_type', sa.String(50), nullable=False),  # certified_mail, priority, express, evidence, legal_document
        sa.Column('package_subtype', sa.String(50), nullable=True),  # return_receipt, signature_required, restricted_delivery
        
        # Addresses
        sa.Column('sender_name', sa.String(255), nullable=True),
        sa.Column('sender_address', sa.Text(), nullable=True),
        sa.Column('recipient_name', sa.String(255), nullable=False),
        sa.Column('recipient_address', sa.Text(), nullable=False),
        
        # Status and dates
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),  # pending, in_transit, out_for_delivery, delivered, returned, failed
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('shipped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_tracking_update', sa.DateTime(timezone=True), nullable=True),
        
        # Linked case/document references
        sa.Column('related_case_id', sa.String(36), nullable=True, index=True),
        sa.Column('related_document_id', sa.String(36), nullable=True, index=True),
        sa.Column('related_complaint_id', sa.String(36), sa.ForeignKey('complaints.id', ondelete='SET NULL'), nullable=True),
        
        # Description/purpose
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('contents_description', sa.Text(), nullable=True),  # What's in the package
        
        # Metadata for custody chain
        sa.Column('is_evidence', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_signature', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('return_receipt_requested', sa.Boolean(), nullable=False, server_default='false'),
        
        # JSONB for carrier-specific data
        sa.Column('carrier_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('raw_tracking_response', postgresql.JSONB(), nullable=True),
        
        # Timestamps
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Indexes for packages
    op.create_index('idx_packages_tracking_number', 'packages', ['tracking_number'])
    op.create_index('idx_packages_status', 'packages', ['status'])
    op.create_index('idx_packages_carrier', 'packages', ['carrier'])
    op.create_index('idx_packages_type', 'packages', ['package_type'])
    op.create_index('idx_packages_is_evidence', 'packages', ['is_evidence'])
    op.create_index('idx_packages_delivered_at', 'packages', ['delivered_at'])
    op.create_index('idx_packages_user_status', 'packages', ['user_id', 'status'])
    op.create_index('idx_packages_user_type', 'packages', ['user_id', 'package_type'])
    
    # ==========================================================================
    # PACKAGE_ATTESTATIONS TABLE - Proof of mailing/delivery
    # ==========================================================================
    op.create_table(
        'package_attestations',
        sa.Column('attestation_id', sa.String(36), primary_key=True),
        sa.Column('package_id', sa.String(36), sa.ForeignKey('packages.package_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(24), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Attestation type
        sa.Column('attestation_type', sa.String(50), nullable=False),  # certified_receipt, delivery_confirmation, signature_proof, return_receipt
        
        # Certificate/receipt data
        sa.Column('certificate_number', sa.String(100), nullable=True, unique=True),
        sa.Column('certificate_path', sa.String(500), nullable=True),  # Path to stored certificate file
        sa.Column('certificate_hash', sa.String(64), nullable=True),  # SHA-256 of certificate for integrity
        
        # Verification data
        sa.Column('verification_hash', sa.String(128), nullable=True),  # Tamper-proof chain hash
        sa.Column('previous_attestation_hash', sa.String(128), nullable=True),  # For chain linking
        
        # Attestation content (extracted data)
        sa.Column('attested_sender', sa.String(255), nullable=True),
        sa.Column('attested_recipient', sa.String(255), nullable=True),
        sa.Column('attested_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attested_delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signature_image_path', sa.String(500), nullable=True),  # For return receipts with signatures
        
        # Legal validity
        sa.Column('is_legally_valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('validity_notes', sa.Text(), nullable=True),
        sa.Column('notarized', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notary_id', sa.String(100), nullable=True),
        
        # Source
        sa.Column('source', sa.String(50), nullable=False, server_default='carrier_api'),  # carrier_api, scanned_document, manual_entry, court_clerk
        sa.Column('source_document_id', sa.String(36), nullable=True),  # If from uploaded certificate scan
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Indexes for attestations
    op.create_index('idx_attestations_package', 'package_attestations', ['package_id'])
    op.create_index('idx_attestations_type', 'package_attestations', ['attestation_type'])
    op.create_index('idx_attestations_certificate', 'package_attestations', ['certificate_number'])
    op.create_index('idx_attestations_hash', 'package_attestations', ['verification_hash'])
    op.create_index('idx_attestations_user_type', 'package_attestations', ['user_id', 'attestation_type'])
    
    # ==========================================================================
    # PACKAGE_EVENTS TABLE - Carrier tracking event history
    # ==========================================================================
    op.create_table(
        'package_events',
        sa.Column('event_id', sa.String(36), primary_key=True),
        sa.Column('package_id', sa.String(36), sa.ForeignKey('packages.package_id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Event details from carrier
        sa.Column('event_code', sa.String(20), nullable=False),  # Carrier-specific event code
        sa.Column('event_description', sa.String(255), nullable=False),  # Human-readable description
        sa.Column('event_category', sa.String(30), nullable=False),  # received, in_transit, out_for_delivery, delivered, exception, pickup_available
        
        # Location
        sa.Column('location_city', sa.String(100), nullable=True),
        sa.Column('location_state', sa.String(50), nullable=True),
        sa.Column('location_zip', sa.String(20), nullable=True),
        sa.Column('location_country', sa.String(2), nullable=True, server_default='US'),
        
        # Timing
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('event_timezone', sa.String(50), nullable=True),
        
        # Raw carrier data
        sa.Column('raw_event_data', postgresql.JSONB(), nullable=True),
        
        # Semptify tracking
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Unique constraint to prevent duplicate events
        sa.UniqueConstraint('package_id', 'event_code', 'event_timestamp', name='uq_package_event'),
    )
    
    # Indexes for package events
    op.create_index('idx_package_events_package', 'package_events', ['package_id', 'event_timestamp'])
    op.create_index('idx_package_events_category', 'package_events', ['event_category'])
    op.create_index('idx_package_events_timestamp', 'package_events', ['event_timestamp'])
    
    # ==========================================================================
    # PACKAGE_ATTACHMENTS TABLE - Documents/photos linked to packages
    # ==========================================================================
    op.create_table(
        'package_attachments',
        sa.Column('attachment_id', sa.String(36), primary_key=True),
        sa.Column('package_id', sa.String(36), sa.ForeignKey('packages.package_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(24), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Attachment details
        sa.Column('attachment_type', sa.String(50), nullable=False),  # photo, receipt_scan, label_scan, contents_photo, signature_capture
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        
        # Integrity
        sa.Column('sha256_hash', sa.String(64), nullable=True),
        
        # Description
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Indexes for attachments
    op.create_index('idx_package_attachments_package', 'package_attachments', ['package_id'])
    op.create_index('idx_package_attachments_type', 'package_attachments', ['attachment_type'])
    
    # ==========================================================================
    # GIN INDEXES for JSONB deep search
    # ==========================================================================
    op.create_index(
        'idx_packages_carrier_metadata_gin',
        'packages',
        [sa.text('carrier_metadata')],
        postgresql_using='gin'
    )
    
    op.create_index(
        'idx_attestations_metadata_gin',
        'package_attestations',
        [sa.text('metadata')],
        postgresql_using='gin'
    )
    
    op.create_index(
        'idx_package_events_raw_data_gin',
        'package_events',
        [sa.text('raw_event_data')],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Remove package tracking and attestation tables."""
    
    # Drop in reverse order of creation (respect foreign keys)
    op.drop_index('idx_package_attachments_type', table_name='package_attachments')
    op.drop_index('idx_package_attachments_package', table_name='package_attachments')
    op.drop_table('package_attachments')
    
    op.drop_index('idx_package_events_raw_data_gin', table_name='package_events')
    op.drop_index('idx_package_events_timestamp', table_name='package_events')
    op.drop_index('idx_package_events_category', table_name='package_events')
    op.drop_index('idx_package_events_package', table_name='package_events')
    op.drop_table('package_events')
    
    op.drop_index('idx_attestations_metadata_gin', table_name='package_attestations')
    op.drop_index('idx_attestations_user_type', table_name='package_attestations')
    op.drop_index('idx_attestations_hash', table_name='package_attestations')
    op.drop_index('idx_attestations_certificate', table_name='package_attestations')
    op.drop_index('idx_attestations_type', table_name='package_attestations')
    op.drop_index('idx_attestations_package', table_name='package_attestations')
    op.drop_table('package_attestations')
    
    op.drop_index('idx_packages_carrier_metadata_gin', table_name='packages')
    op.drop_index('idx_packages_user_type', table_name='packages')
    op.drop_index('idx_packages_user_status', table_name='packages')
    op.drop_index('idx_packages_delivered_at', table_name='packages')
    op.drop_index('idx_packages_is_evidence', table_name='packages')
    op.drop_index('idx_packages_type', table_name='packages')
    op.drop_index('idx_packages_carrier', table_name='packages')
    op.drop_index('idx_packages_status', table_name='packages')
    op.drop_index('idx_packages_tracking_number', table_name='packages')
    op.drop_table('packages')
