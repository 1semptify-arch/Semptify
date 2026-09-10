"""
Module Build Contract — Pydantic schema, loader, and validator.

This module implements Part 1 of docs/admin/SEMPTIFY_BUILD_CONTRACT.md:
- module_contract.json files are the source of truth, colocated with modules.
- docs/registry/module_contracts_index.json is generated, never hand-authored.
- The registry is also consumed at runtime by the Real-Time Narrator (Part 2).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

NARRATOR_VERBS = frozenset(
    {
        "is checking",
        "is waiting for",
        "found",
        "did not find",
        "saved",
        "flagged",
        "is comparing",
        "confirmed",
        "sent",
        "is waiting on approval for",
    }
)

OUTPUT_TYPES = frozenset(
    {"file", "record", "ui_state_change", "notification", "other"}
)

INPUT_SOURCES = frozenset(
    {
        "upload",
        "dropdown",
        "auto_detect",
        "typed",
        "toggle",
        "date_picker",
        "button",
        "import",
        "other",
    }
)


class ModuleContractInput(BaseModel):
    """One input the module accepts."""

    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    expected_size: str | None = None
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class ModuleContractInputAudit(BaseModel):
    """How one of the module's inputs was obtained."""

    input_name: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    note: str | None = None

    @field_validator("source")
    @classmethod
    def _source_known(cls, v: str) -> str:
        if v not in INPUT_SOURCES:
            raise ValueError(
                f"input_audit source {v!r} is not in the approved set: {sorted(INPUT_SOURCES)}"
            )
        return v


class NarratorEvent(BaseModel):
    """One event slot the Real-Time Narrator can render (Part 2)."""

    verb: str = Field(..., min_length=1)
    object: str = Field(..., min_length=1)
    context_clause: str = Field(..., min_length=1)

    @field_validator("verb")
    @classmethod
    def _verb_known(cls, v: str) -> str:
        if v not in NARRATOR_VERBS:
            raise ValueError(
                f"narrator verb {v!r} is not in the approved set: {sorted(NARRATOR_VERBS)}"
            )
        return v


class ModuleContract(BaseModel):
    """Part 1 build contract for a module/function.

    Every module/function must ship a module_contract.json in its folder.
    No function is considered complete without this record.
    """

    module_name: str = Field(..., min_length=1)
    layout: str = Field(..., min_length=1)

    inputs: list[ModuleContractInput] = Field(default_factory=list)
    input_audit: list[ModuleContractInputAudit] = Field(default_factory=list)

    preview_state: str | None = None
    review_state: str | None = None

    output_type: str = Field(..., min_length=1)
    output_how: str = Field(..., min_length=1)
    output_where: str = Field(..., min_length=1)
    output_why: str = Field(..., min_length=1)

    process_description: str = Field(..., min_length=1)
    process_context: str = Field(..., min_length=1)

    narrative_events: list[NarratorEvent] = Field(default_factory=list)

    @field_validator("output_type")
    @classmethod
    def _output_type_known(cls, v: str) -> str:
        if v not in OUTPUT_TYPES:
            raise ValueError(
                f"output_type {v!r} is not in the approved set: {sorted(OUTPUT_TYPES)}"
            )
        return v

    @model_validator(mode="after")
    def _input_audit_covers_inputs(self) -> "ModuleContract":
        if not self.inputs:
            return self
        input_names = {i.name for i in self.inputs}
        audit_names = {a.input_name for a in self.input_audit}
        missing = input_names - audit_names
        if missing:
            raise ValueError(
                f"input_audit is missing entries for inputs: {sorted(missing)}"
            )
        return self

    @model_validator(mode="after")
    def _user_facing_states(self) -> "ModuleContract":
        user_facing = self.output_type in {"ui_state_change", "notification"}
        if user_facing and (not self.preview_state or not self.review_state):
            raise ValueError(
                "preview_state and review_state are required when output_type is "
                f"ui_state_change or notification (got {self.output_type!r})"
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class ModuleContractIndexEntry(BaseModel):
    """One row in the generated docs/registry/module_contracts_index.json."""

    module_path: str
    contract_path: str
    module_name: str
    output_type: str
    has_preview_state: bool
    has_review_state: bool
    narrative_event_count: int


class ModuleContractRegistry:
    """Loads, validates, and indexes module_contract.json files."""

    def __init__(self, modules_root: Path | None = None) -> None:
        self.modules_root = modules_root or Path(__file__).resolve().parent.parent / "modules"
        self.contracts: dict[str, ModuleContract] = {}

    def _discover(self) -> list[tuple[str, Path]]:
        """Return (module_package, contract_path) tuples."""
        found: list[tuple[str, Path]] = []
        if not self.modules_root.exists():
            return found
        for module_dir in sorted(self.modules_root.iterdir()):
            if not module_dir.is_dir():
                continue
            contract_path = module_dir / "module_contract.json"
            if contract_path.exists():
                found.append((f"app.modules.{module_dir.name}", contract_path))
        return found

    def load(self) -> "ModuleContractRegistry":
        """Load all module_contract.json files."""
        self.contracts.clear()
        for module_package, contract_path in self._discover():
            try:
                data = json.loads(contract_path.read_text(encoding="utf-8"))
                self.contracts[module_package] = ModuleContract.model_validate(data)
            except Exception as exc:
                logger.warning(
                    "Failed to load module contract %s: %s",
                    contract_path,
                    exc,
                )
                raise
        return self

    def list_contracts(self) -> list[tuple[str, ModuleContract]]:
        return list(self.contracts.items())

    def get(self, module_package: str) -> ModuleContract | None:
        return self.contracts.get(module_package)

    def validate_all(self) -> dict[str, Any]:
        """Validate every discovered contract. Returns a report dict."""
        violations: list[dict[str, str]] = []
        loaded: list[str] = []

        for module_package, contract_path in self._discover():
            try:
                data = json.loads(contract_path.read_text(encoding="utf-8"))
                ModuleContract.model_validate(data)
                loaded.append(module_package)
            except Exception as exc:
                violations.append(
                    {
                        "module": module_package,
                        "path": str(contract_path),
                        "reason": str(exc),
                    }
                )

        return {
            "status": "pass" if not violations else "fail",
            "loaded": loaded,
            "violations": violations,
        }

    def generate_index(
        self, output_path: Path | None = None
    ) -> list[dict[str, Any]]:
        """Generate a registry index from loaded contracts and write it."""
        if not self.contracts:
            self.load()

        entries: list[dict[str, Any]] = []
        for module_package, contract in sorted(self.contracts.items()):
            parts = module_package.split(".")
            module_name = parts[-1]
            contract_path = f"app/modules/{module_name}/module_contract.json"
            entries.append(
                ModuleContractIndexEntry(
                    module_path=module_package,
                    contract_path=contract_path,
                    module_name=contract.module_name,
                    output_type=contract.output_type,
                    has_preview_state=bool(contract.preview_state),
                    has_review_state=bool(contract.review_state),
                    narrative_event_count=len(contract.narrative_events),
                ).model_dump()
            )

        if output_path is None:
            output_path = (
                Path(__file__).resolve().parent.parent.parent
                / "docs"
                / "registry"
                / "module_contracts_index.json"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps({"version": "1", "entries": entries}, indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        return entries


def load_module_contracts() -> ModuleContractRegistry:
    return ModuleContractRegistry().load()


def validate_all_module_contracts() -> dict[str, Any]:
    return ModuleContractRegistry().validate_all()


def generate_module_contracts_index(output_path: Path | None = None) -> list[dict[str, Any]]:
    return ModuleContractRegistry().generate_index(output_path)
