"""Legal-UI slice 4 live verification — privilege/confidentiality + share links.

Drives a sandbox instance (:8025, SECURITY_MODE=open, own DB — same env as
sandbox/SANDBOX.cmd but on the registered ad-hoc verification port) to verify
matrix rows G5.2–G5.6, G5.8, G5.10, G5.12, G5.13 against the legal_share +
case_review surface. Blocked rows (G5.1, G5.7, G5.9, G5.11) are reported from
code evidence, not driven — they wait on task-b02e2f89.

Writes ONLY to sandbox\sandbox.db and the dev god-mode local vault
(SEMPTIFY_LOCAL_STORAGE_ROOT or %LOCALAPPDATA%/SemptifyVault). All rows and
files carry TEST-SL4-* ids.

    venv311\\Scripts\\python.exe sandbox\\slice4_verify.py
"""
import asyncio
import hashlib
import json
import os
import re
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import timedelta
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DB = MODULE_ROOT / "sandbox" / "sandbox.db"
BASE = "http://127.0.0.1:8025"

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./sandbox/sandbox.db")
os.environ.setdefault("SECURITY_MODE", "open")
os.chdir(MODULE_ROOT)
sys.path.insert(0, str(MODULE_ROOT))

from app.core.cookie_auth import sign_user_id  # noqa: E402
from app.core.utc import utc_now  # noqa: E402

TENANT = "GUbGQUTpK6"      # god-mode user (token planted via /debug/seed-test-user)
DOC_A = "TEST-SL4-DOCA"  # shared document
DOC_B = "TEST-SL4-DOCB"  # held back — the scope-enforcement target
DOC_BOGUS = "TEST-SL4-NOPE"  # id that exists nowhere — error-echo probe
DOC_PATH = "TEST-slice4/notice.txt"
DOC_BYTES = b"TEST-SL4 eviction notice bytes - legal-ui slice4 verification\n"
TENANT_MSG = "TEST-SL4 note: these are the documents we talked about."
LEAK_PATTERNS = ["GUbGQUTpK6", "TEST-SL4", "SemptifyVault", "case-shares:", "cshare_", "share_token"]

RESULTS = []


def rec(row, status, evidence):
    RESULTS.append((row, status, evidence))
    print(f"  [{status:7}] {row}: {evidence}")


def sign(uid):
    return {"Cookie": f"semptify_uid={sign_user_id(uid)}"}


def call(method, path, uid=None, body=None):
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            **({"Cookie": f"semptify_uid={sign_user_id(uid)}"} if uid else {}),
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw), r.headers
            except json.JSONDecodeError:
                return r.status, raw, r.headers
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw), e.headers
        except json.JSONDecodeError:
            return e.code, raw, e.headers


def leaks(blob) -> list[str]:
    """Sensitive substrings that must never appear in an error body."""
    text = blob if isinstance(blob, str) else json.dumps(blob)
    if isinstance(blob, (bytes, bytearray)):
        text = blob.decode("utf-8", "replace")
    return [p for p in LEAK_PATTERNS if p in text]


def storage_root() -> Path:
    root = os.environ.get("SEMPTIFY_LOCAL_STORAGE_ROOT") or str(
        Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SemptifyVault"
    )
    return Path(root)


def _tenant_ctx():
    """Dev god-mode context — access_token maps every provider to local disk."""
    from app.core.user_context import StorageProvider, UserContext, UserRole

    return UserContext(
        user_id=TENANT,
        provider=StorageProvider.GOOGLE_DRIVE,
        storage_user_id="sl4-storage",
        access_token="dev-godmode-token",
        role=UserRole.USER,
    )


def seed_docs():
    db = sqlite3.connect(SANDBOX_DB)
    cur = db.cursor()
    now = utc_now().isoformat()
    sha = hashlib.sha256(DOC_BYTES).hexdigest()
    for did in (DOC_A, DOC_B):
        cur.execute("DELETE FROM vault_index WHERE vault_id=?", (did,))
        cur.execute(
            "INSERT INTO vault_index (vault_id, user_id, filename, safe_filename, sha256_hash,"
            " file_size, mime_type, storage_path, provider_file_id, storage_provider,"
            " integrity_status, processed, source_module, uploaded_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (did, TENANT, f"{did.lower()}.txt", f"{did.lower()}.txt", sha,
             len(DOC_BYTES), "text/plain", DOC_PATH, None, "google_drive",
             "unverified", 0, "direct", now, now),
        )
    db.commit()
    db.close()
    f = storage_root() / DOC_PATH
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(DOC_BYTES)
    return sha


