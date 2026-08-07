"""Journal module smoke tests.

Run via Forge UI: POST /dev/lab/app.modules.journal.router/test
Run locally:     python -m pytest app/modules/journal/tests/ -v
"""
from datetime import UTC

import pytest


def test_journal_module_imports():
    """Journal module imports cleanly and exposes router."""
    from app.modules.journal import router
    assert router is not None


def test_journal_router_is_fastapi_router():
    """Journal router is an APIRouter instance."""
    from fastapi import APIRouter

    from app.modules.journal.router import router
    assert isinstance(router, APIRouter)


def test_journal_router_has_list_endpoint():
    """Journal router exposes GET / (manifest adds /api/journal prefix)."""
    from app.modules.journal.router import router
    paths = [r.path for r in router.routes]
    assert "/" in paths, f"Missing list route: {paths}"


def test_journal_router_has_create_endpoint():
    """Journal router exposes POST / (manifest adds /api/journal prefix)."""
    from app.modules.journal.router import router
    methods_by_path = {}
    for r in router.routes:
        for m in r.methods:
            methods_by_path.setdefault(r.path, set()).add(m)
    assert "/" in methods_by_path and "POST" in methods_by_path["/"], f"Missing POST /: {methods_by_path}"


def test_journal_router_has_get_endpoint():
    """Journal router exposes GET /{entry_id}."""
    from app.modules.journal.router import router
    paths = [r.path for r in router.routes]
    assert "/{entry_id}" in paths, f"Missing get route: {paths}"


def test_journal_contracts_registered():
    """Journal module contracts are registered."""
    import app.modules.journal.register  # noqa: F401
    from app.core.module_contracts import contract_registry

    for name in (
        "journal_create",
        "journal_list",
        "journal_get",
        "journal_update",
        "journal_delete",
        "journal_summary",
    ):
        contract = contract_registry.get("journal", name)
        assert contract is not None, f"Missing contract journal::{name}"


def test_journal_create_request_validation():
    """JournalEntryCreate requires a non-empty title."""
    from app.modules.journal.router import JournalEntryCreate
    with pytest.raises(ValueError):
        JournalEntryCreate(entry_type="note", title="")  # min_length=1


def test_journal_to_response_handles_document_link():
    """_to_response returns document_link when present."""
    from datetime import datetime
    from unittest.mock import MagicMock

    from app.modules.journal.router import _to_response

    entry = MagicMock()
    entry.id = "jrn_abc123"
    entry.entry_type = "conversation"
    entry.title = "Called landlord"
    entry.content = "Landlord said repairs next week."
    entry.occurred_at = datetime(2026, 7, 19, 12, 0, 0, tzinfo=UTC)
    entry.is_urgent = True
    entry.involved_party = "landlord"
    entry.tags = "repair,landlord"
    entry.document_link = "doc_xyz789"
    entry.source = "manual"
    entry.created_at = datetime(2026, 7, 19, 12, 0, 0, tzinfo=UTC)
    entry.updated_at = datetime(2026, 7, 19, 12, 0, 0, tzinfo=UTC)

    result = _to_response(entry)
    assert result.id == "jrn_abc123"
    assert result.document_link == "doc_xyz789"
    assert result.is_urgent is True
    assert result.tags == ["repair", "landlord"]
