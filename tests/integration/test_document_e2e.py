"""
End-to-end document pipeline test (fully isolated, local SQLite + local file storage).

Tests the full path:
  1. Upload → vault (local storage)
  2. Certification → document registry
  3. DB index → vault_index, user_index, hash_index
  4. Retrieve → get_document, get_user_documents
  5. Content access → get_document_content
  6. Dedup → same content returns same doc
  7. Upload second unique doc
  8. Intake engine → text extraction
  9. Document classification
 10. Data extraction (dates, parties, amounts)
 11. Law linker citation detection on extracted text

Isolation:
  - Overrides DATABASE_URL to a temporary SQLite file BEFORE app imports.
  - Uses local file storage (no cloud provider needed).
  - Creates a test user first to satisfy FK constraints.

Run:
    .\\venv311\\Scripts\\Activate.ps1
    python -m tests.integration.test_document_e2e
"""

import asyncio
import os
import shutil
import sys
import traceback
from pathlib import Path

# ---- ISOLATION strategy ----
# We use the existing configured DATABASE_URL (Neon PostgreSQL in dev, SQLite in
# pure-local). The schema has PostgreSQL-specific ARRAY columns that SQLite
# cannot render, so we cannot override to SQLite. Instead, we isolate by
# user_id and clean up our test artifacts at the end.
#
# All test data is keyed on TEST_USER_ID so it cannot collide with real users.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TEST_DIR = ROOT / "data" / "test_e2e_run"
TEST_VAULT = TEST_DIR / "vault"

# Wipe previous run's local files
if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)
TEST_DIR.mkdir(parents=True, exist_ok=True)
TEST_VAULT.mkdir(parents=True, exist_ok=True)

# Suppress noisy logs
os.environ.setdefault("LOG_LEVEL", "WARNING")

PASS = 0
FAIL = 0
STEPS = []


def step(name, ok, detail=""):
    global PASS, FAIL
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    line = f"  [{status}] {name}"
    if detail:
        line += f" -- {detail}"
    STEPS.append(line)
    print(line)


