"""
Semptify Contracts & Waivers Framework
Version: 1.0.0
Purpose: Manage all legal contracts, waivers, and user agreements
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.core.utc import utc_now

logger = logging.getLogger(__name__)


class ContractType(str, Enum):
    """Types of contracts and agreements."""
    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    DATA_PROCESSING = "data_processing"
    AI_CONSENT = "ai_consent"
    THIRD_PARTY = "third_party_service"
    MOBILE_APP = "mobile_app_terms"
    PLUGIN_DEVELOPMENT = "plugin_development"
    USER_WAIVER = "user_waiver"
    ATTORNEY_CLIENT = "attorney_client_privilege"
    COURT_FILING = "court_filing_agreement"


class ContractStatus(str, Enum):
    """Status of contracts."""
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    SUSPENDED = "suspended"


class ConsentLevel(str, Enum):
    """Levels of user consent."""
    NONE = "none"
    IMPLIED = "implied"
    EXPRESS = "express"
    INFORMED = "informed"
    WRITTEN = "written"


class Contract(BaseModel):
    """Legal contract or agreement."""
    contract_id: str
    contract_type: ContractType
    title: str
    description: str
    content: str
    version: str
    status: ContractStatus
    effective_date: datetime
    expiration_date: datetime | None
    required_consent: ConsentLevel
    jurisdictions: list[str]
    dependencies: list[str]  # Other contracts this depends on
    created_at: datetime
    updated_at: datetime
    created_by: str


class UserConsent(BaseModel):
    """User consent record."""
    consent_id: str
    user_id: str
    contract_id: str
    consent_level: ConsentLevel
    consented_at: datetime
    ip_address: str | None
    user_agent: str | None
    withdrawn_at: datetime | None
    metadata: dict[str, Any]


class ContractsFramework:
    """Main contracts and waivers management system."""

    def __init__(self):
        self.contracts: dict[str, Contract] = {}
        self.user_consents: dict[str, list[UserConsent]] = {}
        self._initialize_default_contracts()

    def _initialize_default_contracts(self):
        """Initialize default contracts."""
        default_contracts = {
            "terms_2024_v1": Contract(
                contract_id="terms_2024_v1",
                contract_type=ContractType.TERMS_OF_SERVICE,
                title="Semptify Terms of Service",
                description="Terms governing use of Semptify housing rights platform",
                content=self._get_terms_of_service_content(),
                version="1.0",
                status=ContractStatus.ACTIVE,
                effective_date=datetime(2024, 1, 1, tzinfo=UTC),
                expiration_date=None,
                required_consent=ConsentLevel.EXPRESS,
                jurisdictions=["US", "CA", "EU"],
                dependencies=[],
                created_at=utc_now(),
                updated_at=utc_now(),
                created_by="system"
            ),
            "privacy_2024_v1": Contract(
                contract_id="privacy_2024_v1",
                contract_type=ContractType.PRIVACY_POLICY,
                title="Semptify Privacy Policy",
                description="How Semptify collects, uses, and protects user data",
                content=self._get_privacy_policy_content(),
                version="1.0",
                status=ContractStatus.ACTIVE,
                effective_date=datetime(2024, 1, 1, tzinfo=UTC),
                expiration_date=None,
                required_consent=ConsentLevel.EXPRESS,
                jurisdictions=["US", "CA", "EU"],
                dependencies=["terms_2024_v1"],
                created_at=utc_now(),
                updated_at=utc_now(),
                created_by="system"
            ),
            "ai_consent_2024_v1": Contract(
                contract_id="ai_consent_2024_v1",
                contract_type=ContractType.AI_CONSENT,
                title="AI Processing Consent",
                description="Consent for AI processing of documents and data",
                content=self._get_ai_consent_content(),
                version="1.0",
                status=ContractStatus.ACTIVE,
                effective_date=datetime(2024, 1, 1, tzinfo=UTC),
                expiration_date=None,
                required_consent=ConsentLevel.INFORMED,
                jurisdictions=["US", "CA", "EU"],
                dependencies=["privacy_2024_v1"],
                created_at=utc_now(),
                updated_at=utc_now(),
                created_by="system"
            ),
            "data_processing_2024_v1": Contract(
                contract_id="data_processing_2024_v1",
                contract_type=ContractType.DATA_PROCESSING,
                title="Data Processing Agreement",
                description="Agreement for processing of user data",
                content=self._get_data_processing_content(),
                version="1.0",
                status=ContractStatus.ACTIVE,
                effective_date=datetime(2024, 1, 1, tzinfo=UTC),
                expiration_date=None,
                required_consent=ConsentLevel.EXPRESS,
                jurisdictions=["US", "CA", "EU"],
                dependencies=["privacy_2024_v1"],
                created_at=utc_now(),
                updated_at=utc_now(),
                created_by="system"
            ),
            "mobile_app_2024_v1": Contract(
                contract_id="mobile_app_2024_v1",
                contract_type=ContractType.MOBILE_APP,
                title="Semptify Mobile App Terms",
                description="Terms specific to mobile application usage",
                content=self._get_mobile_app_content(),
                version="1.0",
                status=ContractStatus.DRAFT,
                effective_date=datetime(2024, 6, 1, tzinfo=UTC),
                expiration_date=None,
                required_consent=ConsentLevel.EXPRESS,
                jurisdictions=["US", "CA"],
                dependencies=["terms_2024_v1", "privacy_2024_v1"],
                created_at=utc_now(),
                updated_at=utc_now(),
                created_by="system"
            ),
            "plugin_dev_2024_v1": Contract(
                contract_id="plugin_dev_2024_v1",
                contract_type=ContractType.PLUGIN_DEVELOPMENT,
                title="Plugin Development Agreement",
                description="Terms for third-party plugin developers",
                content=self._get_plugin_dev_content(),
                version="1.0",
                status=ContractStatus.DRAFT,
                effective_date=datetime(2024, 6, 1, tzinfo=UTC),
                expiration_date=None,
                required_consent=ConsentLevel.WRITTEN,
                jurisdictions=["US", "CA", "EU"],
                dependencies=["terms_2024_v1"],
                created_at=utc_now(),
                updated_at=utc_now(),
                created_by="system"
            ),
        }

        self.contracts = default_contracts

    def get_contract(self, contract_id: str) -> Contract | None:
        """Get a contract by ID."""
        return self.contracts.get(contract_id)

    def get_contracts_by_type(self, contract_type: ContractType) -> list[Contract]:
        """Get all contracts of a specific type."""
        return [c for c in self.contracts.values() if c.contract_type == contract_type and c.status == ContractStatus.ACTIVE]

    def record_consent(self, user_id: str, contract_id: str, consent_level: ConsentLevel,
                      ip_address: str | None = None, user_agent: str | None = None,
                      metadata: dict[str, Any] | None = None) -> str:
        """Record user consent for a contract."""
        contract = self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")

        consent_id = f"{user_id}_{contract_id}_{utc_now().timestamp()}"

        consent = UserConsent(
            consent_id=consent_id,
            user_id=user_id,
            contract_id=contract_id,
            consent_level=consent_level,
            consented_at=utc_now(),
            ip_address=ip_address,
            user_agent=user_agent,
            withdrawn_at=None,
            metadata=metadata or {}
        )

        if user_id not in self.user_consents:
            self.user_consents[user_id] = []

        self.user_consents[user_id].append(consent)

        logger.info(f"Recorded consent for user {user_id} on contract {contract_id}")
        return consent_id

    def check_consent(self, user_id: str, contract_id: str) -> UserConsent | None:
        """Check if user has consented to a contract."""
        if user_id not in self.user_consents:
            return None

        user_consents = self.user_consents[user_id]
        for consent in user_consents:
            if consent.contract_id == contract_id and not consent.withdrawn_at:
                return consent

        return None

    def get_required_contracts(self, user_id: str) -> list[Contract]:
        """Get all contracts that require user consent."""
        required_contracts = []

        for contract in self.contracts.values():
            if contract.status == ContractStatus.ACTIVE:
                consent = self.check_consent(user_id, contract.contract_id)
                if not consent:
                    required_contracts.append(contract)

        return required_contracts

    def withdraw_consent(self, user_id: str, contract_id: str) -> bool:
        """Withdraw user consent for a contract."""
        if user_id not in self.user_consents:
            return False

        user_consents = self.user_consents[user_id]
        for consent in user_consents:
            if consent.contract_id == contract_id and not consent.withdrawn_at:
                consent.withdrawn_at = utc_now()
                logger.info(f"Withdrew consent for user {user_id} on contract {contract_id}")
                return True

        return False

    def get_user_consents(self, user_id: str) -> list[UserConsent]:
        """Get all consents for a user."""
        return self.user_consents.get(user_id, [])

    def _get_terms_of_service_content(self) -> str:
        """Get terms of service content."""
        return """
