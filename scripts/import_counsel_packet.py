"""Import the LEGAL_COUNSEL_PACKET folder into Brad's OAuth vault.

Walks the packet tree, uploads every content file through the canonical
VaultService.upload() (SHA256 dedup makes re-runs idempotent), and writes a
manifest JSON mapping relative paths -> vault_ids. That manifest is what
/legal-share needs when creating the reviewer share (documents=[{id,name}]).

Run from module root with venv311 active:
    venv311\\Scripts\\python.exe scripts\\import_counsel_packet.py
"""

import asyncio
import json
import mimetypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PACKET_DIR = Path(r"E:\CASE_FILE_Crowe_Sazama_v_Velair\LEGAL_COUNSEL_PACKET")
USER_ID = "GUbGQUTpK6"  # Brad's Google Drive-backed tenant
MANIFEST_OUT = PACKET_DIR / "_vault_manifest.json"

# Generated UI artifacts exist alongside source docs; import only source files.
SKIP_NAMES = {"index.html", "rebuild_ui.py", "_vault_manifest.json",
              "README_FOR_COUNSEL.html", "LEGAL_REVIEW_2026-09-27.html",
              "MASTER_TIMELINE_ALL_CASES.html", "OVERVIEW.html",
              "AG_SUPPLEMENTAL_REPORT_DRAFT_2026-09-27.html",
              "LIHTC_Form8823_Audit_Request_Letter.html",
              "RESEARCH_FINDINGS_REPORT_2026-09-26.html"}


async def main() -> None:
    from app.core.auto_refresh import ensure_valid_token
    from app.core.database import get_db_session
    from app.services.vault_upload_service import get_vault_service

    files = sorted(
        p for p in PACKET_DIR.rglob("*")
        if p.is_file() and p.name not in SKIP_NAMES
    )
    print(f"Importing {len(files)} files for user {USER_ID}")

    async with get_db_session() as db:
        _, token_obj, _ = await ensure_valid_token(USER_ID, db)
        if not token_obj:
            print("FATAL: no valid storage token for", USER_ID)
            sys.exit(1)
        access_token = token_obj.access_token

    vault = get_vault_service()
    manifest = []
    for path in files:
        rel = path.relative_to(PACKET_DIR).as_posix()
        mime = mimetypes.guess_type(path.name)[0]
        if path.suffix.lower() == ".md":
            mime = "text/markdown"
        elif path.suffix.lower() == ".txt":
            mime = "text/plain"
        mime = mime or "application/octet-stream"
        doc = await vault.upload(
            user_id=USER_ID,
            filename=path.name,
            content=path.read_bytes(),
            mime_type=mime,
            document_type="legal_counsel_packet",
            description=rel,
            tags=["legal_counsel_packet", path.parent.name or "root"],
            source_module="legal_share_import",
            access_token=access_token,
            storage_provider="google_drive",
        )
        manifest.append({"path": rel, "vault_id": doc.vault_id,
                         "name": path.name, "mime": mime})
        print(f"  {doc.vault_id}  {rel}")

    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest: {MANIFEST_OUT} ({len(manifest)} docs)")


if __name__ == "__main__":
    asyncio.run(main())
