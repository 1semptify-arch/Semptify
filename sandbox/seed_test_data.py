"""Seed the Semptify sandbox test-data group.

Writes ONLY to sandbox/sandbox.db — never semptify.db. The DATABASE_URL is
hard-forced to the sandbox path before any app module is imported, and the
script refuses to run if the resolved URL points anywhere else. This is the
bleed guard: synthetic rows can never reach the working group.

    venv311\\Scripts\\python.exe sandbox\\seed_test_data.py

Re-runnable: every seeded row carries a TEST-* id; existing TEST-* rows are
deleted and re-inserted, so the dataset resets cleanly each run. The
dev-godmode user (GUbGQUTpK6) is upserted so drills work on the sandbox —
note its in-memory token is per-process: after launching the server, hit
http://127.0.0.1:8028/debug/seed-test-user once to plant it.
"""
import asyncio
import hashlib
import os
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_URL = "sqlite+aiosqlite:///./sandbox/sandbox.db"

os.environ["DATABASE_URL"] = SANDBOX_URL
os.environ.setdefault("SECURITY_MODE", "open")
os.environ.setdefault("SEMPTIFY_ENV", "development")
os.chdir(MODULE_ROOT)
sys.path.insert(0, str(MODULE_ROOT))

from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import get_session_factory, init_db  # noqa: E402
from app.core.utc import utc_now  # noqa: E402

# Import models so their tables register on Base.metadata before create_all —
# same requirement conftest.py documents ("do not remove").
import app.models.models  # noqa: E402, F401
import app.modules.accountability_ledger.models  # noqa: E402, F401


def _guard():
    url = get_settings().database_url
    if "sandbox" not in url.replace("\\", "/"):
        raise SystemExit(f"REFUSING: DATABASE_URL resolved to {url!r}, not the sandbox")


USERS = [
    # id, provider, storage_user_id, role, intensity, completed_groups
    ("GUbGQUTpK6", "google_drive", "test-storage-user-id", "tenant", "low",
     "storage_connected,vault_initialized,document_uploaded"),
    ("TEST-TENANT-01", "local_disk", "test-tenant-01", "tenant", "low",
     "storage_connected,vault_initialized,document_uploaded"),
    ("TEST-TENANT-02", "local_disk", "test-tenant-02", "tenant", "low", ""),
    ("TEST-ADVOCATE-01", "local_disk", "test-advocate-01", "tenant", "low",
     "storage_connected,vault_initialized"),
]

CONTACTS = [
    ("TEST-CONTACT-LL", "TEST-TENANT-01", "landlord", "landlord",
     "TEST Property Management Co", "TEST Properties LLC", "property manager",
     "612-555-0100", "", "pm@test.example", "", "100 Test Ave", "", "Minneapolis", "MN", "55401", ""),
    ("TEST-CONTACT-LAID", "TEST-TENANT-01", "legal_aid", "legal aid",
     "TEST Legal Aid Intake", "TEST Legal Aid", "intake line",
     "612-555-0101", "", "intake@test.example", "", "200 Test St", "", "Minneapolis", "MN", "55402", ""),
    ("TEST-CONTACT-COURT", "TEST-TENANT-01", "court", "court clerk",
     "TEST District Court", "TEST County District Court", "civil clerk",
     "612-555-0102", "", "civil@test.example", "", "300 Test Blvd", "", "Minneapolis", "MN", "55415", ""),
]

JOURNAL = [
    ("TEST-JRN-001", "TEST-TENANT-01", "notice_received", "TEST notice posted on door",
     "TEST DATA — 14-day notice to quit posted on the unit door. Photographed and logged.", 0, "TEST Property Management Co"),
    ("TEST-JRN-002", "TEST-TENANT-01", "repair_request", "TEST repair request sent",
     "TEST DATA — written request for furnace repair sent to property manager.", 0, "TEST Property Management Co"),
    ("TEST-JRN-003", "TEST-TENANT-01", "call_log", "TEST call with manager",
     "TEST DATA — 10-minute call; manager said repairs scheduled next week.", 0, "TEST Property Management Co"),
]

