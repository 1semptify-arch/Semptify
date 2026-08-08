"""Tests for manager dashboard presence and statistics."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.utc import utc_now
from app.core.manager_dashboard import get_staff_list, ONLINE_THRESHOLD_MINUTES
from app.models.models import User, InviteCode


def _make_session(users_by_id, redeemed_codes):
    """Build a minimal mocked SQLAlchemy session for staff-list tests."""
    session = MagicMock()

    def _query_side_effect(model):
        query_mock = MagicMock()
        if model is InviteCode:
            filter_mock = MagicMock()
            filter_mock.all.return_value = redeemed_codes
            query_mock.filter.return_value = filter_mock
        elif model is User:
            def _first():
                # filter_by was called with keyword args, e.g. filter_by(id=user_id)
                kwargs = query_mock.filter_by.call_args.kwargs
                return users_by_id.get(kwargs.get("id"))

            filter_by_mock = MagicMock()
            filter_by_mock.first.side_effect = _first
            query_mock.filter_by.return_value = filter_by_mock

            filter_mock = MagicMock()
            filter_mock.all.return_value = list(users_by_id.values())
            query_mock.filter.return_value = filter_mock
        else:
            query_mock.all.return_value = []
            query_mock.count.return_value = 0
        return query_mock

    session.query.side_effect = _query_side_effect
    return session


def _user(last_login=None, updated_at=None, user_id="user_123"):
    user = MagicMock(spec=User)
    user.id = user_id
    user.last_login = last_login
    user.updated_at = updated_at
    return user


def _invite_code(role="advocate", used_by=None):
    code = MagicMock(spec=InviteCode)
    code.role = role
    code.used_by = used_by or []
    return code


@pytest.mark.anyio
async def test_staff_list_online_when_last_login_recent():
    """A user with a recent last_login is shown as online."""
    recent = utc_now() - timedelta(minutes=5)
    user = _user(last_login=recent, user_id="user_online")
    code = _invite_code(role="advocate", used_by=["user_online"])
    session = _make_session({"user_online": user}, [code])

    staff = get_staff_list("org_1", session)

    assert len(staff) == 1
    assert staff[0]["status"] == "online"
    assert staff[0]["last_seen"] == recent.isoformat()


@pytest.mark.anyio
async def test_staff_list_offline_when_last_login_old():
    """A user whose last_login is beyond the threshold is shown as offline."""
    old = utc_now() - timedelta(minutes=ONLINE_THRESHOLD_MINUTES + 5)
    user = _user(last_login=old, user_id="user_offline")
    code = _invite_code(role="manager", used_by=["user_offline"])
    session = _make_session({"user_offline": user}, [code])

    staff = get_staff_list("org_1", session)

    assert staff[0]["status"] == "offline"


@pytest.mark.anyio
async def test_staff_list_online_from_updated_at_when_last_login_missing():
    """If last_login is absent, updated_at is used to determine presence."""
    recent = utc_now() - timedelta(minutes=2)
    user = _user(last_login=None, updated_at=recent, user_id="user_updated")
    code = _invite_code(role="legal", used_by=["user_updated"])
    session = _make_session({"user_updated": user}, [code])

    staff = get_staff_list("org_1", session)

    assert staff[0]["status"] == "online"
    assert staff[0]["last_seen"] == recent.isoformat()


@pytest.mark.anyio
async def test_staff_list_online_prefers_most_recent_activity():
    """Presence uses the later of last_login and updated_at."""
    old_login = utc_now() - timedelta(hours=2)
    recent_update = utc_now() - timedelta(minutes=1)
    user = _user(last_login=old_login, updated_at=recent_update, user_id="user_active")
    code = _invite_code(role="admin", used_by=["user_active"])
    session = _make_session({"user_active": user}, [code])

    staff = get_staff_list("org_1", session)

    assert staff[0]["status"] == "online"
    assert staff[0]["last_seen"] == recent_update.isoformat()


@pytest.mark.anyio
async def test_staff_list_handles_naive_datetime():
    """Naive datetimes are treated as UTC before comparing."""
    recent_naive = datetime.utcnow() - timedelta(minutes=3)
    user = _user(last_login=recent_naive, user_id="user_naive")
    code = _invite_code(role="advocate", used_by=["user_naive"])
    session = _make_session({"user_naive": user}, [code])

    staff = get_staff_list("org_1", session)

    assert staff[0]["status"] == "online"
