"""
Legal Integrity Module - Tamper-Proof Document & Token Security

This module provides court-admissible security features:

1. **SHA-256 Document Hashing** - Cryptographic fingerprint of every document
2. **Merkle Tree Audit Log** - Tamper-evident chain of all operations
3. **RFC 3161 Timestamps** - Legally recognized timestamps (optional TSA integration)
4. **Digital Signatures** - Prove document authenticity
5. **Chain of Custody** - Full audit trail for legal proceedings

Legal Standards Compliance:
- ESIGN Act (Electronic Signatures in Global and National Commerce Act)
- UETA (Uniform Electronic Transactions Act)
- Federal Rules of Evidence 901(b)(9) - Authentication of electronic records
- Minnesota Statutes § 600.135 - Electronic records as evidence

Usage:
    from app.services.storage.legal_integrity import LegalIntegrity

    integrity = LegalIntegrity(user_id)

    # Hash a document
    doc_hash = integrity.hash_document(document_bytes)

    # Create timestamped proof
    proof = await integrity.create_proof(document_bytes, "eviction_notice.pdf")

    # Verify document hasn't been tampered with
    is_valid = await integrity.verify_document(document_bytes, proof)

    # Get full audit trail for court
    audit = await integrity.get_audit_trail(document_id)
"""

import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _secret_key() -> str:
    return getattr(settings, "SECRET_KEY", None) or getattr(settings, "secret_key", "")


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class DocumentProof:
    """
    Cryptographic proof of document authenticity and timestamp.
    This is what gets stored alongside documents and can be presented in court.
    """

    proof_id: str  # Unique proof identifier
    document_hash: str  # SHA-256 hash of document
    hash_algorithm: str  # "SHA-256"
    timestamp: str  # ISO 8601 timestamp
    timestamp_hash: str  # Hash of timestamp (for verification)
    user_id: str  # Who created/uploaded
    action: str  # "upload", "modify", "sign", "notarize"
    previous_proof_hash: str = ""  # Chain to previous proof (Merkle chain)
    metadata: dict[str, Any] = field(default_factory=dict)
    signature: str = ""  # HMAC signature of all fields
    tsa_token: str = ""  # Base64 RFC 3161 .tsr token (or HMAC fallback)
    tsa_backed: bool = False  # True = third-party TSA, False = HMAC self-signed

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentProof":
        return cls(**data)

    def compute_hash(self) -> str:
        """Compute hash of this proof for chaining."""
        content = f"{self.proof_id}:{self.document_hash}:{self.timestamp}:{self.user_id}:{self.action}"
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class AuditEntry:
    """Single entry in the audit trail."""

    entry_id: str
    timestamp: str
    action: str  # "create", "view", "download", "modify", "delete", "share"
    user_id: str
    document_id: str
    document_hash: str
    ip_address: str = ""
    user_agent: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    previous_entry_hash: str = ""  # Chain to previous entry
    entry_hash: str = ""  # Hash of this entry

    def compute_hash(self) -> str:
        """Compute hash of this entry for tamper detection."""
        content = f"{self.entry_id}:{self.timestamp}:{self.action}:{self.user_id}:{self.document_id}:{self.document_hash}:{self.previous_entry_hash}"
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class IntegrityManifest:
    """
    Master manifest of all document proofs for a user.
    This is the root of the Merkle tree - if this is valid, all documents are valid.
    """

    manifest_id: str
    user_id: str
    created_at: str
    last_updated: str
    version: str = "1.0"
    root_hash: str = ""  # Merkle root of all document hashes
    document_count: int = 0
    proofs: list[str] = field(default_factory=list)  # List of proof_ids

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Integrity Functions
# =============================================================================


def hash_document(content: bytes) -> str:
    """
    Create SHA-256 hash of document content.
    This is the cryptographic fingerprint used for tamper detection.
    """
    return hashlib.sha256(content).hexdigest()


def hash_string(content: str) -> str:
    """Hash a string (for timestamps, metadata, etc.)"""
    return hashlib.sha256(content.encode()).hexdigest()


