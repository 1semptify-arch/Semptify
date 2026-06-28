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
    """DC router is mounted at /api/dc."""
    from app.modules.document_center.router import router
    assert router.prefix == "/api/dc", f"Expected prefix /api/dc, got {router.prefix}"


def test_dc_router_has_list_endpoint():
    """DC router exposes GET /api/dc/list."""
    from app.modules.document_center.router import router
    paths = [r.path for r in router.routes]
    assert "/api/dc/list" in paths, f"Missing /api/dc/list. Found: {paths}"


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


def test_dc_synthesize_overlays_unprocessed():
    """_synthesize_overlays returns 6 items for an unprocessed doc, all at 0%."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock

    doc = MagicMock()
    doc.registry_id = None
    doc.document_type = None
    doc.processed = False
    doc.extracted_data = None
    doc.integrity_status = "unverified"

    result = _synthesize_overlays(doc)
    assert result["has_data"] is False
    assert len(result["overlays"]) == 6
    assert all(ov["pct"] == 0 for ov in result["overlays"])
    assert result["overall_pct"] == 0


def test_dc_synthesize_overlays_processed():
    """_synthesize_overlays returns elevated pcts for a processed doc with data."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock

    doc = MagicMock()
    doc.registry_id = "SEM-2026-000001-ABCD"
    doc.document_type = "lease"
    doc.processed = True
    doc.extracted_data = {
        "text": "This is a lease agreement.",
        "dates": ["2026-01-01", "2027-01-01"],
        "parties": ["Jane Tenant", "Bob Landlord"],
        "amounts": ["$1,200/month"],
    }
    doc.integrity_status = "verified"

    result = _synthesize_overlays(doc)
    assert result["has_data"] is True
    assert result["overall_pct"] > 0
    certified = next(o for o in result["overlays"] if o["overlay_type"] == "upload_notarization")
    assert certified["pct"] == 100
    parties = next(o for o in result["overlays"] if o["overlay_type"] == "party_extraction")
    assert parties["pct"] == 100


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


def test_dc_synthesize_overlays_cleared_type():
    """_synthesize_overlays shows 0% for Document Type when type is None."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock

    doc = MagicMock()
    doc.registry_id = "SEM-2026-000001-ABCD"
    doc.document_type = None
    doc.processed = False
    doc.extracted_data = None
    doc.integrity_status = "verified"

    result = _synthesize_overlays(doc)
    type_item = next(o for o in result["overlays"] if o["overlay_type"] == "document_classification")
    assert type_item["pct"] == 0
    certified_item = next(o for o in result["overlays"] if o["overlay_type"] == "upload_notarization")
    assert certified_item["pct"] == 100


def test_dc_synthesize_overlays_has_items_field():
    """Every overlay in _synthesize_overlays output has an 'items' list."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock

    doc = MagicMock()
    doc.registry_id = "SEM-2026-000001-ABCD"
    doc.document_type = "lease"
    doc.processed = True
    doc.extracted_data = {
        "dates": ["2026-01-01"],
        "parties": ["Tenant", "Landlord"],
        "amounts": ["$1,200"],
        "text": "Sample text content here",
    }
    doc.integrity_status = "verified"

    result = _synthesize_overlays(doc)
    for ov in result["overlays"]:
        assert "items" in ov, f"overlay '{ov['overlay_type']}' missing 'items'"
        assert isinstance(ov["items"], list), f"'items' must be list on '{ov['overlay_type']}'"


def test_dc_synthesize_overlays_items_populated():
    """items field contains the extracted values for each overlay type."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock

    doc = MagicMock()
    doc.registry_id = "SEM-2026-000001-ABCD"
    doc.document_type = "lease"
    doc.processed = True
    doc.extracted_data = {
        "dates": ["2026-01-01", "2026-12-31"],
        "parties": ["Alice", "Bob"],
        "amounts": ["$1,200"],
        "text": "Lease agreement.",
    }
    doc.integrity_status = "verified"

    result = _synthesize_overlays(doc)
    by_type = {o["overlay_type"]: o for o in result["overlays"]}

    assert "SEM-2026-000001-ABCD" in by_type["upload_notarization"]["items"]
    assert "Lease" in by_type["document_classification"]["items"][0]
    assert len(by_type["key_date_extraction"]["items"]) == 2
    assert "Alice" in by_type["party_extraction"]["items"]
    assert "$1,200" in by_type["amount_extraction"]["items"]


def test_dc_synthesize_overlays_items_empty_when_no_data():
    """items is empty list when no data extracted yet."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock

    doc = MagicMock()
    doc.registry_id = None
    doc.document_type = None
    doc.processed = False
    doc.extracted_data = {}
    doc.integrity_status = None

    result = _synthesize_overlays(doc)
    for ov in result["overlays"]:
        assert ov["items"] == [], f"Expected empty items on '{ov['overlay_type']}', got {ov['items']}"


def test_dc_synthesize_overlays_ocr_excerpt_capped():
    """OCR text excerpt is capped at 200 chars + ellipsis."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock
    doc = MagicMock()
    doc.registry_id = None
    doc.document_type = None
    doc.processed = True
    doc.extracted_data = {"text": "A" * 500}
    doc.integrity_status = None
    result = _synthesize_overlays(doc)
    ocr = next(o for o in result["overlays"] if o["overlay_type"] == "ocr_result")
    assert len(ocr["items"][0]) <= 204
    assert ocr["items"][0].endswith("…")


def test_dc_synthesize_overlays_items_capped_at_10():
    """items lists are capped at 10 entries."""
    from app.modules.document_center.router import _synthesize_overlays
    from unittest.mock import MagicMock
    doc = MagicMock()
    doc.registry_id = None
    doc.document_type = None
    doc.processed = True
    doc.extracted_data = {
        "dates": [f"2026-01-{i:02d}" for i in range(1, 20)],
        "parties": [f"Party {i}" for i in range(15)],
        "amounts": [],
    }
    doc.integrity_status = None
    result = _synthesize_overlays(doc)
    by_type = {o["overlay_type"]: o for o in result["overlays"]}
    assert len(by_type["key_date_extraction"]["items"]) <= 10
    assert len(by_type["party_extraction"]["items"]) <= 10


def test_dc_router_has_unlocks_endpoint():
    """DC router exposes GET /api/dc/unlocks."""
    from app.modules.document_center.router import router
    paths = [r.path for r in router.routes]
    assert "/api/dc/unlocks" in paths, f"Missing /api/dc/unlocks. Found: {paths}"


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
    """_compute_unlocks unlocks all features for a fully extracted document."""
    from app.modules.document_center.router import _compute_unlocks
    from unittest.mock import MagicMock

    def make_doc(**kwargs):
        doc = MagicMock()
        doc.registry_id = "SEM-2026-000001-ABCD"
        doc.document_type = "lease"
        doc.processed = True
        doc.extracted_data = {
            "text": "x" * 500,
            "dates": ["2026-01-01", "2026-06-01", "2026-12-31"],
            "parties": ["Tenant A", "Landlord B"],
            "amounts": ["$1,200/mo"],
        }
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
    doc.extracted_data = {
        "text": "x" * 100,
        "dates": ["2026-01-01"],
        "parties": [],
        "amounts": [],
    }

    result = _compute_unlocks([doc])
    by_name = {r["name"]: r for r in result}

    # Journal needs 2 docs >= 60%; we have 1 — locked
    assert by_name["Journal"]["unlocked"] is False
    assert "0/2" in by_name["Journal"]["progress"]

    # Timeline: dates pct ~33%, parties 0% → avg ~16% < 80 — locked
    assert by_name["Timeline"]["unlocked"] is False
