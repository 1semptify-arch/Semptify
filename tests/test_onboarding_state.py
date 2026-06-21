"""Tests for app.core.onboarding_state — Gate status dataclass & helpers."""

import pytest

from app.core.onboarding_state import (
    OnboardingState,
    get_onboarding_state_no_db,
)


# ---------------------------------------------------------------------------
# OnboardingState dataclass properties
# ---------------------------------------------------------------------------
class TestOnboardingState:
    def test_fully_onboarded(self):
        state = OnboardingState(
            user_id="u1",
            storage_connected=True,
            vault_initialized=True,
        )
        assert state.is_fully_onboarded is True
        assert state.next_required_gate is None

    def test_no_gates_complete(self):
        state = OnboardingState(
            user_id="u1",
            storage_connected=False,
            vault_initialized=False,
        )
        assert state.is_fully_onboarded is False
        assert state.next_required_gate == "storage_connected"

    def test_storage_done_vault_pending(self):
        state = OnboardingState(
            user_id="u1",
            storage_connected=True,
            vault_initialized=False,
        )
        assert state.is_fully_onboarded is False
        assert state.next_required_gate == "vault_initialized"

    def test_vault_done_storage_pending(self):
        state = OnboardingState(
            user_id="u1",
            storage_connected=False,
            vault_initialized=True,
        )
        assert state.is_fully_onboarded is False
        assert state.next_required_gate == "storage_connected"

    def test_frozen(self):
        state = OnboardingState(user_id="u1", storage_connected=True, vault_initialized=True)
        with pytest.raises(AttributeError):
            state.storage_connected = False  # type: ignore[misc]

    def test_next_required_path_none_when_fully_onboarded(self):
        state = OnboardingState(user_id="u1", storage_connected=True, vault_initialized=True)
        assert state.next_required_path is None

    def test_next_required_path_storage_fallback(self):
        state = OnboardingState(user_id="u1", storage_connected=False, vault_initialized=False)
        path = state.next_required_path
        assert path is not None
        assert isinstance(path, str)

    def test_next_required_path_vault_fallback(self):
        state = OnboardingState(user_id="u1", storage_connected=True, vault_initialized=False)
        path = state.next_required_path
        assert path is not None
        assert isinstance(path, str)


# ---------------------------------------------------------------------------
# get_onboarding_state_no_db
# ---------------------------------------------------------------------------
class TestGetOnboardingStateNoDb:
    @pytest.mark.asyncio
    async def test_none_input(self):
        state = await get_onboarding_state_no_db(None, "u1")
        assert state.user_id == "u1"
        assert state.storage_connected is False
        assert state.vault_initialized is False

    @pytest.mark.asyncio
    async def test_empty_string(self):
        state = await get_onboarding_state_no_db("", "u1")
        assert state.storage_connected is False
        assert state.vault_initialized is False

    @pytest.mark.asyncio
    async def test_storage_connected_only(self):
        state = await get_onboarding_state_no_db("storage_connected", "u1")
        assert state.storage_connected is True
        assert state.vault_initialized is False

    @pytest.mark.asyncio
    async def test_both_gates(self):
        state = await get_onboarding_state_no_db("storage_connected,vault_initialized", "u1")
        assert state.storage_connected is True
        assert state.vault_initialized is True

    @pytest.mark.asyncio
    async def test_whitespace_handling(self):
        state = await get_onboarding_state_no_db(" storage_connected , vault_initialized ", "u1")
        assert state.storage_connected is True
        assert state.vault_initialized is True

    @pytest.mark.asyncio
    async def test_extra_gates_ignored(self):
        state = await get_onboarding_state_no_db("storage_connected,vault_initialized,extra_gate", "u1")
        assert state.storage_connected is True
        assert state.vault_initialized is True

    @pytest.mark.asyncio
    async def test_vault_only(self):
        state = await get_onboarding_state_no_db("vault_initialized", "u1")
        assert state.storage_connected is False
        assert state.vault_initialized is True