# Semptify Terms of Service

## 1. Acceptance of Terms
By accessing and using Semptify, you accept and agree to be bound by these terms.

## 2. Description of Service
Semptify is a housing rights platform that provides tools for tenants to organize documents, understand rights, and navigate housing issues.

## 3. User Responsibilities
- Provide accurate information
- Use the service for lawful purposes
- Respect other users' rights
- Maintain account security

## 4. Intellectual Property
All content and materials are owned by Semptify or licensed to us.

## 5. Limitation of Liability
Semptify provides information and tools but is not a law firm. Use does not create an attorney-client relationship.

## 6. Termination
We may terminate access for violations of these terms.

## 7. Changes to Terms
We reserve the right to modify these terms with notice.
        """.strip()

    def _get_privacy_policy_content(self) -> str:
        """Get privacy policy content."""
        return """
# Semptify Privacy Policy

## 1. Information We Collect
- Account information
- Document metadata (not content)
- Usage analytics
- Technical data

## 2. How We Use Information
- Provide services
- Improve platform
- Legal compliance
- Security

## 3. Data Storage
- Documents stored in your cloud storage
- Metadata stored securely
- Encryption in transit and at rest

## 4. Data Sharing
- We do not sell your data
- Limited sharing with service providers
- Legal compliance when required

