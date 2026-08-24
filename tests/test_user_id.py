"""Tests for app.core.user_id and storage_middleware user validation."""

from app.core.cookie_auth import sign_user_id
from app.core.storage_middleware import is_valid_storage_user
from app.core.user_id import (
    ProviderCode,
    generate_user_id,
    parse_user_id,
)


def test_parse_local_user_id():
    """A local user ID with the 'L' provider code parses correctly."""
    provider, role, unique = parse_user_id("LU7x9kM2pQ")
    assert provider == "local"
    assert role == "tenant"
    assert unique == "7x9kM2pQ"


def test_generate_local_user_id():
    """We can generate a local user ID."""
    user_id = generate_user_id("local", "user")
    assert user_id.startswith("LU")
    assert len(user_id) == 10


def test_local_provider_code_is_first_class():
    """ProviderCode includes the LOCAL option."""
    assert ProviderCode.LOCAL == "L"


def test_storage_middleware_accepts_local_user():
    """is_valid_storage_user accepts a properly formed, HMAC-signed local user ID."""
    user_id = "LU7x9kM2pQ"
    signed = sign_user_id(user_id)
    assert is_valid_storage_user(signed) is True
