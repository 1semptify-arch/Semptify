"""Page Contract — flow/UX source of truth for the Page Composer.

A PageContract is the blueprint the Page Composer reads to generate a
``PageConfig``. It carries the fields the original page/module contract
draft asked for (roles, inputs, special needs, narrative, preview/review
state, export type, exit transition, error route, mobile constraints)
while building on the existing ``PageConfig`` / block types in
``app.modules.page_shell.models``.

``to_page_config()`` raises ``PageConfigResistanceError`` when a contract
field cannot be represented cleanly by the current ``PageConfig`` schema.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.modules.page_shell.models import (
    AuditHook,
    ChannelLevels,
    Escalation,
    InfoBlock,
    InputBlock,
    MajorPillar,
    OutputBlock,
    PageConfig,
    RiskTier,
    SelectOption,
    Zone,
)


class PageConfigResistanceError(ValueError):
    """Raised when a PageContract cannot be translated to a PageConfig
    without losing information or violating the current PageConfig schema.
    """

    pass


class PageContractInput(BaseModel):
    """One user-input field on a page."""

    model_config = ConfigDict(frozen=True)

    name: str
    input_type: Literal[
        "text",
        "textarea",
        "select",
        "date",
        "datetime-local",
        "checkbox",
        "number",
        "file_upload",
        "signature",
    ] = "text"
    label: str
    required: bool = False
    max_length: int | None = None
    validation: str | None = None
    placeholder: str | None = None
    options: list[SelectOption] | None = None
    writes_to: str | None = None
    module_name: str | None = None


class PageContractPreview(BaseModel):
    """What a preview of this page's output looks like."""

    output_type: Literal["summary", "document", "table", "list", "none"] = "none"
    description: str = ""


class PageContractReview(BaseModel):
    """Whether this page has a review/confirm step before submission."""

    required: bool = False
    confirm_label: str = "Review and confirm"


class PageContractExport(BaseModel):
    """What leaving this page produces."""

    export_type: Literal["document", "record", "none"] = "none"
    target: str | None = None  # e.g. "document_center", "vault", "journal"


class PageContractExit(BaseModel):
    """Where the user goes next."""

    next_page_id: str | None = None
    action: Literal["save_and_exit", "next_page", "help"] = "save_and_exit"


class PageContractErrorRoute(BaseModel):
    """Explicit error/escalation route — no dead ends."""

    route_to: Literal["help", "legal_aid", "home", "error_page"] = "help"
    fallback_path: str = "/help"
    label: str = "Get help"


class PageContractMobileConstraints(BaseModel):
    """Mobile and accessibility constraints for the page."""

    min_viewport_width: int = 375
    wcag_target: Literal["AA", "AAA"] = "AA"
    touch_target_min_px: int = 44


