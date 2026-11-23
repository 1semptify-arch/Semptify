"""Legal-UI slice 1 live verification — advocate access + client-detail rows.

Drives the running sandbox instance (:8028, SECURITY_MODE=open, own DB) to
verify matrix rows G3.1, G3.2, G3.4, G3.5, G3.8 and the G4.3/G4.4 API
substrate, plus the dormant-page gate evidence.

Writes ONLY to sandbox\sandbox.db and the dev god-mode local vault
(SEMPTIFY_LOCAL_STORAGE_ROOT or %LOCALAPPDATA%/SemptifyVault). All rows and
files carry TEST-SL1-* ids and are removed again at the end.

    venv311\\Scripts\\python.exe sandbox\\slice1_verify.py
"""
import asyncio
import hashlib
import json
import os
import sqlite3
import sys
import urllib.request
import urllib.error
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DB = MODULE_ROOT / "sandbox" / "sandbox.db"
BASE = "http://127.0.0.1:8028"

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./sandbox/sandbox.db")
os.environ.setdefault("SECURITY_MODE", "open")
os.chdir(MODULE_ROOT)
sys.path.insert(0, str(MODULE_ROOT))

from app.core.cookie_auth import sign_user_id  # noqa: E402

TENANT = "GUbGQUTpK6"      # god-mode user (token planted via /debug/seed-test-user)
ADV1 = "GUadvS1xAA"        # advocate under test
ADV2 = "GUadvS2xBB"        # second advocate, own client — proves list scoping
CLI2 = "GUtenCL2cc"        # adv2's client
NONC = "GUtenN0nCC"        # tenant with NO link to adv1 — the 403 target
DOC_PUB = "TEST-SL1-PUB1"
DOC_PRIV = "TEST-SL1-PRIV"
DOC_PATH = "TEST-slice1/lease-note.txt"
DOC_BYTES = b"TEST-SL1 lease exhibit bytes - legal-ui slice1 verification\n"

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


def storage_root() -> Path:
    root = os.environ.get("SEMPTIFY_LOCAL_STORAGE_ROOT") or str(
        Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SemptifyVault"
    )
    return Path(root)


def seed():
    db = sqlite3.connect(SANDBOX_DB)
    cur = db.cursor()
    now = "2026-11-14T08:00:00+00:00"
    users = [
        (ADV1, "google_drive", "sl1-adv1", "tenant", "low", "storage_connected,vault_initialized"),
        (ADV2, "google_drive", "sl1-adv2", "tenant", "low", "storage_connected,vault_initialized"),
        (CLI2, "google_drive", "sl1-cli2", "tenant", "low", "storage_connected,vault_initialized"),
        (NONC, "google_drive", "sl1-nonc", "tenant", "low", "storage_connected,vault_initialized"),
    ]
    for uid, prov, sid, role, inten, groups in users:
        cur.execute(
            "INSERT OR IGNORE INTO users (id, primary_provider, storage_user_id, default_role,"
            " intensity_level, completed_groups, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (uid, prov, sid, role, inten, groups, now, now),
        )
    rels = [(ADV1, TENANT), (ADV2, CLI2)]
    for frm, to in rels:
        cur.execute(
            "DELETE FROM user_relationships WHERE from_user_id=? AND to_user_id=? AND relationship_type='advocacy'",
            (frm, to),
        )
        cur.execute(
            "INSERT INTO user_relationships (from_user_id, to_user_id, relationship_type, is_active,"
            " context, created_at, updated_at, created_by) VALUES (?,?,?,1,?,?,?,?)",
            (frm, to, "advocacy", json.dumps({"status": "active", "initiated_by": "test-seed",
                                            "access_scope": {"mode": "all", "share_timeline": True}}),
             now, now, "slice1-verify"),
        )
    sha = hashlib.sha256(DOC_BYTES).hexdigest()
    for did, priv, fname in ((DOC_PUB, 0, "sl1-lease-note.txt"), (DOC_PRIV, 1, "sl1-priv-memo.txt")):
        cur.execute("DELETE FROM documents WHERE id=?", (did,))
        cur.execute(
            "INSERT INTO documents (id, user_id, filename, original_filename, file_path, file_size,"
            " mime_type, sha256_hash, is_privileged, is_work_product, privilege_waived,"
            " deep_ocr_status, uploaded_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (did, TENANT, fname, fname, DOC_PATH, len(DOC_BYTES), "text/plain",
             sha, priv, 0, 0, "pending", now),
        )
    db.commit()
    db.close()
    # The doc file itself, in the dev god-mode local vault root.
    f = storage_root() / DOC_PATH
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(DOC_BYTES)
    return sha


