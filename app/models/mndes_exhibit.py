"""
MNDES Exhibit Models
====================

Pydantic models for tracking exhibits submitted through the Minnesota
Digital Exhibit System (MNDES) — MN Supreme Court Order ADM09-8010.

Exhibit lifecycle:
  pre_hearing → offered → admitted | rejected | withdrawn

Key rules encoded here:
- Pre-hearing exhibits are NOT case records (not publicly accessible).
- Audio/video exhibits flagged as jury_room_eligible per Order §2/§3.
- Cases with no-contact orders require special sharing handling.
- Exhibits are not returned after case closes — parties retain own copies.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.core.id_gen import make_id


# ============================================================================
# Enums
# ============================================================================

class MNDESExhibitStatus(str, Enum):
    """
    Lifecycle status of an exhibit in MNDES.

    PRE_HEARING  — Uploaded but not yet offered; NOT a case record; not public.
    OFFERED      — Party has asked judge to admit; becomes case record.
    ADMITTED     — Judge admitted as evidence; publicly accessible (unless restricted).
    REJECTED     — Judge declined to admit.
    WITHDRAWN    — Party withdrew the exhibit before ruling.
    PENDING_EXCEPTION — Proprietary format; awaiting judge exception ruling.
    """
    PRE_HEARING        = "pre_hearing"
    OFFERED            = "offered"
    ADMITTED           = "admitted"
    REJECTED           = "rejected"
    WITHDRAWN          = "withdrawn"
    PENDING_EXCEPTION  = "pending_exception"


class MNDESExhibitCategory(str, Enum):
    DOCUMENT = "document"
    IMAGE    = "image"
    AUDIO    = "audio"
    VIDEO    = "video"
    PHYSICAL = "physical"   # Cannot be digitized; tracked but not uploaded


class MNDESCaseType(str, Enum):
    CIVIL    = "civil"
    CRIMINAL = "criminal"
    FAMILY   = "family"
    OTHER    = "other"


# ============================================================================
# Core Exhibit Model
# ============================================================================

class MNDESExhibit(BaseModel):
    """
    A single exhibit tracked through the MNDES submission pipeline.

    Semptify creates this record when a user prepares an exhibit for court.
    The mndes_tracking_number is assigned by MNDES after the user uploads
    and should be entered back into Semptify by the user for full traceability.
    """

    exhibit_id: str = Field(default_factory=lambda: make_id("exh"))
    vault_id: str = Field(..., description="Semptify vault document ID")
    user_id: str = Field(..., description="Semptify user ID")

    # Case identification
    mn_case_number: str = Field(..., description="MN court case number (e.g. 19WS-CV-24-1234)")
    case_type: MNDESCaseType = Field(default=MNDESCaseType.CIVIL)

    # Exhibit identity
    exhibit_name: str = Field(..., description="Brief descriptive name (e.g. 'Photo of rear door')")
    exhibit_number: Optional[str] = Field(
        None,
        description="Number assigned by judge/scheduling order. Leave blank unless ordered."
    )
    original_filename: str
    file_extension: str
    file_size_bytes: Optional[int] = None
    category: Optional[MNDESExhibitCategory] = None

    # MNDES compliance flags
    is_mndes_compliant: bool = Field(default=False)
    is_jury_room_eligible: bool = Field(
        default=False,
        description="True for audio/video — must be permitted in jury room (criminal) per Order §2"
    )
    conversion_required: bool = Field(
        default=False,
        description="File required format conversion before MNDES upload"
    )
    judge_exception_required: bool = Field(
        default=False,
        description="True if proprietary format; requires presiding judge approval per Order §6"
    )
    judge_exception_granted: Optional[bool] = Field(
        default=None,
        description="None = pending; True = granted; False = denied"
    )

    # Case-level safety flags (from Semptify case data)
    no_contact_order: bool = Field(
        default=False,
        description="OFP/HRO/DANCO active — sharing via MNDES requires special handling"
    )
    is_sealed_case: bool = Field(
        default=False,
        description="Sealed cases: cannot upload directly; contact court admin"
    )
    is_in_camera: bool = Field(
        default=False,
        description="In-camera review exhibits go to judge's chambers, not MNDES"
    )

    # User attestations (required before submission)
    user_attested_no_sexual_content: Optional[bool] = Field(
        default=None,
        description="User confirmed exhibit does not contain sexual content or nudity"
    )
    user_attested_not_discovery: Optional[bool] = Field(
        default=None,
        description="User confirmed this is not discovery material (Alford Packets, etc.)"
    )
    user_attested_not_motion_attachment: Optional[bool] = Field(
        default=None,
        description="User confirmed this is not a motion/affidavit attachment (those go to eFS)"
    )

    # MNDES submission tracking
    status: MNDESExhibitStatus = Field(default=MNDESExhibitStatus.PRE_HEARING)
    mndes_tracking_number: Optional[str] = Field(
        None,
        description="Tracking number assigned by MNDES after user uploads. User enters this."
    )
    mndes_submitted_at: Optional[datetime] = None
    mndes_submitted_by_user: bool = Field(
        default=False,
        description="User confirmed they manually completed submission at MNDES portal"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Compliance metadata
    order_reference: str = Field(default="ADM09-8010")
    file_types_version: str = Field(default="2025-01")

    class Config:
        use_enum_values = True

    @property
    def is_case_record(self) -> bool:
        """
        Per Order §9: Pre-hearing exhibits are NOT case records.
        Only exhibits that have been OFFERED in a proceeding become case records.
        """
        return self.status not in (
            MNDESExhibitStatus.PRE_HEARING,
            MNDESExhibitStatus.PENDING_EXCEPTION,
        )

    @property
    def is_publicly_accessible(self) -> bool:
        """
        Per Order §9 and Rules of Public Access:
        Admitted exhibits in public proceedings are publicly accessible
        unless restricted by court order.
        """
        return self.status == MNDESExhibitStatus.ADMITTED

    @property
    def ready_for_mndes_submission(self) -> bool:
        """True when all required attestations are present and file is compliant."""
        return (
            self.is_mndes_compliant
            and self.user_attested_no_sexual_content is True
            and self.user_attested_not_discovery is True
            and self.user_attested_not_motion_attachment is True
            and not self.is_sealed_case
            and not self.is_in_camera
            and (not self.judge_exception_required or self.judge_exception_granted is True)
        )


# ============================================================================
# Exhibit Package — a group of exhibits for one case submission
# ============================================================================

class MNDESExhibitPackage(BaseModel):
    """
    A collection of exhibits being prepared for a single MN court case.
    """

    package_id: str = Field(default_factory=lambda: make_id("pkg"))
    user_id: str
    mn_case_number: str
    case_type: MNDESCaseType = MNDESCaseType.CIVIL

    exhibits: list[MNDESExhibit] = Field(default_factory=list)

    # Package-level compliance summary
    all_compliant: bool = False
    compliance_issues_count: int = 0
    needs_judge_exception: bool = False
    has_jury_room_exhibits: bool = False
    has_no_contact_order: bool = False

    # Submission state
    checklist_complete: bool = False
    mndes_submission_started: bool = False
    mndes_submission_complete: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    notes: Optional[str] = None


# ============================================================================
# API Request/Response Models
# ============================================================================

class MNDESValidateRequest(BaseModel):
    """Request to validate vault files for MNDES compliance."""
    vault_ids: list[str] = Field(..., min_length=1)
    mn_case_number: str
    case_type: MNDESCaseType = MNDESCaseType.CIVIL
    no_contact_order: bool = False
    is_sealed_case: bool = False


class MNDESPackageCreateRequest(BaseModel):
    """Request to create an exhibit package for a case."""
    vault_ids: list[str] = Field(..., min_length=1)
    mn_case_number: str
    case_type: MNDESCaseType = MNDESCaseType.CIVIL
    exhibit_names: Optional[dict[str, str]] = Field(
        None,
        description="Optional map of vault_id -> exhibit name. Defaults auto-generated."
    )
    no_contact_order: bool = False
    is_sealed_case: bool = False


class MNDESAttestationRequest(BaseModel):
    """User attestation before MNDES submission — required per Order §10."""
    package_id: str
    attests_no_sexual_content: bool
    attests_not_discovery: bool
    attests_not_motion_attachment: bool
    attests_understands_no_return: bool = Field(
        ...,
        description="User acknowledges court will not return digital exhibits"
    )
    attests_semptify_not_mndes: bool = Field(
        ...,
        description="User understands Semptify ≠ MNDES submission"
    )


class MNDESSubmissionConfirmRequest(BaseModel):
    """User confirms they completed manual submission at the MNDES portal."""
    package_id: str
    exhibit_id: str
    mndes_tracking_number: Optional[str] = Field(
        None,
        description="Tracking number assigned by MNDES (from the portal)"
    )
    submitted_at: Optional[datetime] = None


class MNDESComplianceSummary(BaseModel):
    """Summary of MNDES compliance for a package or set of files."""
    total_files: int
    compliant: int
    non_compliant: int
    needs_conversion: int
    needs_judge_exception: int
    prohibited: int
    jury_room_eligible: int
    issues: list[dict] = Field(default_factory=list)
    all_clear: bool
    file_types_version: str = "2025-01"
    order_reference: str = "ADM09-8010"
