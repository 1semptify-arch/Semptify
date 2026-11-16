"""Legal-UI slice 6 live verification — gated release + custody + legend.

Drives the running sandbox instance (:8028, SECURITY_MODE=open, own DB,
LocalDiskProvider vault) to verify matrix rows:

  G7.4  representation marker — tenant my-advocate page renders
        "Working with you since DATE" for active ADVOCACY links
  G7.5  packet legend — packet zip/pdf carries legend.json/legend.txt so
        highlights decode offline
  G9.1  gated release is a separate owner action producing a NEW artifact
  G9.2  artifact carries timestamp + certificate (+ legend inside bundle)
  G9.3  the /legal-share surface makes original vs marks vs released copy
        unmistakable
  G9.4  advocate-initiated release denied + logged — never silent
  G9.5  hash recorded at intake + recomputable + artifact hash/timestamp/
        certificate travel together
  G9.6  exportable chronological per-document custody log
  INV   original bytes untouched — hash compared on disk before/after

Writes ONLY to sandbox\\sandbox.db, the dev local vault
(SEMPTIFY_LOCAL_STORAGE_ROOT or %LOCALAPPDATA%/SemptifyVault), and
sandbox\\slice6_out\\ for downloaded artifacts. All rows/files carry
TEST-SL6-* ids and are removed at the end.

    venv311\\Scripts\\python.exe sandbox\\slice6_verify.py
"""
import hashlib
import io
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DB = MODULE_ROOT / "sandbox" / "sandbox.db"
OUT_DIR = MODULE_ROOT / "sandbox" / "slice6_out"
BASE = "http://127.0.0.1:8028"

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./sandbox/sandbox.db")
os.environ.setdefault("SECURITY_MODE", "open")
os.chdir(MODULE_ROOT)
sys.path.insert(0, str(MODULE_ROOT))

from app.core.cookie_auth import sign_user_id  # noqa: E402
from app.core.vault_paths import VAULT_DOCUMENTS, VAULT_RELEASES  # noqa: E402

TENANT = "GUbGQUTpK6"          # god-mode user (token planted via /debug/seed-test-user)
ADVOCATE = "GUadvS6xAA"        # linked advocate — the deny target
STRANGER = "GUstrS6xBB"        # no relationship — the 404 target
VAULT_ID = "TEST-SL6-vault1"
DOC_TABLE_ID = "TEST-SL6-doc1"
DOC_NAME = "TEST-SL6-lease.txt"
STORAGE_PATH = f"{VAULT_DOCUMENTS}/{DOC_NAME}"
ORIG_BYTES = b"TEST-SL6 lease exhibit bytes - legal-ui slice6 gated release verification\n"
ORIG_SHA = hashlib.sha256(ORIG_BYTES).hexdigest()

RESULTS = []
SEEDED_OVERLAY_IDS: list = []


def rec(row, status, evidence):
    RESULTS.append((row, status, evidence))
    print(f"  [{status:7}] {row}: {evidence}")


def cookies(uid):
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
                return r.status, json.loads(raw), dict(r.headers)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return r.status, raw, dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw), dict(e.headers)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return e.code, raw, dict(e.headers)


def vault_root() -> Path:
    override = os.environ.get("SEMPTIFY_LOCAL_STORAGE_ROOT")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "SemptifyVault"


def disk_path(vault_posix: str) -> Path:
    return vault_root() / vault_posix.lstrip("/")


