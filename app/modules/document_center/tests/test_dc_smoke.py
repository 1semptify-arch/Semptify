"""Document Center smoke tests — Forge-compatible test suite.

Run via Forge UI: POST /dev/lab/app.modules.document_center.router/test
Run locally:     python -m pytest app/modules/document_center/tests/ -v

These tests validate module integrity without requiring a live server or DB.
All network/vault calls are intentionally excluded at this stage.
"""
import pytest


def test_dc_module_imports():
    """DC module imports cleanly and exposes router."""
    from app.modules.document_center import router
    assert router is not None, "router must be exported from __init__.py"


def test_dc_router_is_fastapi_router():
    """DC router is an APIRouter instance."""
    from fastapi import APIRouter
    from app.modules.document_center.router import router
    assert isinstance(router, APIRouter), "router must be a FastAPI APIRouter"


def test_dc_router_prefix():
    """DC router routes are mounted at /api/dc via product_manifest prefix."""
    from app.modules.document_center.router import router
    # Prefix is applied by product_manifest at registration time, not on router itself
    # Verify routes have relative paths (no leading /api/dc)
    paths = [r.path for r in router.routes]
    assert all(not p.startswith("/api/dc") for p in paths), \
        f"Routes should not have /api/dc prefix (manifest adds it): {paths}"
    assert "/list" in paths, f"Expected /list route, found: {paths}"


def test_dc_router_has_list_endpoint():
    """DC router exposes GET /list (manifest adds /api/dc prefix)."""
    from app.modules.document_center.router import router
    paths = [r.path for r in router.routes]
    assert "/list" in paths, f"Missing /list. Found: {paths}"


def test_dc_router_has_set_type_endpoint():
    """DC router exposes POST /api/dc/document/{vault_id}/type."""
    from app.modules.document_center.router import router
    paths = [r.path for r in router.routes]
    assert any(p.endswith("/type") for p in paths), \
        f"Missing set_type endpoint in: {paths}"


def test_dc_allowed_types_non_empty():
    """ALLOWED_DOCUMENT_TYPES is defined and contains expected values."""
    from app.modules.document_center.router import ALLOWED_DOCUMENT_TYPES
    assert isinstance(ALLOWED_DOCUMENT_TYPES, frozenset)
    assert len(ALLOWED_DOCUMENT_TYPES) >= 5
    assert "lease" in ALLOWED_DOCUMENT_TYPES
    assert "notice_to_vacate" in ALLOWED_DOCUMENT_TYPES
    assert "court_summons" in ALLOWED_DOCUMENT_TYPES


def test_dc_contracts_registered():
    """DC FunctionGroupContracts are registered after importing register module."""
    import app.modules.document_center.register  # noqa: F401 — triggers registration
    from app.core.module_contracts import contract_registry
    dc_list = contract_registry.get("document_center", "dc_list")
    dc_set  = contract_registry.get("document_center", "dc_set_type")
    assert dc_list is not None, "dc_list contract must be registered"
    assert dc_set  is not None, "dc_set_type contract must be registered"


def test_dc_list_contract_outputs():
    """dc_list contract declares expected outputs."""
    import app.modules.document_center.register  # noqa: F401
    from app.core.module_contracts import contract_registry
    contract = contract_registry.get("document_center", "dc_list")
    assert "documents" in contract.outputs
    assert "total" in contract.outputs


def test_dc_router_has_overlays_endpoint():
    """DC router exposes GET /api/dc/document/{vault_id}/overlays."""
    from app.modules.document_center.router import router
    paths = [r.path for r in router.routes]
    assert any("{vault_id}" in p and p.endswith("/overlays") for p in paths), \
        f"Missing overlays endpoint in: {paths}"


def test_dc_overlays_contract_registered():
    """dc_overlays contract is registered with correct I/O."""
    import app.modules.document_center.register  # noqa: F401
    from app.core.module_contracts import contract_registry
    contract = contract_registry.get("document_center", "dc_overlays")
    assert contract is not None, "dc_overlays contract must be registered"
    assert "vault_id" in contract.inputs
    assert "overlays" in contract.outputs
    assert "overall_pct" in contract.outputs


def test_dc_build_overlay_progress_no_real_overlays():
    """_build_overlay_progress returns processing_incomplete when no real overlays."""
    from app.modules.document_center.router import _build_overlay_progress
    from unittest.mock import MagicMock

    doc = MagicMock()
    doc.vault_id = "test-vault-id"
    doc.registry_id = None
    doc.document_type = None
    doc.processed = False
    doc.integrity_status = "unverified"

    result = _build_overlay_progress(doc, real_overlays=None)
    assert result["status"] == "processing_incomplete"
    assert result["has_data"] is False
    assert result["overlays"] == []
    assert result["overlay_count"] == 0
    assert result["overlay_source"] == "none"


