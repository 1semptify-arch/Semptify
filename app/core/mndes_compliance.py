"""
MNDES Compliance — Minnesota Digital Exhibit System
====================================================

Authoritative file type list and compliance validator for MN Supreme Court
Order ADM09-8010 (effective January 1, 2025).

Reference: https://mncourts.gov/help-topics/evidence-and-exhibits/minnesota-digital-exhibit-system-mndes
Dakota County Guidelines: 19WS-CO-26-1394 (updated 2/28/2025)

LEGAL CONTEXT:
- MNDES is mandatory for all MN district court digital exhibit submissions.
- Exhibits must be uploaded individually (not combined/zipped).
- Acceptable file types are controlled by the State Court Administrator.
- Files requiring proprietary players must be converted or require judge exception.
- Sexual content/nudity is prohibited from MNDES; must be conventional submission.
- Pre-hearing exhibits are NOT case records until offered in a public proceeding.
- Court does NOT return digital exhibits — parties must retain their own copies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================================
# MNDES Order Metadata — for audit trail and version tracking
# ============================================================================

MNDES_ORDER_NUMBER = "ADM09-8010"
MNDES_ORDER_DATE = date(2024, 8, 30)
MNDES_EFFECTIVE_DATE = date(2025, 1, 1)
MNDES_FILE_TYPES_VERSION = "2025-01"  # Update when court updates the list
MNDES_PORTAL_URL = "https://mndigitalexhibitsystem.courts.state.mn.us"
MNDES_SUPPORT_PHONE_METRO = "651-413-8160"
MNDES_SUPPORT_PHONE_OTHER = "1-833-707-2791"
MNDES_SUPPORT_HOURS = "Monday-Friday 8:30am-4:15pm CT (excluding court holidays)"
MNDES_FILE_SIZE_LIMIT_GB = 100  # Per Dakota County Guidelines: 100 GB max

# ============================================================================
# MNDES Acceptable File Types (Official List — Jan 2025)
# Source: Handout-MNDES-Acceptable-File-Formats, mncourts.gov/mndes
# Categories match the court's published groupings.
# ============================================================================

MNDES_ACCEPTABLE_TYPES: dict[str, dict] = {
    # --- Documents ---
    "pdf":  {"category": "document", "description": "PDF Document",              "jury_room_eligible": False},
    "doc":  {"category": "document", "description": "Microsoft Word (legacy)",   "jury_room_eligible": False},
    "docx": {"category": "document", "description": "Microsoft Word",            "jury_room_eligible": False},
    "rtf":  {"category": "document", "description": "Rich Text Format",          "jury_room_eligible": False},
    "txt":  {"category": "document", "description": "Plain Text",                "jury_room_eligible": False},
    "xls":  {"category": "document", "description": "Microsoft Excel (legacy)",  "jury_room_eligible": False},
    "xlsx": {"category": "document", "description": "Microsoft Excel",           "jury_room_eligible": False},
    "ppt":  {"category": "document", "description": "PowerPoint (legacy)",       "jury_room_eligible": False},
    "pptx": {"category": "document", "description": "PowerPoint",                "jury_room_eligible": False},

    # --- Images ---
    "jpg":  {"category": "image", "description": "JPEG Image",  "jury_room_eligible": False},
    "jpeg": {"category": "image", "description": "JPEG Image",  "jury_room_eligible": False},
    "png":  {"category": "image", "description": "PNG Image",   "jury_room_eligible": False},
    "gif":  {"category": "image", "description": "GIF Image",   "jury_room_eligible": False},
    "tif":  {"category": "image", "description": "TIFF Image",  "jury_room_eligible": False},
    "tiff": {"category": "image", "description": "TIFF Image",  "jury_room_eligible": False},
    "bmp":  {"category": "image", "description": "Bitmap Image","jury_room_eligible": False},

    # --- Audio (jury-room eligible per Order §2/§3) ---
    "mp3":  {"category": "audio", "description": "MP3 Audio",  "jury_room_eligible": True},
    "wav":  {"category": "audio", "description": "WAV Audio",  "jury_room_eligible": True},
    "m4a":  {"category": "audio", "description": "M4A Audio",  "jury_room_eligible": True},
    "wma":  {"category": "audio", "description": "WMA Audio",  "jury_room_eligible": True},
    "aac":  {"category": "audio", "description": "AAC Audio",  "jury_room_eligible": True},
    "aiff": {"category": "audio", "description": "AIFF Audio", "jury_room_eligible": True},
    "flac": {"category": "audio", "description": "FLAC Audio", "jury_room_eligible": True},

    # --- Video (jury-room eligible per Order §2/§3) ---
    "mp4":  {"category": "video", "description": "MP4 Video",       "jury_room_eligible": True},
    "mov":  {"category": "video", "description": "QuickTime Video",  "jury_room_eligible": True},
    "avi":  {"category": "video", "description": "AVI Video",        "jury_room_eligible": True},
    "wmv":  {"category": "video", "description": "WMV Video",        "jury_room_eligible": True},
    "mkv":  {"category": "video", "description": "MKV Video",        "jury_room_eligible": True},
    "flv":  {"category": "video", "description": "FLV Video",        "jury_room_eligible": True},
    "mpeg": {"category": "video", "description": "MPEG Video",       "jury_room_eligible": True},
    "mpg":  {"category": "video", "description": "MPG Video",        "jury_room_eligible": True},
    "m4v":  {"category": "video", "description": "M4V Video",        "jury_room_eligible": True},
}

# ============================================================================
# Prohibited and Blocked Types
# ============================================================================

# Explicitly prohibited by MNDES order — must NOT be uploaded
MNDES_PROHIBITED_TYPES: frozenset[str] = frozenset({
    # Archives (Order: no zipped files)
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz",
    # Executables / scripts — cybersecurity threat per Order §5
    "exe", "bat", "cmd", "com", "pif", "scr", "vbs", "js", "jar",
    "app", "deb", "pkg", "dmg", "iso", "img", "bin", "run",
    "sh", "ps1", "py", "pl", "rb", "php", "asp", "jsp",
    "msi", "msp", "mst", "cpl", "inf", "reg",
})

# Proprietary formats that require player/codec — need judge exception per Order §6
MNDES_PROPRIETARY_FORMATS: frozenset[str] = frozenset({
    "mts", "m2ts", "vob", "ts", "mxf", "r3d", "braw",
    "prproj", "aep", "fcp", "fcpx",
    "3gp", "3g2", "asf", "rm", "rmvb", "divx",
})

# Formats that cannot be digitized — must be physical exhibit per Dakota County Guidelines
MNDES_PHYSICAL_ONLY_NOTE = (
    "Physical exhibits (weapons, drugs, objects that cannot be digitized) "
    "must be brought to court in person. Court staff will create a physical "
    "exhibit tracking sheet in MNDES."
)

# ============================================================================
# Compliance Result
# ============================================================================

class MNDESIssueCode(str, Enum):
    PROHIBITED_TYPE       = "prohibited_type"         # Zip, exe, etc.
    PROPRIETARY_FORMAT    = "proprietary_format"       # Needs judge exception
    NOT_ON_APPROVED_LIST  = "not_on_approved_list"     # Unknown/unsupported type
    FILE_TOO_LARGE        = "file_too_large"           # > 100 GB
    COMBINED_EXHIBIT      = "combined_exhibit"         # Should be individual files
    SEXUAL_CONTENT_FLAG   = "sexual_content_flag"      # User must attest
    NO_CONTACT_ORDER      = "no_contact_order"         # OFP/HRO/DANCO — sharing restricted
    SEALED_CASE           = "sealed_case"              # Cannot upload; contact court admin
    CERTIFIED_COPY        = "certified_copy"           # Must be physical exhibit
    MOTION_ATTACHMENT     = "motion_attachment"        # File eFS system, not MNDES
    DISCOVERY_DOCUMENT    = "discovery_document"       # Alford packets — not for MNDES


@dataclass
class MNDESValidationResult:
    """Result of MNDES compliance check for a single file."""
    is_mndes_compliant: bool
    file_extension: str
    file_category: Optional[str] = None        # document, image, audio, video
    is_jury_room_eligible: bool = False
    conversion_required: bool = False          # Needs format conversion
    judge_exception_required: bool = False     # Requires presiding judge approval
    is_prohibited: bool = False                # Hard block — cannot be uploaded
    issues: list[MNDESIssueCode] = field(default_factory=list)
    issue_details: list[str] = field(default_factory=list)
    recommended_action: Optional[str] = None
    file_types_version: str = MNDES_FILE_TYPES_VERSION
    order_reference: str = MNDES_ORDER_NUMBER


# ============================================================================
# Validator
# ============================================================================

class MNDESFileValidator:
    """
    Validates files against the MNDES Acceptable File Types List and
    Supreme Court Order ADM09-8010 requirements.

    Use validate_for_mndes() for all exhibit submissions in Minnesota.
    """

    def validate_for_mndes(
        self,
        filename: str,
        file_size_bytes: Optional[int] = None,
    ) -> MNDESValidationResult:
        """
        Validate a file for MNDES compliance.

        Args:
            filename: Original filename including extension.
            file_size_bytes: File size in bytes (optional; checked against 100 GB limit).

        Returns:
            MNDESValidationResult with full compliance status.
        """
        ext = Path(filename).suffix.lower().lstrip(".")
        issues: list[MNDESIssueCode] = []
        issue_details: list[str] = []

        # --- Hard block: prohibited type ---
        if ext in MNDES_PROHIBITED_TYPES:
            if ext in {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz"}:
                issues.append(MNDESIssueCode.PROHIBITED_TYPE)
                issue_details.append(
                    f"'.{ext}' files (archives/compressed) are explicitly prohibited by MNDES. "
                    "Upload exhibits individually in their original format."
                )
            else:
                issues.append(MNDESIssueCode.PROHIBITED_TYPE)
                issue_details.append(
                    f"'.{ext}' is a prohibited file type (executable/script). "
                    "This file poses a cybersecurity risk and cannot be uploaded to MNDES."
                )
            return MNDESValidationResult(
                is_mndes_compliant=False,
                file_extension=ext,
                is_prohibited=True,
                issues=issues,
                issue_details=issue_details,
                recommended_action=(
                    "Convert to an MNDES-accepted format (e.g., PDF, JPG, MP4) "
                    "or contact court administration."
                ),
            )

        # --- Proprietary format: requires judge exception ---
        if ext in MNDES_PROPRIETARY_FORMATS:
            issues.append(MNDESIssueCode.PROPRIETARY_FORMAT)
            issue_details.append(
                f"'.{ext}' requires a proprietary player or codec. "
                "Per Order ADM09-8010 §6, you must attempt conversion to an accepted format. "
                "If conversion is not possible, contact the presiding judge to request an exception."
            )
            return MNDESValidationResult(
                is_mndes_compliant=False,
                file_extension=ext,
                conversion_required=True,
                judge_exception_required=True,
                issues=issues,
                issue_details=issue_details,
                recommended_action=(
                    "Convert to MP4, MOV, or MP3 using free tools (VLC, HandBrake, Audacity). "
                    "If conversion is impossible, contact the presiding judge before the hearing."
                ),
            )

        # --- Not on approved list ---
        if ext not in MNDES_ACCEPTABLE_TYPES:
            issues.append(MNDESIssueCode.NOT_ON_APPROVED_LIST)
            issue_details.append(
                f"'.{ext}' is not on the MNDES Acceptable File Types List (version {MNDES_FILE_TYPES_VERSION}). "
                "Check mncourts.gov/mndes for the current list or contact the EAST support team."
            )
            return MNDESValidationResult(
                is_mndes_compliant=False,
                file_extension=ext,
                issues=issues,
                issue_details=issue_details,
                recommended_action=(
                    "Convert to PDF, JPG, MP4, or MP3. "
                    f"Contact MNDES support at {MNDES_SUPPORT_PHONE_METRO} if unsure."
                ),
            )

        # --- File size check ---
        if file_size_bytes is not None:
            limit_bytes = MNDES_FILE_SIZE_LIMIT_GB * 1024 * 1024 * 1024
            if file_size_bytes > limit_bytes:
                issues.append(MNDESIssueCode.FILE_TOO_LARGE)
                issue_details.append(
                    f"File size exceeds the {MNDES_FILE_SIZE_LIMIT_GB} GB MNDES limit. "
                    "Per Dakota County Guidelines, files exceeding this limit must be submitted as physical exhibits."
                )
                return MNDESValidationResult(
                    is_mndes_compliant=False,
                    file_extension=ext,
                    issues=issues,
                    issue_details=issue_details,
                    recommended_action=(
                        "Compress or trim the file. If not possible, bring the exhibit to court "
                        "as a physical exhibit and notify court administration."
                    ),
                )

        # --- Compliant ---
        type_info = MNDES_ACCEPTABLE_TYPES[ext]
        return MNDESValidationResult(
            is_mndes_compliant=True,
            file_extension=ext,
            file_category=type_info["category"],
            is_jury_room_eligible=type_info["jury_room_eligible"],
            issues=[],
            issue_details=[],
            recommended_action=None,
        )

    def validate_batch(
        self,
        filenames: list[str],
        file_sizes: Optional[list[int]] = None,
    ) -> list[MNDESValidationResult]:
        """Validate multiple files for MNDES compliance."""
        sizes = file_sizes or [None] * len(filenames)
        return [
            self.validate_for_mndes(fn, sz)
            for fn, sz in zip(filenames, sizes)
        ]

    def get_accepted_extensions(self) -> list[str]:
        """Return sorted list of all MNDES-accepted file extensions."""
        return sorted(MNDES_ACCEPTABLE_TYPES.keys())

    def get_accepted_by_category(self) -> dict[str, list[str]]:
        """Return MNDES-accepted extensions grouped by category."""
        result: dict[str, list[str]] = {}
        for ext, info in MNDES_ACCEPTABLE_TYPES.items():
            cat = info["category"]
            result.setdefault(cat, []).append(ext)
        return {cat: sorted(exts) for cat, exts in sorted(result.items())}

    def is_jury_room_eligible(self, filename: str) -> bool:
        """Return True if this file type must be permitted in the jury room (criminal) or may be (civil)."""
        ext = Path(filename).suffix.lower().lstrip(".")
        return MNDES_ACCEPTABLE_TYPES.get(ext, {}).get("jury_room_eligible", False)


# ============================================================================
# Module-level singleton
# ============================================================================

mndes_validator = MNDESFileValidator()


# ============================================================================
# Conversion Targets — recommended format paths for non-compliant files.
# This is the hook point for future in-app converters.
# To add a converter: set converter_available=True and converter_endpoint=URL.
# ============================================================================

MNDES_CONVERSION_TARGETS: dict[str, dict] = {
    # Semptify-accepted types not on MNDES list
    "csv":   {"target": "xlsx", "instructions": "CSV is not on the MNDES approved list. Export as Excel (.xlsx) or save as PDF."},
    # Proprietary video formats requiring judge exception per Order §6
    "mts":   {"target": "mp4",  "instructions": "Convert using HandBrake or VLC (free). MP4 is fully MNDES-compliant."},
    "m2ts":  {"target": "mp4",  "instructions": "Convert using HandBrake or VLC (free). MP4 is fully MNDES-compliant."},
    "vob":   {"target": "mp4",  "instructions": "Convert using HandBrake (free). MP4 is fully MNDES-compliant."},
    "ts":    {"target": "mp4",  "instructions": "Convert using VLC (free). MP4 is fully MNDES-compliant."},
    "mxf":   {"target": "mp4",  "instructions": "Convert using FFmpeg or Adobe Media Encoder. Requires judge exception if unconverted."},
    "3gp":   {"target": "mp4",  "instructions": "Convert using VLC or HandBrake (free). MP4 is fully MNDES-compliant."},
    "3g2":   {"target": "mp4",  "instructions": "Convert using VLC or HandBrake (free). MP4 is fully MNDES-compliant."},
    "asf":   {"target": "wmv",  "instructions": "Re-export as WMV or MP4 using VLC (free)."},
    "rm":    {"target": "mp4",  "instructions": "Convert using VLC or FFmpeg (free). MP4 is fully MNDES-compliant."},
    "rmvb":  {"target": "mp4",  "instructions": "Convert using VLC or FFmpeg (free). MP4 is fully MNDES-compliant."},
    "divx":  {"target": "mp4",  "instructions": "Convert using HandBrake (free). MP4 is fully MNDES-compliant."},
    "r3d":   {"target": "mp4",  "instructions": "Export from REDCINE-X or DaVinci Resolve to MP4."},
    "braw":  {"target": "mp4",  "instructions": "Export from DaVinci Resolve to MP4."},
    "prproj":{"target": "mp4",  "instructions": "Export the final sequence from Premiere Pro as MP4."},
    "aep":   {"target": "mp4",  "instructions": "Export from After Effects as MP4 via Adobe Media Encoder."},
}


def get_conversion_action(ext: str) -> Optional[dict]:
    """
    Return the recommended conversion action for a non-compliant file extension.

    Returns None if the file is already compliant or no conversion path is known.

    Future converters plug in here:
      - Set converter_available=True
      - Set converter_endpoint to the API route (e.g. "/api/mndes/convert")
    """
    clean_ext = ext.lower().lstrip(".")
    action = MNDES_CONVERSION_TARGETS.get(clean_ext)
    if not action:
        return None
    return {
        "from_format": clean_ext,
        "to_format": action["target"],
        "instructions": action["instructions"],
        "converter_available": False,   # Future: True when in-app converter is built
        "converter_endpoint": None,     # Future: "/api/mndes/convert" when built
    }


# ============================================================================
# Convenience warnings — surfaced to users in UI
# ============================================================================

MNDES_USER_WARNINGS = {
    "no_return": (
        "The court will NOT return your digital exhibits after the case is closed. "
        "Keep your own copies of everything you upload to MNDES."
    ),
    "not_evidence_until_offered": (
        "Uploading to MNDES does NOT automatically make your file evidence. "
        "You must offer each exhibit to the judge at the hearing."
    ),
    "upload_individually": (
        "Upload each exhibit as a separate file. Do not combine multiple exhibits "
        "into one file or use zip/compressed archives."
    ),
    "semptify_not_mndes": (
        "Saving to Semptify does not submit to the court. "
        "You must complete your submission at mndigitalexhibitsystem.courts.state.mn.us"
    ),
    "no_contact_order": (
        "This case has a no-contact order (OFP/HRO/DANCO). "
        "Do NOT use MNDES sharing to contact the other party. "
        "Contact court administration for instructions on how to exchange exhibits."
    ),
    "sexual_content_prohibited": (
        "Do NOT upload exhibits containing sexual content or nudity, "
        "or internet links to such content. These must be submitted as physical exhibits."
    ),
    "discovery_not_for_mndes": (
        "Discovery documents (e.g., Alford Packets) should NOT be uploaded to MNDES "
        "unless a judicial officer specifically orders it."
    ),
    "motion_attachments_not_mndes": (
        "Documents filed with motions or affidavits should NOT go through MNDES. "
        "File those through the eFile and eServe (eFS) system with your pleading."
    ),
    "sealed_case": (
        "Exhibits in sealed cases cannot be uploaded directly. "
        "Contact court administration at 651-377-7180 to upload on your behalf."
    ),
    "certified_copy": (
        "Certified copies that authenticate an original must be submitted as physical exhibits, "
        "not uploaded to MNDES."
    ),
    "prehearing_not_public": (
        "Exhibits in pre-hearing status are NOT publicly accessible unless admitted "
        "as evidence in a public proceeding."
    ),
}
