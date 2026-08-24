"""Tests for app.core.user_id and storage_middleware user validation."""

from app.core.cookie_auth import sign_user_id
from app.core.storage_middleware import is_valid_storage_user
from app.core.user_id import (
    ProviderCode,
    generate_user_id,
    parse_user_id,
)


def test_parse_google_user_id():
    """A Google Drive user ID parses correctly."""
    provider, role, unique = parse_user_id("GU7x9kM2pQ")
    assert provider == "google_drive"
    assert role == "tenant"
    assert unique == "7x9kM2pQ"


def test_generate_google_user_id():
    """We can generate a Google Drive user ID."""
    user_id = generate_user_id("google_drive", "user")
    assert user_id.startswith("GU")
    assert len(user_id) == 10


def test_generate_dropbox_user_id():
    """We can generate a Dropbox user ID."""
    user_id = generate_user_id("dropbox", "user")
    assert user_id.startswith("DU")
    assert len(user_id) == 10


def test_generate_onedrive_user_id():
    """We can generate a OneDrive user ID."""
    user_id = generate_user_id("onedrive", "user")
    assert user_id.startswith("OU")
    assert len(user_id) == 10


def test_local_user_id_is_rejected():
    """Local-only user IDs are not supported; every user must use OAuth storage."""
    provider, role, unique = parse_user_id("LU7x9kM2pQ")
    assert provider is None
    assert role is None
    assert unique is None


def test_local_provider_code_is_not_first_class():
    """ProviderCode does NOT include a LOCAL option."""
    assert not hasattr(ProviderCode, "LOCAL")


def test_storage_middleware_rejects_local_user():
    """is_valid_storage_user rejects a local user ID."""
    user_id = "LU7x9kM2pQ"
    signed = sign_user_id(user_id)
    assert is_valid_storage_user(signed) is False