def test_dc_build_overlay_progress_empty_real_overlays():
    """_build_overlay_progress returns processing_incomplete when real_overlays is empty list."""
    from app.modules.document_center.router import _build_overlay_progress
    from unittest.mock import MagicMock

    doc = MagicMock()
    doc.vault_id = "test-vault-id"
    doc.registry_id = "SEM-2026-000001-ABCD"
    doc.document_type = "lease"
    doc.processed = True
    doc.integrity_status = "verified"

    result = _build_overlay_progress(doc, real_overlays=[])
    assert result["status"] == "processing_incomplete"
    assert result["has_data"] is False


def test_dc_router_has_view_endpoint():
    """DC router exposes GET /api/dc/document/{vault_id}/view."""
    from app.modules.document_center.router import router
    paths = [r.path for r in router.routes]
    assert any("{vault_id}" in p and p.endswith("/view") for p in paths), \
        f"Missing view endpoint in: {paths}"


def test_dc_view_contract_registered():
    """dc_view contract is registered."""
    import app.modules.document_center.register  # noqa: F401
    from app.core.module_contracts import contract_registry
    contract = contract_registry.get("document_center", "dc_view")
    assert contract is not None, "dc_view contract must be registered"
    assert "vault_id" in contract.inputs
    assert "file_bytes" in contract.outputs


def test_dc_set_type_contract_inputs():
    """dc_set_type contract declares required inputs."""
    import app.modules.document_center.register  # noqa: F401
    from app.core.module_contracts import contract_registry
    contract = contract_registry.get("document_center", "dc_set_type")
    assert "doc_id" in contract.inputs
    assert "document_type" in contract.inputs
    assert "user_id" in contract.inputs


def test_dc_set_type_route_uses_vault_id_param():
    """POST /document/{vault_id}/type route uses vault_id path param."""
    from app.modules.document_center.router import router
    for route in router.routes:
        if route.path.endswith("/type") and route.methods and "POST" in route.methods:
            import inspect
            sig = inspect.signature(route.endpoint)
            assert "vault_id" in sig.parameters, \
                f"Expected vault_id param, got: {list(sig.parameters)}"
            return
    raise AssertionError("POST /type route not found")


def test_dc_allowed_types_excludes_generic():
    """ALLOWED_DOCUMENT_TYPES does not accept the generic 'document' catch-all."""
    from app.modules.document_center.router import ALLOWED_DOCUMENT_TYPES
    assert "document" not in ALLOWED_DOCUMENT_TYPES


def test_dc_router_has_unlocks_endpoint():
    """DC router exposes GET /unlocks (manifest adds /api/dc prefix)."""
    from app.modules.document_center.router import router
    paths = [r.path for r in router.routes]
    assert "/unlocks" in paths, f"Missing /unlocks. Found: {paths}"


def test_dc_unlocks_contract_registered():
    """dc_unlocks contract is registered with correct I/O."""
    import app.modules.document_center.register  # noqa: F401
    from app.core.module_contracts import contract_registry
    contract = contract_registry.get("document_center", "dc_unlocks")
    assert contract is not None, "dc_unlocks contract missing"
    assert "user_id" in contract.inputs
    assert "unlocks" in contract.outputs
    assert "doc_count" in contract.outputs


def test_dc_compute_unlocks_empty():
    """_compute_unlocks with no docs returns all locked."""
    from app.modules.document_center.router import _compute_unlocks
    result = _compute_unlocks([])
    assert len(result) == 4
    assert all(not r["unlocked"] for r in result)
    assert all("0/" in r["progress"] for r in result)


def test_dc_compute_unlocks_fully_processed():
    """_compute_unlocks unlocks all features for certified, typed, processed docs."""
    from app.modules.document_center.router import _compute_unlocks
    from unittest.mock import MagicMock

    def make_doc(**kwargs):
        doc = MagicMock()
        doc.registry_id = "SEM-2026-000001-ABCD"
        doc.document_type = "lease"
        doc.processed = True
        for k, v in kwargs.items():
            setattr(doc, k, v)
        return doc

    # 3 fully-processed docs should unlock all features
    docs = [make_doc() for _ in range(3)]
    result = _compute_unlocks(docs)
    by_name = {r["name"]: r for r in result}

    assert by_name["Timeline"]["unlocked"] is True
    assert by_name["Journal"]["unlocked"] is True
    assert by_name["Case Builder"]["unlocked"] is True


def test_dc_compute_unlocks_partial():
    """_compute_unlocks correctly reports partial progress."""
    from app.modules.document_center.router import _compute_unlocks
    from unittest.mock import MagicMock

    doc = MagicMock()
    doc.registry_id = None
    doc.document_type = "lease"
    doc.processed = True

    result = _compute_unlocks([doc])
    by_name = {r["name"]: r for r in result}

    # Journal needs 2 docs; we have 1 — locked
    assert by_name["Journal"]["unlocked"] is False
    assert "1/2" in by_name["Journal"]["progress"]

    # Timeline needs 1 typed doc — unlocked
    assert by_name["Timeline"]["unlocked"] is True
