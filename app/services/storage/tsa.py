"""
RFC 3161 Trusted Timestamping Client

Provides court-admissible third-party timestamps by sending document hashes
to an external Time Stamp Authority (TSA). The TSA countersigns the hash with
their private key and returns a timestamp token (.tsr) that:

  - Proves the document existed at or before a specific time
  - Is independently verifiable by anyone using the TSA's public certificate
  - Cannot be backdated — not by us, not by anyone
  - Survives Semptify shutting down (the proof is standalone)

Legal basis:
  - RFC 3161 (Internet X.509 PKI Time-Stamp Protocol)
  - Federal Rules of Evidence 901(b)(9) — self-authenticating electronic records
  - ESIGN Act / UETA — electronic timestamps as valid evidence

Fallback:
  If the TSA is unreachable (network down, dev environment, TSA outage),
  we fall back to HMAC-SHA256 self-signed timestamp and log a warning.
  The fallback is clearly marked in the stored proof so it can be
  distinguished from a proper TSA-backed timestamp.

Usage:
    from app.services.storage.tsa import stamp_document_hash, verify_tsa_token

    result = await stamp_document_hash(document_hash)
    if result.tsa_backed:
        # Court-grade — independently verifiable
        store(result.token_b64)
    else:
        # HMAC fallback — self-signed
        store(result.token_b64)
"""

import base64
import hashlib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_TSA_TIMEOUT_SECONDS = 10


@dataclass
class TSAResult:
    """
    Result of a timestamp operation.

    tsa_backed=True  ▸ token_b64 is a base64-encoded RFC 3161 .tsr file.
                        Verify with: openssl ts -verify -in token.tsr -data <file>
    tsa_backed=False ▸ token_b64 is a base64-encoded HMAC-SHA256 fallback.
                        Self-signed — weaker legal standing.
    """
    timestamp_iso: str        # UTC ISO 8601 timestamp used in the request
    document_hash: str        # SHA-256 hex of the document
    token_b64: str            # Base64-encoded token (TSA .tsr or HMAC fallback)
    tsa_backed: bool          # True = RFC 3161, False = HMAC fallback
    tsa_url: str | None    # TSA URL used (None for fallback)
    error: str | None      # Set if fallback was triggered and why


def _build_tsr_request(hash_bytes: bytes) -> bytes:
    """
    Build a minimal RFC 3161 TimeStampReq DER-encoded request.

    We build this manually to avoid a hard dependency on a full ASN.1 library
    at import time. The request asks the TSA to stamp a SHA-256 hash.

    Structure (DER):
        TimeStampReq ::= SEQUENCE {
            version         INTEGER { v1(1) },
            messageImprint  MessageImprint,
            nonce           INTEGER  (optional, added for replay protection),
            certReq         BOOLEAN DEFAULT FALSE
        }
        MessageImprint ::= SEQUENCE {
            hashAlgorithm   AlgorithmIdentifier,
            hashedMessage   OCTET STRING
        }
    """
    import secrets as _secrets

    def der_length(n: int) -> bytes:
        if n < 0x80:
            return bytes([n])
        elif n < 0x100:
            return bytes([0x81, n])
        else:
            return bytes([0x82, (n >> 8) & 0xFF, n & 0xFF])

    def der_tlv(tag: int, value: bytes) -> bytes:
        return bytes([tag]) + der_length(len(value)) + value

    def der_integer(n: int) -> bytes:
        if n == 0:
            return der_tlv(0x02, b'\x00')
        result = []
        while n > 0:
            result.append(n & 0xFF)
            n >>= 8
        result.reverse()
        if result[0] & 0x80:
            result.insert(0, 0x00)
        return der_tlv(0x02, bytes(result))

    # SHA-256 OID: 2.16.840.1.101.3.4.2.1
    sha256_oid = bytes([
        0x30, 0x0d,                         # SEQUENCE (13 bytes)
        0x06, 0x09,                         # OID (9 bytes)
        0x60, 0x86, 0x48, 0x01, 0x65,       # 2.16.840.1.101.3.4.2.1
        0x03, 0x04, 0x02, 0x01,
        0x05, 0x00                          # NULL parameters
    ])

    hashed_message = der_tlv(0x04, hash_bytes)          # OCTET STRING
    message_imprint = der_tlv(0x30, sha256_oid + hashed_message)  # SEQUENCE

    version = der_integer(1)                             # version v1

    nonce_bytes = _secrets.token_bytes(8)
    nonce_int = int.from_bytes(nonce_bytes, 'big')
    nonce = der_integer(nonce_int)

    cert_req = bytes([0x01, 0x01, 0xff])                 # BOOLEAN TRUE

    request_body = version + message_imprint + nonce + cert_req
    return der_tlv(0x30, request_body)                   # outer SEQUENCE


