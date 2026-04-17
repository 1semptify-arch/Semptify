"""
Cache Manager - Intelligent Caching System
======================================

Manages caching for frequently accessed data with multiple backends.
"""

import logging
import json
import time
import hashlib
import pickle
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import asyncio
import threading

logger = logging.getLogger(__name__)

class CacheBackend(Enum):
    """Cache backend types."""
    MEMORY = "memory"
    REDIS = "redis"
    FILE = "file"

@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    expires_at: Optional[datetime]
    created_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.last_accessed is None:
            self.last_accessed = self.created_at
        if self.size_bytes == 0:
            self.size_bytes = len(pickle.dumps(self.value))
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at
    
    def touch(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "size_bytes": self.size_bytes,
            "tags": self.tags
        }

class MemoryCache:
    """In-memory cache backend."""
    
    def __init__(self, max_size_mb: int = 100, max_entries: int = 10000):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.cache: Dict[str, CacheEntry] = {}
        self.current_size_bytes = 0
        self.lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expirations = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            entry = self.cache.get(key)
            
            if entry is None:
                self.misses += 1
                return None
            
            if entry.is_expired():
                del self.cache[key]
                self.current_size_bytes -= entry.size_bytes
                self.expirations += 1
                self.misses += 1
                return None
            
            entry.touch()
            self.hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, 
            tags: List[str] = None) -> bool:
        """Set value in cache."""
        with self.lock:
            # Calculate expiration
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at,
                created_at=datetime.now(timezone.utc),
                tags=tags or []
            )
            
            # Check if we need to evict
            self._ensure_capacity(entry.size_bytes)
            
            # Store entry
            old_entry = self.cache.get(key)
            if old_entry:
                self.current_size_bytes -= old_entry.size_bytes
            
            self.cache[key] = entry
            self.current_size_bytes += entry.size_bytes
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self.lock:
            entry = self.cache.pop(key, None)
            if entry:
                self.current_size_bytes -= entry.size_bytes
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.current_size_bytes = 0
    
    def _ensure_capacity(self, new_entry_size: int):
        """Ensure cache has capacity for new entry."""
        # Check entry count limit
        while len(self.cache) >= self.max_entries:
            self._evict_lru()
        
        # Check size limit
        while (self.current_size_bytes + new_entry_size) > self.max_size_bytes:
            self._evict_lru()
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.cache:
            return
        
        # Find LRU entry
        lru_key = min(self.cache.keys(), 
                     key=lambda k: self.cache[k].last_accessed)
        
        lru_entry = self.cache.pop(lru_key)
        self.current_size_bytes -= lru_entry.size_bytes
        self.evictions += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests) if total_requests > 0 else 0
            
            return {
                "entries": len(self.cache),
                "size_bytes": self.current_size_bytes,
                "size_mb": self.current_size_bytes / (1024 * 1024),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": hit_rate * 100,
                "evictions": self.evictions,
                "expirations": self.expirations
            }
    
    def get_entries_by_tag(self, tag: str) -> List[CacheEntry]:
        """Get all entries with a specific tag."""
        with self.lock:
            return [entry for entry in self.cache.values() if tag in entry.tags]
    
    def delete_by_tag(self, tag: str) -> int:
        """Delete all entries with a specific tag."""
        with self.lock:
            keys_to_delete = [key for key, entry in self.cache.items() 
                            if tag in entry.tags]
            
            for key in keys_to_delete:
                entry = self.cache.pop(key)
                self.current_size_bytes -= entry.size_bytes
            
            return len(keys_to_delete)