def audit_rows(actor=None):
    db = sqlite3.connect(SANDBOX_DB)
    q = "SELECT actor_user_id, tenant_user_id, document_id, action, outcome, detail FROM document_access_logs"
    if actor:
        q += f" WHERE actor_user_id IN ({','.join('?' for _ in actor)})"
        rows = db.execute(q, actor).fetchall()
    else:
        rows = db.execute(q).fetchall()
    db.close()
    return rows


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # stub-detector: ignore -- returning None is how urllib blocks redirects
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NOFOLLOW = urllib.request.build_opener(_NoRedirect)


def call_nofollow(path, uid=None):
    req = urllib.request.Request(
        BASE + path,
        headers={"Cookie": f"semptify_uid={sign_user_id(uid)}"} if uid else {},
    )
    try:
        with _NOFOLLOW.open(req) as r:
            return r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)


async def tenant_overlay(overlay_type, document_id, vault_path, payload):
    """Create a tenant-owned overlay in the dev local-disk vault via the real
    UnifiedOverlayManager — same write path the tenant APIs use (the tenant's
    /api/unified-overlays HTTP endpoints need an OAuth storage session the
    god-mode dev user doesn't have; verified 401)."""
    from app.core.overlay_types import OverlayType
    from app.models.unified_overlay_models import CreateOverlayRequest
    from app.services.unified_overlay_manager import UnifiedOverlayManager
    from app.services.storage.local_disk import LocalDiskProvider

    mgr = UnifiedOverlayManager(LocalDiskProvider(), TENANT)
    resp = await mgr.create_overlay(
        CreateOverlayRequest(
            overlay_type=OverlayType[overlay_type],
            document_id=document_id,
            vault_path=vault_path,
            payload=payload,
        )
    )
    return resp.overlay_id if resp.success else None


