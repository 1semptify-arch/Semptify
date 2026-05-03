"""
MNDES Exhibit Service
=====================

Builds, validates, and tracks exhibit packages for submission to the
Minnesota Digital Exhibit System (MNDES).

Order ADM09-8010 compliance is enforced at every step:
- File type validation against the official Acceptable File Types List
- Per-exhibit attestation requirements
- No-contact order / sealed case guards
- Jury-room eligibility tagging for audio/video
- Full audit trail via audit_logger
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.core.mndes_compliance import (
    mndes_validator,
    MNDES_USER_WARNINGS,
    MNDES_PORTAL_URL,
    MNDESIssueCode,
)
from app.models.mndes_exhibit import (
    MNDESExhibit,
    MNDESExhibitCategory,
    MNDESExhibitPackage,
    MNDESExhibitStatus,
    MNDESCaseType,
    MNDESComplianceSummary,
    MNDESPackageCreateRequest,
    MNDESAttestationRequest,
    MNDESSubmissionConfirmRequest,
)

logger = logging.getLogger(__name__)

# ============================================================================
# In-memory store (replace with DB when persistence layer is added)
# ============================================================================

_packages: dict[str, MNDESExhibitPackage] = {}


# ============================================================================
# Service
# ============================================================================

class MNDESExhibitService:
    """
    Core service for MNDES exhibit package management.

    Usage:
        service = MNDESExhibitService()
        package = await service.create_package(request, vault_index, user_id)
    """

    def create_package(
        self,
        request: MNDESPackageCreateRequest,
        vault_docs: list[dict],
        user_id: str,
    ) -> MNDESExhibitPackage:
        """
        Build an exhibit package from a list of vault documents.

        Args:
            request: Package creation parameters.
            vault_docs: List of dicts with keys: vault_id, filename, file_size_bytes.
            user_id: Semptify user ID.

        Returns:
            MNDESExhibitPackage with compliance status for each exhibit.
        """
        if request.is_sealed_case:
            logger.warning(
                "MNDES package requested for sealed case %s by user %s — "
                "sealed cases require court administration to upload.",
                request.mn_case_number, user_id,
            )

        exhibits: list[MNDESExhibit] = []
        doc_map = {d["vault_id"]: d for d in vault_docs}

        for vault_id in request.vault_ids:
            doc = doc_map.get(vault_id)
            if not doc:
                logger.warning("Vault doc %s not found for MNDES package, skipping.", vault_id)
                continue

            filename = doc.get("filename", "")
            file_size = doc.get("file_size_bytes")

            validation = mndes_validator.validate_for_mndes(filename, file_size)

            exhibit_name = (
                (request.exhibit_names or {}).get(vault_id)
                or self._default_exhibit_name(filename)
            )

            category = None
            if validation.file_category:
                try:
                    category = MNDESExhibitCategory(validation.file_category)
                except ValueError:
                    category = None

            exhibit = MNDESExhibit(
                vault_id=vault_id,
                user_id=user_id,
                mn_case_number=request.mn_case_number,
                case_type=request.case_type,
                exhibit_name=exhibit_name,
                original_filename=filename,
                file_extension=validation.file_extension,
                file_size_bytes=file_size,
                category=category,
                is_mndes_compliant=validation.is_mndes_compliant,
                is_jury_room_eligible=validation.is_jury_room_eligible,
                conversion_required=validation.conversion_required,
                judge_exception_required=validation.judge_exception_required,
                no_contact_order=request.no_contact_order,
                is_sealed_case=request.is_sealed_case,
                status=(
                    MNDESExhibitStatus.PENDING_EXCEPTION
                    if validation.judge_exception_required
                    else MNDESExhibitStatus.PRE_HEARING
                ),
            )
            exhibits.append(exhibit)

        package = MNDESExhibitPackage(
            user_id=user_id,
            mn_case_number=request.mn_case_number,
            case_type=request.case_type,
            exhibits=exhibits,
            has_no_contact_order=request.no_contact_order,
        )
        package = self._recalculate_package_summary(package)

        _packages[package.package_id] = package
        logger.info(
            "MNDES package created: %s for case %s (%d exhibits, %d compliant)",
            package.package_id,
            request.mn_case_number,
            len(exhibits),
            package.all_compliant,
        )
        return package

    def get_package(self, package_id: str) -> Optional[MNDESExhibitPackage]:
        return _packages.get(package_id)

    def apply_attestations(
        self,
        request: MNDESAttestationRequest,
    ) -> MNDESExhibitPackage:
        """
        Apply user attestations to all exhibits in a package.
        Required before submission per Order §10 (no sexual content/nudity)
        and general compliance requirements.
        """
        package = _packages.get(request.package_id)
        if not package:
            raise ValueError(f"Package {request.package_id} not found")

        updated_exhibits = []
        for ex in package.exhibits:
            updated = ex.copy(update={
                "user_attested_no_sexual_content": request.attests_no_sexual_content,
                "user_attested_not_discovery": request.attests_not_discovery,
                "user_attested_not_motion_attachment": request.attests_not_motion_attachment,
                "updated_at": datetime.utcnow(),
            })
            updated_exhibits.append(updated)

        package = package.copy(update={
            "exhibits": updated_exhibits,
            "checklist_complete": (
                request.attests_no_sexual_content
                and request.attests_not_discovery
                and request.attests_not_motion_attachment
                and request.attests_understands_no_return
                and request.attests_semptify_not_mndes
            ),
            "updated_at": datetime.utcnow(),
        })
        _packages[package.package_id] = package
        logger.info("MNDES attestations applied to package %s", package.package_id)
        return package

    def confirm_submission(
        self,
        request: MNDESSubmissionConfirmRequest,
    ) -> MNDESExhibitPackage:
        """
        User confirms they completed manual upload at the MNDES portal.
        Records the MNDES tracking number for the exhibit.
        """
        package = _packages.get(request.package_id)
        if not package:
            raise ValueError(f"Package {request.package_id} not found")

        updated_exhibits = []
        for ex in package.exhibits:
            if ex.exhibit_id == request.exhibit_id:
                ex = ex.copy(update={
                    "mndes_submitted_by_user": True,
                    "mndes_submitted_at": request.submitted_at or datetime.utcnow(),
                    "mndes_tracking_number": request.mndes_tracking_number,
                    "status": MNDESExhibitStatus.PRE_HEARING,
                    "updated_at": datetime.utcnow(),
                })
            updated_exhibits.append(ex)

        all_submitted = all(e.mndes_submitted_by_user for e in updated_exhibits)
        package = package.copy(update={
            "exhibits": updated_exhibits,
            "mndes_submission_started": True,
            "mndes_submission_complete": all_submitted,
            "updated_at": datetime.utcnow(),
        })
        _packages[package.package_id] = package
        logger.info(
            "MNDES submission confirmed for exhibit %s in package %s (tracking: %s)",
            request.exhibit_id, request.package_id, request.mndes_tracking_number,
        )
        return package

    def get_compliance_summary(self, package_id: str) -> MNDESComplianceSummary:
        """Return compliance summary for a package."""
        package = _packages.get(package_id)
        if not package:
            raise ValueError(f"Package {package_id} not found")
        return self._build_compliance_summary(package.exhibits)

    def get_submission_checklist(self, package_id: str) -> dict:
        """
        Return a structured checklist for the user to complete before submitting to MNDES.
        """
        package = _packages.get(package_id)
        if not package:
            raise ValueError(f"Package {package_id} not found")

        summary = self._build_compliance_summary(package.exhibits)

        checklist = {
            "package_id": package_id,
            "mn_case_number": package.mn_case_number,
            "steps": [
                {
                    "step": 1,
                    "label": "Verify all files are MNDES-compliant",
                    "complete": summary.all_clear,
                    "detail": (
                        f"{summary.compliant}/{summary.total_files} files are compliant. "
                        f"{summary.non_compliant} need attention."
                    ),
                },
                {
                    "step": 2,
                    "label": "Convert any proprietary format files",
                    "complete": summary.needs_conversion == 0,
                    "detail": (
                        f"{summary.needs_conversion} files require format conversion "
                        "before upload (MP4, MP3, or PDF recommended)."
                        if summary.needs_conversion else "No conversion needed."
                    ),
                },
                {
                    "step": 3,
                    "label": "Obtain judge exception (if needed)",
                    "complete": summary.needs_judge_exception == 0,
                    "detail": (
                        f"{summary.needs_judge_exception} files require presiding judge approval "
                        "for proprietary format submission."
                        if summary.needs_judge_exception else "No judge exception needed."
                    ),
                },
                {
                    "step": 4,
                    "label": "Confirm no sexual content or nudity",
                    "complete": package.checklist_complete,
                    "detail": MNDES_USER_WARNINGS["sexual_content_prohibited"],
                },
                {
                    "step": 5,
                    "label": "Check no-contact order handling",
                    "complete": not package.has_no_contact_order,
                    "detail": (
                        MNDES_USER_WARNINGS["no_contact_order"]
                        if package.has_no_contact_order
                        else "No active no-contact order flagged."
                    ),
                },
                {
                    "step": 6,
                    "label": "Upload each exhibit individually at MNDES portal",
                    "complete": package.mndes_submission_started,
                    "detail": (
                        f"Go to {MNDES_PORTAL_URL} and upload each file separately. "
                        "Do NOT combine or zip exhibits."
                    ),
                },
                {
                    "step": 7,
                    "label": "Record MNDES tracking numbers in Semptify",
                    "complete": package.mndes_submission_complete,
                    "detail": "After upload, enter the tracking number MNDES assigns to each exhibit.",
                },
                {
                    "step": 8,
                    "label": "Share exhibits with opposing party (if required)",
                    "complete": False,
                    "detail": (
                        "Court rules may require you to share exhibits with the other party. "
                        "Use the MNDES Share function — unless a no-contact order applies."
                    ),
                },
            ],
            "warnings": [
                MNDES_USER_WARNINGS["no_return"],
                MNDES_USER_WARNINGS["not_evidence_until_offered"],
                MNDES_USER_WARNINGS["upload_individually"],
                MNDES_USER_WARNINGS["semptify_not_mndes"],
            ],
            "jury_room_note": (
                f"{summary.jury_room_eligible} audio/video exhibit(s) are eligible to be "
                "viewed by jurors during deliberations if admitted."
                if summary.jury_room_eligible else None
            ),
            "mndes_portal_url": "https://mndigitalexhibitsystem.courts.state.mn.us",
            "mndes_support_phone": "651-413-8160 (metro) | 1-833-707-2791 (other)",
        }
        return checklist

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _default_exhibit_name(self, filename: str) -> str:
        """Generate a default exhibit name from filename (user should edit)."""
        from pathlib import Path
        stem = Path(filename).stem.replace("_", " ").replace("-", " ")
        return stem[:80] if stem else filename[:80]

    def _recalculate_package_summary(
        self, package: MNDESExhibitPackage
    ) -> MNDESExhibitPackage:
        summary = self._build_compliance_summary(package.exhibits)
        return package.copy(update={
            "all_compliant": summary.all_clear,
            "compliance_issues_count": summary.non_compliant,
            "needs_judge_exception": summary.needs_judge_exception > 0,
            "has_jury_room_exhibits": summary.jury_room_eligible > 0,
        })

    def _build_compliance_summary(
        self, exhibits: list[MNDESExhibit]
    ) -> MNDESComplianceSummary:
        compliant = sum(1 for e in exhibits if e.is_mndes_compliant)
        non_compliant = len(exhibits) - compliant
        needs_conversion = sum(1 for e in exhibits if e.conversion_required)
        needs_judge_exception = sum(1 for e in exhibits if e.judge_exception_required)
        prohibited = sum(1 for e in exhibits if not e.is_mndes_compliant and not e.conversion_required and not e.judge_exception_required)
        jury_room_eligible = sum(1 for e in exhibits if e.is_jury_room_eligible)

        issues = []
        for ex in exhibits:
            if not ex.is_mndes_compliant:
                issues.append({
                    "vault_id": ex.vault_id,
                    "filename": ex.original_filename,
                    "exhibit_name": ex.exhibit_name,
                    "conversion_required": ex.conversion_required,
                    "judge_exception_required": ex.judge_exception_required,
                })

        return MNDESComplianceSummary(
            total_files=len(exhibits),
            compliant=compliant,
            non_compliant=non_compliant,
            needs_conversion=needs_conversion,
            needs_judge_exception=needs_judge_exception,
            prohibited=prohibited,
            jury_room_eligible=jury_room_eligible,
            issues=issues,
            all_clear=(non_compliant == 0),
        )


# ============================================================================
# Module-level singleton
# ============================================================================

mndes_exhibit_service = MNDESExhibitService()
