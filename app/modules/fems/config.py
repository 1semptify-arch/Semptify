"""FEMS module configuration — reads from Semptify environment."""

import os
from pathlib import Path

FEMS_ENABLED = os.getenv("FEMS_ENABLED", "true").lower() == "true"
FEMS_INBOX_DIR = Path(os.getenv("FEMS_INBOX_DIR", "data/fems/inbox"))
FEMS_QUARANTINE_DIR = Path(os.getenv("FEMS_QUARANTINE_DIR", "data/fems/quarantine"))
FEMS_PREFIX = "/api/fems"
FEMS_MAX_UPLOAD_BYTES = int(os.getenv("FEMS_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))


def ensure_dirs():
    FEMS_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    FEMS_QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
