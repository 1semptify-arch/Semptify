"""
Advanced Search Engine - Full-text Search with Indexing
==================================================

Provides advanced search capabilities with document indexing and relevance scoring.
"""

import logging
import re
import math
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import json
import asyncio
from enum import Enum

logger = logging.getLogger(__name__)

class SearchType(Enum):
    """Search types."""
    FULL_TEXT = "full_text"
    METADATA = "metadata"
    CONTENT = "content"
    HYBRID = "hybrid"

class SearchOperator(Enum):
    """Search operators."""
    AND = "and"
    OR = "or"
    NOT = "not"
    PHRASE = "phrase"

@dataclass
class DocumentIndex:
    """Document index entry."""
    document_id: str
    user_id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    file_type: str
    tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "file_type": self.file_type,
            "tags": self.tags
        }

@dataclass
class SearchResult:
    """Search result with relevance score."""
    document: DocumentIndex
    score: float
    highlights: List[str]
    match_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document": self.document.to_dict(),
            "score": self.score,
            "highlights": self.highlights,
            "match_type": self.match_type
        }

@dataclass
class SearchQuery:
    """Search query with filters."""
    query: str
    search_type: SearchType = SearchType.FULL_TEXT
    operator: SearchOperator = SearchOperator.AND
    user_id: Optional[str] = None
    file_types: List[str] = None
    tags: List[str] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    limit: int = 50
    offset: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "search_type": self.search_type.value,
            "operator": self.operator.value,
            "user_id": self.user_id,
            "file_types": self.file_types,
            "tags": self.tags,
            "date_range": [
                self.date_range[0].isoformat(),
                self.date_range[1].isoformat()
            ] if self.date_range else None,
            "limit": self.limit,
            "offset": self.offset
        }