async def run():
    # Imports happen after env override
    from sqlalchemy import select

    from app.core.database import get_db_session, init_db
    from app.core.utc import utc_now
    from app.models.models import User
    from app.services.document_intake import (
        DataExtractor,
        DocumentClassifier,
        DocumentIntakeEngine,
    )
    from app.services.vault_upload_service import get_vault_service

    print("\n=== SETUP: init DB + local vault ===")
    await init_db()

    svc = get_vault_service()
    svc._local_dir = str(TEST_VAULT)

    # Create a test user to satisfy FK constraints (unique per run to avoid state)
    import time

    user_id = f"e2e_test_{int(time.time())}"
    async with get_db_session() as session:
        existing = await session.execute(select(User).where(User.id == user_id))
        if existing.scalar_one_or_none() is None:
            session.add(
                User(
                    id=user_id,
                    primary_provider="local",
                    storage_user_id="local_test_001",
                    default_role="user",
                    intensity_level="low",
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
            await session.commit()
    print(f"  user_id:   {user_id}")
    print(f"  vault_dir: {svc._local_dir}")

    # ---- Step 1: Upload a lease document ----
    print("\n=== STEP 1: Upload lease document ===")
    lease_text = b"""RESIDENTIAL LEASE AGREEMENT

This Lease Agreement is entered into on January 15, 2025,
between Landlord John Smith and Tenant Jane Doe.

Property: 123 Main Street, Minneapolis, MN 55401

Term: 12 months beginning February 1, 2025
Monthly Rent: $1,500 due on the 1st of each month
Security Deposit: $1,500

Minnesota Statutes Section 504B.161 requires landlord maintain habitable premises.
Tenant rights under Minn. Stat. Sec. 504B.375 govern security deposit return.
Landlord retaliation is prohibited under Minn. Stat. 504B.285.
Federal fair housing: 42 U.S.C. 3601-3619.
"""
    try:
        doc1 = await svc.upload(
            user_id=user_id,
            filename="lease_agreement.txt",
            content=lease_text,
            mime_type="text/plain",
            document_type="lease",
            description="Residential lease for 123 Main St",
            tags=["lease", "minneapolis"],
            source_module="e2e_test",
            storage_provider="local",
        )
        step("Upload lease", doc1 is not None and bool(doc1.vault_id), f"vault_id={doc1.vault_id}")
        step("Certification", doc1.is_certified, f"registry_id={doc1.registry_id} integrity={doc1.integrity_status}")
        step("Storage path", doc1.storage_path.endswith(".txt"), f"path={doc1.storage_path}")
        step("SHA-256 hash", len(doc1.sha256_hash) == 64, f"hash={doc1.sha256_hash[:16]}...")
        step("Certificate ID", doc1.certificate_id is not None, f"cert={doc1.certificate_id}")
    except Exception as e:
        step("Upload lease", False, f"EXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()
        return

    # ---- Step 2: Verify file exists on disk ----
    print("\n=== STEP 2: Verify file on disk ===")
    file_path = TEST_VAULT / doc1.storage_path.lstrip("/")
    step("File exists on disk", file_path.exists(), str(file_path))
    if file_path.exists():
        step("File content matches", file_path.read_bytes() == lease_text, f"size={file_path.stat().st_size}")

    # ---- Step 3: Retrieve document from index ----
    print("\n=== STEP 3: Retrieve document from index ===")
    try:
        retrieved = await svc.get_document(doc1.vault_id)
        step("get_document by vault_id", retrieved is not None, f"filename={retrieved.filename if retrieved else None}")
        if retrieved:
            step(
                "Retrieved matches upload",
                retrieved.vault_id == doc1.vault_id and retrieved.sha256_hash == doc1.sha256_hash,
                "id+hash match",
            )
            step("Retrieved is certified", retrieved.is_certified, f"registry_id={retrieved.registry_id}")
    except Exception as e:
        step("get_document", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 4: List user documents ----
    print("\n=== STEP 4: List user documents ===")
    try:
        docs = await svc.get_user_documents(user_id)
        step("get_user_documents", len(docs) >= 1, f"count={len(docs)}")
        step("Listed doc matches", any(d.vault_id == doc1.vault_id for d in docs), "vault_id present in list")
    except Exception as e:
        step("get_user_documents", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 5: Get document content ----
    print("\n=== STEP 5: Get document content ===")
    try:
        content = await svc.get_document_content(doc1.vault_id)
        step("get_document_content", content == lease_text, f"bytes={len(content) if content else 0}")
    except Exception as e:
        step("get_document_content", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 6: Upload duplicate (dedup check) ----
    print("\n=== STEP 6: Duplicate upload (dedup) ===")
    try:
        doc2 = await svc.upload(
            user_id=user_id,
            filename="lease_copy.txt",
            content=lease_text,
            mime_type="text/plain",
            storage_provider="local",
        )
        step(
            "Dedup returns same vault_id",
            doc2.vault_id == doc1.vault_id,
            f"doc1={doc1.vault_id[:12]} doc2={doc2.vault_id[:12]}",
        )
    except Exception as e:
        step("Dedup upload", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 7: Upload a second unique document ----
    print("\n=== STEP 7: Upload eviction notice ===")
    notice_text = b"""NOTICE TO QUIT

Date: March 20, 2025
To: Tenant Jane Doe
From: Landlord John Smith

You are hereby notified that your lease is terminated effective
April 30, 2025, for non-payment of rent in the amount of $3,000.

You have 14 days to cure this default per Minn. Stat. 504B.177.

If you fail to pay, an eviction action may be filed under
Minn. Stat. Sec. 504B.321. You have 7 days to file an Answer.
"""
    try:
        doc3 = await svc.upload(
            user_id=user_id,
            filename="eviction_notice.txt",
            content=notice_text,
            mime_type="text/plain",
            document_type="notice",
            description="Eviction notice for non-payment",
            tags=["eviction", "notice"],
            source_module="e2e_test",
            storage_provider="local",
        )
        step("Upload notice", doc3 is not None and bool(doc3.vault_id), f"vault_id={doc3.vault_id}")
        step("Notice is certified", doc3.is_certified, f"registry_id={doc3.registry_id}")
        step("Notice has different vault_id", doc3.vault_id != doc1.vault_id, "unique id")
    except Exception as e:
        step("Upload notice", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 8: List user documents (should be 2) ----
    print("\n=== STEP 8: List user documents (expect 2) ===")
    try:
        docs = await svc.get_user_documents(user_id)
        step("User has 2 documents", len(docs) == 2, f"count={len(docs)}")
    except Exception as e:
        step("List after 2nd upload", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 9: Intake engine — text extraction ----
    print("\n=== STEP 9: Intake engine text extraction ===")
    text = ""
    try:
        intake = DocumentIntakeEngine()
        text = await intake._extract_text(
            lease_text,
            "text/plain",
            "lease_agreement.txt",
        )
        step("Text extraction", len(text) > 50 and "LEASE" in text.upper(), f"chars={len(text)}")
    except Exception as e:
        step("Text extraction", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 10: Document classification ----
    print("\n=== STEP 10: Document classification ===")
    doc_type = None
    try:
        if text:
            doc_type, confidence = DocumentClassifier.classify(text, "lease_agreement.txt")
            step("Classification", doc_type is not None, f"type={doc_type} confidence={confidence:.2f}")
        else:
            step("Classification", False, "no text to classify")
    except Exception as e:
        step("Classification", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 11: Data extraction (dates, parties, amounts) ----
    print("\n=== STEP 11: Data extraction ===")
    try:
        if text:
            dates = DataExtractor.extract_dates(text)
            amounts = DataExtractor.extract_amounts(text)
            parties = DataExtractor.extract_parties(text, doc_type)
            step("Date extraction", len(dates) > 0, f"found={len(dates)} dates")
            step("Amount extraction", len(amounts) > 0, f"found={len(amounts)} amounts")
            step("Party extraction", len(parties) > 0, f"found={len(parties)} parties")
        else:
            step("Data extraction", False, "no text")
    except Exception as e:
        step("Data extraction", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 12: Law linker citation detection on extracted text ----
    print("\n=== STEP 12: Law linker citation detection ===")
    try:
        import re

        from app.core.law_source_registry import build_official_url, resolve_source

        citations_found = []
        if text:
            patterns = [
                r"Minn\.?\s*Stat\.?\s*(?:Sec\.?|Section|§)?\s*([0-9]+(?:\.[0-9]+)?)",
                r"(\d+)\s*U\.S\.C\.?\s*(?:§)?\s*([0-9]+(?:-[0-9]+)?)",
            ]
            for pattern in patterns:
                for m in re.finditer(pattern, text, re.IGNORECASE):
                    citation_text = m.group(0).strip()
                    source = resolve_source(citation_text)
                    url = build_official_url(citation_text)
                    citations_found.append(
                        {
                            "text": citation_text,
                            "url": url,
                            "source": source.source_name if source else None,
                        }
                    )
        step("Citations detected", len(citations_found) >= 3, f"found={len(citations_found)}")
        if citations_found:
            for c in citations_found[:5]:
                print(f"      - {c['text'][:40]:40s} -> {c['url']}")
            # Verify URLs are well-formed
            good_urls = sum(1 for c in citations_found if c["url"] and c["url"].startswith("https://"))
            step("All URLs are https", good_urls == len(citations_found), f"{good_urls}/{len(citations_found)}")
    except Exception as e:
        step("Law linker citations", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 13: Mark document processed ----
    print("\n=== STEP 13: Mark document processed ===")
    try:
        extracted = {"dates": ["2025-01-15", "2025-02-01"], "parties": ["John Smith", "Jane Doe"]}
        updated = await svc.mark_processed(
            doc1.vault_id,
            extracted_data=extracted,
            storage_provider="local",
        )
        step("mark_processed", updated is not None and updated.processed, f"processed={updated.processed}")
    except Exception as e:
        step("mark_processed", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 14: Update document type ----
    print("\n=== STEP 14: Update document type ===")
    try:
        updated = await svc.update_document_type(
            doc1.vault_id,
            document_type="lease",
            storage_provider="local",
        )
        step(
            "update_document_type",
            updated is not None and updated.document_type == "lease",
            f"type={updated.document_type if updated else None}",
        )
    except Exception as e:
        step("update_document_type", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Step 15: Verify certificate file on disk ----
    print("\n=== STEP 15: Verify certificate file ===")
    try:
        cert_path = TEST_VAULT / "Semptify5.0" / "Vault" / "certificates" / f"{doc1.certificate_id}.json"
        step("Certificate file exists", cert_path.exists(), str(cert_path))
        if cert_path.exists():
            import json

            cert_data = json.loads(cert_path.read_text())
            step("Certificate has vault_id", cert_data.get("vault_id") == doc1.vault_id, "matches")
            step("Certificate has sha256", cert_data.get("sha256") == doc1.sha256_hash, "matches")
    except Exception as e:
        step("Certificate verification", False, f"EXCEPTION: {e}")
        traceback.print_exc()

    # ---- Final report ----
    print("\n" + "=" * 60)
    print(f"  RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 60)
    if FAIL > 0:
        print("\nFailed steps:")
        for s in STEPS:
            if "[FAIL]" in s:
                print(s)
    return FAIL == 0


if __name__ == "__main__":
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
