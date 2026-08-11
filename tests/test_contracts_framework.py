"""Tests for app.core.contracts_framework."""

import pytest

from app.core.contracts_framework import (
    ConsentLevel,
    ContractStatus,
    ContractType,
    ContractsFramework,
)


def test_default_contracts_loaded():
    """Framework loads the default set of contracts."""
    framework = ContractsFramework()
    assert "terms_2024_v1" in framework.contracts
    assert "privacy_2024_v1" in framework.contracts
    assert framework.contracts["terms_2024_v1"].status == ContractStatus.ACTIVE


def test_get_contract_found():
    """get_contract returns a contract for an existing ID."""
    framework = ContractsFramework()
    contract = framework.get_contract("terms_2024_v1")
    assert contract is not None
    assert contract.contract_id == "terms_2024_v1"


def test_get_contract_missing():
    """get_contract returns None for an unknown ID."""
    framework = ContractsFramework()
    assert framework.get_contract("missing") is None


def test_get_contracts_by_type():
    """get_contracts_by_type returns only active contracts of that type."""
    framework = ContractsFramework()
    terms = framework.get_contracts_by_type(ContractType.TERMS_OF_SERVICE)
    assert len(terms) >= 1
    assert all(c.contract_type == ContractType.TERMS_OF_SERVICE for c in terms)
    assert all(c.status == ContractStatus.ACTIVE for c in terms)


def test_record_and_check_consent():
    """record_consent stores a consent and check_consent retrieves it."""
    framework = ContractsFramework()
    consent_id = framework.record_consent(
        user_id="user_1",
        contract_id="terms_2024_v1",
        consent_level=ConsentLevel.EXPRESS,
    )
    assert consent_id

    consent = framework.check_consent("user_1", "terms_2024_v1")
    assert consent is not None
    assert consent.user_id == "user_1"
    assert consent.contract_id == "terms_2024_v1"
    assert consent.withdrawn_at is None


def test_record_consent_missing_contract():
    """record_consent raises ValueError for an unknown contract."""
    framework = ContractsFramework()
    with pytest.raises(ValueError):
        framework.record_consent(
            user_id="user_1",
            contract_id="missing",
            consent_level=ConsentLevel.EXPRESS,
        )


def test_check_consent_missing_user():
    """check_consent returns None for a user with no consents."""
    framework = ContractsFramework()
    assert framework.check_consent("no_one", "terms_2024_v1") is None


def test_withdraw_consent():
    """withdraw_consent marks a consent as withdrawn."""
    framework = ContractsFramework()
    framework.record_consent(
        user_id="user_1",
        contract_id="terms_2024_v1",
        consent_level=ConsentLevel.EXPRESS,
    )
    assert framework.withdraw_consent("user_1", "terms_2024_v1") is True
    assert framework.check_consent("user_1", "terms_2024_v1") is None


def test_withdraw_consent_missing_user():
    """withdraw_consent returns False for a user with no consents."""
    framework = ContractsFramework()
    assert framework.withdraw_consent("no_one", "terms_2024_v1") is False


def test_get_required_contracts():
    """get_required_contracts returns contracts the user has not consented to."""
    framework = ContractsFramework()
    required = framework.get_required_contracts("user_1")
    assert all(c.status == ContractStatus.ACTIVE for c in required)

    framework.record_consent(
        user_id="user_1",
        contract_id="terms_2024_v1",
        consent_level=ConsentLevel.EXPRESS,
    )
    required_after = framework.get_required_contracts("user_1")
    assert "terms_2024_v1" not in {c.contract_id for c in required_after}


def test_get_user_consents():
    """get_user_consents returns all consents for a user."""
    framework = ContractsFramework()
    framework.record_consent(
        user_id="user_2",
        contract_id="terms_2024_v1",
        consent_level=ConsentLevel.EXPRESS,
    )
    framework.record_consent(
        user_id="user_2",
        contract_id="privacy_2024_v1",
        consent_level=ConsentLevel.EXPRESS,
    )
    consents = framework.get_user_consents("user_2")
    assert len(consents) == 2


def test_default_content_methods_return_strings():
    """Private _get_*_content helpers return non-empty strings."""
    framework = ContractsFramework()
    for method_name in (
        "_get_terms_of_service_content",
        "_get_privacy_policy_content",
        "_get_ai_consent_content",
        "_get_data_processing_content",
        "_get_mobile_app_content",
        "_get_plugin_dev_content",
    ):
        content = getattr(framework, method_name)()
        assert isinstance(content, str)
        assert len(content) > 0
