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
    from unittest.mock import MagicMock

    from app.modules.rent.router import _compute_running_balances

    e1 = MagicMock()
    e1.id = "rnt_001"
    e1.entry_type = "payment"
    e1.amount = 1000
    e2 = MagicMock()
    e2.id = "rnt_002"
    e2.entry_type = "fee"
    e2.amount = 200
    result = _compute_running_balances([e1, e2])
    assert result["rnt_001"] == 1000
    assert result["rnt_002"] == 800


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
