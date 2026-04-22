"""
Unit tests for the Redis-backed session store in app.core.security.

Tests the full session lifecycle against both the in-memory fallback path
(no Redis configured) and the Redis path (mocked).  All tests run without
requiring a live Redis instance.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import app.core.security as sec
from app.core.security import (
    create_session,
    get_session,
    update_session_role,
    update_session_token,
    invalidate_session,
    StoredSession,
    _store_session,
    _load_session,
    _delete_session,
    ACTIVE_SESSIONS,
)


# =============================================================================
# Helpers
# =============================================================================

def _make_session(**kwargs) -> StoredSession:
    defaults = dict(
        user_id="GUa8Km3xPq",
        provider="google",
        storage_user_id="goog-123",
        access_token="tok-abc",
        refresh_token=None,
        role="user",
        email=None,
        display_name=None,
        ttl_hours=24,
    )
    defaults.update(kwargs)
    return create_session(**defaults)


def _clear_memory():
    ACTIVE_SESSIONS.clear()


# =============================================================================
# In-Memory Fallback (no REDIS_URL set)
# =============================================================================

class TestInMemoryFallback:
    def setup_method(self):
        _clear_memory()
        # Ensure Redis is disabled
        sec._REDIS_CLIENT = None

    def test_create_and_get_session(self):
        with patch.dict("os.environ", {"REDIS_URL": ""}):
            session = _make_session()
            assert session.session_id
            loaded = get_session(session.session_id)
            assert loaded is not None
            assert loaded.user_id == "GUa8Km3xPq"

    def test_get_nonexistent_session(self):
        with patch.dict("os.environ", {"REDIS_URL": ""}):
            assert get_session("not-a-real-session-id") is None

    def test_get_expired_session_returns_none(self):
        with patch.dict("os.environ", {"REDIS_URL": ""}):
            session = _make_session(ttl_hours=0)
            # Force expiry into the past
            session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            ACTIVE_SESSIONS[session.session_id] = session
            assert get_session(session.session_id) is None
            assert session.session_id not in ACTIVE_SESSIONS

    def test_update_session_role(self):
        with patch.dict("os.environ", {"REDIS_URL": ""}):
            session = _make_session()
            updated = update_session_role(session.session_id, "admin")
            assert updated is not None
            assert updated.role == "admin"
            assert get_session(session.session_id).role == "admin"

    def test_update_session_role_nonexistent(self):
        with patch.dict("os.environ", {"REDIS_URL": ""}):
            result = update_session_role("bad-id", "admin")
            assert result is None

    def test_update_session_token(self):
        with patch.dict("os.environ", {"REDIS_URL": ""}):
            session = _make_session()
            updated = update_session_token(session.session_id, "new-token-xyz")
            assert updated is not None
            assert get_session(session.session_id).access_token == "new-token-xyz"

    def test_invalidate_session(self):
        with patch.dict("os.environ", {"REDIS_URL": ""}):
            session = _make_session()
            sid = session.session_id
            assert invalidate_session(sid) is True
            assert get_session(sid) is None

    def test_invalidate_nonexistent_session(self):
        with patch.dict("os.environ", {"REDIS_URL": ""}):
            assert invalidate_session("ghost-session-id") is False


# =============================================================================
# Redis Path (mocked)
# =============================================================================

class TestRedisPath:
    def setup_method(self):
        _clear_memory()
        sec._REDIS_CLIENT = None

    def _make_mock_redis(self):
        store = {}
        r = MagicMock()
        r.ping.return_value = True

        def _setex(key, ttl, value):
            store[key] = value

        def _set(key, value):
            store[key] = value

        def _get(key):
            return store.get(key)

        def _delete(key):
            existed = key in store
            store.pop(key, None)
            return int(existed)

        r.setex.side_effect = _setex
        r.set.side_effect = _set
        r.get.side_effect = _get
        r.delete.side_effect = _delete
        return r

    def test_session_written_to_redis(self):
        mock_redis = self._make_mock_redis()
        sec._REDIS_CLIENT = mock_redis

        session = _make_session()
        mock_redis.setex.assert_called_once()
        key_used = mock_redis.setex.call_args[0][0]
        assert key_used.startswith("semptify:session:")

    def test_session_read_from_redis(self):
        mock_redis = self._make_mock_redis()
        sec._REDIS_CLIENT = mock_redis

        session = _make_session()
        _clear_memory()  # wipe local dict to prove Redis is the source

        loaded = get_session(session.session_id)
        assert loaded is not None
        assert loaded.user_id == session.user_id

    def test_session_deleted_from_redis(self):
        mock_redis = self._make_mock_redis()
        sec._REDIS_CLIENT = mock_redis

        session = _make_session()
        result = invalidate_session(session.session_id)
        assert result is True

        mock_redis.delete.assert_called_once()
        _clear_memory()
        assert get_session(session.session_id) is None

    def test_redis_read_failure_falls_back_to_memory(self):
        mock_redis = self._make_mock_redis()
        mock_redis.get.side_effect = Exception("Redis connection lost")
        sec._REDIS_CLIENT = mock_redis

        # Store directly in memory fallback
        session = _make_session()
        ACTIVE_SESSIONS[session.session_id] = session

        loaded = _load_session(session.session_id)
        assert loaded is not None
        assert loaded.session_id == session.session_id

    def test_redis_write_failure_falls_back_to_memory(self):
        mock_redis = self._make_mock_redis()
        mock_redis.setex.side_effect = Exception("Redis write failed")
        mock_redis.set.side_effect = Exception("Redis write failed")
        sec._REDIS_CLIENT = mock_redis

        session = create_session(
            user_id="fallback-user",
            provider="google",
            storage_user_id="goog-fb",
            access_token="tok-fb",
        )
        # Should have fallen back to in-memory
        assert session.session_id in ACTIVE_SESSIONS
