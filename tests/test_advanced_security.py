"""Tests for app.core.advanced_security."""

from datetime import timedelta

import pyotp
import pytest
from unittest.mock import patch

from app.core.advanced_security import (
    AdvancedSecurityManager,
    SessionManager,
    SessionStatus,
    TwoFactorAuthManager,
    TwoFactorMethod,
    create_secure_session,
    disable_two_factor,
    enable_two_factor,
    get_advanced_security_manager,
    get_security_status,
    setup_two_factor_auth,
    validate_secure_session,
    verify_two_factor,
)


def test_two_factor_setup_and_verify():
    """Setup TOTP and verify a generated code."""
    manager = TwoFactorAuthManager()
    setup = manager.setup_two_factor("user_1", "user@example.com", method=TwoFactorMethod.BACKUP_CODES)
    assert setup.user_id == "user_1"
    assert len(setup.backup_codes) > 0

    # Generate and verify a TOTP code
    totp = pyotp.TOTP(setup.secret)
    code = totp.now()
    assert manager.verify_totp("user_1", code) is True

    # Enable 2FA
    assert manager.enable_two_factor("user_1") is True
    assert manager.is_two_factor_enabled("user_1") is True

    # Verify two_factor with backup code
    backup_code = setup.backup_codes[0]
    assert manager.verify_two_factor("user_1", backup_code, method=TwoFactorMethod.BACKUP_CODES) is True
    # Used backup code is removed
    assert manager.verify_two_factor("user_1", backup_code, method=TwoFactorMethod.BACKUP_CODES) is False


def test_two_factor_enable_without_setup():
    """Enable 2FA for a user without setup returns False."""
    manager = TwoFactorAuthManager()
    assert manager.enable_two_factor("no_setup") is False


def test_two_factor_status_and_disable():
    """Status reflects setup and disable removes 2FA."""
    manager = TwoFactorAuthManager()
    manager.setup_two_factor("user_2", "user2@example.com", method=TwoFactorMethod.BACKUP_CODES)
    manager.enable_two_factor("user_2")

    status = manager.get_two_factor_status("user_2")
    assert status["enabled"] is True
    assert status["has_setup"] is True
    assert status["method"] == TwoFactorMethod.TOTP.value

    assert manager.disable_two_factor("user_2") is True
    assert manager.is_two_factor_enabled("user_2") is False


def test_two_factor_unknown_method():
    """verify_two_factor with an unsupported method returns False."""
    manager = TwoFactorAuthManager()
    setup = manager.setup_two_factor("user_3", "user3@example.com", method=TwoFactorMethod.BACKUP_CODES)
    assert manager.verify_two_factor("user_3", setup.backup_codes[0], method=TwoFactorMethod.SMS) is False


def test_regenerate_backup_codes():
    """regenerate_backup_codes replaces codes for a user."""
    manager = TwoFactorAuthManager()
    setup = manager.setup_two_factor("user_4", "user4@example.com", method=TwoFactorMethod.BACKUP_CODES)
    new_codes = manager.regenerate_backup_codes("user_4")
    assert len(new_codes) == len(setup.backup_codes)
    assert manager.backup_codes["user_4"] == new_codes

    assert manager.regenerate_backup_codes("unknown") == []


def test_generate_qr_code_requires_qrcode():
    """generate_qr_code raises when the qrcode package is not installed."""
    manager = TwoFactorAuthManager()
    with pytest.raises(RuntimeError):
        manager.generate_qr_code("secret", "user@example.com")


def test_session_lifecycle():
    """Create, validate, extend, and revoke a session."""
    manager = SessionManager()
    session_id = manager.create_session("user_1", "127.0.0.1", "pytest")
    assert session_id in manager.sessions

    session = manager.validate_session(session_id)
    assert session is not None
    assert session.status == SessionStatus.ACTIVE

    assert manager.extend_session(session_id, duration=timedelta(hours=1)) is True
    session = manager.sessions[session_id]
    assert session.expires_at > session.created_at

    assert manager.revoke_session(session_id) is True
    assert session_id not in manager.sessions


