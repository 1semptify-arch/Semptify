"""
Global Search API - Enhanced with Advanced Search Engine
========================================================

Searches across all Semptify data sources with advanced indexing:
- Documents (full-text indexed)
- Timeline events
- Contacts
- Law library

Provides unified search results with BM25 relevance scoring, highlights, and suggestions.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import require_user, StorageUser
from app.core.search_engine import get_search_engine, SearchType, SearchOperator
from app.models.models import (
    Document as DocumentModel,
    TimelineEvent as TimelineEventModel,
    Contact as ContactModel,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class SearchResult(BaseModel):
    """A single search result."""
    id: str
    type: str  # document, timeline, contact, law
    title: str
    snippet: str
    url: str
    score: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Search response with results grouped by type."""
    query: str
    total_results: int
    documents: List[SearchResult] = Field(default_factory=list)
    timeline: List[SearchResult] = Field(default_factory=list)
    contacts: List[SearchResult] = Field(default_factory=list)
    law_library: List[SearchResult] = Field(default_factory=list)


# =============================================================================
# Minnesota Tenant Law Quick Reference
# =============================================================================

MINNESOTA_LAW_ENTRIES = [
    {
        "id": "504b-161",
        "title": "Minnesota Statute 504B.161 - Covenants of Landlord",
        "content": "Landlord must keep premises fit for use, make repairs, keep in reasonable repair, comply with health codes. Implied warranty of habitability.",
        "url": "/static/law_library.html#504b-161",
        "keywords": ["habitability", "repair", "health", "safety", "warranty", "fit", "condition"]
    },
    {
        "id": "504b-178",
        "title": "Minnesota Statute 504B.178 - Security Deposits",
        "content": "Security deposit return within 21 days. Interest required after 6 months. Itemized list of deductions. Maximum one month rent.",
        "url": "/static/law_library.html#504b-178",
        "keywords": ["security deposit", "deposit", "return", "21 days", "deductions", "interest"]
    },
    {
        "id": "504b-285",
        "title": "Minnesota Statute 504B.285 - Eviction Actions",
        "content": "Eviction procedures, notice requirements, court process. Must file unlawful detainer action. Tenant has right to answer.",
        "url": "/static/law_library.html#504b-285",
        "keywords": ["eviction", "unlawful detainer", "notice", "court", "answer", "hearing"]
    },
    {
        "id": "504b-321",
        "title": "Minnesota Statute 504B.321 - Notice to Quit",
        "content": "Proper notice requirements for termination. 14-day notice for nonpayment. Written notice required.",
        "url": "/static/law_library.html#504b-321",
        "keywords": ["notice", "quit", "14 days", "termination", "nonpayment", "written"]
    },
    {
        "id": "504b-211",
        "title": "Minnesota Statute 504B.211 - Retaliation",
        "content": "Landlord cannot retaliate against tenant for exercising rights. Presumption of retaliation within 90 days.",
        "url": "/static/law_library.html#504b-211",
        "keywords": ["retaliation", "rights", "complaint", "90 days", "protected"]
    },
    {
        "id": "504b-181",
        "title": "Minnesota Statute 504B.181 - Landlord Access",
        "content": "Landlord must give reasonable notice before entry. Emergency exceptions. Tenant right to privacy.",
        "url": "/static/law_library.html#504b-181",
        "keywords": ["access", "entry", "notice", "privacy", "reasonable"]
    },
    {
        "id": "504b-155",
        "title": "Minnesota Statute 504B.155 - Tenant Remedies",
        "content": "Rent escrow, repair and deduct, lease termination for habitability issues. Relief through housing court.",
        "url": "/static/law_library.html#504b-155",
        "keywords": ["remedies", "escrow", "repair", "deduct", "termination", "relief"]
    },
    {
        "id": "minn-ag-rights",
        "title": "Minnesota Tenant Rights - Attorney General Guide",
        "content": "Comprehensive tenant rights guide. Lease requirements, discrimination, repairs, eviction process, resources.",
        "url": "/static/law_library.html",
        "keywords": ["rights", "guide", "tenant", "lease", "discrimination", "resources"]
    },
]


# =============================================================================
# Helper Functions
# =============================================================================

def _snippet(text: str, query: str, max_length: int = 150) -> str:
    """Create a snippet highlighting the query match."""
    if not text:
        return ""
    
    text = text.strip()
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Find query position
    pos = text_lower.find(query_lower)
    
    if pos >= 0:
        # Show context around match
        start = max(0, pos - 50)
        end = min(len(text), pos + len(query) + 100)
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet
    
    # No match, just truncate
    return text[:max_length] + ("..." if len(text) > max_length else "")


def _score_match(text: str, query: str) -> float:
    """Calculate relevance score for a match."""
    if not text:
        return 0.0
    
    text_lower = text.lower()
    query_lower = query.lower()
    query_words = query_lower.split()
    
    score = 0.0
    
    # Exact match bonus
    if query_lower in text_lower:
        score += 1.0
    
    # Word match scoring
    for word in query_words:
        if word in text_lower:
            score += 0.5
            # Title/start bonus
            if text_lower.startswith(word):
                score += 0.3
    
    return min(score, 2.0)  # Cap at 2.0


