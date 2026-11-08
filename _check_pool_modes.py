"""One-shot pool-mode check for neon-db-pool-nullpool-render-balanced.

Spawns a fresh interpreter per env combination (get_settings is lru_cached)
and prints the resolved engine pool class. Read-only: no DB connection is
ever opened -- create_async_engine only builds the object.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = ROOT / "venv311" / "Scripts" / "python.exe"

SNIPPET = (
    "from app.core import database as d\n"
    "d._engine = None\n"
    "e = d.get_engine()\n"
    "print(type(e.pool).__name__)\n"
)

PG_URL = "postgresql+asyncpg://u:p@ep-fake.neon.tech/semptify"
SQLITE_MEM = "sqlite+aiosqlite:///:memory:"
SQLITE_FILE = "sqlite+aiosqlite:///./_poolcheck.db"

COMBOS = [
    ("render_auto_nullpool", {"RENDER": "1", "DATABASE_URL": PG_URL}, "NullPool"),
    ("local_auto_queue", {"DATABASE_URL": PG_URL}, "AsyncAdaptedQueuePool"),
    ("local_explicit_nullpool", {"DATABASE_URL": PG_URL, "DB_POOL_MODE": "nullpool"}, "NullPool"),
    ("render_explicit_queue", {"RENDER": "1", "DATABASE_URL": PG_URL, "DB_POOL_MODE": "queue"}, "AsyncAdaptedQueuePool"),
    ("local_queue_sizes", {"DATABASE_URL": PG_URL, "DB_POOL_MODE": "queue", "DB_POOL_SIZE": "3", "DB_MAX_OVERFLOW": "7"}, "AsyncAdaptedQueuePool"),
    ("sqlite_memory_static", {"DATABASE_URL": SQLITE_MEM}, "StaticPool"),
    ("sqlite_file_nullpool", {"DATABASE_URL": SQLITE_FILE}, "NullPool"),
]

fails = []
for name, env_add, expected in COMBOS:
    env = dict(os.environ)
    env.pop("RENDER", None)
    env.pop("DB_POOL_MODE", None)
    env.pop("DB_POOL_SIZE", None)
    env.pop("DB_MAX_OVERFLOW", None)
    env["DB_SSL_MODE"] = "disable"
    env.update(env_add)
    r = subprocess.run(
        [str(PY), "-c", SNIPPET], cwd=str(ROOT), env=env,
        capture_output=True, text=True, timeout=60,
    )
    got = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    ok = r.returncode == 0 and got == expected
    print(f"{'PASS' if ok else 'FAIL'} {name}: expected={expected} got={got!r} rc={r.returncode}")
    if not ok:
        fails.append(name)
        if r.stderr:
            print("   stderr:", r.stderr.strip().splitlines()[-1][:300])

print(f"\n{len(COMBOS) - len(fails)}/{len(COMBOS)} pool-mode checks pass")
sys.exit(1 if fails else 0)
