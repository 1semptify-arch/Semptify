"""Tests for app.core.cache_manager — caching system."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.cache_manager import (
    CacheBackend,
    CacheEntry,
    CacheManager,
    MemoryCache,
)

# ── CacheEntry ───────────────────────────────────────────────────────────────

class TestCacheEntry:
    def test_defaults(self):
        entry = CacheEntry(
            key="k",
            value="v",
            expires_at=None,
            created_at=datetime.now(UTC),
        )
        assert entry.access_count == 0
        assert entry.tags == []
        assert entry.size_bytes > 0

    def test_is_expired_false_when_no_expiry(self):
        entry = CacheEntry(
            key="k", value="v",
            expires_at=None,
            created_at=datetime.now(UTC),
        )
        assert entry.is_expired() is False

    def test_is_expired_false_when_future(self):
        entry = CacheEntry(
            key="k", value="v",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            created_at=datetime.now(UTC),
        )
        assert entry.is_expired() is False

    def test_is_expired_true_when_past(self):
        entry = CacheEntry(
            key="k", value="v",
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
            created_at=datetime.now(UTC),
        )
        assert entry.is_expired() is True

    def test_touch_increments(self):
        entry = CacheEntry(
            key="k", value="v",
            expires_at=None,
            created_at=datetime.now(UTC),
        )
        entry.touch()
        assert entry.access_count == 1
        entry.touch()
        assert entry.access_count == 2

    def test_to_dict(self):
        entry = CacheEntry(
            key="k", value="v",
            expires_at=None,
            created_at=datetime.now(UTC),
            tags=["t1"],
        )
        d = entry.to_dict()
        assert d["key"] == "k"
        assert d["tags"] == ["t1"]
        assert d["expires_at"] is None
        assert "created_at" in d


# ── MemoryCache ──────────────────────────────────────────────────────────────

class TestMemoryCache:
    def test_set_and_get(self):
        cache = MemoryCache()
        cache.set("k", "v")
        assert cache.get("k") == "v"

    def test_get_missing(self):
        cache = MemoryCache()
        assert cache.get("nope") is None

    def test_get_expired(self):
        cache = MemoryCache()
        cache.set("k", "v", ttl_seconds=1)
        cache.cache["k"].expires_at = datetime.now(UTC) - timedelta(seconds=10)
        assert cache.get("k") is None

    def test_delete_existing(self):
        cache = MemoryCache()
        cache.set("k", "v")
        assert cache.delete("k") is True
        assert cache.get("k") is None

    def test_delete_missing(self):
        cache = MemoryCache()
        assert cache.delete("nope") is False

    def test_clear(self):
        cache = MemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.current_size_bytes == 0

    def test_overwrite(self):
        cache = MemoryCache()
        cache.set("k", "old")
        cache.set("k", "new")
        assert cache.get("k") == "new"

    def test_stats_hits_and_misses(self):
        cache = MemoryCache()
        cache.set("k", "v")
        cache.get("k")
        cache.get("miss")
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["entries"] == 1

    def test_eviction_on_max_entries(self):
        cache = MemoryCache(max_entries=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert len(cache.cache) == 2
        assert cache.evictions >= 1

    def test_get_entries_by_tag(self):
        cache = MemoryCache()
        cache.set("a", 1, tags=["t1"])
        cache.set("b", 2, tags=["t2"])
        cache.set("c", 3, tags=["t1", "t2"])
        tagged = cache.get_entries_by_tag("t1")
        keys = {e.key for e in tagged}
        assert keys == {"a", "c"}

    def test_delete_by_tag(self):
        cache = MemoryCache()
        cache.set("a", 1, tags=["t1"])
        cache.set("b", 2, tags=["t2"])
        cache.set("c", 3, tags=["t1"])
        deleted = cache.delete_by_tag("t1")
        assert deleted == 2
        assert cache.get("b") == 2
        assert cache.get("a") is None


# ── CacheManager ─────────────────────────────────────────────────────────────

class TestCacheManager:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        mgr = CacheManager()
        await mgr.set("k", "v")
        result = await mgr.get("k")
        assert result == "v"

    @pytest.mark.asyncio
    async def test_get_missing(self):
        mgr = CacheManager()
        result = await mgr.get("nope")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        mgr = CacheManager()
        await mgr.set("k", "v")
        deleted = await mgr.delete("k")
        assert deleted is True
        assert await mgr.get("k") is None

    @pytest.mark.asyncio
    async def test_clear(self):
        mgr = CacheManager()
        await mgr.set("a", 1)
        await mgr.set("b", 2)
        await mgr.clear()
        assert await mgr.get("a") is None

    @pytest.mark.asyncio
    async def test_ttl_capped_at_max(self):
        mgr = CacheManager()
        mgr.max_ttl = 100
        await mgr.set("k", "v", ttl_seconds=999)
        entry = mgr.get_backend().cache["k"]
        diff = (entry.expires_at - entry.created_at).total_seconds()
        assert diff <= 100

    @pytest.mark.asyncio
    async def test_default_ttl_applied(self):
        mgr = CacheManager()
        mgr.default_ttl = 60
        await mgr.set("k", "v")
        entry = mgr.get_backend().cache["k"]
        assert entry.expires_at is not None

    @pytest.mark.asyncio
    async def test_get_backend_none_for_unknown(self):
        mgr = CacheManager()
        backend = mgr.get_backend(CacheBackend.REDIS)
        assert backend is None

    @pytest.mark.asyncio
    async def test_set_returns_false_for_missing_backend(self):
        mgr = CacheManager()
        result = await mgr.set("k", "v", backend=CacheBackend.REDIS)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_backend(self):
        mgr = CacheManager()
        result = await mgr.get("k", backend=CacheBackend.REDIS)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_missing_backend(self):
        mgr = CacheManager()
        result = await mgr.delete("k", backend=CacheBackend.REDIS)
        assert result is False


# ── CacheBackend enum ────────────────────────────────────────────────────────

class TestCacheBackendEnum:
    def test_values(self):
        assert CacheBackend.MEMORY.value == "memory"
        assert CacheBackend.REDIS.value == "redis"
        assert CacheBackend.FILE.value == "file"
