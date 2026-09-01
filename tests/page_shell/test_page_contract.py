"""Tests for PageContract and its conversion to PageConfig.

Pressure-test the PageContract Pydantic model against four real page shapes
(RECORD, KNOW, ACT, GOVERN). All four contracts should validate cleanly and
convert to ``PageConfig`` without raising ``PageConfigResistanceError``.
"""

from __future__ import annotations

from app.modules.page_shell.models import PageConfig
from app.modules.page_shell.page_contract import (
    PageContract,
    PageContractErrorRoute,
    PageContractInput,
    page_contract_registry,
)

# Importing sample_contracts populates page_contract_registry with the four samples.
import app.modules.page_shell.sample_contracts  # noqa: F401


def _get_contract(page_id: str) -> PageContract:
    contract = page_contract_registry.get(page_id)
    assert contract is not None, f"Sample contract {page_id} not found"
    return contract


class TestPageContractRegistry:
    def test_registry_has_four_samples(self) -> None:
        contracts = page_contract_registry.list()
        page_ids = {c.page_id for c in contracts}
        expected = {
            "journal_create",
            "law_library_get_statute",
            "eviction_defense_calculate_deadlines",
            "high_stakes_review",
        }
        assert page_ids == expected, f"Expected {expected}, got {page_ids}"


class TestPageContractFields:
    def test_error_route_is_non_optional(self) -> None:
        contract = _get_contract("journal_create")
        assert contract.error_route is not None
        assert contract.error_route.route_to in {
            "help",
            "legal_aid",
            "home",
            "error_page",
        }

    def test_full_field_set_present(self) -> None:
        contract = _get_contract("eviction_defense_calculate_deadlines")
        assert contract.pillar == "act"
        assert contract.roles == ["tenant"]
        assert contract.inputs
        assert contract.special_needs
        assert contract.narrative_ref
        assert contract.preview_state
        assert contract.export_type
        assert contract.exit_transition
        assert contract.error_route
        assert contract.mobile_constraints
        assert contract.risk_tier == "medium_high"

    def test_govern_contract_carries_page_config(self) -> None:
        contract = _get_contract("high_stakes_review")
        assert contract.page_config is not None
        assert contract.page_config.major_pillar == "govern"
        assert contract.page_config.audit_hook.log_on_render is True

    def test_text_only_contract_converts_cleanly(self) -> None:
        """A contract with only text/date inputs should map to a valid PageConfig."""
        contract = PageContract(
            page_id="text_only_demo",
            page_title="Text-only demo",
            pillar="record",
            inputs=[
                PageContractInput(
                    name="note",
                    input_type="text",
                    label="Note",
                    required=True,
                ),
            ],
            error_route=PageContractErrorRoute(
                route_to="help", fallback_path="/help"
            ),
        )
        config = contract.to_page_config()
        assert isinstance(config, PageConfig)
        assert config.major_pillar == "record"
        assert config.zones is not None
        assert "record" in config.zones
        assert len(config.zones["record"].blocks) == 1
        assert config.zones["govern"].blocks


class TestPageContractToPageConfig:
    def test_govern_page_config_round_trips(self) -> None:
        contract = _get_contract("high_stakes_review")
        config = contract.to_page_config()
        assert config.page_id == "draft_answer_review"
        assert config.major_pillar == "govern"
        assert config.zones is not None
        govern_zone = config.zones["govern"]
        assert any(
            b.block_id == "blk_upl_banner" for b in govern_zone.blocks
        ), "UPL banner should be in GOVERN zone"

    def test_record_select_converts_cleanly(self) -> None:
        contract = _get_contract("journal_create")
        config = contract.to_page_config()
        assert isinstance(config, PageConfig)
        assert config.major_pillar == "record"
        record_zone = config.zones["record"]
        entry_type = next(
            (b for b in record_zone.blocks if b.block_id == "input_0_entry_type"), None
        )
        assert entry_type is not None
        assert entry_type.input_type == "select"
        assert entry_type.options
        assert entry_type.options[0].value == "note"

    def test_know_select_converts_cleanly(self) -> None:
        contract = _get_contract("law_library_get_statute")
        config = contract.to_page_config()
        assert isinstance(config, PageConfig)
        assert config.major_pillar == "know"
        know_zone = config.zones["know"]
        statute_input = next(
            (b for b in know_zone.blocks if b.block_id == "input_0_statute_id"), None
        )
        assert statute_input is not None
        assert statute_input.input_type == "select"
        assert statute_input.options[0].disabled is True

    def test_act_select_converts_cleanly(self) -> None:
        contract = _get_contract("eviction_defense_calculate_deadlines")
        config = contract.to_page_config()
        assert isinstance(config, PageConfig)
        assert config.major_pillar == "act"
        act_zone = config.zones["act"]
        case_type = next(
            (b for b in act_zone.blocks if b.block_id == "input_1_case_type"), None
        )
        assert case_type is not None
        assert case_type.input_type == "select"
        assert any(opt.selected for opt in case_type.options)
