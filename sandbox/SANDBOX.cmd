@echo off
rem ============================================================
rem  Semptify SANDBOX - isolated test instance on :8028
rem
rem  Isolation boundary (everything this instance writes stays
rem  inside sandbox\ - nothing touches the working group):
rem    DATABASE_URL      -> sandbox\sandbox.db   (never semptify.db)
rem    SEMPTIFY_UPLOAD_DIR / SEMPTIFY_VAULT_DIR
rem                      -> sandbox\uploads      (never real uploads)
rem    SECURITY_MODE=open, SEMPTIFY_ENV=development
rem                      - no OAuth, no Neon, no cloud calls
rem
rem  Seed the test-data group first (once, or to refresh):
rem    venv311\Scripts\python.exe sandbox\seed_test_data.py
rem  Then after the server is up, hit once per restart:
rem    http://127.0.0.1:8028/debug/seed-test-user
rem  (plants the in-memory dev-godmode token for DB surfaces)
rem ============================================================
cd /d %~dp0..
set "DATABASE_URL=sqlite+aiosqlite:///./sandbox/sandbox.db"
set "SEMPTIFY_UPLOAD_DIR=./sandbox/uploads"
set "SEMPTIFY_VAULT_DIR=./sandbox/uploads/vault"
set "SECURITY_MODE=open"
set "SEMPTIFY_ENV=development"
set "ADMIN_TOKEN=sandbox-admin"
venv311\Scripts\python.exe -m uvicorn app.main:fastapi_app --host 127.0.0.1 --port 8028
