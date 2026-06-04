"""Tests for app.core.sessions — session storage backends."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from app.core.sessions import (
    MemorySessionBackend,
    RedisSessionBackend,
    close_session_backend,
    configure_session_backend,
    get_session_backend,
)


@pytest.fixture
def backend():
    return MemorySessionBackend()


# ── MemorySessionBackend ─────────────────────────────────────────────────────

class TestMemorySessionBackend:
    @pytest.mark.asyncio
    async def test_set_and_get(self, backend):
        await backend.set("key1", {"user": "alice"})
        result = await backend.get("key1")
        assert result == {"user": "alice"}

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, backend):
        result = await backend.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing(self, backend):
        await backend.set("key1", {"user": "alice"})
        deleted = await backend.delete("key1")
        assert deleted is True
        assert await backend.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_missing(self, backend):
        deleted = await backend.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_exists_true(self, backend):
        await backend.set("key1", {"user": "alice"})
        assert await backend.exists("key1") is True

    @pytest.mark.asyncio
    async def test_exists_false(self, backend):
        assert await backend.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_extend_existing(self, backend):
        await backend.set("key1", {"user": "alice"}, ttl_seconds=10)
        result = await backend.extend("key1", ttl_seconds=3600)
        assert result is True
        assert await backend.get("key1") is not None

    @pytest.mark.asyncio
    async def test_extend_missing(self, backend):
        result = await backend.extend("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_expired_session_removed(self, backend):
        await backend.set("key1", {"user": "alice"}, ttl_seconds=1)
        from app.core.utc import utc_now
        backend._expiry["key1"] = utc_now() - timedelta(seconds=10)
        result = await backend.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_expired_not_in_exists(self, backend):
        await backend.set("key1", {"user": "alice"}, ttl_seconds=1)
        from app.core.utc import utc_now
        backend._expiry["key1"] = utc_now() - timedelta(seconds=10)
        assert await backend.exists("key1") is False

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, backend):
        await backend.set("key1", {"user": "alice"}, ttl_seconds=1)
        await backend.set("key2", {"user": "bob"}, ttl_seconds=3600)
        from app.core.utc import utc_now
        backend._expiry["key1"] = utc_now() - timedelta(seconds=10)
        backend._cleanup_expired()
        assert "key1" not in backend._store
        assert "key2" in backend._store

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self, backend):
        await backend.set("key1", {"version": 1})
        await backend.set("key1", {"version": 2})
        result = await backend.get("key1")
        assert result == {"version": 2}


# ── RedisSessionBackend ──────────────────────────────────────────────────────

class TestRedisSessionBackend:
    def test_key_prefix(self):
        rb = RedisSessionBackend(prefix="test:")
        assert rb._key("sess-1") == "test:sess-1"

    def test_default_prefix(self):
        rb = RedisSessionBackend()
        assert rb._key("abc") == "semptify:session:abc"


# ── Module-level functions ───────────────────────────────────────────────────

class TestModuleFunctions:
    @pytest.mark.asyncio
    async def test_get_session_backend_returns_memory_by_default(self):
        import app.core.sessions as mod
        mod._session_backend = None
        backend = get_session_backend()
        assert isinstance(backend, MemorySessionBackend)

    @pytest.mark.asyncio
    async def test_configure_memory(self):
        import app.core.sessions as mod
        configure_session_backend(redis_url=None)
        assert isinstance(mod._session_backend, MemorySessionBackend)

    @pytest.mark.asyncio
    async def test_configure_redis(self):
        import app.core.sessions as mod
        configure_session_backend(redis_url="redis://localhost:6379")
        assert isinstance(mod._session_backend, RedisSessionBackend)

    @pytest.mark.asyncio
    async def test_close_memory_backend(self):
        import app.core.sessions as mod
        configure_session_backend(redis_url=None)
        await close_session_backend()
        assert mod._session_backend is None

    @pytest.mark.asyncio
    async def test_close_redis_backend(self):
        import app.core.sessions as mod
        configure_session_backend(redis_url="redis://localhost:6379")
        rb = mod._session_backend
        rb._client = AsyncMock()
        await close_session_backend()
        assert mod._session_backend is None
