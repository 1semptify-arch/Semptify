"""ONBOARDING SOLO — tenant-only onboarding guarantees.

Brad, 2026-09-23: this repo onboards tenants only. There is no role
selection page, no role URL parameter, and no OAuth state path that can mint
or advertise a professional role. Pro-role onboarding is a separate add-on
(different repo); there is no in-repo elevation path — the role-switch
endpoint was deleted entirely.
"""

import importlib
from pathlib import Path

from app.modules.onboarding import oauth as onboarding_oauth
from app.modules.onboarding.router import _render_providers_page
from app.modules.onboarding.config import OnboardingConfig
from app.core.page_manifest import PAGE_MANIFEST

storage_module = importlib.import_module("app.modules.storage.router")

REPO_ROOT = Path(__file__).resolve().parent.parent

PRO_ROLES = {
    "advocate",
    "legal",
    "manager",
    "admin",
    "judge",
    "multi_client_advocate",
    "donor_supporter",
    "researcher",
    "research",
    "agency",
    "developer",
}


def _config() -> OnboardingConfig:
    return OnboardingConfig(
        product_name="Semptify",
        allowed_roles=["tenant"],
        allowed_providers=["google_drive"],
        on_complete_redirect="/home",
    )


def test_onboarding_oauth_only_mints_tenant():
    """Onboarding OAuth can never mint a professional-role user_id."""
    assert onboarding_oauth.ALLOWED_ROLES == {"tenant", "user"}
    assert PRO_ROLES.isdisjoint(onboarding_oauth.ALLOWED_ROLES)


def test_storage_oauth_mintable_roles():
    """ROLE REVIVAL (Brad, 2026-11-19): storage OAuth may mint tenant plus the
    client-facing professional roles (advocate, legal) via ?role=. 'admin' is
    NOT mintable through OAuth — ops-level access is minted server-side only."""
    assert storage_module.MINTABLE_ROLES == {"tenant", "user", "advocate", "legal"}
    assert "admin" not in storage_module.MINTABLE_ROLES


def test_no_role_switch_surface():
    """The /api/storage/role switch endpoint and its plumbing were deleted —
    there is no in-repo elevation path at all (Brad: 'none are to be gated,
    there is no other role other than tenant')."""
    assert not hasattr(storage_module, "ALLOWED_ROLES")
    assert not hasattr(storage_module, "RoleSwitchRequest")
    assert not hasattr(storage_module, "VALID_INVITE_CODES")
    assert not hasattr(storage_module, "ADMIN_PIN")
    route_paths = {getattr(r, "path", "") for r in storage_module.router.routes}
    assert "/role" not in route_paths


def test_user_ids_decode_real_role():
    """ROLE REVIVAL (Brad, 2026-11-19): the role letter in a user_id decodes
    as written — tenant, advocate, legal, admin all decode to their role.
    Forgery protection comes from the HMAC cookie signature and from mint
    gating (onboarding ALLOWED_ROLES / storage MINTABLE_ROLES), not from
    decode coercion."""
    from app.core.user_id import parse_user_id, generate_user_id

    expected = {
        "U": "tenant", "A": "admin", "M": "manager", "L": "legal",
        "V": "advocate", "J": "judge", "C": "multi_client_advocate",
        "S": "donor_supporter", "R": "researcher", "P": "developer",
    }
    for letter, want in expected.items():
        provider, role, _ = parse_user_id(f"G{letter}abc12345")
        assert role == want, f"letter {letter} decoded as {role}, want {want}"

    # Minting produces the letter for the requested role
    for role, letter in (("tenant", "U"), ("legal", "L"), ("advocate", "V"), ("admin", "A")):
        uid = generate_user_id("google_drive", role)
        assert uid[1] == letter, f"generate_user_id({role}) minted letter {uid[1]}, want {letter}"


def test_only_tenant_role_config_remains():
    """The pro-role configs are gone — the role plugin registry in this
    repo defines tenant only. Future roles live in the add-on repo."""
    config_dir = REPO_ROOT / "app/modules/onboarding/role_configs"
    configs = {p.name for p in config_dir.glob("*.json")}
    assert configs == {"tenant.json"}


def test_role_selection_page_is_gone():
    """The role picker was removed entirely — no manifest entry, no template,
    no render function."""
    assert all(e.page_id != "role_selection" for e in PAGE_MANIFEST)
    assert not (REPO_ROOT / "app/templates/pages/role_selection.html").exists()
    router_mod = importlib.import_module("app.modules.onboarding.router")
    assert not hasattr(router_mod, "_render_role_selection_page")


def test_no_pro_role_validation_pages():
    """Static advocate/legal invite-validation pages are removed — pro
    onboarding lives in a separate repo."""
    validation_dir = REPO_ROOT / "static/onboarding/validation"
    for name in ("validate-advocate.html", "validate-legal.html"):
        assert not (validation_dir / name).exists()


def test_providers_page_carries_no_role():
    """The provider-selection page must not read or forward any role."""
    html = _render_providers_page(_config())
    assert "role=" not in html
    for role in PRO_ROLES:
        assert role not in html
