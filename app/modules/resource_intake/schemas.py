"""Resource Intake & Integrity Engine — Pydantic schemas.

Implements the Part 3 Resource Sourcing Contract for the Information Composer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PURPOSE_TAGS = frozenset(
    {
        "strength",
        "unity",
        "confidence",
        "reassurance",
        "answers-unasked-question",
    }
)

SOURCE_TYPES = frozenset(
    {
        "research_paper",
        "news_article",
        "case_study",
        "statistical_report",
        "government_source",
        "legal_source",
        "advocate_report",
    }
)

FACT_CHECK_STATUSES = frozenset({"Pending", "Verified", "Rejected"})
APPROVAL_STATUSES = frozenset({"Pending", "Approved", "Rejected"})


class ResourceCandidate(BaseModel):
    """A candidate resource item awaiting fact-check and human approval."""

    source: str = Field(..., min_length=1)
    source_type: str = Field(..., min_length=1)
    fact_check_status: str = Field(..., min_length=1)
    fact_check_method: str = Field(..., min_length=1)
    fact_check_date: str = Field(..., min_length=1)
    purpose_tag: str = Field(..., min_length=1)
    ai_generated: bool = Field(
        ...,
        description="Hard gate — must be false for any item entering the pool.",
    )
    approval_status: str = Field(..., min_length=1)
    approved_by: str | None = Field(
        default=None,
        description="Human approver of record. Required for Approved status.",
    )

    @field_validator("source_type")
    @classmethod
    def _source_type_known(cls, v: str) -> str:
        if v not in SOURCE_TYPES:
            raise ValueError(
                f"source_type {v!r} is not in the approved set: {sorted(SOURCE_TYPES)}"
            )
        return v

    @field_validator("fact_check_status")
    @classmethod
    def _fact_check_status_known(cls, v: str) -> str:
        if v not in FACT_CHECK_STATUSES:
            raise ValueError(
                f"fact_check_status {v!r} must be one of {sorted(FACT_CHECK_STATUSES)}"
            )
        return v

    @field_validator("approval_status")
    @classmethod
    def _approval_status_known(cls, v: str) -> str:
        if v not in APPROVAL_STATUSES:
            raise ValueError(
                f"approval_status {v!r} must be one of {sorted(APPROVAL_STATUSES)}"
            )
        return v

    @field_validator("purpose_tag")
    @classmethod
    def _purpose_tag_known(cls, v: str) -> str:
        if v not in PURPOSE_TAGS:
            raise ValueError(
                f"purpose_tag {v!r} is not in the approved set: {sorted(PURPOSE_TAGS)}"
            )
        return v


class ApprovedResource(ResourceCandidate):
    """A resource that has been verified and approved for the Composer."""

    approved_by: str = Field(..., min_length=1)
    fact_check_status: Literal["Verified"] = "Verified"
    approval_status: Literal["Approved"] = "Approved"
    released_at: str | None = None

    def model_post_init(self, __context: object) -> None:
        if self.fact_check_status != "Verified" or self.approval_status != "Approved":
            raise ValueError("ApprovedResource requires fact_check_status=Verified and approval_status=Approved")
        if not self.approved_by or not self.approved_by.strip():
            raise ValueError("ApprovedResource requires a non-empty approved_by")


class ResourcePool(BaseModel):
    """The compiled Information Composer resource pool.

    This is the file the Composer reads at runtime. The guardrail check
    blocks the build if any item in `items` fails the hard gates.
    """

    version: str = "1"
    generated_at: str | None = None
    items: list[ApprovedResource] = Field(default_factory=list)

    @field_validator("items")
    @classmethod
    def _items_are_approved(cls, v: list[ApprovedResource]) -> list[ApprovedResource]:
        for item in v:
            if item.ai_generated is not False:
                raise ValueError(f"Item from {item.source!r}: ai_generated must be false")
            if not item.approved_by or not item.approved_by.strip():
                raise ValueError(f"Item from {item.source!r}: approved_by is required")
        return v