def _search_law_library(query: str) -> List[SearchResult]:
    """Search Minnesota law entries."""
    results = []
    query_lower = query.lower()
    query_words = query_lower.split()
    
    for entry in MINNESOTA_LAW_ENTRIES:
        # Check title, content, and keywords
        searchable = f"{entry['title']} {entry['content']} {' '.join(entry['keywords'])}".lower()
        
        # Score based on matches
        score = 0.0
        
        if query_lower in searchable:
            score += 1.5
        
        for word in query_words:
            if word in searchable:
                score += 0.5
            if word in entry['keywords']:
                score += 0.3  # Keyword bonus
        
        if score > 0:
            results.append(SearchResult(
                id=entry['id'],
                type="law",
                title=entry['title'],
                snippet=_snippet(entry['content'], query),
                url=entry['url'],
                score=score,
                metadata={"keywords": entry['keywords']}
            ))
    
    # Sort by score
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:5]  # Top 5


# =============================================================================
# Search Endpoint
# =============================================================================

@router.get("/", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results per category"),
    user: StorageUser = Depends(require_user),
):
    """
    Search across all Semptify data sources.
    
    Returns results grouped by type:
    - documents: Files in document vault
    - timeline: Timeline events
    - contacts: Contact entries
    - law_library: Minnesota tenant law references
    """
    response = SearchResponse(query=q, total_results=0)
    
    async with get_db_session() as session:
        # Search Documents
        try:
            doc_query = select(DocumentModel).where(
                DocumentModel.user_id == user.user_id,
                or_(
                    DocumentModel.filename.ilike(f"%{q}%"),
                    DocumentModel.document_type.ilike(f"%{q}%"),
                    DocumentModel.extracted_text.ilike(f"%{q}%"),
                )
            ).limit(limit)
            
            result = await session.execute(doc_query)
            docs = result.scalars().all()
            
            for doc in docs:
                searchable = f"{doc.filename or ''} {doc.extracted_text or ''}"
                score = _score_match(searchable, q)
                
                response.documents.append(SearchResult(
                    id=doc.id,
                    type="document",
                    title=doc.filename or "Untitled Document",
                    snippet=_snippet(doc.extracted_text or doc.filename or "", q),
                    url=f"/static/documents.html?id={doc.id}",
                    score=score,
                    metadata={
                        "document_type": doc.document_type,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    }
                ))
        except Exception as e:
            logger.warning(f"Document search error: {e}")
        
        # Search Timeline
        try:
            timeline_query = select(TimelineEventModel).where(
                TimelineEventModel.user_id == user.user_id,
                or_(
                    TimelineEventModel.title.ilike(f"%{q}%"),
                    TimelineEventModel.description.ilike(f"%{q}%"),
                )
            ).limit(limit)
            
            result = await session.execute(timeline_query)
            events = result.scalars().all()
            
            for event in events:
                searchable = f"{event.title or ''} {event.description or ''}"
                score = _score_match(searchable, q)
                
                response.timeline.append(SearchResult(
                    id=event.id,
                    type="timeline",
                    title=event.title or "Timeline Event",
                    snippet=_snippet(event.description or "", q),
                    url=f"/static/timeline.html?event={event.id}",
                    score=score,
                    metadata={
                        "event_type": event.event_type,
                        "event_date": event.event_date.isoformat() if event.event_date else None,
                        "is_evidence": event.is_evidence,
                    }
                ))
        except Exception as e:
            logger.warning(f"Timeline search error: {e}")
        
        # Search Contacts
        try:
            contact_query = select(ContactModel).where(
                ContactModel.user_id == user.user_id,
                or_(
                    ContactModel.name.ilike(f"%{q}%"),
                    ContactModel.role.ilike(f"%{q}%"),
                    ContactModel.organization.ilike(f"%{q}%"),
                    ContactModel.notes.ilike(f"%{q}%"),
                )
            ).limit(limit)
            
            result = await session.execute(contact_query)
            contacts = result.scalars().all()
            
            for contact in contacts:
                searchable = f"{contact.name or ''} {contact.role or ''} {contact.organization or ''}"
                score = _score_match(searchable, q)
                
                response.contacts.append(SearchResult(
                    id=contact.id,
                    type="contact",
                    title=contact.name or "Contact",
                    snippet=f"{contact.role or ''} - {contact.organization or ''}".strip(" -"),
                    url=f"/static/contacts.html?id={contact.id}",
                    score=score,
                    metadata={
                        "role": contact.role,
                        "phone": contact.phone,
                        "email": contact.email,
                    }
                ))
        except Exception as e:
            logger.warning(f"Contact search error: {e}")
    
    # Search Law Library (no DB, just local data)
    response.law_library = _search_law_library(q)
    
    # Sort each category by score
    response.documents.sort(key=lambda r: r.score, reverse=True)
    response.timeline.sort(key=lambda r: r.score, reverse=True)
    response.contacts.sort(key=lambda r: r.score, reverse=True)
    
    # Calculate total
    response.total_results = (
        len(response.documents) + 
        len(response.timeline) + 
        len(response.contacts) + 
        len(response.law_library)
    )
    
    return response