class TextProcessor:
    """Text processing for search indexing."""
    
    def __init__(self):
        # Common stop words
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
            'had', 'what', 'said', 'each', 'which', 'their', 'time', 'if',
            'up', 'out', 'many', 'then', 'them', 'can', 'would', 'there',
            'been', 'may', 'my', 'than', 'call', 'who', 'oil', 'sit', 'now',
            'find', 'long', 'down', 'day', 'did', 'get', 'come', 'made',
            'may', 'part', 'over', 'some', 'your', 'made', 'would', 'there',
            'been', 'may', 'my', 'than', 'call', 'who', 'oil', 'sit', 'now'
        }
        
        # Housing-related terms to boost
        self.housing_terms = {
            'lease', 'rent', 'tenant', 'landlord', 'eviction', 'housing',
            'apartment', 'rental', 'property', 'agreement', 'contract',
            'notice', 'court', 'judge', 'law', 'legal', 'rights', 'violation',
            'maintenance', 'repair', 'deposit', 'security', 'utilities',
            'mortgage', 'foreclosure', 'inspection', 'code', 'violation'
        }
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Convert to lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        # Remove stop words and filter short tokens
        tokens = [token for token in tokens 
                 if token not in self.stop_words and len(token) >= 2]
        
        return tokens
    
    def normalize(self, text: str) -> str:
        """Normalize text for search."""
        # Remove special characters, normalize whitespace
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract important keywords from text."""
        tokens = self.tokenize(text)
        
        # Count frequency
        token_freq = Counter(tokens)
        
        # Boost housing-related terms
        for token in tokens:
            if token in self.housing_terms:
                token_freq[token] *= 2
        
        # Get top keywords
        keywords = [token for token, freq in token_freq.most_common(max_keywords)]
        
        return keywords

class InvertedIndex:
    """Inverted index for fast text search."""
    
    def __init__(self):
        self.index: Dict[str, Set[str]] = defaultdict(set)  # word -> document_ids
        self.document_index: Dict[str, DocumentIndex] = {}  # document_id -> DocumentIndex
        self.word_counts: Dict[str, Dict[str, int]] = defaultdict(dict)  # word -> {doc_id: count}
        self.document_lengths: Dict[str, int] = {}  # document_id -> word_count
        self.total_documents = 0
        self.avg_document_length = 0
        
    def add_document(self, doc: DocumentIndex):
        """Add document to index."""
        processor = TextProcessor()
        
        # Process content
        content_tokens = processor.tokenize(doc.content)
        title_tokens = processor.tokenize(doc.title)
        
        # Combine tokens (title gets higher weight)
        all_tokens = title_tokens + content_tokens
        
        # Update document length
        self.document_lengths[doc.document_id] = len(all_tokens)
        
        # Update inverted index
        token_counts = Counter(all_tokens)
        
        for token, count in token_counts.items():
            self.index[token].add(doc.document_id)
            self.word_counts[token][doc.document_id] = count
        
        # Store document
        self.document_index[doc.document_id] = doc
        self.total_documents += 1
        
        # Update average document length
        total_length = sum(self.document_lengths.values())
        self.avg_document_length = total_length / self.total_documents
    
    def remove_document(self, document_id: str):
        """Remove document from index."""
        if document_id not in self.document_index:
            return
        
        doc = self.document_index[document_id]
        processor = TextProcessor()
        
        # Get tokens
        content_tokens = processor.tokenize(doc.content)
        title_tokens = processor.tokenize(doc.title)
        all_tokens = title_tokens + content_tokens
        
        # Remove from inverted index
        token_counts = Counter(all_tokens)
        
        for token in token_counts:
            if document_id in self.index[token]:
                self.index[token].discard(document_id)
                if not self.index[token]:
                    del self.index[token]
            
            if token in self.word_counts and document_id in self.word_counts[token]:
                del self.word_counts[token][document_id]
        
        # Remove document
        del self.document_index[document_id]
        del self.document_lengths[document_id]
        self.total_documents -= 1
        
        # Update average document length
        if self.total_documents > 0:
            total_length = sum(self.document_lengths.values())
            self.avg_document_length = total_length / self.total_documents
        else:
            self.avg_document_length = 0
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search documents."""
        processor = TextProcessor()
        
        # Process query
        query_tokens = processor.tokenize(query.query)
        
        if not query_tokens:
            return []
        
        # Get matching documents
        matching_docs = set()
        
        if query.operator == SearchOperator.AND:
            # All tokens must be present
            matching_docs = set.intersection(*[
                self.index.get(token, set()) for token in query_tokens
                if token in self.index
            ]) if query_tokens else set()
        
        elif query.operator == SearchOperator.OR:
            # Any token can be present
            for token in query_tokens:
                if token in self.index:
                    matching_docs.update(self.index[token])
        
        elif query.operator == SearchOperator.NOT:
            # Exclude documents with certain tokens
            # This is simplified - real implementation would be more complex
            exclude_tokens = [token for token in query_tokens if token.startswith('-')]
            include_tokens = [token for token in query_tokens if not token.startswith('-')]
            
            if include_tokens:
                matching_docs = set.union(*[
                    self.index.get(token, set()) for token in include_tokens
                    if token in self.index
                ])
            
            for token in exclude_tokens:
                clean_token = token[1:]  # Remove '-'
                if clean_token in self.index:
                    matching_docs.difference_update(self.index[clean_token])
        
        # Apply filters
        filtered_docs = self._apply_filters(matching_docs, query)
        
        # Calculate relevance scores
        results = []
        for doc_id in filtered_docs:
            doc = self.document_index[doc_id]
            score = self._calculate_relevance_score(doc, query_tokens, query)
            highlights = self._generate_highlights(doc, query_tokens)
            
            results.append(SearchResult(
                document=doc,
                score=score,
                highlights=highlights,
                match_type=query.search_type.value
            ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply pagination
        start = query.offset
        end = start + query.limit
        return results[start:end]
    
    def _apply_filters(self, document_ids: Set[str], query: SearchQuery) -> Set[str]:
        """Apply search filters."""
        filtered_docs = set(document_ids)
        
        for doc_id in list(filtered_docs):
            doc = self.document_index[doc_id]
            
            # User filter
            if query.user_id and doc.user_id != query.user_id:
                filtered_docs.discard(doc_id)
                continue
            
            # File type filter
            if query.file_types and doc.file_type not in query.file_types:
                filtered_docs.discard(doc_id)
                continue
            
            # Tags filter
            if query.tags and not any(tag in doc.tags for tag in query.tags):
                filtered_docs.discard(doc_id)
                continue
            
            # Date range filter
            if query.date_range:
                start_date, end_date = query.date_range
                if not (start_date <= doc.created_at <= end_date):
                    filtered_docs.discard(doc_id)
                    continue
        
        return filtered_docs
    
    def _calculate_relevance_score(self, doc: DocumentIndex, query_tokens: List[str], 
                                  query: SearchQuery) -> float:
        """Calculate BM25 relevance score."""
        k1 = 1.2  # BM25 parameter
        b = 0.75  # BM25 parameter
        
        score = 0.0
        doc_length = self.document_lengths[doc.document_id]
        
        for token in query_tokens:
            if token not in self.index or doc.document_id not in self.index[token]:
                continue
            
            # BM25 formula
            df = len(self.index[token])  # Document frequency
            idf = math.log((self.total_documents - df + 0.5) / (df + 0.5))
            
            tf = self.word_counts[token].get(doc.document_id, 0)  # Term frequency
            
            # Normalize term frequency
            normalized_tf = (tf * (k1 + 1)) / (
                tf + k1 * (1 - b + b * (doc_length / self.avg_document_length))
            )
            
            score += idf * normalized_tf
        
        # Boost for title matches
        title_tokens = TextProcessor().tokenize(doc.title)
        title_matches = len(set(query_tokens) & set(title_tokens))
        score += title_matches * 2.0
        
        # Boost for recent documents
        days_old = (datetime.now(timezone.utc) - doc.created_at).days
        recency_boost = max(0, 1 - (days_old / 365))  # Decay over year
        score += recency_boost * 0.5
        
        return score
    
    def _generate_highlights(self, doc: DocumentIndex, query_tokens: List[str]) -> List[str]:
        """Generate search highlights."""
        highlights = []
        content = doc.content.lower()
        
        for token in query_tokens[:3]:  # Limit to top 3 tokens
            positions = []
            start = 0
            
            while True:
                pos = content.find(token, start)
                if pos == -1:
                    break
                
                positions.append(pos)
                start = pos + 1
            
            # Generate highlight snippets
            for pos in positions[:2]:  # Max 2 snippets per token
                start_pos = max(0, pos - 50)
                end_pos = min(len(content), pos + len(token) + 50)
                
                snippet = doc.content[start_pos:end_pos]
                if snippet.strip():
                    highlights.append(snippet.strip())
        
        return highlights[:5]  # Max 5 highlights
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "total_documents": self.total_documents,
            "total_terms": len(self.index),
            "avg_document_length": self.avg_document_length,
            "document_lengths": {
                "min": min(self.document_lengths.values()) if self.document_lengths else 0,
                "max": max(self.document_lengths.values()) if self.document_lengths else 0,
                "avg": self.avg_document_length
            }
        }

class SearchEngine:
    """Advanced search engine with indexing."""
    
    def __init__(self):
        self.index = InvertedIndex()
        self.processor = TextProcessor()
        
        # Search statistics
        self.search_stats = {
            "total_searches": 0,
            "avg_search_time": 0.0,
            "popular_queries": Counter(),
            "zero_result_queries": Counter()
        }
    
    def index_document(self, document_id: str, user_id: str, title: str, 
                      content: str, metadata: Dict[str, Any], file_type: str,
                      tags: List[str] = None) -> bool:
        """Index a document for search."""
        try:
            # Remove existing document if it exists
            if document_id in self.index.document_index:
                self.index.remove_document(document_id)
            
            # Create document index
            doc = DocumentIndex(
                document_id=document_id,
                user_id=user_id,
                title=title,
                content=content,
                metadata=metadata,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                file_type=file_type,
                tags=tags or []
            )
            
            # Add to index
            self.index.add_document(doc)
            
            logger.info(f"Indexed document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document {document_id}: {e}")
            return False
    
    def remove_document(self, document_id: str) -> bool:
        """Remove document from search index."""
        try:
            self.index.remove_document(document_id)
            logger.info(f"Removed document {document_id} from index")
            return True
        except Exception as e:
            logger.error(f"Failed to remove document {document_id}: {e}")
            return False
    
    def search(self, query: str, user_id: str = None, search_type: SearchType = SearchType.FULL_TEXT,
               operator: SearchOperator = SearchOperator.AND, file_types: List[str] = None,
               tags: List[str] = None, date_range: Optional[Tuple[datetime, datetime]] = None,
               limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Perform search."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create search query
            search_query = SearchQuery(
                query=query,
                search_type=search_type,
                operator=operator,
                user_id=user_id,
                file_types=file_types,
                tags=tags,
                date_range=date_range,
                limit=limit,
                offset=offset
            )
            
            # Perform search
            results = self.index.search(search_query)
            
            # Update statistics
            search_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.search_stats["total_searches"] += 1
            self.search_stats["avg_search_time"] = (
                (self.search_stats["avg_search_time"] * (self.search_stats["total_searches"] - 1) + search_time) /
                self.search_stats["total_searches"]
            )
            self.search_stats["popular_queries"][query.lower()] += 1
            
            if not results:
                self.search_stats["zero_result_queries"][query.lower()] += 1
            
            return {
                "results": [result.to_dict() for result in results],
                "total": len(results),
                "query": search_query.to_dict(),
                "search_time": search_time,
                "statistics": self.get_search_statistics()
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "results": [],
                "total": 0,
                "error": str(e),
                "search_time": (datetime.now(timezone.utc) - start_time).total_seconds()
            }
    
    def suggest_queries(self, partial_query: str, user_id: str = None, limit: int = 10) -> List[str]:
        """Suggest search queries based on partial input."""
        suggestions = []
        
        # Get popular queries that start with partial query
        for query, count in self.search_stats["popular_queries"].most_common():
            if query.startswith(partial_query.lower()):
                suggestions.append(query)
                if len(suggestions) >= limit:
                    break
        
        return suggestions
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search statistics."""
        return {
            "search_stats": self.search_stats.copy(),
            "index_stats": self.index.get_statistics()
        }
    
    def reindex_all_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Reindex all documents."""
        try:
            # Clear existing index
            self.index = InvertedIndex()
            
            # Reindex all documents
            for doc_data in documents:
                self.index_document(
                    document_id=doc_data["document_id"],
                    user_id=doc_data["user_id"],
                    title=doc_data["title"],
                    content=doc_data["content"],
                    metadata=doc_data.get("metadata", {}),
                    file_type=doc_data["file_type"],
                    tags=doc_data.get("tags", [])
                )
            
            logger.info(f"Reindexed {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reindex documents: {e}")
            return False

# Global search engine instance
_search_engine: Optional[SearchEngine] = None

def get_search_engine() -> SearchEngine:
    """Get the global search engine instance."""
    global _search_engine
    
    if _search_engine is None:
        _search_engine = SearchEngine()
    
    return _search_engine

# Helper functions
def index_document_for_search(document_id: str, user_id: str, title: str, 
                            content: str, metadata: Dict[str, Any], 
                            file_type: str, tags: List[str] = None) -> bool:
    """Index a document for search."""
    engine = get_search_engine()
    return engine.index_document(document_id, user_id, title, content, 
                               metadata, file_type, tags)

def remove_from_search_index(document_id: str) -> bool:
    """Remove document from search index."""
    engine = get_search_engine()
    return engine.remove_document(document_id)

def search_documents(query: str, user_id: str = None, **kwargs) -> Dict[str, Any]:
    """Search documents."""
    engine = get_search_engine()
    return engine.search(query, user_id, **kwargs)

def get_search_suggestions(partial_query: str, user_id: str = None, limit: int = 10) -> List[str]:
    """Get search suggestions."""
    engine = get_search_engine()
    return engine.suggest_queries(partial_query, user_id, limit)

def get_search_statistics() -> Dict[str, Any]:
    """Get search statistics."""
    engine = get_search_engine()
    return engine.get_search_statistics()
