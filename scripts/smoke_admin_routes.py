"""Smoke test all admin console GET endpoints.

Without admin auth, most should return:
  - 200 (public pages like /admin/login)
  - 302 (redirect to login for protected pages)
  - 404 (stealth admin guard returns 404 to non-admins)

FAILURES = any 500 (server error) or 502/503/504.
"""

import sys

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

admin_routes = []
for r in app.routes:
    if not hasattr(r, "path"):
        continue
    path = r.path
    if path.startswith("/admin") or path.startswith("/admin-console"):
        methods = set(r.methods) if hasattr(r, "methods") else set()
        if "GET" in methods:
            admin_routes.append(path)

admin_routes.sort()
print(f"Testing {len(admin_routes)} admin GET endpoints...\n")

results = {"ok": [], "redirect": [], "not_found": [], "errors": []}

for path in admin_routes:
    try:
        resp = client.get(path, follow_redirects=False)
        code = resp.status_code
        if code == 200:
            results["ok"].append((path, code))
        elif code in (301, 302, 303, 307, 308):
            results["redirect"].append((path, code))
        elif code == 404:
            results["not_found"].append((path, code))
        elif code >= 500:
            results["errors"].append((path, code, resp.text[:200]))
        else:
            results["ok"].append((path, code))  # 401/403 etc. are fine
    except Exception as exc:
        results["errors"].append((path, "EXC", str(exc)[:200]))

print(f"OK (200/4xx):      {len(results['ok'])}")
print(f"Redirects (3xx):   {len(results['redirect'])}")
print(f"Not Found (404):   {len(results['not_found'])}")
print(f"ERRORS (5xx/EXC):  {len(results['errors'])}")

if results["errors"]:
    print("\n=== ERRORS ===")
    for path, code, detail in results["errors"]:
        print(f"  {code} {path}")
        print(f"      {detail[:150]}")

if results["redirect"]:
    print("\n=== REDIRECTS ===")
    for path, code in results["redirect"]:
        print(f"  {code} {path}")

if results["not_found"]:
    print("\n=== NOT FOUND (stealth admin guard — expected without auth) ===")
    for path, code in results["not_found"]:
        print(f"  {code} {path}")

sys.exit(1 if results["errors"] else 0)
