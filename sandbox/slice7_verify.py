"""Legal-UI slice 7 live verification — failure/edge/adversarial sweep.

Drives the running sandbox instance (:8028, SECURITY_MODE=open, own DB) to
verify the API/SEC halves of matrix rows G1.5, G1.6, G10.1, G10.7, G11.1-7
plus the unowned API-verifiable rows (G3.6, G3.7, G4.1, G4.2, G4.5, G4.6,
G4.8). UI halves are verified separately via IronBee browser.

Writes ONLY to sandbox\sandbox.db and the dev god-mode local vault
(SEMPTIFY_LOCAL_STORAGE_ROOT or %LOCALAPPDATA%/SemptifyVault). All rows and
files carry TEST-SL7-* ids.

    venv311\\Scripts\\python.exe sandbox\\slice7_verify.py
"""
import asyncio
import hashlib
import json
import os
import secrets
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MODULE_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DB = MODULE_ROOT / "sandbox" / "sandbox.db"
BASE = "http://127.0.0.1:8028"

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./sandbox/sandbox.db")
os.environ.setdefault("SECURITY_MODE", "open")
os.chdir(MODULE_ROOT)
sys.path.insert(0, str(MODULE_ROOT))

from app.core.cookie_auth import sign_user_id  # noqa: E402
from app.core.utc import utc_now  # noqa: E402

TENANT = "GUbGQUTpK6"      # god-mode tenant (token planted via /debug/seed-test-user)
ADV7 = "GUadvS7xAA"        # advocate linked to TENANT
TENB = "GUtenS7BBB"        # second tenant — cross-tenant isolation target
NOSN = "GUstale77S"        # user with NO storage session — reconnect-prompt target
GHOST = "GUtenGh0st1"      # valid-format user id that exists nowhere

DOC_T = "TEST-SL7-DOC1"    # tenant doc (documents table + vault file)
DOC_B = "TEST-SL7-DOCB"    # tenant-B doc
VDOC = "TEST-SL7-VSHARE"   # vault_index doc used for share creation
DOC_PATH_T = "TEST-slice7/tenant-eviction-notice.txt"
DOC_PATH_B = "TEST-slice7/tenantb-private.txt"
DOC_BYTES_T = b"TEST-SL7 tenant notice bytes - legal-ui slice7 verification\n"
DOC_BYTES_B = b"TEST-SL7 tenant-B private bytes - must never leak to others\n"

INJECT = '<script>alert("sl7xss")</script><img src=x onerror="alert(2)">'

LEAK_PATTERNS = [
    "GUbGQUTpK6", "GUadvS1xAA", "GUadvS7xAA", "GUtenS7BBB", "TEST-SL7", "TEST-SL1",
    "TEST-SL4", "SemptifyVault", "case-shares:", "share_token", "refresh_token",
    "access_token_encrypted", "sandbox.db",
]

RESULTS = []


def rec(row, status, evidence):
    RESULTS.append((row, status, evidence))
    print(f"  [{status:7}] {row}: {evidence}")


def sign(uid):
    return {"Cookie": f"semptify_uid={sign_user_id(uid)}"}


def cookie_header(raw_value):
    return {"Cookie": f"semptify_uid={raw_value}"}


def call(method, path, uid=None, body=None, headers=None):
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            **(sign(uid) if uid else {}),
            **({"Content-Type": "application/json"} if body is not None else {}),
            **(headers or {}),
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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NOFOLLOW = urllib.request.build_opener(_NoRedirect)


def call_nofollow(path, uid=None, cookie=None):
    hdrs = sign(uid) if uid else (cookie_header(cookie) if cookie else {})
    req = urllib.request.Request(BASE + path, headers=hdrs)
    try:
        with _NOFOLLOW.open(req) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def timed(method, path, uid=None, n=8):
    """n alternating-style calls → (last_status, last_body, [durations_ms])."""
    ds = []
    st = body = None
    for _ in range(n):
        t0 = time.perf_counter()
        st, body, _ = call(method, path, uid)
        ds.append((time.perf_counter() - t0) * 1000)
    return st, body, ds


