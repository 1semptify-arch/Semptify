# Re-export from templates.services.tenancy_hub
try:
    from app.templates.services.tenancy_hub import *
except ImportError:
    # Stub for Core build where tenancy_hub is not available
    def get_tenancy_hub_service():
        raise RuntimeError("Tenancy hub not available in Core build")