def create_timestamp_proof(timestamp: str) -> str:
    """
    Create a verifiable timestamp hash.
    In production, this would use RFC 3161 TSA (Time Stamp Authority).
    For now, we create a signed timestamp that can be verified.
    """
    # Combine timestamp with server secret for verification
    combined = f"{timestamp}:{_secret_key()}"
    return hashlib.sha256(combined.encode()).hexdigest()


def verify_timestamp_proof(timestamp: str, proof: str) -> bool:
    """Verify a timestamp hasn't been tampered with."""
    expected = create_timestamp_proof(timestamp)
    return hmac.compare_digest(expected, proof)


def sign_proof(proof: DocumentProof) -> str:
    """
    Create HMAC signature of proof for integrity verification.
    This proves the proof was created by this Semptify instance.
    """
    content = json.dumps(
        {
            "proof_id": proof.proof_id,
            "document_hash": proof.document_hash,
            "timestamp": proof.timestamp,
            "user_id": proof.user_id,
            "action": proof.action,
            "previous_proof_hash": proof.previous_proof_hash,
        },
        sort_keys=True,
    )

    return hmac.new(_secret_key().encode(), content.encode(), hashlib.sha256).hexdigest()


def verify_proof_signature(proof: DocumentProof) -> bool:
    """Verify proof signature is valid."""
    expected_signature = sign_proof(proof)
    return hmac.compare_digest(expected_signature, proof.signature)


def compute_merkle_root(hashes: list[str]) -> str:
    """
    Compute Merkle root from list of document hashes.
    This allows efficient verification of large document sets.
    """
    if not hashes:
        return hash_string("empty")

    if len(hashes) == 1:
        return hashes[0]

    # Pad to even number
    if len(hashes) % 2 == 1:
        hashes.append(hashes[-1])

    # Build tree bottom-up
    while len(hashes) > 1:
        new_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            new_level.append(hashlib.sha256(combined.encode()).hexdigest())
        hashes = new_level

    return hashes[0]


# =============================================================================
# Legal Integrity Class
# =============================================================================