def leaks(blob) -> list[str]:
    if isinstance(blob, (bytes, bytearray)):
        text = blob.decode("utf-8", "replace")
    elif isinstance(blob, str):
        text = blob
    else:
        text = json.dumps(blob, default=str)
    return [p for p in LEAK_PATTERNS if p in text]


def storage_root() -> Path:
    root = os.environ.get("SEMPTIFY_LOCAL_STORAGE_ROOT") or str(
        Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SemptifyVault"
    )
    return Path(root)


def _ctx(uid, storage_id):
    """Dev god-mode context — access_token maps every provider to local disk."""
    from app.core.user_context import StorageProvider, UserContext, UserRole

    return UserContext(
        user_id=uid,
        provider=StorageProvider.GOOGLE_DRIVE,
        storage_user_id=storage_id,
        access_token="dev-godmode-token",
        role=UserRole.USER,
    )


def audit_rows(actor=None):
    db = sqlite3.connect(SANDBOX_DB)
    q = "SELECT actor_user_id, tenant_user_id, document_id, action, outcome, detail FROM document_access_logs"
    if actor:
        rows = db.execute(
            q + f" WHERE actor_user_id IN ({','.join('?' for _ in actor)})", actor
        ).fetchall()
    else:
        rows = db.execute(q).fetchall()
    db.close()
    return rows


def seed():
    db = sqlite3.connect(SANDBOX_DB)
    cur = db.cursor()
    now = utc_now().isoformat()
    users = [
        (ADV7, "google_drive", "sl7-adv", "tenant", "low", "storage_connected,vault_initialized"),
        (TENB, "google_drive", "sl7-tenb", "tenant", "low", "storage_connected,vault_initialized"),
        (NOSN, "google_drive", "sl7-nosn", "tenant", "low", "storage_connected,vault_initialized"),
    ]
    for uid, prov, sid, role, inten, groups in users:
        cur.execute(
            "INSERT OR IGNORE INTO users (id, primary_provider, storage_user_id, default_role,"
            " intensity_level, completed_groups, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (uid, prov, sid, role, inten, groups, now, now),
        )
    # Advocate ↔ tenant link (active, whole-file scope)
    cur.execute(
        "DELETE FROM user_relationships WHERE from_user_id=? AND to_user_id=? AND relationship_type='advocacy'",
        (ADV7, TENANT),
    )
    cur.execute(
        "INSERT INTO user_relationships (from_user_id, to_user_id, relationship_type, is_active,"
        " context, created_at, updated_at, created_by) VALUES (?,?,?,1,?,?,?,?)",
        (ADV7, TENANT, "advocacy",
         json.dumps({"status": "active", "initiated_by": "test-seed",
                     "access_scope": {"mode": "all", "share_timeline": True}}),
         now, now, "slice7-verify"),
    )
    sha_t = hashlib.sha256(DOC_BYTES_T).hexdigest()
    sha_b = hashlib.sha256(DOC_BYTES_B).hexdigest()
    for did, owner, fname, path, size, sha in (
        (DOC_T, TENANT, "sl7-notice.txt", DOC_PATH_T, len(DOC_BYTES_T), sha_t),
        (DOC_B, TENB, "sl7-private.txt", DOC_PATH_B, len(DOC_BYTES_B), sha_b),
    ):
        cur.execute("DELETE FROM documents WHERE id=?", (did,))
        cur.execute(
            "INSERT INTO documents (id, user_id, filename, original_filename, file_path, file_size,"
            " mime_type, sha256_hash, is_privileged, is_work_product, privilege_waived,"
            " deep_ocr_status, uploaded_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (did, owner, fname, fname, path, size, "text/plain",
             sha, 0, 0, 0, "pending", now),
        )
    # vault_index row for share creation (share reads via vault_upload_service)
    cur.execute("DELETE FROM vault_index WHERE vault_id=?", (VDOC,))
    cur.execute(
        "INSERT INTO vault_index (vault_id, user_id, filename, safe_filename, sha256_hash,"
        " file_size, mime_type, storage_path, provider_file_id, storage_provider,"
        " integrity_status, processed, source_module, uploaded_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (VDOC, TENANT, f"{VDOC.lower()}.txt", f"{VDOC.lower()}.txt", sha_t,
         len(DOC_BYTES_T), "text/plain", DOC_PATH_T, None, "google_drive",
         "unverified", 0, "direct", now, now),
    )
    # Invite codes: one expired, one spent — codes in self-normalizing storage
    # form (validate_invite_code strips hyphens then re-hyphenates at len//2,
    # so "SL7-OLDX" and "SL7-SPEN" are lookup-stable; see intake-0a2b4733).
    past = "2026-11-01T00:00:00+00:00"
    cur.execute("DELETE FROM invite_codes WHERE code IN ('SL7-OLDX','SL7-SPEN')")
    cur.execute(
        "INSERT INTO invite_codes (code, created_by, organization_id, organization_name,"
        " role, max_uses, uses_count, used_by, expires_at, is_active, description,"
        " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("SL7-OLDX", ADV7, "sl7org", "SL7 Org", "advocate", 1, 0, "[]",
         past, 1, "expired code", now, now),
    )
    cur.execute(
        "INSERT INTO invite_codes (code, created_by, organization_id, organization_name,"
        " role, max_uses, uses_count, used_by, expires_at, is_active, description,"
        " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("SL7-SPEN", ADV7, "sl7org", "SL7 Org", "advocate", 1, 1, '["GUsomeone"]',
         None, 0, "spent code", now, now),
    )
    db.commit()
    db.close()
    for path, data in ((DOC_PATH_T, DOC_BYTES_T), (DOC_PATH_B, DOC_BYTES_B)):
        f = storage_root() / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
    return sha_t