## 5. Your Rights
- Access your data
- Correct inaccuracies
- Delete your account
- Export your data

## 6. Security
- Industry-standard encryption
- Regular security audits
- Limited access controls
        """.strip()

    def _get_ai_consent_content(self) -> str:
        """Get AI consent content."""
        return """
# AI Processing Consent

## 1. AI Services
Semptify uses AI to:
- Classify documents
- Extract key information
- Provide legal insights
- Detect duplicates

## 2. Data Processing
- AI processes document metadata only
- No personal content shared with third parties
- Processing occurs in secure environments

## 3. Accuracy
- AI results are for assistance only
- Not legal advice
- Human review recommended

## 4. Opt-Out
You can disable AI processing at any time
- Manual classification available
- No impact on core services

## 5. Data Retention
- AI processing logs retained 30 days
- No training on your data without consent
        """.strip()

    def _get_data_processing_content(self) -> str:
        """Get data processing agreement content."""
        return """
# Data Processing Agreement

## 1. Data Controller
Semptify acts as data controller for your information.

## 2. Processing Purposes
- Document organization
- Legal information provision
- Service improvement
- Legal compliance

## 3. Legal Basis
- User consent
- Contract necessity
- Legal obligation
- Legitimate interest

## 4. Data Subjects' Rights
- Right to information
- Right to access
- Right to rectification
- Right to erasure
- Right to portability
- Right to object

## 5. Security Measures
- Technical safeguards
- Organizational controls
- Regular assessments
- Breach notification
        """.strip()

    def _get_mobile_app_content(self) -> str:
        """Get mobile app terms content."""
        return """
# Semptify Mobile App Terms

## 1. Additional Terms
These terms supplement the main Terms of Service.

## 2. Mobile Features
- Document scanning
- Offline access
- Push notifications
- Location services

## 3. Device Permissions
- Camera for document scanning
- Storage for offline access
- Notifications for updates
- Location for jurisdiction detection

## 4. Data Usage
- Minimal data collection
- Offline-first design
- Optional cloud sync
- No tracking without consent

## 5. App Store Terms
Subject to additional terms from app stores.
        """.strip()

    def _get_plugin_dev_content(self) -> str:
        """Get plugin development agreement content."""
        return """
# Plugin Development Agreement

## 1. Plugin Guidelines
- Must not violate user privacy
- Must comply with housing laws
- No deceptive practices
- Proper attribution required

## 2. Technical Requirements
- Use provided APIs
- Follow security standards
- Handle errors gracefully
- No unauthorized data access

## 3. Content Standards
- Accurate legal information
- No harmful content
- Proper disclaimers
- User transparency

## 4. Commercial Terms
- Free plugins allowed
- Commercial plugins require approval
- Revenue sharing for premium features
- No user data monetization

## 5. Liability
- Developer responsible for plugin content
- Semptify not liable for plugin errors
- Users assume risk
        """.strip()


# Global instance
contracts_framework = ContractsFramework()
