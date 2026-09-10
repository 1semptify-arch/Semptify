"""Resource Intake & Integrity Engine.

Ingests candidate material, tags it, fact-checks it, routes it for human
approval, and releases verified, human-approved resources into the compiled
Information Composer resource pool (data/composer_resources.json).

This engine does NOT render tenant-facing output. It is a build-time and
admin-time gate between raw candidate material and the Composer.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.core.utc import utc_now_iso
from app.modules.resource_intake.schemas import (
    ApprovedResource,
    ResourceCandidate,
    ResourcePool,
)

logger = logging.getLogger(__name__)

DEFAULT_POOL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "composer_resources.json"


def _default_pool_path() -> Path:
    return DEFAULT_POOL_PATH


def load_composer_resource_pool(pool_path: Path | None = None) -> ResourcePool:
    """Load the compiled Information Composer resource pool."""
    pool_path = pool_path or _default_pool_path()
    if not pool_path.exists():
        return ResourcePool()
    try:
        data = json.loads(pool_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Could not parse resource pool {pool_path}: {exc}") from exc
    return ResourcePool.model_validate(data)


class ResourceIntakeEngine:
    """Runtime / build-time engine for the resource intake pipeline.

    The pipeline is intentionally synchronous and file-backed for v1:
    1. `ingest` — accept a ResourceCandidate.
    2. `tag` — tag with purpose and source_type (already present on candidate).
    3. `fact_check` — external / human verification (placeholder hook).
    4. `route_for_approval` — mark pending human approval.
    5. `approve` / `reject` — human decision.
    6. `release` — write approved items to the compiled pool.
    """

    def __init__(self, pool_path: Path | None = None) -> None:
        self.pool_path = pool_path or _default_pool_path()
        self.candidates: list[ResourceCandidate] = []

    def ingest(self, candidate: ResourceCandidate) -> dict[str, Any]:
        """Stage a candidate resource for the intake pipeline."""
        if candidate.ai_generated is not False:
            raise ValueError(
                f"Candidate {candidate.source!r} is marked ai_generated={candidate.ai_generated}; "
                "no AI-generated material may enter the pool."
            )
        self.candidates.append(candidate)
        return {"status": "staged", "source": candidate.source}

    def tag(self, source: str, purpose_tag: str, source_type: str) -> dict[str, Any]:
        """Update purpose and source_type tags on a staged candidate."""
        for c in self.candidates:
            if c.source == source:
                c.purpose_tag = purpose_tag
                c.source_type = source_type
                return {"status": "tagged", "source": source}
        raise ValueError(f"Candidate {source!r} not found.")

    def fact_check(
        self,
        source: str,
        status: str,
        method: str,
        checked_by: str,
    ) -> dict[str, Any]:
        """Record fact-check status for a staged candidate.

        This is a bookkeeping hook; real verification is a human process.
        """
        for c in self.candidates:
            if c.source == source:
                c.fact_check_status = status
                c.fact_check_method = f"{method} (checked by {checked_by})"
                c.fact_check_date = utc_now_iso()
                return {"status": "fact_checked", "source": source}
        raise ValueError(f"Candidate {source!r} not found.")

    def route_for_approval(self, source: str) -> dict[str, Any]:
        """Mark a verified candidate as pending human approval."""
        for c in self.candidates:
            if c.source == source:
                if c.fact_check_status != "Verified":
                    raise ValueError(
                        f"Candidate {source!r} must be Verified before routing for approval; "
                        f"current status is {c.fact_check_status!r}."
                    )
                c.approval_status = "Pending"
                return {"status": "pending_approval", "source": source}
        raise ValueError(f"Candidate {source!r} not found.")

    def approve(self, source: str, approved_by: str) -> ApprovedResource:
        """Approve a verified candidate and return an ApprovedResource."""
        for c in self.candidates:
            if c.source == source:
                if c.fact_check_status != "Verified":
                    raise ValueError(
                        f"Candidate {source!r} must be Verified before approval."
                    )
                if c.approval_status == "Rejected":
                    raise ValueError(f"Candidate {source!r} was rejected and cannot be approved.")
                if c.ai_generated is not False:
                    raise ValueError(
                        f"Candidate {source!r} is marked as AI-generated; cannot approve."
                    )
                c.approval_status = "Approved"
                c.approved_by = approved_by
                return ApprovedResource(
                    source=c.source,
                    source_type=c.source_type,
                    fact_check_status="Verified",
                    fact_check_method=c.fact_check_method,
                    fact_check_date=c.fact_check_date,
                    purpose_tag=c.purpose_tag,
                    ai_generated=False,
                    approval_status="Approved",
                    approved_by=approved_by,
                    released_at=utc_now_iso(),
                )
        raise ValueError(f"Candidate {source!r} not found.")

    def reject(self, source: str) -> dict[str, Any]:
        """Reject a candidate and remove it from the staging list."""
        for i, c in enumerate(self.candidates):
            if c.source == source:
                c.approval_status = "Rejected"
                self.candidates.pop(i)
                return {"status": "rejected", "source": source}
        raise ValueError(f"Candidate {source!r} not found.")

    def release(self, *approved: ApprovedResource) -> ResourcePool:
        """Write approved resources to the compiled Composer pool."""
        pool = load_composer_resource_pool(self.pool_path)

        # Deduplicate by source, keeping the latest release.
        by_source = {item.source: item for item in pool.items}
        for item in approved:
            by_source[item.source] = item

        pool.items = list(by_source.values())
        pool.generated_at = utc_now_iso()

        self.pool_path.parent.mkdir(parents=True, exist_ok=True)
        self.pool_path.write_text(
            json.dumps(pool.model_dump(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Released %d approved resource(s) to %s", len(approved), self.pool_path)
        return pool

    def validate_pool(self, pool_path: Path | None = None) -> dict[str, Any]:
        """Validate the compiled pool without modifying it.

        Returns a dict with status 'pass' or 'fail' and a list of violations.
        """
        pool = load_composer_resource_pool(pool_path or self.pool_path)
        violations: list[str] = []

        for i, item in enumerate(pool.items):
            if item.ai_generated is not False:
                violations.append(
                    f"item[{i}] source={item.source!r}: ai_generated must be false"
                )
            if not item.approved_by or not item.approved_by.strip():
                violations.append(
                    f"item[{i}] source={item.source!r}: approved_by is required"
                )

        return {
            "status": "pass" if not violations else "fail",
            "count": len(pool.items),
            "violations": violations,
        }
