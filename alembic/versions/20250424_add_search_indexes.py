"""
Add PostgreSQL full-text search indexes

Revision ID: 20250424_add_search_indexes
Revises: 20250424_add_invite_codes
Create Date: 2026-04-24

This migration adds PostgreSQL full-text search capabilities:
- tsvector columns for documents and vault_items
- GIN indexes for fast text search
- Triggers to auto-update search vectors
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250424_add_search_indexes'
down_revision: Union[str, None] = '20250424_add_invite_codes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add full-text search columns and indexes."""
    
    # Add tsvector column to documents table
    op.add_column(
        'documents',
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True)
    )
    
    # Add tsvector column to vault_items table
    op.add_column(
        'vault_items',
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True)
    )
    
    # Create GIN indexes for fast full-text search
    op.create_index(
        'idx_documents_search_vector',
        'documents',
        ['search_vector'],
        postgresql_using='gin'
    )
    
    op.create_index(
        'idx_vault_items_search_vector',
        'vault_items',
        ['search_vector'],
        postgresql_using='gin'
    )
    
    # Create function to update document search vector
    op.execute("""
        CREATE OR REPLACE FUNCTION update_document_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', COALESCE(NEW.filename, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.document_type, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.extracted_text, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger to auto-update document search vector
    op.execute("""
        CREATE TRIGGER trigger_update_document_search_vector
        BEFORE INSERT OR UPDATE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION update_document_search_vector();
    """)
    
    # Create function to update vault item search vector
    op.execute("""
        CREATE OR REPLACE FUNCTION update_vault_item_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.summary, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.item_type, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger to auto-update vault item search vector
    op.execute("""
        CREATE TRIGGER trigger_update_vault_item_search_vector
        BEFORE INSERT OR UPDATE ON vault_items
        FOR EACH ROW
        EXECUTE FUNCTION update_vault_item_search_vector();
    """)
    
    # Populate existing data
    op.execute("""
        UPDATE documents
        SET search_vector = 
            setweight(to_tsvector('english', COALESCE(filename, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(document_type, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(extracted_text, '')), 'C')
        WHERE search_vector IS NULL;
    """)


def downgrade() -> None:
    """Remove full-text search columns and indexes."""
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_update_document_search_vector ON documents")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_vault_item_search_vector ON vault_items")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_document_search_vector()")
    op.execute("DROP FUNCTION IF EXISTS update_vault_item_search_vector()")
    
    # Drop indexes
    op.drop_index('idx_documents_search_vector', table_name='documents')
    op.drop_index('idx_vault_items_search_vector', table_name='vault_items')
    
    # Drop columns
    op.drop_column('documents', 'search_vector')
    op.drop_column('vault_items', 'search_vector')