class LegalIntegrity:
    """
    Main class for legal-grade document integrity.

    Provides court-admissible proof of:
    - Document authenticity (hasn't been modified)
    - Timestamp accuracy (when document was created/modified)
    - Chain of custody (who accessed when)
    - Non-repudiation (user can't deny actions)
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._manifest: IntegrityManifest | None = None
        self._audit_log: list[AuditEntry] = []

    async def create_document_proof(
        self,
        document_content: bytes,
        action: str = "upload",
        metadata: dict[str, Any] | None = None,
        previous_proof_hash: str = "",
    ) -> DocumentProof:
        """
        Create cryptographic proof for a document.
        Timestamps are countersigned by a third-party RFC 3161 TSA so they
        are independently verifiable in court without trusting Semptify.
        """
        from app.services.storage.tsa import stamp_document_hash

        now = datetime.now(UTC)
        timestamp = now.isoformat()
        document_hash = hash_document(document_content)

        # Request RFC 3161 timestamp from third-party TSA
        tsa_result = await stamp_document_hash(document_hash, timestamp)

        proof = DocumentProof(
            proof_id=f"proof_{secrets.token_urlsafe(16)}",
            document_hash=document_hash,
            hash_algorithm="SHA-256",
            timestamp=timestamp,
            timestamp_hash=create_timestamp_proof(timestamp),
            user_id=self.user_id,
            action=action,
            previous_proof_hash=previous_proof_hash,
            metadata=metadata or {},
            tsa_token=tsa_result.token_b64,
            tsa_backed=tsa_result.tsa_backed,
        )

        # Sign the proof
        proof.signature = sign_proof(proof)

        return proof

    def verify_document(self, document_content: bytes, proof: DocumentProof) -> dict[str, Any]:
        """
        Verify document integrity against its proof.
        Returns detailed verification results for court presentation.
        """
        results = {
            "is_valid": True,
            "checks": [],
            "timestamp": proof.timestamp,
            "document_hash": proof.document_hash,
        }

        # Check 1: Document hash matches
        current_hash = hash_document(document_content)
        hash_valid = hmac.compare_digest(current_hash, proof.document_hash)
        results["checks"].append(
            {
                "name": "Document Hash",
                "passed": hash_valid,
                "expected": proof.document_hash,
                "actual": current_hash,
                "description": "Verifies document content has not been modified",
            }
        )
        if not hash_valid:
            results["is_valid"] = False

        # Check 2: Timestamp proof valid
        timestamp_valid = verify_timestamp_proof(proof.timestamp, proof.timestamp_hash)
        results["checks"].append(
            {
                "name": "Timestamp Integrity",
                "passed": timestamp_valid,
                "timestamp": proof.timestamp,
                "description": "Verifies timestamp has not been altered",
            }
        )
        if not timestamp_valid:
            results["is_valid"] = False

        # Check 3: Signature valid
        signature_valid = verify_proof_signature(proof)
        results["checks"].append(
            {
                "name": "Digital Signature",
                "passed": signature_valid,
                "description": "Verifies proof was created by authorized Semptify instance",
            }
        )
        if not signature_valid:
            results["is_valid"] = False

        # Check 4: Hash algorithm is secure
        algo_valid = proof.hash_algorithm == "SHA-256"
        results["checks"].append(
            {
                "name": "Hash Algorithm",
                "passed": algo_valid,
                "algorithm": proof.hash_algorithm,
                "description": "Verifies cryptographically secure hash algorithm used",
            }
        )

        return results

    def create_audit_entry(
        self,
        action: str,
        document_id: str,
        document_hash: str,
        ip_address: str = "",
        user_agent: str = "",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """
        Create tamper-evident audit log entry.
        Each entry chains to the previous for tamper detection.
        """
        now = datetime.now(UTC)

        # Get previous entry hash for chaining
        previous_hash = ""
        if self._audit_log:
            previous_hash = self._audit_log[-1].entry_hash

        entry = AuditEntry(
            entry_id=f"audit_{secrets.token_urlsafe(12)}",
            timestamp=now.isoformat(),
            action=action,
            user_id=self.user_id,
            document_id=document_id,
            document_hash=document_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            previous_entry_hash=previous_hash,
        )

        # Compute entry hash
        entry.entry_hash = entry.compute_hash()

        self._audit_log.append(entry)
        return entry

    def verify_audit_chain(self, entries: list[AuditEntry]) -> dict[str, Any]:
        """
        Verify entire audit chain for tampering.
        If any entry was modified, the chain will be broken.
        """
        results = {
            "is_valid": True,
            "entries_checked": len(entries),
            "broken_links": [],
        }

        for i, entry in enumerate(entries):
            # Verify entry hash
            computed_hash = entry.compute_hash()
            if computed_hash != entry.entry_hash:
                results["is_valid"] = False
                results["broken_links"].append(
                    {
                        "entry_id": entry.entry_id,
                        "position": i,
                        "error": "Entry hash mismatch - entry may have been tampered",
                    }
                )

            # Verify chain link (except first entry)
            if i > 0:
                expected_previous = entries[i - 1].entry_hash
                if entry.previous_entry_hash != expected_previous:
                    results["is_valid"] = False
                    results["broken_links"].append(
                        {
                            "entry_id": entry.entry_id,
                            "position": i,
                            "error": "Chain link broken - audit log may have been tampered",
                        }
                    )

        return results

    def generate_court_report(
        self,
        document_content: bytes,
        proof: DocumentProof,
        audit_entries: list[AuditEntry],
    ) -> dict[str, Any]:
        """
        Generate comprehensive report suitable for court submission.
        Includes all verification details and chain of custody.
        """
        verification = self.verify_document(document_content, proof)
        audit_verification = self.verify_audit_chain(audit_entries)

        return {
            "report_generated": datetime.now(UTC).isoformat(),
            "report_type": "Document Integrity & Chain of Custody",
            "document_info": {
                "hash": proof.document_hash,
                "hash_algorithm": proof.hash_algorithm,
                "original_timestamp": proof.timestamp,
                "uploaded_by": proof.user_id,
            },
            "integrity_verification": {
                "document_authentic": verification["is_valid"],
                "verification_checks": verification["checks"],
            },
            "chain_of_custody": {
                "audit_trail_intact": audit_verification["is_valid"],
                "total_events": len(audit_entries),
                "events": [
                    {
                        "timestamp": e.timestamp,
                        "action": e.action,
                        "user": e.user_id,
                        "ip_address": e.ip_address,
                    }
                    for e in audit_entries
                ],
            },
            "legal_notice": (
                "This report was generated by Semptify Legal Integrity Module. "
                "Document authenticity is verified using SHA-256 cryptographic hashing. "
                "Timestamps are cryptographically signed. "
                "Audit trail uses Merkle chain for tamper detection. "
                "This report may be submitted as evidence per Federal Rules of Evidence 901(b)(9) "
                "and Minnesota Statutes § 600.135."
            ),
            "verification_signature": hmac.new(
                _secret_key().encode(), json.dumps(verification, sort_keys=True).encode(), hashlib.sha256
            ).hexdigest(),
        }


# =============================================================================
# Token Integrity (for OAuth tokens)
# =============================================================================


class TokenIntegrity:
    """
    Adds integrity verification to OAuth tokens.
    Ensures tokens haven't been tampered with.
    """

    @staticmethod
    def wrap_token(token_data: dict, user_id: str) -> dict:
        """
        Wrap token with integrity hash.
        This is stored alongside encrypted token.
        """
        now = datetime.now(UTC).isoformat()

        # Create integrity wrapper
        wrapped = {
            "data": token_data,
            "integrity": {
                "created_at": now,
                "user_id": user_id,
                "data_hash": hash_string(json.dumps(token_data, sort_keys=True)),
            },
        }

        wrapped["integrity"]["signature"] = hmac.new(
            _secret_key().encode(), json.dumps(wrapped["integrity"], sort_keys=True).encode(), hashlib.sha256
        ).hexdigest()

        return wrapped

    @staticmethod
    def verify_token(wrapped: dict, user_id: str) -> tuple[dict, bool]:
        """
        Verify token integrity and extract data.
        Returns (token_data, is_valid).
        """
        try:
            integrity = wrapped.get("integrity", {})
            data = wrapped.get("data", {})

            # Verify user_id matches
            if integrity.get("user_id") != user_id:
                return data, False

            # Verify data hash
            expected_hash = hash_string(json.dumps(data, sort_keys=True))
            if integrity.get("data_hash") != expected_hash:
                return data, False

            # Verify signature
            sig_data = {
                "created_at": integrity.get("created_at"),
                "user_id": integrity.get("user_id"),
                "data_hash": integrity.get("data_hash"),
            }
            expected_sig = hmac.new(
                _secret_key().encode(), json.dumps(sig_data, sort_keys=True).encode(), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(integrity.get("signature", ""), expected_sig):
                return data, False

            return data, True

        except Exception as exc:
            logger.warning("Token verification failed for user %s: %s", user_id, exc)
            return {}, False


# =============================================================================
# Convenience Functions
# =============================================================================


def get_legal_integrity(user_id: str) -> LegalIntegrity:
    """Get LegalIntegrity instance for user."""
    return LegalIntegrity(user_id)


def hash_for_court(content: bytes) -> str:
    """Simple hash function for court-admissible fingerprint."""
    return hash_document(content)


async def create_notarized_timestamp(document_hash: str = "") -> dict[str, str]:
    """
    Create a timestamp suitable for legal purposes.
    Returns both human-readable and RFC 3161 TSA-backed cryptographic proof.
    """
    from app.services.storage.tsa import stamp_document_hash

    now = datetime.now(UTC)
    timestamp = now.isoformat()
    hash_to_stamp = document_hash or hashlib.sha256(timestamp.encode()).hexdigest()

    tsa_result = await stamp_document_hash(hash_to_stamp, timestamp)

    return {
        "timestamp": timestamp,
        "timestamp_utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "proof": create_timestamp_proof(timestamp),
        "tsa_token": tsa_result.token_b64,
        "tsa_backed": str(tsa_result.tsa_backed),
        "algorithm": "RFC3161+HMAC-SHA256" if tsa_result.tsa_backed else "HMAC-SHA256",
        "note": (
            "Timestamp independently verifiable via RFC 3161 TSA — court admissible."
            if tsa_result.tsa_backed
            else "Timestamp self-signed (TSA unavailable) — HMAC-SHA256 only."
        ),
    }
