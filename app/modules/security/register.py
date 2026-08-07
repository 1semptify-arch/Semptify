"""Security module registration helper — FunctionGroupContracts.

The security module handles 2FA, session management, security events,
and security recommendations. It is the protection layer for user accounts.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

# --- Two-Factor Authentication ---

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_2fa_setup",
        title="Security 2FA Setup (SSOT)",
        description=(
            "CANONICAL setup two-factor authentication. Generates a TOTP "
            "secret and QR code for the user to scan with their authenticator."
        ),
        inputs=("user_id", "method?"),
        outputs=("secret", "qr_code", "backup_codes"),
        dependencies=("app.modules.security.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_2fa_verify",
        title="Security 2FA Verify (SSOT)",
        description=(
            "CANONICAL verify a 2FA code during setup. Confirms the user "
            "has correctly configured their authenticator before enabling."
        ),
        inputs=("user_id", "code"),
        outputs=("verified",),
        dependencies=("app.modules.security.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_2fa_enable",
        title="Security 2FA Enable (SSOT)",
        description=(
            "CANONICAL enable 2FA after successful verification. Activates 2FA requirement for the user's account."
        ),
        inputs=("user_id", "code"),
        outputs=("enabled",),
        dependencies=("app.modules.security.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_2fa_disable",
        title="Security 2FA Disable (SSOT)",
        description=(
            "CANONICAL disable 2FA. Removes the 2FA requirement from the "
            "user's account. Requires the user's password or a valid 2FA code."
        ),
        inputs=("user_id",),
        outputs=("disabled",),
        dependencies=("app.modules.security.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_2fa_status",
        title="Security 2FA Status (SSOT)",
        description=(
            "CANONICAL 2FA status check. Returns whether 2FA is enabled, "
            "the method, and whether backup codes are available."
        ),
        inputs=("user_id",),
        outputs=("enabled", "method", "backup_codes_available"),
        dependencies=("app.modules.security.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_2fa_regenerate_codes",
        title="Security 2FA Regenerate Backup Codes (SSOT)",
        description=(
            "CANONICAL regenerate backup codes for 2FA. Issues a new set of "
            "one-time backup codes. Previous codes are invalidated."
        ),
        inputs=("user_id",),
        outputs=("backup_codes",),
        dependencies=("app.modules.security.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_2fa_methods",
        title="Security 2FA Supported Methods (SSOT)",
        description=(
            "CANONICAL list of supported 2FA methods. Returns the available "
            "methods (totp, sms, email) for the frontend to display."
        ),
        inputs=(),
        outputs=("methods",),
        dependencies=("app.modules.security.router",),
        deterministic=True,
    )
)

# --- Session Management ---

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_session_create",
        title="Security Session Create (SSOT)",
        description=(
            "CANONICAL create a secure session. Issues a session token with "
            "device info and expiration. Used after login."
        ),
        inputs=("user_id", "device_info?"),
        outputs=("session_id", "expires_at"),
        dependencies=("app.modules.security.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_session_validate",
        title="Security Session Validate (SSOT)",
        description=("CANONICAL validate a session. Returns whether the session is valid, expired, or revoked."),
        inputs=("user_id",),
        outputs=("valid",),
        dependencies=("app.modules.security.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_session_revoke",
        title="Security Session Revoke (SSOT)",
        description=(
            "CANONICAL revoke a specific session. Used when the user logs out "
            "from a specific device or when a session is compromised."
        ),
        inputs=("session_id", "reason?"),
        outputs=("revoked",),
        dependencies=("app.modules.security.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_session_revoke_all",
        title="Security Session Revoke All (SSOT)",
        description=(
            "CANONICAL revoke all sessions for the user. Used when the user "
            "suspects their account is compromised. Optionally keeps one "
            "session active."
        ),
        inputs=("user_id", "except_session_id?"),
        outputs=("revoked_count",),
        dependencies=("app.modules.security.router",),
        deterministic=False,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_sessions_list",
        title="Security Sessions List (SSOT)",
        description=(
            "CANONICAL list of active sessions for the user. Returns session "
            "metadata (device, location, last active) for the session manager."
        ),
        inputs=("user_id",),
        outputs=("sessions",),
        dependencies=("app.modules.security.router",),
        deterministic=True,
    )
)

# --- Security Status & Events ---

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_status",
        title="Security Status (SSOT)",
        description=(
            "CANONICAL security status for the user. Returns 2FA status, "
            "active session count, and recent security events. "
            "Used by the security settings page."
        ),
        inputs=("user_id",),
        outputs=("two_factor", "active_sessions", "recent_events"),
        dependencies=("app.modules.security.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_events",
        title="Security Events (SSOT)",
        description=(
            "CANONICAL list of security events for the user. Returns login "
            "attempts, 2FA changes, session revocations, and other security-"
            "relevant events. Supports filtering by severity."
        ),
        inputs=("user_id", "severity?", "limit?"),
        outputs=("events",),
        dependencies=("app.modules.security.router",),
        deterministic=True,
    )
)

register_function_group(
    FunctionGroupContract(
        module="security",
        group_name="security_recommendations",
        title="Security Recommendations (SSOT)",
        description=(
            "CANONICAL security recommendations for the user. Returns "
            "suggestions like 'enable 2FA', 'revoke old sessions', etc. "
            "Used by the security settings page."
        ),
        inputs=("user_id",),
        outputs=("recommendations",),
        dependencies=("app.modules.security.router",),
        deterministic=True,
    )
)