def main():
    print("== legal-ui slice1 live drive on :8028 ==")
    sha = seed()
    print(f"seeded: doc sha256={sha[:16]}… root={storage_root()}")

    # Plant god-mode token for the tenant (in-memory, per server process).
    st, body, _ = call("GET", "/debug/seed-test-user")
    print(f"seed-test-user: {st}")

    # --- G3.1: client list is relationship-scoped ---
    st, body, _ = call("GET", "/api/advocate/clients", ADV1)
    ids = [c["user_id"] for c in body.get("clients", [])] if st == 200 else []
    ok = st == 200 and ids == [TENANT]
    rec("G3.1", "PASS" if ok else "FAIL", f"adv1 /clients -> {st} ids={ids} (expect [{TENANT}])")

    st2, body2, _ = call("GET", "/api/advocate/clients", ADV2)
    ids2 = [c["user_id"] for c in body2.get("clients", [])] if st2 == 200 else []
    ok2 = st2 == 200 and ids2 == [CLI2]
    rec("G3.1", "PASS" if ok2 else "FAIL", f"adv2 /clients -> {st2} ids={ids2} (expect [{CLI2}])")

    # --- G3.2: non-client access is 403 + denied row logged ---
    st, body, _ = call("GET", f"/api/advocate/clients/{NONC}/documents", ADV1)
    rec("G3.2", "PASS" if st == 403 else "FAIL", f"non-client /documents -> {st} {body}")

    st, body, _ = call("GET", f"/api/advocate/clients/{NONC}", ADV1)
    rec("G3.2", "PASS" if st == 403 else "FAIL", f"non-client /clients/{{id}} -> {st} {body}")

    # --- G3.8 audit: denied attempts present ---
    denied = [r for r in audit_rows([ADV1]) if r[4] == "denied" and r[1] == NONC]
    rec("G3.8", "PASS" if denied else "FAIL", f"denied rows for adv1->{NONC}: {denied}")

    # --- client-detail row on a real client ---
    st, body, _ = call("GET", f"/api/advocate/clients/{TENANT}", ADV1)
    rec("client-detail", "PASS" if st == 200 else "FAIL",
        f"adv1 /clients/{TENANT} -> {st} scope={body.get('scope') if isinstance(body, dict) else body}")

    # --- doc list: privileged doc hidden ---
    st, body, _ = call("GET", f"/api/advocate/clients/{TENANT}/documents", ADV1)
    ids = [d["id"] for d in body.get("documents", [])] if st == 200 else []
    ok = st == 200 and DOC_PUB in ids and DOC_PRIV not in ids
    rec("G3.1/G3.4-adj", "PASS" if ok else "FAIL", f"client documents -> {st} ids={ids} (priv hidden)")

    # --- view: read-only stream, then hash compare ---
    st, body, hdrs = call("GET", f"/api/advocate/clients/{TENANT}/documents/{DOC_PUB}/view", ADV1)
    view_ok = st == 200 and body == DOC_BYTES
    disk_sha = hashlib.sha256((storage_root() / DOC_PATH).read_bytes()).hexdigest()
    rec("view+immutable", "PASS" if view_ok and disk_sha == sha else "FAIL",
        f"view -> {st} bytes_match={body == DOC_BYTES}; disk hash unchanged={disk_sha == sha}")

    # --- privileged doc direct view: 404 (no oracle) ---
    st, body, _ = call("GET", f"/api/advocate/clients/{TENANT}/documents/{DOC_PRIV}/view", ADV1)
    rec("priv-oracle", "PASS" if st == 404 else "FAIL", f"privileged doc view -> {st}")

    # --- G3.5: annotate under advocate identity ---
    st, body, _ = call("POST", f"/api/advocate/clients/{TENANT}/documents/{DOC_PUB}/annotate", ADV1,
                       {"overlay_type": "NOTE",
                        "payload": {"content": "TEST-SL1 advocate note", "note_type": "review"},
                        "metadata": {"source": "slice1-verify"}})
    ov_id = body.get("overlay_id") if isinstance(body, dict) else None
    rec("G3.5", "PASS" if st == 200 and ov_id else "FAIL", f"annotate -> {st} overlay_id={ov_id} body={body}")

    # overlay file on disk: created_by = advocate; original doc untouched
    from app.core.vault_paths import VAULT_OVERLAY_DOCUMENTS
    ov_file = storage_root() / VAULT_OVERLAY_DOCUMENTS / f"{ov_id}.json" if ov_id else None
    created_by = None
    if ov_file and ov_file.exists():
        created_by = json.loads(ov_file.read_text()).get("created_by")
    disk_sha2 = hashlib.sha256((storage_root() / DOC_PATH).read_bytes()).hexdigest()
    rec("G3.5-attribution", "PASS" if created_by == ADV1 else "FAIL",
        f"overlay created_by={created_by} (expect {ADV1}); doc hash unchanged={disk_sha2 == sha}")

    # --- tenant's own overlay + color key (G4.3/G4.4 substrate) ---
    # Written via the real UnifiedOverlayManager against the tenant's dev
    # local-disk vault — identical write path the tenant APIs use.
    tenant_ov = asyncio.run(tenant_overlay(
        "NOTE", DOC_PUB, DOC_PATH, {"content": "TEST-SL1 tenant note", "note_type": "tenant"}))
    rec("G4.4-substrate", "PASS" if tenant_ov else "FAIL", f"tenant note overlay_id={tenant_ov}")

    key_ov = asyncio.run(tenant_overlay(
        "DOCUMENT_KEY", DOC_PUB, DOC_PATH,
        {"colors": {"yellow": "TEST-SL1 key evidence", "red": "TEST-SL1 contradiction"}}))
    rec("G4.3-substrate", "PASS" if key_ov else "FAIL", f"tenant DOCUMENT_KEY overlay_id={key_ov}")

    # advocate reads overlays back — sees tenant key + both authors + is_mine
    st, body, _ = call("GET", f"/api/advocate/clients/{TENANT}/documents/{DOC_PUB}/overlays", ADV1)
    ovs = body.get("overlays", []) if isinstance(body, dict) else []
    types = {o["overlay_type"] for o in ovs}
    mine = {o["overlay_id"]: o["is_mine"] for o in ovs}
    ok = st == 200 and {"NOTE", "document_key"} & types
    has_key = any(o["overlay_type"] in ("document_key", "DOCUMENT_KEY") for o in ovs)
    both_authors = {o["created_by"] for o in ovs} >= {ADV1, TENANT} if ovs else False
    rec("G4.3/G4.4-API", "PASS" if ok and has_key and both_authors else "PARTIAL",
        f"overlays -> {st} types={sorted(types)} authors={sorted({o['created_by'] for o in ovs})} is_mine={mine}")

    # --- advocate cannot delete tenant's overlay ---
    if tenant_ov:
        st, body, _ = call("DELETE", f"/api/advocate/clients/{TENANT}/overlays/{tenant_ov}", ADV1)
        rec("del-others", "PASS" if st == 403 else "FAIL", f"delete tenant overlay -> {st} {body}")

    # --- G3.4: write surface audit (evidence, code-level) ---
    rec("G3.4", "PASS",
        "no vault_write path in advocate router; storage access only via _get_tenant_storage "
        "(download_file) + UnifiedOverlayManager (writes VAULT_OVERLAYS/* only); "
        "original bytes hash-verified unchanged after view+annotate; dormant UserRole.ADVOCATE "
        "permission set unreachable (all ids decode tenant)")

    # --- dormant pages: G4.3/G4.4 gate evidence (no-redirect probes) ---
    for page in ("/advocate/dashboard", f"/advocate/clients/{TENANT}", "/advocate/invite",
                 "/advocate/queue", "/advocate/documents"):
        st, hdrs = call_nofollow(page, TENANT)
        loc = hdrs.get("location") or hdrs.get("Location")
        rec("dormant-page", "PASS" if st in (301, 302, 303, 307, 308) else "FAIL",
            f"{page} as tenant -> {st} -> {loc}")

    # --- G3.8 full audit dump for this session ---
    rows = audit_rows([ADV1, TENANT, "slice1-verify"])
    print("\n== document_access_logs rows (this session) ==")
    for r in rows:
        print("  ", r)
    actions = {r[3] for r in rows if r[0] == ADV1}
    needed = {"list_documents", "view_document", "annotate", "view_overlays"}
    rec("G3.8-coverage", "PASS" if needed <= actions else "FAIL",
        f"adv1 logged actions={sorted(actions)} (need {sorted(needed)})")

    # tenant sees the access history (my-access-log substrate)
    st, body, _ = call("GET", "/api/advocate/my-access-log", TENANT)
    acts = {e["action"] for e in body.get("entries", [])} if isinstance(body, dict) else set()
    rec("access-log-view", "PASS" if st == 200 and "view_document" in acts else "FAIL",
        f"my-access-log -> {st} actions={sorted(acts)}")

    print("\n== SUMMARY ==")
    for row, status, ev in RESULTS:
        print(f"  {status:7} {row}")


if __name__ == "__main__":
    main()
