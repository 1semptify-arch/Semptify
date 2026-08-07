"""Check which tiers and modules actually load cleanly."""
import logging
import sys

from fastapi import FastAPI

from app.core.product_manifest import ProductTier, register_tiers

# Capture skipped/error logs
failures = []
_orig = logging.Logger.warning
def _capture(self, msg, *args, **kwargs):
    txt = msg % args if args else str(msg)
    if "skipped" in txt.lower() or "failed" in txt.lower():
        failures.append(txt)
    _orig(self, msg, *args, **kwargs)
logging.Logger.warning = _capture

app = FastAPI()
try:
    register_tiers(app, ProductTier.CORE, ProductTier.DEV, ProductTier.EXTENDED, ProductTier.ADVOCATE, ProductTier.ADMIN)
except Exception as e:
    print(f"FATAL: {e}")
    sys.exit(1)

routes = [r.path for r in app.routes]
print(f"\nRoutes loaded: {len(routes)}")
print(f"Failures captured: {len(failures)}")
for f in failures:
    print(f"  FAIL: {f}")