@router.get("/advanced")
async def advanced_search(
    q: str = Query(..., min_length=1, description="Search query"),
    search_type: str = Query("full_text", description="Search type: full_text, metadata, content, hybrid"),
    operator: str = Query("and", description="Search operator: and, or, not"),
    file_types: Optional[str] = Query(None, description="Comma-separated file types to filter"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    user: StorageUser = Depends(require_user),
):
    """
    Advanced search with BM25 relevance scoring and filters.
    
    Features:
    - Full-text search with BM25 scoring
    - Multiple search operators (AND, OR, NOT)
    - File type and tag filtering
    - Date range filtering
    - Search highlights
    """
    try:
        # Parse search parameters
        search_type_enum = SearchType(search_type)
        operator_enum = SearchOperator(operator)
        
        file_type_list = file_types.split(',') if file_types else None
        tag_list = tags.split(',') if tags else None
        
        date_range = None
        if date_from and date_to:
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d")
                end_date = datetime.strptime(date_to, "%Y-%m-%d")
                date_range = (start_date, end_date)
            except ValueError:
                pass
        
        # Perform advanced search
        search_engine = get_search_engine()
        results = search_engine.search(
            query=q,
            user_id=user.user_id,
            search_type=search_type_enum,
            operator=operator_enum,
            file_types=file_type_list,
            tags=tag_list,
            date_range=date_range,
            limit=limit,
            offset=offset
        )
        
        return results
        
    except ValueError as e:
        return {
            "error": f"Invalid search parameters: {str(e)}",
            "results": [],
            "total": 0
        }
    except Exception as e:
        logger.error(f"Advanced search error: {e}")
        return {
            "error": "Search failed",
            "results": [],
            "total": 0
        }

@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=1, description="Partial query for suggestions"),
    limit: int = Query(10, ge=1, le=20, description="Max suggestions"),
    user: StorageUser = Depends(require_user),
):
    """
    Get search suggestions based on partial query.
    Uses popular queries and auto-completion.
    """
    try:
        search_engine = get_search_engine()
        suggestions = search_engine.suggest_queries(q, user.user_id, limit)
        
        return {
            "query": q,
            "suggestions": suggestions,
            "total": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"Search suggestions error: {e}")
        return {
            "query": q,
            "suggestions": [],
            "total": 0
        }

@router.get("/statistics")
async def search_statistics(
    user: StorageUser = Depends(require_user),
):
    """
    Get search statistics and index information.
    """
    try:
        search_engine = get_search_engine()
        stats = search_engine.get_search_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Search statistics error: {e}")
        return {
            "error": "Failed to get statistics",
            "search_stats": {},
            "index_stats": {}
        }

@router.post("/index")
async def index_document(
    document_id: str = Query(..., description="Document ID to index"),
    user: StorageUser = Depends(require_user),
):
    """
    Manually index a document for search.
    """
    try:
        # Get document from database
        async with get_db_session() as session:
            doc_query = select(DocumentModel).where(
                DocumentModel.id == document_id,
                DocumentModel.user_id == user.user_id
            )
            result = await session.execute(doc_query)
            doc = result.scalar_one_or_none()
            
            if not doc:
                return {"error": "Document not found"}
            
            # Index document
            search_engine = get_search_engine()
            success = search_engine.index_document(
                document_id=doc.id,
                user_id=doc.user_id,
                title=doc.filename or "Untitled",
                content=doc.extracted_text or "",
                metadata={
                    "document_type": doc.document_type,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None
                },
                file_type=doc.document_type or "unknown",
                tags=[]
            )
            
            return {
                "success": success,
                "document_id": document_id,
                "message": "Document indexed successfully" if success else "Indexing failed"
            }
            
    except Exception as e:
        logger.error(f"Document indexing error: {e}")
        return {
            "error": f"Indexing failed: {str(e)}",
            "document_id": document_id
        }

@router.delete("/index/{document_id}")
async def remove_from_index(
    document_id: str,
    user: StorageUser = Depends(require_user),
):
    """
    Remove a document from search index.
    """
    try:
        search_engine = get_search_engine()
        success = search_engine.remove_document(document_id)
        
        return {
            "success": success,
            "document_id": document_id,
            "message": "Document removed from index" if success else "Removal failed"
        }
        
    except Exception as e:
        logger.error(f"Document removal error: {e}")
        return {
            "error": f"Removal failed: {str(e)}",
            "document_id": document_id
        }

@router.get("/quick")
async def quick_search(
    q: str = Query(..., min_length=1),
    user: StorageUser = Depends(require_user),
):
    """
    Quick search for autocomplete/suggestions.
    Returns top 5 results across all categories.
    """
    full_results = await global_search(q=q, limit=3, user=user)
    
    # Combine and sort all results
    all_results = (
        full_results.documents + 
        full_results.timeline + 
        full_results.contacts + 
        full_results.law_library
    )
    
    all_results.sort(key=lambda r: r.score, reverse=True)
    
    return {
        "query": q,
        "results": [r.dict() for r in all_results[:5]],
        "total": full_results.total_results,
    }