TIMELINE = [
    ("TEST-TL-001", "TEST-TENANT-01", "notice", "TEST notice served", "TEST DATA — notice to quit served.", 0, "TEST Property Management Co", "100 Test Ave"),
    ("TEST-TL-002", "TEST-TENANT-01", "deadline", "TEST response deadline", "TEST DATA — deadline to respond.", 1, "", ""),
]

DISPUTES = [
    ("TEST-CASE-001", "TEST-TENANT-01", "TEST Property Management Co", "TEST Properties LLC",
     "eviction_defense", "active", "MN"),
]

EVICTION_EVENTS = [
    ("TEST-EVT-001", "TEST-TENANT-01", "TEST-CASE-001", "notice_served", "manual", "MN"),
]

ACCOUNTABILITY = [
    ("TEST-PMCO-01", "company", "TEST Property Management Co", "MN"),
]

VOICE = [
    ("TEST-VOICE-001", "question", "TEST DATA — what are my options after a 14-day notice?",
     "TEST DATA — review the notice, log it in the journal, and gather your lease and payment records.",
     "TEST responder", "answered", 1),
]


async def main():
    _guard()
    await init_db()
    factory = get_session_factory()
    now = utc_now()
    uploads = MODULE_ROOT / "sandbox" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    doc_a = uploads / "TEST-doc-notice.txt"
    doc_a.write_text("TEST DATA — 14-day notice to quit (seeded sandbox document).\n", encoding="utf-8")
    doc_b = uploads / "TEST-doc-lease.txt"
    doc_b.write_text("TEST DATA — sample lease excerpt (seeded sandbox document).\n", encoding="utf-8")

    async with factory() as db:
        # Reset the test-data group: every seeded row carries a TEST-* id.
        for table in ("contacts", "journal_entries", "timeline_events", "documents",
                      "dispute_records", "eviction_timeline_events",
                      "accountability_subjects", "voice_posts"):
            await db.execute(text(f"DELETE FROM {table} WHERE id LIKE 'TEST-%'"))
        await db.execute(text("DELETE FROM users WHERE id LIKE 'TEST-%'"))

        for uid, prov, sid, role, lvl, groups in USERS:
            await db.execute(
                text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
            await db.execute(
                text(
                    "INSERT INTO users (id, primary_provider, storage_user_id, "
                    "default_role, intensity_level, completed_groups, created_at, updated_at) "
                    "VALUES (:uid, :prov, :sid, :role, :lvl, :groups, :now, :now)"
                ),
                {"uid": uid, "prov": prov, "sid": sid, "role": role,
                 "lvl": lvl, "groups": groups, "now": now},
            )

        for (cid, uid, ctype, role, name, org, title, phone, alt, email,
             fax, a1, a2, city, st, zc, web) in CONTACTS:
            await db.execute(
                text(
                    "INSERT INTO contacts (id, user_id, contact_type, role, name, "
                    "organization, title, phone, phone_alt, email, fax, address_line1, "
                    "address_line2, city, state, zip_code, website, is_active, "
                    "is_starred, interaction_count, created_at, updated_at) VALUES "
                    "(:id, :uid, :ctype, :role, :name, :org, :title, :phone, :alt, "
                    ":email, :fax, :a1, :a2, :city, :st, :zc, :web, 1, 0, 0, :now, :now)"
                ),
                {"id": cid, "uid": uid, "ctype": ctype, "role": role, "name": name,
                 "org": org, "title": title, "phone": phone, "alt": alt, "email": email,
                 "fax": fax, "a1": a1, "a2": a2, "city": city, "st": st, "zc": zc,
                 "web": web, "now": now},
            )

        for jid, uid, etype, title, content, urgent, party in JOURNAL:
            await db.execute(
                text(
                    "INSERT INTO journal_entries (id, user_id, entry_type, title, "
                    "content, occurred_at, is_urgent, involved_party, source, "
                    "created_at, updated_at) VALUES (:id, :uid, :etype, :title, "
                    ":content, :now, :urgent, :party, 'seed', :now, :now)"
                ),
                {"id": jid, "uid": uid, "etype": etype, "title": title,
                 "content": content, "urgent": urgent, "party": party, "now": now},
            )

        for seq, (tid, uid, etype, title, desc, is_dl, party, loc) in enumerate(TIMELINE, 1):
            await db.execute(
                text(
                    "INSERT INTO timeline_events (id, user_id, event_type, title, "
                    "description, event_date, is_deadline, who_involved, location, "
                    "sequence_number, urgency, is_evidence, created_at) VALUES (:id, :uid, :etype, :title, "
                    ":desc, :now, :is_dl, :party, :loc, :seq, 'normal', 0, :now)"
                ),
                {"id": tid, "uid": uid, "etype": etype, "title": title, "desc": desc,
                 "is_dl": is_dl, "party": party, "loc": loc, "seq": seq, "now": now},
            )

        for did, uid, fname, fpath in (
                ("TEST-DOC-001", "TEST-TENANT-01", "TEST-doc-notice.txt", str(doc_a)),
                ("TEST-DOC-002", "TEST-TENANT-01", "TEST-doc-lease.txt", str(doc_b))):
            await db.execute(
                text(
                    "INSERT INTO documents (id, user_id, filename, original_filename, "
                    "file_path, file_size, mime_type, sha256_hash, document_type, "
                    "is_privileged, is_work_product, privilege_waived, "
                    "deep_ocr_status, uploaded_at) VALUES (:id, "
                    ":uid, :fname, :fname, :fpath, :fsize, 'text/plain', :sha, "
                    "'evidence', 0, 0, 0, 'pending', :now)"
                ),
                {"id": did, "uid": uid, "fname": fname, "fpath": fpath,
                 "fsize": os.path.getsize(fpath),
                 "sha": hashlib.sha256(Path(fpath).read_bytes()).hexdigest(),
                 "now": now},
            )

        for rid, uid, landlord, prop, dtype, status, juris in DISPUTES:
            await db.execute(
                text(
                    "INSERT INTO dispute_records (id, user_id, landlord_entity, "
                    "property_name, dispute_type, status, jurisdiction, created_at, "
                    "updated_at) VALUES (:id, :uid, :ll, :prop, :dtype, :status, "
                    ":juris, :now, :now)"
                ),
                {"id": rid, "uid": uid, "ll": landlord, "prop": prop, "dtype": dtype,
                 "status": status, "juris": juris, "now": now},
            )

        for eid, uid, sid, etype, source, juris in EVICTION_EVENTS:
            await db.execute(
                text(
                    "INSERT INTO eviction_timeline_events (id, user_id, subject_id, "
                    "event_type, event_date, source, jurisdiction, created_at, "
                    "updated_at) VALUES (:id, :uid, :sid, :etype, :now, :source, "
                    ":juris, :now, :now)"
                ),
                {"id": eid, "uid": uid, "sid": sid, "etype": etype,
                 "source": source, "juris": juris, "now": now},
            )

        for aid, stype, name, juris in ACCOUNTABILITY:
            await db.execute(
                text(
                    "INSERT INTO accountability_subjects (id, subject_type, "
                    "canonical_name, jurisdiction, created_at, updated_at) VALUES "
                    "(:id, :stype, :name, :juris, :now, :now)"
                ),
                {"id": aid, "stype": stype, "name": name, "juris": juris, "now": now},
            )

        for vid, kind, post, resp, label, status, pub in VOICE:
            await db.execute(
                text(
                    "INSERT INTO voice_posts (id, kind, post_text, response_text, "
                    "responder_label, status, is_published, flag_count, created_at, "
                    "updated_at) VALUES (:id, :kind, :post, :resp, :label, :status, "
                    ":pub, 0, :now, :now)"
                ),
                {"id": vid, "kind": kind, "post": post, "resp": resp,
                 "label": label, "status": status, "pub": pub, "now": now},
            )

        await db.commit()

    counts = {
        "users": len(USERS), "contacts": len(CONTACTS), "journal": len(JOURNAL),
        "timeline": len(TIMELINE), "documents": 2, "disputes": len(DISPUTES),
        "eviction_events": len(EVICTION_EVENTS),
        "accountability": len(ACCOUNTABILITY), "voice": len(VOICE),
    }
    print("sandbox test-data group seeded ->", SANDBOX_URL)
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print()
    print("Next: launch SANDBOX.cmd, then hit once per restart:")
    print("  http://127.0.0.1:8028/debug/seed-test-user")


if __name__ == "__main__":
    asyncio.run(main())