class CacheManager:
    """Intelligent cache manager with multiple backends."""
    
    def __init__(self, default_backend: CacheBackend = CacheBackend.MEMORY,
                 memory_size_mb: int = 100):
        self.default_backend = default_backend
        self.backends: Dict[CacheBackend, Any] = {}
        
        # Initialize memory backend
        self.backends[CacheBackend.MEMORY] = MemoryCache(
            max_size_mb=memory_size_mb
        )
        
        # Cache policies
        self.default_ttl = 3600  # 1 hour
        self.max_ttl = 86400  # 24 hours
        
        # Statistics
        self.operation_counts = defaultdict(int)
        
    def get_backend(self, backend: CacheBackend = None) -> Any:
        """Get cache backend."""
        backend = backend or self.default_backend
        return self.backends.get(backend)
    
    async def get(self, key: str, backend: CacheBackend = None) -> Optional[Any]:
        """Get value from cache."""
        cache_backend = self.get_backend(backend)
        if not cache_backend:
            return None
        
        value = cache_backend.get(key)
        self.operation_counts[f"get_{backend.value if backend else 'default'}"] += 1
        
        return value
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
                  backend: CacheBackend = None, tags: List[str] = None) -> bool:
        """Set value in cache."""
        cache_backend = self.get_backend(backend)
        if not cache_backend:
            return False
        
        # Use default TTL if not provided
        ttl_seconds = ttl_seconds or self.default_ttl
        
        # Enforce max TTL
        if ttl_seconds > self.max_ttl:
            ttl_seconds = self.max_ttl
        
        success = cache_backend.set(key, value, ttl_seconds, tags)
        self.operation_counts[f"set_{backend.value if backend else 'default'}"] += 1
        
        return success
    
    async def delete(self, key: str, backend: CacheBackend = None) -> bool:
        """Delete value from cache."""
        cache_backend = self.get_backend(backend)
        if not cache_backend:
            return False
        
        success = cache_backend.delete(key)
        self.operation_counts[f"delete_{backend.value if backend else 'default'}"] += 1
        
        return success
    
    async def clear(self, backend: CacheBackend = None):
        """Clear cache."""
        cache_backend = self.get_backend(backend)
        if cache_backend:
            cache_backend.clear()
            self.operation_counts[f"clear_{backend.value if backend else 'default'}"] += 1
    
    def cache_result(self, key_prefix: str = None, ttl_seconds: int = None, 
                    backend: CacheBackend = None, tags: List[str] = None):
        """Decorator to cache function results."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_cache_key(
                    func.__name__, args, kwargs, key_prefix
                )
                
                # Try to get from cache
                cached_result = await self.get(cache_key, backend)
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                await self.set(cache_key, result, ttl_seconds, backend, tags)
                
                return result
            
            return wrapper
        return decorator
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict, 
                           prefix: str = None) -> str:
        """Generate cache key for function call."""
        # Create hash of arguments
        args_hash = hashlib.md5(
            json.dumps([args, kwargs], sort_keys=True, default=str).encode()
        ).hexdigest()
        
        # Build key
        if prefix:
            return f"{prefix}:{func_name}:{args_hash}"
        else:
            return f"{func_name}:{args_hash}"
    
    async def invalidate_by_tag(self, tag: str, backend: CacheBackend = None) -> int:
        """Invalidate cache entries by tag."""
        cache_backend = self.get_backend(backend)
        if not cache_backend or not hasattr(cache_backend, 'delete_by_tag'):
            return 0
        
        deleted_count = cache_backend.delete_by_tag(tag)
        self.operation_counts[f"invalidate_tag_{backend.value if backend else 'default'}"] += 1
        
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "backends": {},
            "operations": dict(self.operation_counts)
        }
        
        for backend_name, backend in self.backends.items():
            if hasattr(backend, 'get_stats'):
                stats["backends"][backend_name.value] = backend.get_stats()
        
        return stats
    
    async def cleanup_expired(self):
        """Clean up expired entries."""
        for backend_name, backend in self.backends.items():
            if hasattr(backend, 'cleanup_expired'):
                await backend.cleanup_expired()

# Global cache manager instance
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
    
    return _cache_manager

# Cache decorators and helpers
def cache_user_data(ttl_seconds: int = 3600, tags: List[str] = None):
    """Cache user-specific data."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user_id from kwargs or args
            user_id = kwargs.get('user_id') or (args[0] if args else None)
            
            if not user_id:
                return await func(*args, **kwargs)
            
            cache_manager = get_cache_manager()
            cache_key = f"user_data:{user_id}:{func.__name__}"
            
            # Try cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute and cache
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl_seconds, tags=tags)
            
            return result
        
        return wrapper
    return decorator

def cache_document_data(ttl_seconds: int = 1800, tags: List[str] = None):
    """Cache document-specific data."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract document_id from kwargs or args
            document_id = kwargs.get('document_id') or kwargs.get('vault_id') or (args[0] if args else None)
            
            if not document_id:
                return await func(*args, **kwargs)
            
            cache_manager = get_cache_manager()
            cache_key = f"document_data:{document_id}:{func.__name__}"
            
            # Try cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute and cache
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl_seconds, tags=tags)
            
            return result
        
        return wrapper
    return decorator

def cache_system_data(ttl_seconds: int = 7200, tags: List[str] = None):
    """Cache system-wide data."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            cache_key = f"system_data:{func.__name__}"
            
            # Try cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute and cache
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl_seconds, tags=tags)
            
            return result
        
        return wrapper
    return decorator

# Helper functions
async def cache_get(key: str, backend: CacheBackend = None) -> Optional[Any]:
    """Get value from cache."""
    cache_manager = get_cache_manager()
    return await cache_manager.get(key, backend)

async def cache_set(key: str, value: Any, ttl_seconds: Optional[int] = None,
                   backend: CacheBackend = None, tags: List[str] = None) -> bool:
    """Set value in cache."""
    cache_manager = get_cache_manager()
    return await cache_manager.set(key, value, ttl_seconds, backend, tags)

async def cache_delete(key: str, backend: CacheBackend = None) -> bool:
    """Delete value from cache."""
    cache_manager = get_cache_manager()
    return await cache_manager.delete(key, backend)

async def cache_clear(backend: CacheBackend = None):
    """Clear cache."""
    cache_manager = get_cache_manager()
    await cache_manager.clear(backend)

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    cache_manager = get_cache_manager()
    return cache_manager.get_stats()

# Background cleanup task
async def start_cache_cleanup():
    """Start background cache cleanup task."""
    cache_manager = get_cache_manager()
    
    while True:
        try:
            await cache_manager.cleanup_expired()
            await asyncio.sleep(300)  # Run every 5 minutes
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute
