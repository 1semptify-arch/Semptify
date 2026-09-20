"""Vault-resident config transport (prov-role-configs, Step 1d).

Installs the per-role config JSON payloads from ``app.core.vault_configs``
into the tenant's own storage under ``.semptify/configs/``. Same dependency
envelope as ``client.py`` / ``db.py``: stdlib + vault_paths + the storage
provider — no FastAPI, SQLAlchemy, or DB access; gate marking stays with
the caller.

Idempotent semantics per file:
- missing            -> upload (``created``)
- existing, version matches  -> left alone (``verified``)
- existing, older version or unparseable -> replaced (``refreshed``);
  configs are app-generated, never tenant data, so replacement loses nothing
- existing, NEWER version -> left alone (``kept_newer``) — never downgrade
"""

from __future__ import annotations

import json
import logging

from app.core.vault_configs import configs_for_role
from app.core.vault_paths import CONFIGS_FOLDER

logger = logging.getLogger(__name__)

_CONFIG_MIME = "application/json"


def _remote_version(raw: bytes) -> int | None:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    version = payload.get("version")
    return version if isinstance(version, int) else None


async def _upload_config(storage, path: str, payload: dict) -> None:
    folder, _, filename = path.rpartition("/")
    await storage.upload_file(
        file_content=json.dumps(payload, indent=2).encode("utf-8"),
        destination_path=folder,
        filename=filename,
        mime_type=_CONFIG_MIME,
    )


async def ensure_configs_remote(storage, role: str | None) -> dict:
    """Install or refresh the role's config files in the vault.

    Returns ``{"success": True, "role": ..., "files": {path: state}}``.
    Raises ``VaultError``-adjacent provider exceptions to the caller — the
    provisioning step wraps them in its timeout/error envelope.
    """
    await storage.create_folder(CONFIGS_FOLDER)  # idempotent
    states: dict[str, str] = {}
    for path, payload in configs_for_role(role).items():
        wanted = payload["version"]
        if await storage.file_exists(path):
            existing = _remote_version(await storage.download_file(path))
            if existing == wanted:
                states[path] = "verified"
                continue
            if existing is not None and existing > wanted:
                states[path] = "kept_newer"
                continue
            await storage.delete_file(path)
            states[path] = "refreshed"
        else:
            states[path] = "created"
        await _upload_config(storage, path, payload)
    return {"success": True, "role": role or "unknown", "files": states}
