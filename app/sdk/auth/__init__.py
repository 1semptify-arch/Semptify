"""
Semptify Auth SDK
=================
Framework-free authentication primitives.

Zero dependencies on FastAPI, SQLAlchemy, or any web framework.
Importable by any Semptify product, module, or external SDK consumer.

Usage:
    from app.sdk.auth import CookieAuth, hash_token, make_user_id, UserRole
"""

from app.sdk.auth.cookie import CookieAuth, set_auth_cookie, verify_auth_cookie
from app.sdk.auth.tokens import hash_token, generate_token, verify_hmac_user_id
from app.sdk.auth.user_id import make_user_id, parse_user_id, UserIdComponents
from app.sdk.auth.roles import UserRole, ROLE_PERMISSIONS, get_permissions

__all__ = [
    "CookieAuth",
    "set_auth_cookie",
    "verify_auth_cookie",
    "hash_token",
    "generate_token",
    "verify_hmac_user_id",
    "make_user_id",
    "parse_user_id",
    "UserIdComponents",
    "UserRole",
    "ROLE_PERMISSIONS",
    "get_permissions",
]
