"""Module Contract — lifecycle and metadata source of truth for a module.

A ModuleContract sits alongside ``FunctionGroupContract`` (service API contract)
and ``ModuleEntry`` / ``ModuleManifest`` (product/lifecycle metadata). It captures
the module-level fields the AI hand-off packet and architecture review asked for:
pillar, roles, lifecycle, security classification, acceptance test, rollback plan,
and a richer input model.

It is Pydantic so it can serve as both a declaration and a runtime validator.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModuleContractInput(BaseModel):
    """One declared input or output of a module."""

    model_config = ConfigDict(frozen=True)

    name: str
    kind: Literal["input", "output"] = "input"
    data_type: str = "str"
    required: bool = False
    sensitive: bool = False
    description: str = ""
    source: str | None = None


class ModuleContractErrorRoute(BaseModel):
    """Where the module sends a user when it cannot complete safely."""

    model_config = ConfigDict(frozen=True)

    route_to: Literal["help", "legal_aid", "home", "error_page"] = "help"
    fallback_path: str = "/help"
    label: str = "Get help"


ModuleContractLifecycle = Literal[
    "dev_only",
    "preview",
    "experimental",
    "beta",
    "stable",
    "internal",
    "deprecated",
]

ModuleContractUPLRiskTier = Literal[
    "low",
    "low_medium",
    "medium",
    "medium_high",
    "high",
    "very_high_do_not_build",
    "none",
]


class ModuleContractSecurityClassification(BaseModel):
    """Security/PII posture for the module."""

    model_config = ConfigDict(frozen=True)

    level: Literal["public", "tenant", "pii", "legal_sensitive"] = "public"
    notes: str = ""


class ModuleContract(BaseModel):
    """High-level module contract.

    This is not a replacement for ``FunctionGroupContract`` or
    ``ModuleEntry`` / ``ModuleManifest``. It references them by
    ``module_path`` and ``function_group_id`` and adds the module-level
    metadata they do not currently carry.
    """

    model_config = ConfigDict(frozen=False)

    # Stable dotted module path, e.g. "app.modules.page_shell".
    module_path: str

    # Human title and description.
    title: str
    description: str = ""

    # Four-pillar mapping and tenant roles that may use this module.
    pillar: Literal["record", "know", "act", "govern"]
    roles: list[str] = Field(default_factory=lambda: ["tenant"])

    # Lifecycle and operational metadata.
    lifecycle: ModuleContractLifecycle = "preview"
    security_classification: ModuleContractSecurityClassification = Field(
        default_factory=ModuleContractSecurityClassification
    )

    # Richer inputs/outputs/dependencies than FunctionGroupContract's string tuples.
    inputs: list[ModuleContractInput] = Field(default_factory=list)
    outputs: list[ModuleContractInput] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)

    # Operational gates.
    acceptance_test: str = ""
    rollback_plan: str = ""
    error_route: ModuleContractErrorRoute = Field(
        default_factory=ModuleContractErrorRoute
    )

    # References to existing runtime metadata (kept separate, not duplicated).
    function_group_ids: list[str] = Field(default_factory=list)
    product_manifest_path: str | None = None
    module_manifest_path: str | None = None

    # UPL and financial guardrails.
    upl_risk_tier: ModuleContractUPLRiskTier = "none"
    fees_policy: str = ""

    # Optional flat stable contract ID. If not provided, the registry uses
    # the dotted module_path as the canonical key (per the decision to keep
    # hierarchical keys for now).
    contract_id: str | None = None

    @property
    def stable_id(self) -> str:
        return self.contract_id or self.module_path
