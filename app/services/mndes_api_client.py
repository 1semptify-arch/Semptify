"""
MNDES API Client — Future Integration Hook
==========================================

CURRENT STATUS: No public API exists for MNDES (as of 2025).
MNDES is a web portal built by i3-ImageSoft LLC. Submission is manual.

This module defines the interface so that when (if) the Minnesota Judicial
Branch releases a programmatic API, the implementation can be swapped in
without changing any callers.

To enquire about API access, contact:
  MNDES External Application Support Team (EAST)
  Phone: 651-413-8160 (Twin Cities metro) | 1-833-707-2791 (other)
  Email: https://www.mncourts.gov/MNDES/Contact.aspx
  Hours: Mon–Fri 8:30am–4:15pm CT (excluding court holidays)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

MNDES_PORTAL_URL = "https://mndigitalexhibitsystem.courts.state.mn.us"
MNDES_DOCS_URL = "https://mndigitalexhibitsystem.courts.state.mn.us/docs/"
MNDES_SUPPORT_EMAIL_FORM = "https://www.mncourts.gov/MNDES/Contact.aspx"


# ============================================================================
# Data contracts (shared by all implementations)
# ============================================================================

@dataclass
class MNDESSubmissionResult:
    success: bool
    tracking_number: Optional[str] = None
    message: str = ""
    portal_url: str = MNDES_PORTAL_URL
    submitted_at: Optional[datetime] = None


@dataclass
class MNDESTrackingStatus:
    tracking_number: str
    status: str           # e.g. "pre_hearing", "offered", "admitted"
    case_number: str
    exhibit_name: Optional[str] = None
    last_updated: Optional[datetime] = None
    message: str = ""


@dataclass
class MNDESCaseExhibit:
    tracking_number: str
    exhibit_name: str
    file_type: str
    status: str
    uploaded_at: Optional[datetime] = None


# ============================================================================
# Abstract interface
# ============================================================================

class MNDESApiClient(ABC):
    """
    Abstract interface for MNDES exhibit submission.

    Implementations:
      - ManualPortalClient (current): returns instructions for manual upload
      - MNDESRestClient (future): direct API calls when MN courts release an API
    """

    @abstractmethod
    def submit_exhibit(
        self,
        case_number: str,
        file_content: bytes,
        filename: str,
        exhibit_name: str,
        exhibit_type: str,
    ) -> MNDESSubmissionResult:
        """Submit a single exhibit to MNDES for a case."""

    @abstractmethod
    def get_submission_status(
        self,
        tracking_number: str,
    ) -> MNDESTrackingStatus:
        """Get current status of a submitted exhibit."""

    @abstractmethod
    def get_case_exhibits(
        self,
        case_number: str,
    ) -> list[MNDESCaseExhibit]:
        """List exhibits for a given case number."""


# ============================================================================
# Current implementation: Manual portal guidance
# ============================================================================

class ManualPortalClient(MNDESApiClient):
    """
    No-API implementation.

    Returns step-by-step instructions for the user to submit manually
    via the MNDES web portal. All methods are safe to call — they return
    guidance, not errors.

    Replace with MNDESRestClient when a public API becomes available.
    """

    def submit_exhibit(
        self,
        case_number: str,
        file_content: bytes,
        filename: str,
        exhibit_name: str,
        exhibit_type: str,
    ) -> MNDESSubmissionResult:
        logger.info(
            "MNDES manual submission required for case %s, file %s",
            case_number, filename,
        )
        return MNDESSubmissionResult(
            success=False,
            tracking_number=None,
            message=(
                f"MNDES does not have a public API. "
                f"Please submit '{filename}' manually at: {MNDES_PORTAL_URL}\n"
                f"1. Log in (or register) at {MNDES_PORTAL_URL}\n"
                f"2. Search for case number: {case_number}\n"
                f"3. Click 'New Submission' and upload '{filename}'\n"
                f"4. Set exhibit name to: '{exhibit_name}'\n"
                f"5. Record the tracking number MNDES assigns back into Semptify"
            ),
            portal_url=MNDES_PORTAL_URL,
        )

    def get_submission_status(
        self,
        tracking_number: str,
    ) -> MNDESTrackingStatus:
        return MNDESTrackingStatus(
            tracking_number=tracking_number,
            status="unknown",
            case_number="",
            message=(
                f"MNDES does not have a public API. "
                f"Check status manually at: {MNDES_PORTAL_URL}"
            ),
        )

    def get_case_exhibits(
        self,
        case_number: str,
    ) -> list[MNDESCaseExhibit]:
        logger.debug("MNDES case exhibit lookup not available without API (case %s)", case_number)
        return []


# ============================================================================
# Future REST implementation (skeleton — fill in when API is available)
# ============================================================================

class MNDESRestClient(MNDESApiClient):
    """
    Future REST API client for MNDES.

    Activate when the MN Judicial Branch releases an API.
    Contact EAST team to obtain credentials and endpoint documentation.
    """

    def __init__(self, api_base_url: str, api_key: str) -> None:
        self._base = api_base_url.rstrip("/")
        self._api_key = api_key

    def submit_exhibit(
        self,
        case_number: str,
        file_content: bytes,
        filename: str,
        exhibit_name: str,
        exhibit_type: str,
    ) -> MNDESSubmissionResult:
        raise NotImplementedError(
            "MNDESRestClient.submit_exhibit: implement when API is available. "
            f"Contact EAST team: {MNDES_SUPPORT_EMAIL_FORM}"
        )

    def get_submission_status(
        self,
        tracking_number: str,
    ) -> MNDESTrackingStatus:
        raise NotImplementedError("MNDESRestClient.get_submission_status: not yet implemented")

    def get_case_exhibits(
        self,
        case_number: str,
    ) -> list[MNDESCaseExhibit]:
        raise NotImplementedError("MNDESRestClient.get_case_exhibits: not yet implemented")


# ============================================================================
# Active client (swap when API becomes available)
# ============================================================================

mndes_client: MNDESApiClient = ManualPortalClient()