async def seed_incident():
    """INCIDENT overlay via the real incident_store write path."""
    from app.services.incident_store import create_incident

    return await create_incident(
        _tenant_ctx(), title="TEST-SL4 notice case", incident_type="eviction",
        description="slice4 verification", status="active",
    )


async def make_expired_share(case_id):
    """CASE_SHARE overlay already past expiry — same write path the API uses."""
    from app.modules.legal_share import service

    return await service.create_share(
        _tenant_ctx(),
        case_id=case_id,
        case_title="TEST-SL4 expired case",
        reviewer_label="Expired reviewer",
        tenant_message=None,
        documents=[{"id": DOC_A, "name": f"{DOC_A}.txt"}],
        include_notes=False,
        deadlines=[],
        include_summary=False,
        expires_at=utc_now() - timedelta(days=1),
    )


def main():
    print("== legal-ui slice4 live drive on :8025 ==")
    seed_docs()
    print(f"seeded docs root={storage_root()}")

    st, _, _ = call("GET", "/debug/seed-test-user")
    print(f"seed-test-user: {st} (redirect is fine)")

    incident = asyncio.run(seed_incident())
    if incident is None:
        rec("seed-incident", "FAIL", "create_incident returned None")
        return
    case_id = incident.incident_id
    print(f"seeded incident_id={case_id}")

    # --- Tenant share flow ---------------------------------------------------
    st, body, _ = call("GET", "/api/legal-share/cases", TENANT)
    ids = [c["incident_id"] for c in body.get("cases", [])] if st == 200 else []
    rec("cases", "PASS" if case_id in ids else "FAIL", f"/cases -> {st} ids={ids}")

    st, body, _ = call("GET", f"/api/legal-share/cases/{case_id}/items", TENANT)
    doc_ids = [d["id"] for d in body.get("documents", [])] if st == 200 else []
    rec("items", "PASS" if st == 200 and DOC_A in doc_ids and DOC_B in doc_ids else "FAIL",
        f"/items -> {st} docs={doc_ids}")

    st, body, _ = call("POST", "/api/legal-share/shares", TENANT, {
        "case_id": case_id,
        "reviewer_label": "Attorney SL4",
        "tenant_message": TENANT_MSG,
        "document_ids": [DOC_A],
        "include_notes": True,
        "include_summary": True,
        "expires_days": 7,
    })
    share = body.get("share") if isinstance(body, dict) else None
    share_url = share.get("share_url") if share else None
    token = share_url.split("/r/", 1)[1] if share_url and "/r/" in share_url else None
    rec("share-create", "PASS" if st == 201 and token else "FAIL", f"POST /shares -> {st} token={'yes' if token else 'no'}")
    if not token:
        return
    rec("G5.4-msg-field", "PASS" if share.get("tenant_message") == TENANT_MSG else "FAIL",
        f"share_json.tenant_message={share.get('tenant_message')!r}")

    # --- G5.4: reviewer sees only the shared slice + tenant message -----------
    st, bundle, _ = call("GET", f"/api/legal-share/r/{token}")
    ok = (st == 200
          and [d["id"] for d in bundle.get("documents", [])] == [DOC_A]
          and bundle.get("message") == TENANT_MSG
          and bundle.get("status") == "active")
    rec("G5.4-bundle", "PASS" if ok else "FAIL",
        f"bundle -> {st} docs={[d['id'] for d in bundle.get('documents', [])] if isinstance(bundle, dict) else bundle} "
        f"message={bundle.get('message')!r} status={bundle.get('status') if isinstance(bundle, dict) else '-'}")

    # no navigation into anything else — page must not link tenant surfaces
    st, page, _ = call("GET", f"/r/{token}")
    html = page.decode("utf-8", "replace") if isinstance(page, (bytes, bytearray)) else str(page)
    bad_hrefs = [h for h in re.findall(r'href="([^"]+)"', html)
                 if not h.startswith("/static/")
                 and re.search(r"/tenant|/legal-share\b|/api/|/dc\b|/advocate", h)]
    rec("G5.4-no-nav", "PASS" if st == 200 and not bad_hrefs else "FAIL",
        f"/r/{{token}} -> {st}; tenant-surface hrefs={bad_hrefs or 'none'}")

    # reviewer scope enforcement — out-of-scope doc ids are refused, not leaked
    st, err, _ = call("GET", f"/api/legal-share/r/{token}/document/{DOC_B}")
    rec("G5.4-scope", "PASS" if st == 403 and not leaks(err) else "FAIL",
        f"out-of-scope doc -> {st} {err} leaks={leaks(err)}")

    st, meta, _ = call("GET", f"/api/legal-share/r/{token}/document/{DOC_A}")
    rec("doc-meta", "PASS" if st == 200 else "FAIL", f"in-scope meta -> {st}")

    st, content, hdrs = call("GET", f"/api/legal-share/r/{token}/document/{DOC_A}/content")
    header_leaks = [p for p in LEAK_PATTERNS if p in str(hdrs)]
    rec("G5.12-stream", "PASS" if st == 200 and content == DOC_BYTES and not header_leaks else "FAIL",
        f"content -> {st} bytes_match={content == DOC_BYTES} header_leaks={header_leaks} "
        f"disposition={hdrs.get('Content-Disposition', hdrs.get('content-disposition'))}")

    # --- reviewer Q&A --------------------------------------------------------
    st, err, _ = call("POST", f"/api/legal-share/r/{token}/questions",
                      body={"document_id": DOC_B, "body": "out of scope?"})
    rec("qa-scope", "PASS" if st == 403 and not leaks(err) else "FAIL",
        f"question on non-shared doc -> {st} {err} leaks={leaks(err)}")

    st, thread, _ = call("POST", f"/api/legal-share/r/{token}/questions",
                         body={"document_id": DOC_A, "body": "What date is on the notice?", "subject": "Dates"})
    tid = thread.get("thread_id") if isinstance(thread, dict) else None
    rec("qa-ask", "PASS" if st == 201 and tid else "FAIL", f"question -> {st} thread={tid}")

    if tid:
        st, t2, _ = call("POST", f"/api/legal-share/r/{token}/threads/{tid}/messages",
                         body={"body": "And which page?"})
        rec("qa-followup", "PASS" if st == 201 else "FAIL", f"follow-up -> {st}")
        st, t3, _ = call("GET", f"/api/legal-share/r/{token}/threads")
        rec("qa-threads", "PASS" if st == 200 and any(t["thread_id"] == tid for t in t3.get("threads", [])) else "FAIL",
            f"threads -> {st}")

    # --- G5.8: error surfaces never echo tenant data / paths / ids -----------
    st, err, _ = call("GET", "/api/legal-share/r/not-a-token")
    rec("G5.8-malformed", "PASS" if st == 404 and not leaks(err) else "FAIL",
        f"malformed token -> {st} {err} leaks={leaks(err)}")

    st, err, _ = call("GET", f"/api/legal-share/r/{TENANT}:definitely-bogus-token")
    rec("G5.8-unknown", "PASS" if st == 404 and not leaks(err) else "FAIL",
        f"unknown token -> {st} {err} leaks={leaks(err)}")

    st, err, _ = call("GET", f"/api/legal-share/r/{token}/document/{DOC_BOGUS}")
    rec("G5.8-docid", "PASS" if st == 403 and not leaks(err) else "FAIL",
        f"bogus doc id -> {st} {err} leaks={leaks(err)}")

    st, err, _ = call("GET", f"/api/legal-share/r/{token}/threads/rth_bogus")
    rec("G5.8-misc", "PASS" if not leaks(err) else "FAIL", f"misc probe -> {st} leaks={leaks(err)}")

    # tenant-side: bogus vault id at share-create must not echo the id back
    st, err, _ = call("POST", "/api/legal-share/shares", TENANT, {
        "case_id": case_id, "reviewer_label": "Echo probe",
        "document_ids": [DOC_BOGUS], "expires_days": 7,
    })
    rec("G5.8-create-echo", "PASS" if st == 404 and DOC_BOGUS not in json.dumps(err) else "FAIL",
        f"share-create bogus doc -> {st} {err}")

    # --- G5.5: ended links render a clean page with a next step ---------------
    st, body, _ = call("POST", f"/api/legal-share/shares/{share['share_id']}/revoke", TENANT)
    rec("revoke", "PASS" if st == 200 else "FAIL", f"revoke -> {st}")

    st, err, _ = call("GET", f"/api/legal-share/r/{token}")
    rec("G5.5-api-410", "PASS" if st == 410 and not leaks(err) else "FAIL",
        f"revoked bundle -> {st} {err} leaks={leaks(err)}")

    st, page, _ = call("GET", f"/r/{token}")
    html = page.decode("utf-8", "replace") if isinstance(page, (bytes, bytearray)) else str(page)
    closed_copy = "has been closed" in html
    next_step = 'href="/help"' in html
    rec("G5.5-revoked", "PASS" if st == 200 and closed_copy and next_step else "FAIL",
        f"revoked page -> {st} closed_copy={closed_copy} next_step={next_step}")

    expired = asyncio.run(make_expired_share(case_id))
    if expired is not None:
        etok = expired.share_token
        st, err, _ = call("GET", f"/api/legal-share/r/{etok}")
        rec("G5.5-expired-api", "PASS" if st == 410 and not leaks(err) else "FAIL",
            f"expired bundle -> {st} {err} leaks={leaks(err)}")
        st, page, _ = call("GET", f"/r/{etok}")
        html = page.decode("utf-8", "replace") if isinstance(page, (bytes, bytearray)) else str(page)
        rec("G5.5-expired", "PASS" if st == 200 and "has expired" in html else "FAIL",
            f"expired page -> {st} copy={'has expired' in html}")

    st, page, _ = call("GET", "/r/definitely-not-real")
    html = page.decode("utf-8", "replace") if isinstance(page, (bytes, bytearray)) else str(page)
    next_step = 'href="/help"' in html or "ask the person" in html
    rec("G5.5-unknown", "PASS" if st == 200 and "doesn" in html and next_step else "FAIL",
        f"unknown-token page -> {st} next_step={next_step}")

    # tenant page renders (cookie-gated shell)
    st, page, _ = call("GET", "/legal-share", TENANT)
    html = page.decode("utf-8", "replace") if isinstance(page, (bytes, bytearray)) else str(page)
    checks = {
        "forward_warn": "handing someone the paper" in html,
        "priv_waiver": "undo the confidentiality" in html,
        "atty_vs_adv": "attorney-client confidential" in html,
        "discoverable": "asked for in a court case" in html,
        "metadata": "hidden details saved inside the file" in html,
        "message_field": 'id="lsMessage"' in html,
    }
    rec("G5.3/5.6/5.10/5.12/5.13-copy", "PASS" if st == 200 and all(checks.values()) else "FAIL",
        f"/legal-share -> {st} {checks}")

    # G5.2 — copy audit: advocate/tenant/reviewer templates never label comms privileged
    tpl_root = MODULE_ROOT / "app" / "templates"
    hits = []
    for name in ("pages/tenant_my_advocate.html", "pages/legal_share.html",
                 "pages/reviewer_share.html", "pages/reviewer_unavailable.html",
                 "pages/case_review.html", "pages/advocate_dashboard.html",
                 "pages/advocate_client_detail.html", "pages/advocate_invite.html"):
        p = tpl_root / name
        if p.exists() and re.search(r"privileg", p.read_text(encoding="utf-8", errors="replace"), re.I):
            hits.append(name)
    rec("G5.2-copy", "PASS" if not hits else "FAIL",
        f"privilege wording in advocate/tenant/reviewer templates: {hits or 'none'}")

    print("\n== SUMMARY ==")
    for row, status, ev in RESULTS:
        print(f"  {status:7} {row}")


if __name__ == "__main__":
    main()
