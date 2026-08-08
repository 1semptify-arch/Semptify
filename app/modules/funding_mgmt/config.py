"""
Funding Management Module Configuration
"""

from dataclasses import dataclass


@dataclass
class FundingModuleConfig:
    """Configuration for the funding management module."""

    # Module settings
    module_name: str = "Funding Management"
    module_version: str = "1.0.0"

    # Access control
    required_role: str = "admin"  # Only admins can access

    # Default funding categories
    default_categories: list[str] = None

    # Application stages
    application_stages: list[str] = None

    def __post_init__(self):
        if self.default_categories is None:
            self.default_categories = [
                "Federal Grant",
                "Foundation Grant",
                "Corporate Sponsorship",
                "Individual Donor",
                "State/Local Grant",
                "In-Kind Contribution",
                "Other",
            ]

        if self.application_stages is None:
            self.application_stages = [
                "Prospect Identified",
                "Research Complete",
                "Application Draft",
                "Submitted",
                "Under Review",
                "Awarded",
                "Declined",
                "Withdrawn",
            ]