async def mgr_for(uid):
    """UnifiedOverlayManager on the dev local-disk provider — same write path
    the HTTP endpoints use once storage is resolved."""
    from app.services.unified_overlay_manager import UnifiedOverlayManager
    from app.services.storage.local_disk import LocalDiskProvider

    return UnifiedOverlayManager(LocalDiskProvider(), uid)


async def mk_overlay(uid, overlay_type, document_id, vault_path, payload):
    from app.core.overlay_types import OverlayType
    from app.models.unified_overlay_models import CreateOverlayRequest

    mgr = await mgr_for(uid)
    resp = await mgr.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType[overlay_type],
            document_id=document_id,
            vault_path=vault_path,
            payload=payload,
        )
    )
    return resp.overlay_id if resp.success else None


async def list_overlays(uid, document_id=None):
    mgr = await mgr_for(uid)
    resp = await mgr.get_overlays(document_id=document_id, include_ephemeral=True)
    return resp.overlays if resp.success else []


def main():
    print("== legal-ui slice7 live drive on :8028 ==")
    sha_t = seed()
    print(f"seeded: doc sha256={sha_t[:16]}… root={storage_root()}")
    st, body, _ = call("GET", "/debug/seed-test-user")
    print(f"seed-test-user: {st}")

    # ==================================================================
    # G1.5 — forged/invalid session → rejected, clean redirect, no render
    # ==================================================================
    st, body, _ = call("GET", "/api/advocate/clients",
                       headers=cookie_header(f"{TENANT}.deadbeefdeadbeef"))
    rec("G1.5", "PASS" if st == 401 else "FAIL",
        f"forged-signature cookie /api/advocate/clients -> {st} {body}")

    st, body, _ = call("GET", "/api/advocate/clients", headers=cookie_header("notacookie"))
    rec("G1.5", "PASS" if st == 401 else "FAIL", f"malformed cookie -> {st} {body}")

    st, body, _ = call("GET", "/api/advocate/clients", headers=cookie_header(f"{TENANT}."))
    rec("G1.5", "PASS" if st == 401 else "FAIL", f"empty-signature cookie -> {st} {body}")

    st, body, _ = call("GET", "/api/advocate/my-advocates", headers=cookie_header("x"))
    rec("G1.5", "PASS" if st == 401 else "FAIL", f"tiny cookie on tenant API -> {st}")

    st, raw, hdrs = call_nofollow("/legal-share", cookie=f"{TENANT}.deadbeef")
    loc = next((v for k, v in hdrs.items() if k.lower() == "location"), "")
    rec("G1.5", "PASS" if st in (302, 303, 307) and "storage" in loc else "FAIL",
        f"forged cookie /legal-share -> {st} Location={loc}")

    # valid-format user that exists nowhere (stale session shape)
    st, body, _ = call("GET", "/api/advocate/clients", GHOST)
    rec("G1.5", "PASS" if st in (200, 401) else "FAIL",
        f"ghost user (valid sig, no DB row) /api/advocate/clients -> {st} {body}")

    # ==================================================================
    # G1.6 — adversary sees nothing: probe every door anonymously/forged,
    # scan body + headers for tenant identifiers, ids, paths.
    # ==================================================================
    adv_probes = [
        ("/api/advocate/clients", None), ("/api/advocate/clients/" + TENANT, None),
        ("/api/advocate/clients/" + TENANT + "/documents", None),
        ("/api/advocate/my-advocates", None), ("/api/advocate/my-access-log", None),
        ("/api/legal/matters", None), ("/api/unified-overlays/list?document_id=" + DOC_T, None),
        ("/tenant/my-advocate", None), ("/legal/dashboard", None),
        ("/api/documents", None), ("/api/legal-share/cases", None),
        ("/api/legal-share/r/zzz", None),
        ("/r/zzz", None),
    ]
    all_leaks = []
    for path, uid in adv_probes:
        st, raw, hdrs = call_nofollow(path, cookie=f"{TENANT}.deadbeef")
        hit = leaks(raw if isinstance(raw, bytes) else str(raw)) + [
            p for k, v in hdrs.items() for p in LEAK_PATTERNS if p in str(v)
        ]
        if hit:
            all_leaks.append((path, st, hit))
    st, raw, hdrs = call_nofollow("/api/advocate/clients", cookie=None)
    hit = leaks(raw if isinstance(raw, bytes) else str(raw))
    if hit:
        all_leaks.append(("/api/advocate/clients anon", st, hit))
    rec("G1.6", "PASS" if not all_leaks else "FAIL",
        f"forged/anon probes: {len(adv_probes)+1} routes, leak hits={all_leaks or 'none'}")

    # ==================================================================
    # G11.1 — enumeration oracle: linked-vs-nonexistent must be identical
    # ==================================================================
    st_a, body_a, t_a = timed("GET", f"/api/advocate/clients/{TENB}", ADV7, n=8)
    st_b, body_b, t_b = timed("GET", f"/api/advocate/clients/{GHOST}", ADV7, n=8)
    same = st_a == st_b == 403 and isinstance(body_a, dict) and isinstance(body_b, dict) \
        and body_a.get("detail") == body_b.get("detail")
    avg_a, avg_b = sum(t_a) / len(t_a), sum(t_b) / len(t_b)
    rec("G11.1", "PASS" if same and abs(avg_a - avg_b) < 150 else "FAIL",
        f"unlinked-real({st_a},{avg_a:.0f}ms) vs nonexistent({st_b},{avg_b:.0f}ms) identical={same}")

    # share-token oracle: malformed vs well-formed-unknown must match
    st1, b1, _ = call("GET", "/api/legal-share/r/zzz")
    good_unknown = f"{TENANT}:{secrets.token_urlsafe(32)}"
    st2, b2, _ = call("GET", f"/api/legal-share/r/{good_unknown}")
    same2 = st1 == st2 == 404 and b1 == b2
    rec("G11.1", "PASS" if same2 else "FAIL",
        f"share token malformed({st1},{b1}) vs well-formed-unknown({st2},{b2}) identical={same2}")

    # ==================================================================
    # G11.2 — replay of expired/dead tokens rejected (+ logged where spec'd)
    # ==================================================================
    # expired share — mint CASE_SHARE overlay with past expires_at
    from app.modules.legal_share import service as ls_service

    expired_share = asyncio.run(ls_service.create_share(
        _ctx(TENANT, "sl7-storage"),
        case_id=1, case_title="TEST-SL7 expired share case",
        reviewer_label="SL7 expired reviewer", tenant_message=None,
        documents=[{"id": VDOC, "name": f"{VDOC.lower()}.txt"}],
        include_notes=False, deadlines=[], include_summary=False,
        expires_at=utc_now() - __import__("datetime").timedelta(days=1),
    ))
    if expired_share is None:
        rec("G11.2", "FAIL", "could not mint expired share overlay")
    else:
        etok = expired_share.share_token
        st, body, _ = call("GET", f"/api/legal-share/r/{etok}")
        rec("G11.2", "PASS" if st == 410 and "share_expired" in json.dumps(body)
            else "FAIL", f"expired share replay -> {st} {body}")
        st2, body2, _ = call("GET", f"/api/legal-share/r/{etok}")
        rec("G11.2", "PASS" if st2 == 410 else "FAIL", f"replay again -> {st2}")

    # live share then revoke then replay
    live_share = asyncio.run(ls_service.create_share(
        _ctx(TENANT, "sl7-storage"),
        case_id=1, case_title="TEST-SL7 revoked share case",
        reviewer_label="SL7 revoked reviewer", tenant_message=None,
        documents=[{"id": VDOC, "name": f"{VDOC.lower()}.txt"}],
        include_notes=False, deadlines=[], include_summary=False,
        expires_at=utc_now() + __import__("datetime").timedelta(days=7),
    ))
    if live_share is not None:
        rtok = live_share.share_token
        st, body, _ = call("GET", f"/api/legal-share/r/{rtok}")
        rec("G11.2", "PASS" if st == 200 else "WARN",
            f"live share bundle -> {st} (pre-revoke baseline)")
        asyncio.run(ls_service.revoke_share(_ctx(TENANT, "sl7-storage"), live_share.id))
        st, body, _ = call("GET", f"/api/legal-share/r/{rtok}")
        rec("G11.2", "PASS" if st == 410 and "share_revoked" in json.dumps(body)
            else "FAIL", f"revoked share replay -> {st} {body}")

    # expired + spent invite codes
    for code, want in (("SL7-OLDX", "expired"), ("SL7-SPEN", "deactivated")):
        st, body, _ = call("POST", "/api/invite-codes/redeem", ADV7, {"code": code})
        msg = json.dumps(body)
        rec("G11.2", "PASS" if st == 400 and want in msg else "FAIL",
            f"redeem {code} -> {st} {msg[:140]}")

    # forged cookie replay (retired-key shape) covered under G1.5 above.

    # ==================================================================
    # G11.3 — overlay payload injection → stored verbatim, rendered as text
    # ==================================================================
    st, body, _ = call("POST", f"/api/advocate/clients/{TENANT}/documents/{DOC_T}/annotate",
                       ADV7, {"overlay_type": "NOTE",
                              "payload": {"content": INJECT, "note_type": "review"}})
    inj_ov = body.get("overlay_id") if st == 200 else None
    rec("G11.3", "PASS" if st == 200 and inj_ov else "FAIL",
        f"annotate with script payload -> {st} overlay={inj_ov}")

    st, body, _ = call("GET", f"/api/advocate/clients/{TENANT}/documents/{DOC_T}/overlays", ADV7)
    payloads = [o.get("payload") for o in (body.get("overlays") or [])]
    found = any(isinstance(p, dict) and p.get("content") == INJECT for p in payloads)
    rec("G11.3", "PASS" if st == 200 and found else "FAIL",
        f"injection payload round-trips verbatim in API (render escapes it — browser pass)")

    # ==================================================================
    # G11.4 — cross-tenant overlay isolation
    # ==================================================================
    b_overlay = asyncio.run(mk_overlay(TENB, "NOTE", DOC_B, DOC_PATH_B,
                                       {"content": "tenant-B private note", "note_type": "user"}))
    rec("G11.4", "PASS" if b_overlay else "FAIL", f"tenant-B overlay created {b_overlay}")

    async def cross_probe():
        mgr = await mgr_for(TENANT)
        ov = await mgr.get_overlay(b_overlay) if b_overlay else "no-overlay"
        listed = await list_overlays(TENB)
        return ov, listed

    cross_ov, b_list = asyncio.run(cross_probe())
    # Dev caveat: local_disk dev provider maps every user's "vault" onto the
    # same filesystem root, so the manager resolves the id locally. Isolation
    # in production = per-user cloud vault + router checks; verify the router
    # path is the enforcement (below).
    print(f"    note: dev local_disk manager cross-read -> {type(cross_ov).__name__} "
          f"(shared dev vault, service layer is not the isolation boundary)")

    st, body, _ = call("GET", f"/api/advocate/clients/{TENB}/documents", ADV7)
    rec("G11.4", "PASS" if st == 403 else "FAIL",
        f"advocate -> unlinked tenant-B docs -> {st} {body}")

    st, body, _ = call("GET", f"/api/advocate/clients/{TENB}/documents/{DOC_B}/overlays", ADV7)
    rec("G11.4", "PASS" if st == 403 else "FAIL",
        f"advocate -> unlinked tenant-B overlays endpoint -> {st} {body}")

    # direct unified-overlays single-get as a different user — must not leak payload
    st, body, _ = call("GET", f"/api/unified-overlays/overlay/{b_overlay}", TENANT)
    leaked = st == 200 and "tenant-B private note" in json.dumps(body)
    rec("G11.4", "PASS" if not leaked else "FAIL",
        f"tenant-A /api/unified-overlays/overlay/{b_overlay} -> {st} "
        f"(payload leaked={leaked})")

    # ==================================================================
    # G11.5 — API-only enforcement (UI never the enforcement)
    # ==================================================================
    proofs = []
    st, _, _ = call("GET", "/api/advocate/clients", headers=cookie_header("x.bad"))
    proofs.append(("advocate-list forged", st))
    st, _, _ = call("DELETE", f"/api/advocate/my-advocates/{ADV7}", headers=cookie_header("x.bad"))
    proofs.append(("tenant revoke forged", st))
    st, _, _ = call("GET", "/api/legal-share/r/zzz")
    proofs.append(("share bundle no-token", st))
    st, _, _ = call("GET", "/api/unified-overlays/list", headers=cookie_header("x.bad"))
    proofs.append(("overlays-list forged", st))
    ok = all(s in (401, 403, 404) for _, s in proofs)
    rec("G11.5", "PASS" if ok else "FAIL", f"credential-free API probes all rejected: {proofs}")

    # ==================================================================
    # G11.6 — audit log: append-only + failed attempts logged
    # ==================================================================
    denied = [r for r in audit_rows([ADV7]) if r[4] == "denied" and r[1] == TENB]
    rec("G11.6", "PASS" if denied else "FAIL",
        f"denied attempt on TENB logged -> {denied}")

    for method in ("DELETE", "PUT", "PATCH"):
        st, body, _ = call(method, "/api/advocate/my-access-log", TENANT)
        rec("G11.6", "PASS" if st in (405, 404) else "FAIL",
            f"{method} /api/advocate/my-access-log -> {st}")

    # ==================================================================
    # G11.7 — token entropy + rate limiting
    # ==================================================================
    tok_secret = etok.split(":", 1)[1] if expired_share else ""
    ent_ok = len(tok_secret) == 43  # token_urlsafe(32) → 43 chars ≈ 256 bits
    rec("G11.7", "PASS" if ent_ok else "FAIL",
        f"share token secret len={len(tok_secret)} chars (urlsafe-32 ≈ 256 bits)")

    # brute-force probe: rapid invalid-token hits — count 429s + status shape
    statuses = {}
    t0 = time.perf_counter()
    for i in range(215):
        req = urllib.request.Request(BASE + f"/api/legal-share/r/zz{i}")
        try:
            with urllib.request.urlopen(req) as r:
                statuses[r.status] = statuses.get(r.status, 0) + 1
        except urllib.error.HTTPError as e:
            statuses[e.code] = statuses.get(e.code, 0) + 1
    el = time.perf_counter() - t0
    rec("G11.7", "PASS" if statuses.get(429) else ("WARN" if statuses.get(404) else "FAIL"),
        f"215 rapid bad-token probes in {el:.1f}s -> {statuses} (429 = limiter engaged)")

    # ==================================================================
    # G10.1 — expired/missing storage session → honest reconnect (API half)
    # ==================================================================
    st, body, _ = call("GET", "/api/unified-overlays/list", NOSN)
    msg = json.dumps(body)
    ok = st == 401 and "reconnect" in msg and "documents" in msg.lower()
    rec("G10.1", "PASS" if ok else "FAIL",
        f"no-session user /api/unified-overlays/list -> {st} {msg[:180]}")

    st, body, _ = call("GET", "/api/legal-share/cases", NOSN)
    rec("G10.1", "PASS" if st == 401 and "reconnect" in json.dumps(body) else "FAIL",
        f"no-session user /api/legal-share/cases -> {st} {json.dumps(body)[:160]}")

    # ==================================================================
    # G10.7 — concurrent color-key edits → last-write-wins, no corruption
    # ==================================================================
    async def ck_race():
        mgr = await mgr_for(TENANT)
        from app.core.overlay_types import OverlayType
        from app.models.unified_overlay_models import CreateOverlayRequest
        # ensure a DOCUMENT_KEY overlay exists
        existing = await mgr.get_overlays(document_id=DOC_T, overlay_type=OverlayType.DOCUMENT_KEY)
        if existing.overlays:
            oid = existing.overlays[0].overlay_id
        else:
            resp = await mgr.create_overlay(CreateOverlayRequest(
                overlay_type=OverlayType.DOCUMENT_KEY, document_id=DOC_T,
                vault_path=DOC_PATH_T, payload={"colors": {"yellow": "first"}},
            ))
            oid = resp.overlay_id
        # two rapid writers — same write path the PUT endpoint uses
        w1 = await mgr.update_overlay(oid, payload={"colors": {"yellow": "writer-A"}})
        w2 = await mgr.update_overlay(oid, payload={"colors": {"blue": "writer-B"}})
        final = await mgr.get_overlay(oid)
        return oid, w1, w2, final

    oid, w1, w2, final = asyncio.run(ck_race())
    ok = w1 and w2 and final and final.payload.get("colors") == {"blue": "writer-B"}
    rec("G10.7", "PASS" if ok else "FAIL",
        f"two sequential writes -> final colors={final.payload.get('colors') if final else None} "
        f"(last write intact, single overlay id={oid})")

    # ==================================================================
    # G4.x unowned tenant-side rows — API-verifiable halves
    # ==================================================================
    # G4.1: DOCUMENT_KEY persists + merges with defaults via HTTP wrapper path
    async def g41():
        ovs = await list_overlays(TENANT, DOC_T)
        return [o for o in ovs if (o.overlay_type.value if hasattr(o.overlay_type, "value")
                                   else o.overlay_type) == "document_key"]
    keys = asyncio.run(g41())
    rec("G4.1", "PASS" if keys and keys[0].payload.get("colors") == {"blue": "writer-B"}
        else "FAIL", f"DOCUMENT_KEY persisted, colors={keys[0].payload.get('colors') if keys else None}")

    # G4.2: highlight+footnote overlays; original bytes untouched
    hl = asyncio.run(mk_overlay(TENANT, "HIGHLIGHT", DOC_T, DOC_PATH_T,
                                {"range": {"text": "eviction notice"}, "color": "red",
                                 "note": "sl7 highlight"}))
    fn = asyncio.run(mk_overlay(TENANT, "FOOTNOTE", DOC_T, DOC_PATH_T,
                                {"number": 1, "range": {"text": "notice"},
                                 "content": "sl7 footnote", "citation": "src"}))
    sha_after = hashlib.sha256((storage_root() / DOC_PATH_T).read_bytes()).hexdigest()
    rec("G4.2", "PASS" if hl and fn and sha_after == sha_t else "FAIL",
        f"hl={hl} fn={fn} sha256 unchanged={sha_after == sha_t}")

    # G4.5: two authors on same doc — both sets persist, distinguishable
    adv_ov = asyncio.run(mk_overlay(ADV7, "NOTE", DOC_T, DOC_PATH_T,
                                    {"content": "advocate note on tenant doc", "note_type": "review"}))
    ten_ov = asyncio.run(mk_overlay(TENANT, "NOTE", DOC_T, DOC_PATH_T,
                                    {"content": "tenant note", "note_type": "user"}))
    all_ovs = asyncio.run(list_overlays(TENANT, DOC_T))
    authors = {o.created_by for o in all_ovs}
    both = any(o.overlay_id == adv_ov for o in all_ovs) and any(
        o.overlay_id == ten_ov for o in all_ovs)
    rec("G4.5", "PASS" if both and len(authors) >= 2 else "FAIL",
        f"doc overlays authors={authors} both present={both}")

    # G3.6: tenant's overlay list shows advocate's marks WITH attribution
    adv_marks = [o for o in all_ovs if o.created_by == ADV7]
    rec("G3.6", "PASS" if adv_marks else "FAIL",
        f"tenant-side get_overlays shows advocate marks w/ created_by={ADV7}: {[o.overlay_id for o in adv_marks]}")

    # G3.7: advocate deletes own, cannot delete tenant's
    st, body, _ = call("DELETE", f"/api/advocate/clients/{TENANT}/overlays/{ten_ov}", ADV7)
    rec("G3.7", "PASS" if st == 403 else "FAIL",
        f"advocate delete tenant's overlay -> {st} {body}")
    st, body, _ = call("DELETE", f"/api/advocate/clients/{TENANT}/overlays/{adv_ov}", ADV7)
    rec("G3.7", "PASS" if st == 200 else "FAIL",
        f"advocate delete own overlay -> {st} {body}")

    # G4.6: orphaned overlays — delete the documents row + file; overlays remain
    db = sqlite3.connect(SANDBOX_DB)
    db.execute("DELETE FROM documents WHERE id=?", (DOC_B,))
    db.commit()
    db.close()
    orphans = asyncio.run(list_overlays(TENB, DOC_B))
    rec("G4.6", "PASS" if any(o.overlay_id == b_overlay for o in orphans) else "FAIL",
        f"doc row deleted; overlays still resolvable ({len(orphans)} returned) — orphaned cleanly")
    st, body, _ = call("GET", f"/api/advocate/clients/{TENANT}/documents/{DOC_T}X/overlays", ADV7)
    rec("G4.6", "PASS" if st == 404 else "FAIL",
        f"overlays on nonexistent doc -> {st} {body} (honest, no crash)")

    # G4.8: overlay fetch failure → honest state, doc render not gated
    st, body, _ = call("GET", f"/api/dc/document/{VDOC}/overlays", TENANT)
    honest = st in (200, 404) and isinstance(body, dict)
    rec("G4.8", "PASS" if honest else "FAIL",
        f"/api/dc/document/{VDOC}/overlays -> {st} {json.dumps(body)[:200]}")

    # ==================================================================
    # Summary
    # ==================================================================
    print("\n== RESULTS ==")
    fails = [r for r in RESULTS if r[1] == "FAIL"]
    warns = [r for r in RESULTS if r[1] == "WARN"]
    print(f"checks: {len(RESULTS)}  pass: {len(RESULTS)-len(fails)-len(warns)}  "
          f"warn: {len(warns)}  fail: {len(fails)}")
    for r in fails:
        print(f"  FAIL: {r[0]} — {r[2]}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
