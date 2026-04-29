# Services re-export from templates.services
# This allows imports like: from app.services.storage import ...
# to resolve to app.templates.services.storage

import sys
import importlib
from pathlib import Path

# Add templates.services to the path for this package
_templates_services = Path(__file__).parent.parent / "templates" / "services"
if _templates_services.exists() and str(_templates_services) not in sys.path:
    sys.path.insert(0, str(_templates_services))

# Re-export common services
try:
    from app.templates.services import vault_upload_service
    from app.templates.services import storage
    from app.templates.services import legal_analysis_engine
    from app.templates.services import communication_service
    from app.templates.services import ocr_service
    from app.templates.services import recognition_service
    from app.templates.services import location_service
    from app.templates.services import calendar_service
    from app.templates.services import plan_maker_service
    from app.templates.services import functionx_service
    from app.templates.services import preview_service
    from app.templates.services import document_delivery_service
    from app.templates.services import legal_filing_service
    from app.templates.services import user_service
    from app.templates.services import auto_mode_summary_service
except ImportError as e:
    # Some services may not exist - that's ok for modular builds
    pass

# Handle optional services with graceful degradation
try:
    from app.templates.services import tenancy_hub
except ImportError:
    tenancy_hub = None

try:
    from app.templates.services import positronic_brain
except ImportError:
    positronic_brain = None
