"""List all admin console routes for verification."""

from app.main import app

admin_routes = []
for r in app.routes:
    if not hasattr(r, "path"):
        continue
    path = r.path
    if path.startswith("/admin") or path.startswith("/admin-console"):
        methods = sorted(r.methods) if hasattr(r, "methods") else []
        admin_routes.append((methods, path))

admin_routes.sort(key=lambda x: x[1])
print(f"Admin routes: {len(admin_routes)}")
for methods, path in admin_routes:
    print(f"  {','.join(methods):20s} {path}")
