"""Tests for the async cache and cache decorators."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.core.cache as cache_module
from app.core.cache import (
    CacheManager,
    InMemoryCache,
    RedisCache,
    _make_cache_key,
    cache_invalidate,
    cached,
)


class TestInMemoryCache:
    @pytest.mark.asyncio
    async def test_lifecycle_and_prefix_operations(self):
        cache = InMemoryCache()

        assert await cache.get("missing") is None
        assert await cache.set("user:1", {"name": "Ada"}) is True
        assert await cache.set("user:2", "two", ttl=60) is True
        assert await cache.exists("user:1") is True
        assert await cache.delete("user:1") is True
        assert await cache.delete("user:1") is False
        assert await cache.clear_prefix("user:") == 1
        assert await cache.exists("user:2") is False

        await cache.set("keep", "value")
        stats = await cache.get_stats()
        assert stats == {
            "backend": "memory",
            "total_keys": 1,
            "valid_keys": 1,
            "expired_keys": 0,
        }
        await cache.clear_all()
        assert await cache.get("keep") is None

    @pytest.mark.asyncio
    async def test_expired_entries_are_removed(self, monkeypatch):
        cache = InMemoryCache()
        await cache.set("expired", "value", ttl=1)
        value, _ = cache._cache["expired"]
        monkeypatch.setattr(cache_module, "utc_now", lambda: cache._cache["expired"][1])
        assert value == "value"
        assert await cache.get("expired") == "value"

        monkeypatch.setattr(
            cache_module,
            "utc_now",
            lambda: cache._cache["expired"][1].replace(microsecond=999999),
        )
        assert await cache.get("expired") is None


class FakeRedis:
    def __init__(self):
        self.get = AsyncMock(return_value='{"value": 1}')
        self.setex = AsyncMock()
        self.set = AsyncMock()
        self.delete = AsyncMock(return_value=1)
        self.exists = AsyncMock(return_value=1)
        self.scan = AsyncMock(side_effect=[(1, ["a", "b"]), (0, ["c"])])
        self.flushdb = AsyncMock()
        self.info = AsyncMock(
            return_value={"used_memory_human": "1M", "connected_clients": 2}
        )


class TestRedisCache:
    @pytest.mark.asyncio
    async def test_operations(self):
        cache = RedisCache("redis://localhost")
        cache._redis = FakeRedis()
        cache._connected = True

        assert await cache.get("key") == {"value": 1}
        assert await cache.set("key", {"value": 2}, ttl=30) is True
        cache._redis.setex.assert_awaited_once()
        assert await cache.delete("key") is True
        assert await cache.exists("key") is True
        assert await cache.clear_prefix("user:") == 3
        await cache.clear_all()
        assert await cache.get_stats() == {
            "backend": "redis",
            "connected": True,
            "used_memory": "1M",
            "connected_clients": 2,
        }

    @pytest.mark.asyncio
    async def test_operations_return_fallback_values_on_errors(self):
        cache = RedisCache("redis://localhost")
        cache._redis = FakeRedis()
        cache._connected = True
        cache._redis.get.side_effect = RuntimeError("get failed")
        cache._redis.set.side_effect = RuntimeError("set failed")
        cache._redis.delete.side_effect = RuntimeError("delete failed")
        cache._redis.exists.side_effect = RuntimeError("exists failed")
        cache._redis.scan.side_effect = RuntimeError("scan failed")
        cache._redis.flushdb.side_effect = RuntimeError("flush failed")
        cache._redis.info.side_effect = RuntimeError("info failed")

        assert await cache.get("key") is None
        assert await cache.set("key", "value") is False
        assert await cache.delete("key") is False
        assert await cache.exists("key") is False
        assert await cache.clear_prefix("key:") == 0
        await cache.clear_all()
        assert (await cache.get_stats())["connected"] is False

    @pytest.mark.asyncio
    async def test_disconnected_backend_returns_fallback_values(self):
        cache = RedisCache("redis://localhost")
        cache._ensure_connected = AsyncMock(return_value=False)

        assert await cache.get("key") is None
        assert await cache.set("key", "value") is False
        assert await cache.delete("key") is False
        assert await cache.exists("key") is False
        assert await cache.clear_prefix("key:") == 0
        await cache.clear_all()
        assert await cache.get_stats() == {"backend": "redis", "connected": False}


class TestCacheManagerAndDecorators:
    @pytest.mark.asyncio
    async def test_manager_uses_memory_backend_without_redis(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.config.get_settings",
            lambda: SimpleNamespace(redis_url=None),
        )
        manager = CacheManager()
        assert await manager.set("key", "value") is True
        assert await manager.get("key") == "value"
        assert await manager.exists("key") is True
        assert await manager.delete("key") is True
        assert await manager.clear_prefix("key") == 0
        assert (await manager.get_stats())["backend"] == "memory"

    @pytest.mark.asyncio
    async def test_cached_decorator_hits_and_caches_non_null_results(self, monkeypatch):
        monkeypatch.setattr(cache_module, "cache", CacheManager())
        calls = 0

        @cached(ttl=60, key_prefix="item")
        async def load_item(item_id: int):
            nonlocal calls
            calls += 1
            return {"id": item_id}

        assert await load_item(7) == {"id": 7}
        assert await load_item(7) == {"id": 7}
        assert calls == 1
        assert load_item.cache_key(7).startswith("item:")
        await load_item.cache_clear()
        assert await load_item(7) == {"id": 7}
        assert calls == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_does_not_cache_none_and_supports_custom_key(
        self, monkeypatch
    ):
        monkeypatch.setattr(cache_module, "cache", CacheManager())
        calls = 0

        @cached(key_builder=lambda item_id: f"custom:{item_id}")
        async def missing_item(item_id: int):
            nonlocal calls
            calls += 1
            return None

        assert await missing_item(3) is None
        assert await missing_item(3) is None
        assert calls == 2

    @pytest.mark.asyncio
    async def test_cache_invalidate_clears_prefix_after_success(self, monkeypatch):
        monkeypatch.setattr(cache_module, "cache", CacheManager())
        await cache_module.cache.set("user:1", "cached")

        @cache_invalidate("user")
        async def update_user(user_id: str):
            return user_id

        assert await update_user("user-1") == "user-1"
        assert await cache_module.cache.get("user:1") is None

    def test_cache_key_is_stable_for_keyword_order(self):
        assert _make_cache_key("item", (1,), {"b": 2, "a": 1}) == _make_cache_key(
            "item", (1,), {"a": 1, "b": 2}
        )