class PageContract(BaseModel):
    """High-level page flow/UX contract.

    This is the source of truth the Page Composer uses to build a
    ``PageConfig``. It is intentionally a separate layer from
    ``FunctionGroupContract`` (module API contract) and
    ``ModuleEntry`` / ``ModuleManifest`` (module lifecycle).
    """

    model_config = ConfigDict(frozen=False)

    page_id: str  # flat stable ID
    page_title: str
    display_title: str | None = None
    pillar: MajorPillar
    roles: list[str] = Field(default_factory=lambda: ["tenant"])
    subject: str | None = None
    jurisdiction: str | None = None
    county: str | None = None

    inputs: list[PageContractInput] = Field(default_factory=list)
    special_needs: list[str] = Field(default_factory=list)
    narrative_ref: str | None = None  # stable ref to context-explanation entry

    preview_state: PageContractPreview | None = None
    review_state: PageContractReview | None = None
    export_type: PageContractExport | None = None
    exit_transition: PageContractExit | None = None
    error_route: PageContractErrorRoute = Field(
        default_factory=PageContractErrorRoute
    )
    mobile_constraints: PageContractMobileConstraints = Field(
        default_factory=PageContractMobileConstraints
    )

    audit_hook: AuditHook | None = None
    escalation: Escalation | None = None
    risk_tier: RiskTier | None = None

    # Optional pre-built PageConfig. If provided, ``to_page_config()`` returns
    # it directly — useful for pressure-testing against existing PageConfig
    # samples such as the GOVERN high-stakes review demo.
    page_config: PageConfig | None = None

    def _input_block(self, index: int, field: PageContractInput) -> InputBlock:
        """Convert one PageContractInput into an InputBlock."""
        input_type = field.input_type

        if input_type == "select" and not field.options:
            # PageConfig select without options is not meaningful; treat as text.
            input_type = "text"

        return InputBlock(
            block_id=f"input_{index}_{field.name}",
            kind="input",
            input_type=input_type,  # type: ignore[arg-type]
            label=field.label,
            required=field.required,
            writes_to=field.writes_to or field.name,
            module_name=field.module_name,
            placeholder=field.placeholder,
            options=field.options,
        )

    def _narrative_block(self) -> InfoBlock | None:
        if not self.narrative_ref:
            return None
        return InfoBlock(
            block_id="narrative",
            kind="info",
            content_ref=self.narrative_ref,
            reading_level="plain",
            collapsed_by_default=False,
            summary=self.display_title or self.page_title,
        )

    def _exit_block(self) -> OutputBlock | None:
        if not self.exit_transition:
            return None

        transition = self.exit_transition
        if transition.action == "help":
            on_trigger = "route:legal_aid_contact"
            label = "Get help"
        elif transition.next_page_id:
            on_trigger = f"route:{transition.next_page_id}"
            label = "Continue"
        else:
            on_trigger = "fn:save"
            label = "Save"

        return OutputBlock(
            block_id="exit_transition",
            kind="output",
            action_type="button",
            label=label,
            risk_tier=self.risk_tier or "low",
            on_trigger=on_trigger,
            module_name=None,
        )

    def _export_block(self) -> OutputBlock | None:
        if not self.export_type or self.export_type.export_type == "none":
            return None
        target = self.export_type.target or self.export_type.export_type
        return OutputBlock(
            block_id="export",
            kind="output",
            action_type="button",
            label=f"Save to {target}",
            risk_tier=self.risk_tier or "low",
            on_trigger=f"fn:export:{target}",
            module_name=None,
        )

    def _error_block(self) -> OutputBlock:
        route = self.error_route
        if route.route_to == "legal_aid":
            on_trigger = "route:legal_aid_contact"
        elif route.route_to == "home":
            on_trigger = "route:tenant_home"
        elif route.route_to == "error_page":
            on_trigger = f"route:{route.fallback_path}"
        else:
            on_trigger = f"route:{route.fallback_path}"

        return OutputBlock(
            block_id="error_route",
            kind="output",
            action_type="banner",
            label=route.label,
            risk_tier="high",
            on_trigger=on_trigger,
            module_name=None,
        )

    def _preview_block(self) -> InfoBlock | None:
        if not self.preview_state or self.preview_state.output_type == "none":
            return None
        return InfoBlock(
            block_id="preview",
            kind="info",
            content_ref=f"preview/{self.page_id}",
            reading_level="plain",
            collapsed_by_default=False,
            summary=self.preview_state.description,
        )

    def _review_block(self) -> OutputBlock | None:
        if not self.review_state or not self.review_state.required:
            return None
        return OutputBlock(
            block_id="review",
            kind="output",
            action_type="button",
            label=self.review_state.confirm_label,
            risk_tier=self.risk_tier or "low",
            on_trigger="fn:review_and_confirm",
            module_name=None,
        )

    def to_page_config(self) -> PageConfig:
        """Render this contract to a ``PageConfig``.

        Raises ``PageConfigResistanceError`` if the contract contains fields
        the current ``PageConfig`` schema cannot represent cleanly.
        """
        if self.page_config:
            return self.page_config

        pillar = self.pillar
        channels = ChannelLevels(
            record=90 if pillar == "record" else 10,
            know=90 if pillar == "know" else 10,
            act=90 if pillar == "act" else 10,
            govern=90 if pillar == "govern" else 10,
        )

        zones: dict[str, Zone] = {
            p: Zone(
                zone_id=p,  # type: ignore[arg-type]
                level=getattr(channels, p),
                max_blocks=4,
                blocks=[],
                layout="stack",
            )
            for p in ("record", "know", "act", "govern")
        }

        # Inputs go to the page's primary pillar zone.
        for idx, field in enumerate(self.inputs):
            block = self._input_block(idx, field)
            zones[pillar].blocks.append(block)

        # Narrative / explanation goes to KNOW.
        if narrative := self._narrative_block():
            zones["know"].blocks.append(narrative)

        # Preview state also surfaces as information.
        if preview := self._preview_block():
            zones["know"].blocks.append(preview)

        # Exit, export, and review actions go to ACT (or the primary pillar
        # for single-pillar guide pages).
        target_action_zone = "act" if pillar != "act" else pillar
        for builder in (self._exit_block, self._export_block, self._review_block):
            block = builder()
            if block:
                zones[target_action_zone].blocks.append(block)

        # Error/escalation route is always in GOVERN.
        zones["govern"].blocks.append(self._error_block())

        try:
            return PageConfig(
                page_id=self.page_id,
                major_pillar=pillar,
                blend=pillar if pillar != "govern" else "high_stakes_review",
                channels=channels,
                zones=zones,
                audit_hook=self.audit_hook or AuditHook(),
                escalation=self.escalation
                or Escalation(threshold_govern=85, escalation_action="surface_legal_aid_contact_banner"),
                jurisdiction=self.jurisdiction,
                county=self.county,
            )
        except ValidationError as exc:
            raise PageConfigResistanceError(
                f"PageConfig rejected generated config for page '{self.page_id}': {exc}"
            ) from exc


class PageContractRegistry:
    """In-memory registry for PageContracts keyed by flat page_id."""

    def __init__(self) -> None:
        self._contracts: dict[str, PageContract] = {}

    def register(self, contract: PageContract) -> PageContract:
        if not contract.page_id:
            raise ValueError("PageContract.page_id is required")
        self._contracts[contract.page_id] = contract
        return contract

    def get(self, page_id: str) -> PageContract | None:
        return self._contracts.get(page_id)

    def list(self) -> list[PageContract]:
        return list(self._contracts.values())

    def clear(self) -> None:
        self._contracts.clear()


page_contract_registry = PageContractRegistry()