async def stamp_document_hash(
    document_hash: str,
    timestamp_iso: str,
    tsa_url: str | None = None,
) -> TSAResult:
    """
    Send a SHA-256 document hash to a TSA and get back a signed timestamp token.

    Args:
        document_hash: Hex SHA-256 of the document content
        timestamp_iso: UTC ISO timestamp string (already computed by caller)
        tsa_url:       TSA endpoint. Defaults to settings.tsa_url (FreeTSA).

    Returns:
        TSAResult with tsa_backed=True on success, or HMAC fallback on failure.
    """
    from app.core.config import get_settings
    settings = get_settings()

    url = tsa_url or settings.tsa_url
    if not url:
        return _hmac_fallback(document_hash, timestamp_iso, reason="TSA_URL not configured")

    try:
        import httpx

        hash_bytes = bytes.fromhex(document_hash)
        tsr_request = _build_tsr_request(hash_bytes)

        async with httpx.AsyncClient(timeout=_TSA_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                content=tsr_request,
                headers={
                    "Content-Type": "application/timestamp-query",
                    "Accept": "application/timestamp-reply",
                },
            )

        if response.status_code != 200:
            raise ValueError(f"TSA returned HTTP {response.status_code}")

        tsr_bytes = response.content
        if len(tsr_bytes) < 10:
            raise ValueError("TSA response too short — likely an error page")

        token_b64 = base64.b64encode(tsr_bytes).decode()

        logger.info(
            "RFC 3161 timestamp obtained from %s for hash %s...",
            url, document_hash[:16]
        )

        return TSAResult(
            timestamp_iso=timestamp_iso,
            document_hash=document_hash,
            token_b64=token_b64,
            tsa_backed=True,
            tsa_url=url,
            error=None,
        )

    except Exception as exc:
        logger.warning(
            "TSA request to %s failed (%s) — using HMAC fallback. "
            "This timestamp will have weaker legal standing.",
            url, exc,
        )
        return _hmac_fallback(document_hash, timestamp_iso, reason=str(exc))


def _hmac_fallback(document_hash: str, timestamp_iso: str, reason: str) -> TSAResult:
    """
    HMAC-SHA256 self-signed fallback when TSA is unreachable.
    Clearly marked so it can be distinguished from a real TSA token.
    """
    import hmac as _hmac

    from app.core.config import get_settings
    secret = get_settings().secret_key

    combined = f"HMAC-FALLBACK:{timestamp_iso}:{document_hash}:{secret}"
    hmac_hex = _hmac.new(secret.encode(), combined.encode(), hashlib.sha256).hexdigest()

    fallback_payload = {
        "type": "hmac_fallback",
        "reason": reason,
        "timestamp": timestamp_iso,
        "document_hash": document_hash,
        "hmac": hmac_hex,
    }
    import json
    token_b64 = base64.b64encode(json.dumps(fallback_payload).encode()).decode()

    return TSAResult(
        timestamp_iso=timestamp_iso,
        document_hash=document_hash,
        token_b64=token_b64,
        tsa_backed=False,
        tsa_url=None,
        error=reason,
    )


def verify_tsa_token(token_b64: str, document_hash: str) -> dict:
    """
    Verify a stored TSA token against a document hash.

    For TSA-backed tokens: validates the DER structure and confirms the
    hash matches (full cryptographic verification requires the TSA's cert
    bundle which is available from the TSA's website).

    For HMAC fallback tokens: re-derives the HMAC and compares.

    Returns a dict with:
        verified: bool
        method:   "rfc3161" | "hmac_fallback"
        detail:   human-readable explanation
    """
    import hmac as _hmac
    import json

    try:
        raw = base64.b64decode(token_b64)
    except Exception as exc:
        return {"verified": False, "method": "unknown", "detail": f"Base64 decode failed: {exc}"}

    # Check if it's JSON (HMAC fallback) or DER (TSA)
    try:
        payload = json.loads(raw.decode())
        if payload.get("type") == "hmac_fallback":
            from app.core.config import get_settings
            secret = get_settings().secret_key
            ts = payload["timestamp"]
            dh = payload["document_hash"]
            combined = f"HMAC-FALLBACK:{ts}:{dh}:{secret}"
            expected = _hmac.new(secret.encode(), combined.encode(), hashlib.sha256).hexdigest()
            ok = _hmac.compare_digest(expected, payload.get("hmac", ""))
            return {
                "verified": ok,
                "method": "hmac_fallback",
                "detail": (
                    "HMAC-SHA256 self-signed timestamp. "
                    "Tamper-evident but not independently verifiable by third parties. "
                    "Reason TSA was unavailable: " + payload.get("reason", "unknown")
                ) if ok else "HMAC verification failed — token may be tampered.",
            }
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Payload is not JSON, try DER binary format below
        pass

    # DER binary — RFC 3161 token
    # Basic structural check: must start with SEQUENCE tag (0x30)
    if raw[0] != 0x30:
        return {"verified": False, "method": "rfc3161", "detail": "Invalid DER structure"}

    hash_bytes = bytes.fromhex(document_hash)
    token_contains_hash = hash_bytes in raw

    return {
        "verified": token_contains_hash,
        "method": "rfc3161",
        "detail": (
            "RFC 3161 token — independently verifiable using TSA public certificate. "
            "Full cryptographic verification: openssl ts -verify -in token.tsr -data <document>"
        ) if token_contains_hash else
            "Document hash not found in TSA token — possible mismatch or corruption.",
    }