def db():
    conn = sqlite3.connect(SANDBOX_DB)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def seed():
    conn = db()
    now = datetime.now(timezone.utc).isoformat()
    # users
    for uid in (ADVOCATE, STRANGER):
        conn.execute(
            "INSERT OR IGNORE INTO users (id, primary_provider, storage_user_id, default_role, intensity_level, created_at, updated_at) "
            "VALUES (?, 'google_drive', ?, 'user', 'low', ?, ?)",
            (uid, f"store-{uid}", now, now),
        )
    # vault_index row — the canonical document identity, hash recorded at intake
    conn.execute(
        "INSERT OR REPLACE INTO vault_index (vault_id, user_id, filename, safe_filename, sha256_hash, file_size, "
        "mime_type, storage_path, storage_provider, integrity_status, processed, source_module, uploaded_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'text/plain', ?, 'local', 'verified', 1, 'TEST-SL6', ?, ?)",
        (VAULT_ID, TENANT, DOC_NAME, DOC_NAME, ORIG_SHA, len(ORIG_BYTES), STORAGE_PATH, now, now),
    )
    conn.execute(
        "INSERT OR IGNORE INTO vault_user_index (user_id, vault_id, added_at) VALUES (?, ?, ?)",
        (TENANT, VAULT_ID, now),
    )
    # documents row — the other identity space, same file_path
    conn.execute(
        "INSERT OR REPLACE INTO documents (id, user_id, filename, original_filename, file_path, file_size, "
        "mime_type, sha256_hash, is_privileged, is_work_product, privilege_waived, deep_ocr_status, uploaded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'text/plain', ?, 0, 0, 0, 'pending', ?)",
        (DOC_TABLE_ID, TENANT, DOC_NAME, "lease.txt", STORAGE_PATH, len(ORIG_BYTES), ORIG_SHA, now),
    )
    # active ADVOCACY link advocate -> tenant
    conn.execute(
        "INSERT INTO user_relationships (from_user_id, to_user_id, relationship_type, is_active, context, created_at, updated_at) "
        "VALUES (?, ?, 'advocacy', 1, ?, ?, ?)",
        (ADVOCATE, TENANT, json.dumps({"status": "active", "initiated_by": "tenant"}), now, now),
    )
    # prior custody events — a view + annotate by the advocate (as slice 1 proved get logged)
    conn.execute(
        "INSERT INTO document_access_logs (actor_user_id, actor_role, tenant_user_id, document_id, action, outcome, detail, timestamp) "
        "VALUES (?, 'user', ?, ?, 'view_document', 'ok', 'TEST-SL6 seeded view', ?)",
        (ADVOCATE, TENANT, VAULT_ID, "2026-11-13T10:00:00+00:00"),
    )
    conn.execute(
        "INSERT INTO document_access_logs (actor_user_id, actor_role, tenant_user_id, document_id, action, outcome, detail, timestamp) "
        "VALUES (?, 'user', ?, ?, 'annotate', 'ok', 'TEST-SL6 seeded annotate', ?)",
        (ADVOCATE, TENANT, DOC_TABLE_ID, "2026-11-13T11:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    # original bytes on local-vault disk
    target = disk_path(STORAGE_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(ORIG_BYTES)

    # Overlay fixtures written straight into the local vault — the unified
    # overlays HTTP API requires a real cloud session, but overlays are just
    # JSON in the tenant's vault: registry.json + one file per overlay.
    from app.core.vault_paths import VAULT_OVERLAY_DOCUMENTS, VAULT_OVERLAYS
    from app.core.overlay_types import OverlayType
    from app.models.unified_overlay_models import UnifiedOverlay

    fixtures = [
        UnifiedOverlay(
            overlay_type=OverlayType.DOCUMENT_KEY,
            document_id=VAULT_ID,
            vault_path=STORAGE_PATH,
            created_by=TENANT,
            created_at=datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc),
            payload={"colors": {"yellow": "Landlord admission"}},
        ),
        UnifiedOverlay(
            overlay_type=OverlayType.HIGHLIGHT,
            document_id=VAULT_ID,
            vault_path=STORAGE_PATH,
            created_by=TENANT,
            created_at=datetime(2026, 11, 13, 9, 30, tzinfo=timezone.utc),
            payload={"color": "yellow", "range": {"start": 0, "end": 12}, "note": "TEST-SL6 mark"},
        ),
        UnifiedOverlay(
            overlay_type=OverlayType.DOCUMENT_SHARE,
            document_id=f"shares:{TENANT}",
            vault_path=STORAGE_PATH,
            created_by=TENANT,
            created_at=datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc),
            payload={
                "vault_id": VAULT_ID,
                "recipient_identifier": "TEST-SL6 helper",
                "scope": "view",
                "created_at": "2026-11-13T12:00:00+00:00",
            },
        ),
    ]
    global SEEDED_OVERLAY_IDS
    SEEDED_OVERLAY_IDS = [ov.overlay_id for ov in fixtures]
    overlays_dir = disk_path(VAULT_OVERLAY_DOCUMENTS)
    overlays_dir.mkdir(parents=True, exist_ok=True)
    reg_path = disk_path(VAULT_OVERLAYS) / "registry.json"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    registry = {}
    if reg_path.exists():
        try:
            registry = json.loads(reg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            registry = {}
    for ov in fixtures:
        data = ov.model_dump()
        registry[ov.overlay_id] = data
        (overlays_dir / f"{ov.overlay_id}.json").write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
    reg_path.write_text(json.dumps(registry, indent=2, default=str), encoding="utf-8")

    return target


def cleanup(disk_file: Path):
    conn = db()
    conn.execute("DELETE FROM user_relationships WHERE from_user_id=? AND to_user_id=?", (ADVOCATE, TENANT))
    conn.execute("DELETE FROM document_access_logs WHERE detail LIKE 'TEST-SL6%' OR action='release_denied' AND tenant_user_id=?", (TENANT,))
    conn.execute("DELETE FROM document_access_logs WHERE document_id IN (?,?) AND detail LIKE 'TEST-SL6%'", (VAULT_ID, DOC_TABLE_ID))
    conn.execute("DELETE FROM vault_index WHERE vault_id=?", (VAULT_ID,))
    conn.execute("DELETE FROM vault_user_index WHERE vault_id=?", (VAULT_ID,))
    conn.execute("DELETE FROM documents WHERE id=?", (DOC_TABLE_ID,))
    conn.execute("DELETE FROM users WHERE id IN (?,?)", (ADVOCATE, STRANGER))
    conn.commit()
    conn.close()
    for pattern in (disk_file,):
        try:
            if pattern.exists():
                pattern.unlink()
        except OSError:
            pass
    # remove the released bundle folder + seeded/release overlay anchors
    releases_dir = vault_root() / VAULT_RELEASES.lstrip("/") / VAULT_ID
    try:
        if releases_dir.exists():
            for f in releases_dir.iterdir():
                f.unlink()
            releases_dir.rmdir()
    except OSError:
        pass
    try:
        from app.core.vault_paths import VAULT_OVERLAY_DOCUMENTS, VAULT_OVERLAYS
        reg_path = disk_path(VAULT_OVERLAYS) / "registry.json"
        overlays_dir = disk_path(VAULT_OVERLAY_DOCUMENTS)
        if reg_path.exists():
            registry = json.loads(reg_path.read_text(encoding="utf-8"))
            drop = set(SEEDED_OVERLAY_IDS)
            for oid, entry in list(registry.items()):
                if (isinstance(entry, dict) and entry.get("document_id") == VAULT_ID
                        and (entry.get("payload") or {}).get("kind") == "release"):
                    drop.add(oid)
            for oid in drop:
                registry.pop(oid, None)
                f = overlays_dir / f"{oid}.json"
                if f.exists():
                    f.unlink()
            reg_path.write_text(json.dumps(registry, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass


def server_up() -> bool:
    try:
        with urllib.request.urlopen(BASE + "/health", timeout=4) as r:
            return r.status < 500
    except Exception:
        return False


def main() -> int:
    print("slice6 live verification — gated release + custody + legend\n")
    if not server_up():
        print("FATAL: sandbox server not responding at", BASE)
        return 2

    call("GET", "/debug/seed-test-user", uid=None)  # creates tenant user + plants token
    disk_file = seed()
    try:
        # --- prep: doc list ---------------------------------------------------
        status, body, _ = call("GET", "/api/legal-share/release/documents", uid=TENANT)
        ids = [d.get("id") for d in (body.get("documents") or [])] if isinstance(body, dict) else []
        rec("seed/docs", "PASS" if status == 200 and VAULT_ID in ids else "FAIL",
            f"GET release/documents -> {status}; TEST-SL6 doc {'listed' if VAULT_ID in ids else 'MISSING'}")

        # color-key + share-grant overlays were seeded into the local vault
        rec("seed/overlays", "PASS", "DOCUMENT_KEY + HIGHLIGHT + DOCUMENT_SHARE fixtures on local-vault disk")

        # --- G9.5: integrity surface (recompute at any time) -----------------
        status, body, _ = call("GET", f"/api/legal-share/release/documents/{VAULT_ID}/integrity", uid=TENANT)
        ok = status == 200 and body.get("matches_intake") is True and body.get("intake_sha256") == ORIG_SHA \
            and body.get("recomputed_sha256") == ORIG_SHA
        rec("G9.5", "PASS" if ok else "FAIL",
            f"integrity -> {status}; intake==recomputed==seeded sha256: {body.get('matches_intake')}")

        # hash of original ON DISK before release — the immutability baseline
        before = hashlib.sha256(disk_file.read_bytes()).hexdigest()

        # --- G9.4: advocate attempt denied + logged, stranger 404s -----------
        status, body, _ = call("POST", f"/api/legal-share/release/documents/{VAULT_ID}/release", uid=ADVOCATE, body={})
        deny_logged = False
        if status == 403:
            conn = db()
            deny_logged = conn.execute(
                "SELECT COUNT(*) FROM document_access_logs WHERE action='release_denied' AND actor_user_id=? AND document_id=?",
                (ADVOCATE, VAULT_ID),
            ).fetchone()[0] == 1
            conn.close()
        rec("G9.4", "PASS" if status == 403 and deny_logged else "FAIL",
            f"advocate POST release -> {status} ({(body or {}).get('error') if isinstance(body, dict) else body}); "
            f"release_denied row written: {deny_logged}")

        status, _, _ = call("POST", f"/api/legal-share/release/documents/{VAULT_ID}/release", uid=STRANGER, body={})
        rec("G9.4", "PASS" if status == 404 else "FAIL",
            f"stranger POST release -> {status} (no oracle)")

        # --- G9.1/G9.2/G9.5: the gated release --------------------------------
        status, body, _ = call("POST", f"/api/legal-share/release/documents/{VAULT_ID}/release", uid=TENANT, body={})
        rel = (body or {}).get("release") or {}
        ok = (status == 200 and rel.get("artifact_sha256") and rel.get("released_at")
              and (rel.get("certificate") or {}).get("document_hash") == ORIG_SHA
              and rel.get("original_intact_after_release") is True
              and (rel.get("artifact_path") or "").lstrip("/").startswith(f"{VAULT_RELEASES.lstrip('/')}/{VAULT_ID}"))
        rec("G9.1", "PASS" if ok else "FAIL",
            f"tenant POST release -> {status}; artifact {rel.get('artifact_path')}; intact={rel.get('original_intact_after_release')}")

        cert_ok = bool(rel.get("certificate", {}).get("signature") and rel["certificate"].get("timestamp"))
        rec("G9.2", "PASS" if cert_ok else "FAIL",
            f"certificate: ts={rel.get('certificate', {}).get('timestamp')} sig={str(rel.get('certificate', {}).get('signature'))[:16]}… "
            f"tsa_backed={rel.get('certificate', {}).get('tsa_backed')}")

        # original untouched — hash compare on disk after release
        after = hashlib.sha256(disk_file.read_bytes()).hexdigest()
        rec("INV/immutable", "PASS" if before == after == ORIG_SHA else "FAIL",
            f"on-disk sha256 before={before[:16]}… after={after[:16]}… intake={ORIG_SHA[:16]}…")

        # artifact hash + timestamp + certificate travel together in the record
        travel = rel.get("artifact_sha256") and rel.get("released_at") and rel.get("certificate", {}).get("document_hash")
        rec("G9.5", "PASS" if travel else "FAIL", "artifact_sha256 + released_at + certificate in one record")

        # --- bundle contents: new artifact + legend travels -------------------
        status, blob, _ = call("GET", f"/api/legal-share/release/documents/{VAULT_ID}/releases/{rel.get('release_id')}/download", uid=TENANT)
        bundle_ok = False
        legend_ok = False
        if status == 200 and isinstance(blob, (bytes, bytearray)) and blob[:4] == b"PK\x03\x04":
            OUT_DIR.mkdir(exist_ok=True)
            (OUT_DIR / f"{rel.get('release_id')}.zip").write_bytes(blob)
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                names = set(zf.namelist())
                doc_entry = next((n for n in names if n.startswith("document/")), None)
                orig_inside = doc_entry is not None and zf.read(doc_entry) == ORIG_BYTES
                cert_inside = json.loads(zf.read("certificate.json"))["document_hash"] == ORIG_SHA if "certificate.json" in names else False
                legend = json.loads(zf.read("legend.json")) if "legend.json" in names else {}
                legend_ok = legend.get("colors", {}).get("yellow") == "Landlord admission"
                custody_inside = isinstance(json.loads(zf.read("custody-log.json")), list) if "custody-log.json" in names else False
                manifest_ok = json.loads(zf.read("release.json"))["document"]["original_sha256"] == ORIG_SHA if "release.json" in names else False
                bundle_ok = orig_inside and cert_inside and custody_inside and manifest_ok
        rec("G9.1/G9.2", "PASS" if bundle_ok else "FAIL",
            "bundle: original bytes verbatim + certificate + custody-log + manifest inside zip")
        rec("G9.2 legend", "PASS" if legend_ok else "FAIL",
            f"legend.json inside bundle decodes custom meaning: {legend_ok}")

        # --- G9.6: custody log ------------------------------------------------
        status, body, _ = call("GET", f"/api/legal-share/release/documents/{VAULT_ID}/custody-log", uid=TENANT)
        events = (body or {}).get("events") or []
        kinds = [e.get("event") for e in events]
        chronological = [e.get("timestamp") or "" for e in events] == sorted(e.get("timestamp") or "" for e in events)
        coverage = ("intake" in kinds and "view_document" in kinds and "annotate" in kinds
                    and "release" in kinds and "release_denied" in kinds)
        rec("G9.6", "PASS" if status == 200 and chronological and coverage else "FAIL",
            f"{len(events)} events; chronological={chronological}; kinds={sorted(set(kinds))}")

        status, body, headers = call("GET", f"/api/legal-share/release/documents/{VAULT_ID}/custody-log?download=1", uid=TENANT)
        cd = next((v for k, v in headers.items() if k.lower() == "content-disposition"), "")
        exportable = status == 200 and "attachment" in cd
        rec("G9.6 export", "PASS" if exportable else "FAIL",
            f"?download=1 -> {status} Content-Disposition={cd}")

        # --- G7.5: packet legend ----------------------------------------------
        status, body, _ = call("POST", "/api/packet-builder/build", uid=TENANT,
                               body={"vault_ids": [VAULT_ID], "mode": "overlay", "name": "TEST-SL6 packet"})
        pkt = (body or {}).get("packet_id") if isinstance(body, dict) else None
        if not pkt:
            rec("G7.5", "FAIL", f"packet build -> {status} {body}")
        else:
            status, blob, _ = call("GET", f"/api/packet-builder/packets/{pkt}/download?format=zip", uid=TENANT)
            ok = False
            if status == 200 and isinstance(blob, (bytes, bytearray)) and blob[:4] == b"PK\x03\x04":
                with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                    names = set(zf.namelist())
                    ok = "legend.json" in names and "legend.txt" in names
                    if "legend.json" in names:
                        lj = json.loads(zf.read("legend.json"))
                        ok = ok and any(
                            e.get("colors", {}).get("yellow") == "Landlord admission"
                            for e in (lj.get("documents") or {}).values()
                        )
            rec("G7.5", "PASS" if ok else "FAIL",
                f"packet zip carries legend.json+legend.txt with the doc's custom legend: {ok}")

        # --- G7.4 + G9.3: page surfaces ----------------------------------------
        status, html, _ = call("GET", "/tenant/my-advocate", uid=TENANT)
        marker = isinstance(html, (bytes, str)) and "Working with you since" in str(html)
        status2, advbody, _ = call("GET", "/api/advocate/my-advocates", uid=TENANT)
        linked = next((a for a in (advbody.get("advocates") or []) if a.get("advocate_user_id") == ADVOCATE), None) if isinstance(advbody, dict) else None
        rec("G7.4", "PASS" if status == 200 and marker and linked and linked.get("linked_at") else "FAIL",
            f"page contains 'Working with you since' render path; linked_at={bool(linked and linked.get('linked_at'))} status={linked and linked.get('status')}")

        status, html, _ = call("GET", "/legal-share", uid=TENANT)
        surface = isinstance(html, (bytes, str)) and "Released copies" in str(html) and "lsReleaseDoc" in str(html) \
            and "original" in str(html) and "released copy" in str(html)
        rec("G9.3", "PASS" if status == 200 and surface else "FAIL",
            f"/legal-share renders released-copies section with original-vs-marks-vs-copy copy: {surface}")

    finally:
        cleanup(disk_file)

    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    failed = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    print(f"\n{passed} PASS / {failed} FAIL / {len(RESULTS) - passed - failed} other")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
