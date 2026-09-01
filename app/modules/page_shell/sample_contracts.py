"""Sample PageContract instances for pressure-testing the Page Shell contract
system against four real page shapes: RECORD, KNOW, ACT, and GOVERN.

These are loaded into ``page_contract_registry`` at import time only when
this module is explicitly imported (e.g. by tests or by a future page loader).
They are not auto-loaded at application startup.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.page_shell.models import PageConfig
from app.modules.page_shell.page_contract import (
    PageContract,
    PageContractErrorRoute,
    PageContractExit,
    PageContractExport,
    PageContractInput,
    PageContractMobileConstraints,
    PageContractPreview,
    PageContractReview,
    page_contract_registry,
)


def _govern_focus_config() -> PageConfig:
    """Load the existing GOVERN focus demo PageConfig as a pressure-test fixture."""
    sample_path = Path(__file__).parent / "sample_configs" / "govern_focus_demo.json"
    with open(sample_path, encoding="utf-8") as f:
        raw = json.load(f)
    return PageConfig.model_validate(raw)


# ---------------------------------------------------------------------------
# RECORD — journal_create
# ---------------------------------------------------------------------------

register_contract = page_contract_registry.register

register_contract(
    PageContract(
        page_id="journal_create",
        page_title="Create a journal entry",
        display_title="Add the entry",
        pillar="record",
        roles=["tenant"],
        subject="journal",
        jurisdiction="MN",
        inputs=[
            PageContractInput(
                name="entry_type",
                input_type="select",
                label="Type",
                required=True,
                options=["note", "conversation", "incident", "repair_request", "other"],
                writes_to="journal.entry_type",
            ),
            PageContractInput(
                name="title",
                input_type="text",
                label="Title",
                required=True,
                max_length=255,
                placeholder="Short name for this entry",
                writes_to="journal.title",
            ),
            PageContractInput(
                name="content",
                input_type="textarea",
                label="What happened",
                required=False,
                placeholder="What did the landlord say or do?",
                writes_to="journal.content",
            ),
            PageContractInput(
                name="occurred_at",
                input_type="datetime-local",
                label="When it happened",
                required=False,
                writes_to="journal.occurred_at",
            ),
            PageContractInput(
                name="involved_party",
                input_type="text",
                label="Who was involved",
                required=False,
                max_length=255,
                placeholder="Landlord, manager, neighbor…",
                writes_to="journal.involved_party",
            ),
            PageContractInput(
                name="tags",
                input_type="text",
                label="Tags",
                required=False,
                placeholder="repair, notice, conversation (comma-separated)",
                writes_to="journal.tags",
            ),
            PageContractInput(
                name="document_link",
                input_type="text",
                label="Linked document ID",
                required=False,
                max_length=36,
                placeholder="Optional vault document ID",
                writes_to="journal.document_link",
            ),
            PageContractInput(
                name="is_urgent",
                input_type="checkbox",
                label="Mark as high priority",
                required=False,
                writes_to="journal.is_urgent",
            ),
        ],
        special_needs=["large-touch-targets", "screen-reader-first"],
        narrative_ref="context/journal/what-is-a-journal-entry",
        preview_state=PageContractPreview(
            output_type="summary",
            description="A saved journal entry with entry ID.",
        ),
        review_state=PageContractReview(required=False),
        export_type=PageContractExport(export_type="record", target="journal"),
        exit_transition=PageContractExit(
            action="next_page", next_page_id="tenant_journal"
        ),
        error_route=PageContractErrorRoute(
            route_to="help",
            fallback_path="/help",
            label="Get help with your journal",
        ),
        mobile_constraints=PageContractMobileConstraints(
            min_viewport_width=375,
            wcag_target="AA",
            touch_target_min_px=44,
        ),
    )
)


# ---------------------------------------------------------------------------
# KNOW — law_library_get_statute
# ---------------------------------------------------------------------------

register_contract(
    PageContract(
        page_id="law_library_get_statute",
        page_title="Look up a statute",
        display_title="Look it up",
        pillar="know",
        roles=["tenant"],
        subject="law_library",
        jurisdiction="MN",
        inputs=[
            PageContractInput(
                name="statute_id",
                input_type="select",
                label="Statute",
                required=True,
                options=[
                    "minn_stat_504b",
                    "minn_stat_504b_321",
                    "minn_stat_504b_375",
                    "minn_stat_504b_211",
                    "minn_stat_504b_285",
                ],
                placeholder="Choose a statute",
                writes_to="law_library.statute_id",
            ),
        ],
        special_needs=["plain-language-default"],
        narrative_ref="context/law_library/what-is-a-statute",
        preview_state=PageContractPreview(
            output_type="document",
            description="Full statute text, citation, and related cases.",
        ),
        review_state=PageContractReview(required=False),
        export_type=PageContractExport(export_type="none"),
        exit_transition=PageContractExit(
            action="next_page", next_page_id="law_library"
        ),
        error_route=PageContractErrorRoute(
            route_to="legal_aid",
            fallback_path="/help",
            label="Find legal help",
        ),
    )
)


# ---------------------------------------------------------------------------
# ACT — eviction_defense_calculate_deadlines
# ---------------------------------------------------------------------------

register_contract(
    PageContract(
        page_id="eviction_defense_calculate_deadlines",
        page_title="Calculate your eviction deadlines",
        display_title="Calculate deadlines",
        pillar="act",
        roles=["tenant"],
        subject="eviction_defense",
        jurisdiction="MN",
        inputs=[
            PageContractInput(
                name="start_date",
                input_type="date",
                label="When were you served?",
                required=True,
                placeholder="Use the date on the eviction notice or the date you were served.",
                writes_to="eviction.start_date",
            ),
            PageContractInput(
                name="case_type",
                input_type="select",
                label="Case type",
                required=False,
                options=[
                    "nonpayment",
                    "lease_violation",
                    "holdover",
                    "other",
                ],
                placeholder="This does not change the deadlines, but helps Semptify label your plan.",
                writes_to="eviction.case_type",
            ),
        ],
        special_needs=["high-contrast-warning", "screen-reader-first"],
        narrative_ref="context/eviction/what-is-an-eviction-notice",
        preview_state=PageContractPreview(
            output_type="table",
            description="A table of key deadlines for your response.",
        ),
        review_state=PageContractReview(required=False),
        export_type=PageContractExport(export_type="document", target="document_center"),
        exit_transition=PageContractExit(
            action="next_page", next_page_id="know_law_library_get_statute"
        ),
        error_route=PageContractErrorRoute(
            route_to="legal_aid",
            fallback_path="/help",
            label="Find legal help now",
        ),
        risk_tier="medium_high",
    )
)


# ---------------------------------------------------------------------------
# GOVERN — high_stakes_review
# ---------------------------------------------------------------------------

register_contract(
    PageContract(
        page_id="high_stakes_review",
        page_title="Review before filing",
        display_title="Attorney review required",
        pillar="govern",
        roles=["tenant"],
        subject="eviction_defense",
        jurisdiction="MN",
        inputs=[
            PageContractInput(
                name="case_ref",
                input_type="text",
                label="Case reference",
                required=False,
                writes_to="case.ref",
            ),
        ],
        special_needs=["escalation-banner-first", "large-touch-targets"],
        narrative_ref="context/govern/why-attorney-review-matters",
        preview_state=PageContractPreview(
            output_type="document",
            description="A draft answer or filing packet ready for attorney review.",
        ),
        review_state=PageContractReview(
            required=True,
            confirm_label="I understand this is a draft and must be reviewed",
        ),
        export_type=PageContractExport(export_type="document", target="document_center"),
        exit_transition=PageContractExit(
            action="save_and_exit", next_page_id=None
        ),
        error_route=PageContractErrorRoute(
            route_to="legal_aid",
            fallback_path="/help",
            label="Talk to a qualified attorney before filing",
        ),
        risk_tier="high",
        page_config=_govern_focus_config(),
    )
)