def test_session_ip_change_logs_event():
    """Session validation with a different IP logs a security event."""
    manager = SessionManager()
    session_id = manager.create_session("user_1", "127.0.0.1", "pytest")
    session = manager.validate_session(session_id, ip_address="10.0.0.1")
    assert session is not None
    events = manager.get_user_security_events("user_1")
    assert any(e.event_type == "ip_address_change" for e in events)


def test_session_max_per_user_and_cleanup():
    """Create more sessions than the limit and verify cleanup."""
    manager = SessionManager()
    max_sessions = manager.max_sessions_per_user
    session_ids = []
    for i in range(max_sessions + 2):
        sid = manager.create_session("user_2", f"127.0.0.{i}", "pytest")
        session_ids.append(sid)

    user_sessions = manager.get_user_sessions("user_2")
    assert len(user_sessions) == max_sessions

    # Clean up expired sessions should remove none
    assert manager.cleanup_expired_sessions() == 0


def test_cleanup_expired_sessions():
    """Expired sessions are removed by cleanup_expired_sessions."""
    manager = SessionManager()
    sid = manager.create_session("user_3", "127.0.0.1", "pytest", duration=timedelta(seconds=-1))
    assert sid in manager.sessions
    assert manager.cleanup_expired_sessions() == 1
    assert sid not in manager.sessions


def test_get_session_statistics():
    """get_session_statistics reports total and active session counts."""
    manager = SessionManager()
    manager.create_session("user_1", "127.0.0.1", "pytest")
    stats = manager.get_session_statistics()
    assert stats["total_sessions"] == 1
    assert stats["active_sessions"] == 1
    assert stats["unique_users"] == 1


def test_revoke_all_user_sessions():
    """revoke_all_user_sessions revokes all but the excepted session."""
    manager = SessionManager()
    sid1 = manager.create_session("user_4", "127.0.0.1", "pytest")
    sid2 = manager.create_session("user_4", "127.0.0.2", "pytest")
    sid3 = manager.create_session("user_4", "127.0.0.3", "pytest")

    assert manager.revoke_all_user_sessions("user_4", except_session_id=sid2) == 2
    user_sessions = manager.get_user_sessions("user_4")
    assert len(user_sessions) == 1
    assert user_sessions[0].session_id == sid2


def test_advanced_security_manager_combined():
    """AdvancedSecurityManager orchestrates 2FA and sessions."""
    manager = AdvancedSecurityManager()
    with patch.object(manager.two_factor, "generate_qr_code", return_value="mock-qr"):
        setup = manager.setup_two_factor_auth("user_1", "user1@example.com")
    assert setup.user_id == "user_1"
    assert manager.enable_two_factor("user_1") is True

    session = manager.create_secure_session("user_1", "127.0.0.1", "pytest", require_2fa=True)
    assert session["two_factor_required"] is True
    assert "session_id" in session

    # Validate the session
    validated = manager.validate_secure_session(session["session_id"])
    assert validated is not None

    status = manager.get_security_status("user_1")
    assert status["user_id"] == "user_1"
    assert status["two_factor"]["enabled"] is True
    assert status["security_score"] >= 0


def test_global_helper_functions():
    """Module-level helper functions return consistent results."""
    # Reset global singleton so we don't share state with other tests
    import app.core.advanced_security as sec

    original = sec._advanced_security_manager
    sec._advanced_security_manager = AdvancedSecurityManager()
    try:
        assert get_advanced_security_manager() is sec._advanced_security_manager

        with patch.object(sec._advanced_security_manager.two_factor, "generate_qr_code", return_value="mock-qr"):
            setup = setup_two_factor_auth("global_user", "global@example.com")
        assert setup.user_id == "global_user"

        enable_two_factor("global_user")
        assert get_security_status("global_user")["two_factor"]["enabled"] is True

        session = create_secure_session("global_user", "127.0.0.1", "pytest")
        sid = session["session_id"]
        assert validate_secure_session(sid) is not None

        disable_two_factor("global_user")
        assert verify_two_factor("global_user", "000000") is False
    finally:
        sec._advanced_security_manager = original
