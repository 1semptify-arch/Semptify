"""
PostgreSQL Full-Text Search Service
==================================

Provides PostgreSQL-native full-text search capabilities using tsvector/tsquery.
This serves as a fallback/alternative to the BM25 search engine.

Features:
- GIN index support for fast text search
- tsvector column management
- Query ranking with ts_rank
- Highlighting with ts_headline
- Hybrid search combining FTS with BM25
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import text, func
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class FTSResult:
    """Full-text search result."""
    document_id: str
    rank: float
    headline: str
    table_name: str


class PostgresFTSService:
    """
    PostgreSQL Full-Text Search Service.
    
    Uses PostgreSQL's built-in full-text search capabilities:
    - tsvector: Text search vector (indexed document content)
    - tsquery: Text search query
    - ts_rank: Relevance ranking
    - ts_headline: Result highlighting
    - GIN index: Fast inverted index
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def search_documents(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 20,
        highlight_max_length: int = 150
    ) -> List[FTSResult]:
        """
        Search documents using PostgreSQL FTS.
        
        Args:
            query: Search query text
            user_id: Optional user ID filter
            limit: Maximum results
            highlight_max_length: Max length for highlighted snippets
            
        Returns:
            List of FTSResult with ranked documents
        """
        # Build the tsquery
        tsquery = self._build_tsquery(query)
        
        # Build the SQL query
        sql = """
        SELECT 
            d.id,
            d.filename as title,
            ts_rank(d.search_vector, to_tsquery(:tsquery)) as rank,
            ts_headline(
                'english',
                COALESCE(d.extracted_text, d.filename),
                to_tsquery(:tsquery),
                'MaxWords=25, MinWords=10, MaxFragments=3'
            ) as headline
        FROM documents d
        WHERE d.search_vector @@ to_tsquery(:tsquery)
        """
        
        params = {"tsquery": tsquery, "limit": limit}
        
        if user_id:
            sql += " AND d.user_id = :user_id"
            params["user_id"] = user_id
        
        sql += """
        ORDER BY rank DESC
        LIMIT :limit
        """
        
        result = await self.db.execute(text(sql), params)
        
        return [
            FTSResult(
                document_id=row.id,
                rank=row.rank,
                headline=row.headline or row.title,
                table_name="documents"
            )
            for row in result.fetchall()
        ]
    
    async def search_vault_items(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[FTSResult]:
        """
        Search vault items using PostgreSQL FTS.
        
        Args:
            query: Search query text
            user_id: Optional user ID filter
            limit: Maximum results
            
        Returns:
            List of FTSResult with ranked vault items
        """
        tsquery = self._build_tsquery(query)
        
        sql = """
        SELECT 
            v.id,
            v.title,
            ts_rank(v.search_vector, to_tsquery(:tsquery)) as rank,
            ts_headline(
                'english',
                COALESCE(v.summary, v.title),
                to_tsquery(:tsquery),
                'MaxWords=25, MinWords=10'
            ) as headline
        FROM vault_items v
        WHERE v.search_vector @@ to_tsquery(:tsquery)
        """
        
        params = {"tsquery": tsquery, "limit": limit}
        
        if user_id:
            sql += " AND v.user_id = :user_id"
            params["user_id"] = user_id
        
        sql += """
        ORDER BY rank DESC
        LIMIT :limit
        """
        
        result = await self.db.execute(text(sql), params)
        
        return [
            FTSResult(
                document_id=row.id,
                rank=row.rank,
                headline=row.headline or row.title,
                table_name="vault_items"
            )
            for row in result.fetchall()
        ]
    
    async def hybrid_search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining FTS with simple text search.
        
        This provides best results by:
        1. Getting FTS ranked results
        2. Adding fallback text search results
        3. Merging and re-ranking
        
        Args:
            query: Search query text
            user_id: Optional user ID filter
            limit: Maximum results
            
        Returns:
            List of merged search results
        """
        # Get FTS results
        fts_results = await self.search_documents(query, user_id, limit)
        
        # Get vault results
        vault_results = await self.search_vault_items(query, user_id, limit)
        
        # Combine results
        all_results = []
        seen_ids = set()
        
        # Add FTS results first (higher relevance)
        for result in fts_results:
            if result.document_id not in seen_ids:
                all_results.append({
                    "id": result.document_id,
                    "type": "document",
                    "title": result.headline,
                    "rank": result.rank,
                    "source": "fts"
                })
                seen_ids.add(result.document_id)
        
        # Add vault results
        for result in vault_results:
            if result.document_id not in seen_ids:
                all_results.append({
                    "id": result.document_id,
                    "type": "vault_item",
                    "title": result.headline,
                    "rank": result.rank * 0.9,  # Slight penalty vs documents
                    "source": "fts"
                })
                seen_ids.add(result.document_id)
        
        # Sort by rank and limit
        all_results.sort(key=lambda x: x["rank"], reverse=True)
        
        return all_results[:limit]
    
    def _build_tsquery(self, query: str) -> str:
        """
        Build a PostgreSQL tsquery from user input.
        
        Converts simple query to tsquery format:
        - "rent increase" → 'rent' & 'increase'
        - "eviction notice" → 'eviction' & 'notice'
        
        Args:
            query: User search query
            
        Returns:
            Formatted tsquery string
        """
        # Clean and normalize
        words = query.strip().lower().split()
        
        if not words:
            return ""
        
        # Handle single word
        if len(words) == 1:
            return words[0]
        
        # Join multiple words with AND operator (&)
        return " & ".join(words)
    
    async def update_document_vector(self, document_id: str) -> bool:
        """
        Update the search vector for a document.
        
        This should be called when:
        - Document is created/updated
        - OCR/extraction completes
        - Content changes
        
        Args:
            document_id: Document ID to update
            
        Returns:
            True if updated successfully
        """
        sql = """
        UPDATE documents
        SET search_vector = 
            setweight(to_tsvector('english', COALESCE(filename, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(document_type, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(extracted_text, '')), 'C')
        WHERE id = :document_id
        """
        
        try:
            await self.db.execute(text(sql), {"document_id": document_id})
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            return False
    
    async def update_vault_item_vector(self, item_id: str) -> bool:
        """
        Update the search vector for a vault item.
        
        Args:
            item_id: Vault item ID to update
            
        Returns:
            True if updated successfully
        """
        sql = """
        UPDATE vault_items
        SET search_vector = 
            setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(summary, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(item_type, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(tags::text, '')), 'D')
        WHERE id = :item_id
        """
        
        try:
            await self.db.execute(text(sql), {"item_id": item_id})
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            return False
    
    async def get_search_suggestions(
        self,
        partial: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[str]:
        """
        Get search suggestions based on partial input.
        
        Uses prefix matching on document titles and vault item titles.
        
        Args:
            partial: Partial query string
            user_id: Optional user ID filter
            limit: Maximum suggestions
            
        Returns:
            List of suggested completions
        """
        suggestions = []
        
        # Search document filenames
        doc_sql = """
        SELECT DISTINCT filename as suggestion
        FROM documents
        WHERE filename ILIKE :pattern
        """
        
        params = {"pattern": f"%{partial}%", "limit": limit}
        
        if user_id:
            doc_sql += " AND user_id = :user_id"
        
        doc_sql += " LIMIT :limit"
        
        result = await self.db.execute(text(doc_sql), params)
        suggestions.extend([row.suggestion for row in result.fetchall()])
        
        # Search vault item titles
        vault_sql = """
        SELECT DISTINCT title as suggestion
        FROM vault_items
        WHERE title ILIKE :pattern
        """
        
        if user_id:
            vault_sql += " AND user_id = :user_id"
        
        vault_sql += " LIMIT :limit"
        
        result = await self.db.execute(text(vault_sql), params)
        suggestions.extend([row.suggestion for row in result.fetchall()])
        
        # Return unique suggestions
        seen = set()
        unique = []
        for s in suggestions:
            if s and s.lower() not in seen:
                unique.append(s)
                seen.add(s.lower())
        
        return unique[:limit]


# Sync wrapper for non-async contexts
def get_fts_service(db: AsyncSession) -> PostgresFTSService:
    """Get FTS service instance."""
    return PostgresFTSService(db)
