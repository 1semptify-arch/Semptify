"""Packet Builder smoke tests."""

import pytest
from fastapi import APIRouter
from pydantic import ValidationError

from app.modules.packet_builder import router
from app.modules.packet_builder.router import (
    BuildPacketRequest,
    router as packet_router,
)


def test_module_imports():
    """Module exports a router."""
    assert router is not None


def test_router_is_fastapi_router():
    """Router is a FastAPI APIRouter."""
    assert isinstance(packet_router, APIRouter)


def test_router_prefix():
    """Router is mounted under /api/packet-builder."""
    assert packet_router.prefix == "/api/packet-builder"


def test_routes_exist():
    """Required routes are registered on the router."""
    paths = [route.path for route in packet_router.routes]
    assert any(p.endswith("/build") for p in paths), f"Missing /build in {paths}"
    assert any(p.endswith("/packets/{packet_id}") for p in paths), f"Missing /packets/{{packet_id}} in {paths}"
    assert any(p.endswith("/packets/{packet_id}/download") for p in paths), (
        f"Missing /packets/{{packet_id}}/download in {paths}"
    )


def test_build_request_validates_empty_sources():
    """BuildPacketRequest rejects empty vault_ids with no case_id or folder_id."""
    with pytest.raises(ValidationError):
        BuildPacketRequest(vault_ids=[], mode="overlay")


def test_build_request_accepts_case_id():
    """BuildPacketRequest accepts a case_id without vault_ids."""
    request = BuildPacketRequest(case_id="123", mode="overlay")
    assert request.case_id == "123"
    assert request.vault_ids == []


def test_build_request_rejects_invalid_mode():
    """BuildPacketRequest rejects unknown modes."""
    with pytest.raises(ValidationError):
        BuildPacketRequest(vault_ids=["doc_1"], mode="invalid")


def test_contracts_registered():
    """Packet builder FunctionGroupContracts are registered."""
    import app.modules.packet_builder.register  # noqa: F401
    from app.core.module_contracts import contract_registry

    assert contract_registry.get("packet_builder", "packet_builder_build") is not None
    assert contract_registry.get("packet_builder", "packet_builder_get") is not None
    assert contract_registry.get("packet_builder", "packet_builder_download") is not None
