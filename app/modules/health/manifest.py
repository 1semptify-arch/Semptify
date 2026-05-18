"""
Health Module Manifest

Self-contained SDK module for observability endpoints.
- Liveness/readiness probes (Kubernetes compatible)
- Prometheus metrics
- System dashboard
- API capability summary
"""

from app.sdk import ModuleManifest, ModuleCapability, ProductTier


MANIFEST = ModuleManifest(
    name="health",
    display_name="System Health",
    description="Observability endpoints for monitoring, metrics, and system dashboard",
    version="1.0.0",
    tier=ProductTier.CORE,
    capabilities=(ModuleCapability.ROUTER,),
    router_module="app.modules.health.router",
    tags=("Health",),
    optional=False,
)
