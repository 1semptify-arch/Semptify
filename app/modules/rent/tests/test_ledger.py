"""Rent ledger smoke tests."""

import pytest


def test_entry_sign_positive():
    from app.modules.rent.router import _entry_sign

    assert _entry_sign("payment") == 1
    assert _entry_sign("deposit") == 1
    assert _entry_sign("credit") == 1


def test_entry_sign_negative():
    from app.modules.rent.router import _entry_sign

    assert _entry_sign("fee") == -1
    assert _entry_sign("charge") == -1


def test_compute_running_balances_empty():
    from app.modules.rent.router import _compute_running_balances

    assert _compute_running_balances([]) == {}


def test_compute_running_balances_order():
    from app.core.overlay_types import OverlayType
    from app.modules.rent.router import _compute_running_balances
    from app.modules.rent.service import get_ledger_anchor_id, get_ledger_vault_path
    from app.models.unified_overlay_models import UnifiedOverlay

    def _entry(overlay_id: str, entry_type: str, amount: int) -> UnifiedOverlay:
        return UnifiedOverlay(
            overlay_id=overlay_id,
            overlay_type=OverlayType.RENT_LEDGER_ENTRY,
            document_id=get_ledger_anchor_id("GUtestuser1"),
            vault_path=get_ledger_vault_path(),
            created_by="GUtestuser1",
            payload={"id": f"rnt_{overlay_id}", "entry_type": entry_type, "amount": amount},
        )

    e1 = _entry("ovl_001", "payment", 1000)
    e2 = _entry("ovl_002", "fee", 200)
    result = _compute_running_balances([e1, e2])
    assert result["ovl_001"] == 1000
    assert result["ovl_002"] == 800


def test_rent_ledger_create_validation():
    from pydantic import ValidationError

    from app.modules.rent.router import RentPaymentCreate

    with pytest.raises(ValidationError):
        RentPaymentCreate(amount=-1, payment_date="2026-07-20")


def test_rent_ledger_contracts_registered():
    import app.modules.rent.register  # noqa: F401
    from app.core.module_contracts import contract_registry

    for name in (
        "rent_ledger_create",
        "rent_ledger_list",
        "rent_ledger_get",
        "rent_ledger_update",
        "rent_ledger_delete",
    ):
        contract = contract_registry.get("rent", name)
        assert contract is not None, f"Missing contract rent::{name}"
