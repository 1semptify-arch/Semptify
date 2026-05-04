"""
Semptify - FastAPI Application
Tenant rights protection platform.

Core Promise: Help tenants with tools and information to uphold tenant rights,
in court if it goes that far - hopefully it won't.
"""

# Fix Windows console encoding for emojis
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Python version check - Semptify requires Python 3.11+
python_version = sys.version_info
if python_version >= (3, 14):
    print("=" * 70)
    print("⚠️  CRITICAL WARNING: Python 3.14+ detected!")
    print("=" * 70)
    print("Semptify is NOT compatible with Python 3.14.")
    print("Python 3.14 has known compatibility issues with required packages.")
    print("")
    print("Please use Python 3.11 or 3.12 instead:")
    print("  1. Install Python 3.11: https://python.org/downloads/release/python-3119/")
    print("  2. Create a virtual environment: python3.11 -m venv venv")
    print("  3. Activate and reinstall dependencies")
    print("=" * 70)
    sys.exit(1)
elif python_version < (3, 11):
    print("=" * 70)
    print("⚠️  ERROR: Python version too old!")
    print("=" * 70)
    print(f"Detected Python {python_version.major}.{python_version.minor}")
    print("Semptify requires Python 3.11 or higher.")
    print("=" * 70)
    sys.exit(1)
else:
    # Log Python version for debugging
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro} - Compatible")

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.compliance import validate_app_compliance
from app.core.database import init_db, close_db

# PyInstaller frozen executable detection
def get_base_path() -> Path:
    """Get base path - handles PyInstaller frozen mode."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return Path(getattr(sys, "_MEIPASS", "."))
    return Path(".")

BASE_PATH = get_base_path()

# Jinja2 templates for frontend UI pages
templates = Jinja2Templates(directory=str(BASE_PATH / "app" / "templates"))

def _safe_router_import(module_path: str):
    try:
        module = __import__(module_path, fromlist=["router"])
        return getattr(module, "router")
    except (ImportError, AttributeError) as ex:
        logging.getLogger(__name__).warning("Router import failed (%s): %s", module_path, ex)
        return None

# =============================================================================
# SEMPTIFY 5.0 CORE — Lightweight Base (always active)
# Philosophy: Document Everything. Avoid the Pitfalls.
# =============================================================================
from app.routers import health
from app.routers import storage
from app.routers import onboarding
from app.routers import plugins
from app.routers import development

# Core Document/Vault System
documents_router        = _safe_router_import("app.routers.documents")
vault_router            = _safe_router_import("app.routers.vault")
vault_engine_router     = _safe_router_import("app.routers.vault_engine")
timeline_unified_router = _safe_router_import("app.routers.timeline_unified")
briefcase_router        = _safe_router_import("app.routers.briefcase")  # Vault viewer
workflow_router         = _safe_router_import("app.routers.workflow")
role_ui_router          = _safe_router_import("app.routers.role_ui")
websocket_router        = _safe_router_import("app.routers.websocket")
free_api_router         = _safe_router_import("app.routers.free_api")

# Core Rights & Education
state_laws_router       = _safe_router_import("app.routers.state_laws")
law_library_router      = _safe_router_import("app.routers.law_library")

# Core Tools (lightweight utilities)
contacts_router         = _safe_router_import("app.routers.contacts")
search_router           = _safe_router_import("app.routers.search")
pdf_tools_router        = _safe_router_import("app.routers.pdf_tools")
preview_router          = _safe_router_import("app.routers.preview")
document_converter_router = _safe_router_import("app.routers.document_converter")
legal_analysis_router   = _safe_router_import("app.routers.legal_analysis")  # Brain-optional

# Workflow Validator (admin/diagnostic tool)
workflow_validator_router = _safe_router_import("app.routers.workflow_validator")

# Disabled for tenant-only core build
role_upgrade_router     = None  # Multi-role feature - deferred
invite_codes_router     = None  # Collaboration feature - deferred

# =============================================================================
# SEMPTIFY EXTENDED — EVICTION DEFENSE ADD-ON (disabled)
# To enable: uncomment the lines below and add consent gate
# =============================================================================
# eviction_defense_router  = _safe_router_import("app.routers.eviction_defense")
# zoom_court_router        = _safe_router_import("app.routers.zoom_court")
# zoom_court_prep_router   = _safe_router_import("app.routers.zoom_court_prep")
eviction_defense_router  = None
zoom_court_router        = None
zoom_court_prep_router   = None
# Dakota County Eviction Defense Module
# try:
#     from app.routers.eviction import (
#         flows_router as dakota_flows,
#         forms_router as dakota_forms,
#         case_router as dakota_case,
#         learning_router as dakota_learning,
#         procedures_router as dakota_procedures,
#     )
#     DAKOTA_AVAILABLE = True
# except ImportError as e:
#     logging.getLogger(__name__).warning("Dakota County module import failed: %s", e)
#     DAKOTA_AVAILABLE = False
DAKOTA_AVAILABLE = False

# =============================================================================
# SEMPTIFY CORE — MNDES (MN Court Exhibit System) — ALWAYS ENABLED
# Required for MN Supreme Court Order ADM09-8010 compliance (eff. Jan 1, 2025)
# =============================================================================
mndes_router = _safe_router_import("app.routers.mndes")

# =============================================================================
# SEMPTIFY EXTENDED — LEGAL/COURT ADD-ON (disabled)
# Heavy legal filing features - enable for Extended build
# =============================================================================
court_forms_router    = None
court_packet_router   = None
legal_filing_router   = None
legal_trails_router   = None

# =============================================================================
# SEMPTIFY EXTENDED — CASE MANAGEMENT ADD-ON (disabled)
# =============================================================================
# intake_router        = _safe_router_import("app.routers.intake")
# guided_intake_router = _safe_router_import("app.routers.guided_intake")
# case_builder_router  = _safe_router_import("app.routers.case_builder")
# progress_router      = _safe_router_import("app.routers.progress")
# actions_router       = _safe_router_import("app.routers.actions")
# plan_maker_router    = _safe_router_import("app.routers.plan_maker")
# tools_api_router     = _safe_router_import("app.routers.tools_api")
intake_router        = None
guided_intake_router = None
case_builder_router  = None
progress_router      = None
actions_router       = None
plan_maker_router    = None
tools_api_router     = None

# =============================================================================
# OTHER DIVISION — Preserved for Future Product Lines
# These serve different purposes than Core tenant journaling
# =============================================================================
# Campaign/Public/Fraud modules - for separate advocacy product lines
# campaign_router         = _safe_router_import("app.routers.campaign")
# public_exposure_router  = _safe_router_import("app.routers.public_exposure")
# fraud_exposure_router   = _safe_router_import("app.routers.fraud_exposure")
campaign_router         = None   # Marketing/Public Division
public_exposure_router  = None   # Advocacy Division
fraud_exposure_router   = None   # Investigation Division

# Complaints - could be Core or Extended depending on scope
# complaints_router    = _safe_router_import("app.routers.complaints")
complaints_router       = None

# =============================================================================
# SEMPTIFY EXTENDED — ADVOCATE NETWORK ADD-ON (disabled)
# Requires: user consent to share documents with advocates
# =============================================================================
# communication_router      = _safe_router_import("app.routers.communication")
# document_delivery_router  = _safe_router_import("app.routers.document_delivery")
communication_router      = None
document_delivery_router  = None
# Tenant Defense Module
# from app.modules.tenant_defense import router as tenant_defense_router
tenant_defense_router = None

# =============================================================================
# SEMPTIFY EXTENDED — FUNDING SEARCH ADD-ON (disabled)
# =============================================================================
# funding_search_router = _safe_router_import("app.routers.funding_search")
# hud_funding_router    = _safe_router_import("app.routers.hud_funding")
# location_router       = _safe_router_import("app.routers.location")
funding_search_router = None
hud_funding_router    = None
location_router       = None

# =============================================================================
# SEMPTIFY EXTENDED — ADMIN / REPORTING ADD-ON (disabled)
# =============================================================================
# analytics_router           = _safe_router_import("app.routers.analytics")
# dashboard_router           = _safe_router_import("app.routers.dashboard")
# enterprise_dashboard_router = _safe_router_import("app.routers.enterprise_dashboard")
# batch_router               = _safe_router_import("app.routers.batch")
# registry_router            = _safe_router_import("app.routers.registry")
# tenancy_hub_router         = _safe_router_import("app.routers.tenancy_hub")
analytics_router           = None
dashboard_router           = None
enterprise_dashboard_router = None
batch_router               = None
registry_router            = None
tenancy_hub_router         = None

# =============================================================================
# SEMPTIFY RESEARCH — AI INTELLIGENCE ADD-ON (disabled)
# Requires: explicit user consent to allow AI to read documents
# =============================================================================
# recognition_router      = _safe_router_import("app.routers.recognition")
# extraction_router       = _safe_router_import("app.routers.extraction")
# crawler_router          = _safe_router_import("app.routers.crawler")
# research_router         = _safe_router_import("app.routers.research")
# research_module_router  = _safe_router_import("app.modules.research_module")
# form_data_router        = _safe_router_import("app.routers.form_data")
# overlays_router         = _safe_router_import("app.routers.overlays")
# unified_overlays_router = _safe_router_import("app.routers.unified_overlays")
# vault_all_in_one_router = _safe_router_import("app.routers.vault_all_in_one")
# cloud_sync_router       = _safe_router_import("app.routers.cloud_sync")
recognition_router      = None
extraction_router       = None
crawler_router          = None
research_router         = None
research_module_router  = None
form_data_router        = None
overlays_router         = None
unified_overlays_router = None
vault_all_in_one_router = None
cloud_sync_router       = None

# =============================================================================
# SEMPTIFY AI INFRASTRUCTURE — Internal (disabled)
# =============================================================================
# brain_router           = _safe_router_import("app.routers.brain")
# auto_mode_router       = _safe_router_import("app.routers.auto_mode")
# emotion_router         = _safe_router_import("app.routers.emotion")
# positronic_mesh_router = _safe_router_import("app.routers.positronic_mesh")
# mesh_network_router    = _safe_router_import("app.routers.mesh_network")
# distributed_mesh_router = _safe_router_import("app.routers.mesh")
# module_hub_router      = _safe_router_import("app.routers.module_hub")
# functionx_router       = _safe_router_import("app.routers.functionx")
brain_router           = None
auto_mode_router       = None
emotion_router         = None
positronic_mesh_router = None
mesh_network_router    = None
distributed_mesh_router = None
module_hub_router      = None
functionx_router       = None

# =============================================================================
# DEV / INTERNAL ONLY
# =============================================================================
setup_router    = _safe_router_import("app.routers.setup")
page_index_router = _safe_router_import("app.routers.page_index")


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging():
    """Configure logging based on settings using enhanced logging config."""
    from app.core.logging_config import setup_logging as configure_logging
    logging_settings = get_settings()
    configure_logging(
        level=logging_settings.log_level.upper(),
        json_format=logging_settings.log_json_format,
        log_file=Path("logs/semptify.log") if logging_settings.log_json_format else None,
    )


# =============================================================================
# Lifespan (Startup/Shutdown)
# =============================================================================

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Application lifespan handler with staged setup.
    - Runs setup in stages with verification
    - Retries failed stages up to max attempts
    - Total timeout: 20 seconds
    - If all retries fail, wipes and starts fresh
    """
    lifespan_settings = get_settings()
    logger = logging.getLogger(__name__)
    
    # Configuration
    TOTAL_TIMEOUT = 20  # Total seconds allowed for setup
    MAX_RETRIES = 3     # Max retries per stage
    STAGE_DELAY = 0.5   # Delay between retries
    
    import time
    import shutil
    start_time = time.time()
    
    def time_remaining():
        return max(0, TOTAL_TIMEOUT - (time.time() - start_time))
    
    def log_stage(stage_num: int, total: int, name: str, status: str):
        elapsed = time.time() - start_time
        remaining = time_remaining()
        bar = "█" * stage_num + "░" * (total - stage_num)
        logger.info("[%s] Stage %s/%s: %s - %s (%.1fs elapsed, %.1fs remaining)", bar, stage_num, total, name, status, elapsed, remaining)
    
    async def run_stage(stage_num: int, total: int, name: str, action, verify=None):
        """Run a stage with retries and verification."""
        for attempt in range(1, MAX_RETRIES + 1):
            if time_remaining() <= 0:
                raise TimeoutError(f"Setup timeout - exceeded {TOTAL_TIMEOUT}s")
            
            try:
                log_stage(stage_num, total, name, f"Attempt {attempt}/{MAX_RETRIES}...")
                if asyncio.iscoroutinefunction(action):
                    await action()
                else:
                    action()
                
                # Verify if verification function provided
                if verify:
                    await asyncio.sleep(0.2)  # Brief pause before verify
                    is_valid = await verify() if asyncio.iscoroutinefunction(verify) else verify()
                    if not is_valid:
                        raise RuntimeError(f"Verification failed for {name}")
                
                log_stage(stage_num, total, name, "✅ COMPLETE")
                return True
                
            except (ValueError, RuntimeError, ImportError, AssertionError, TimeoutError) as e:
                logger.warning("Stage %s '%s' attempt %s failed: %s", stage_num, name, attempt, e)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(STAGE_DELAY)
                else:
                    raise RuntimeError(f"Stage {stage_num} '{name}' failed after {MAX_RETRIES} attempts: {e}") from e
        return False
    
    async def wipe_and_reset():
        """Wipe everything clean for fresh start."""
        logger.warning("=" * 50)
        logger.warning("⚠️  WIPING EVERYTHING FOR FRESH START...")
        logger.warning("=" * 50)
        
        # Remove runtime directories
        dirs_to_wipe = ["uploads", "logs", "data/semptify.db"]
        for dir_path in dirs_to_wipe:
            path = Path(dir_path)
            if path.exists():
                if path.is_file():
                    path.unlink()
                    logger.info("  Removed file: %s", dir_path)
                else:
                    shutil.rmtree(path, ignore_errors=True)
                    logger.info("  Removed directory: %s", dir_path)
        
        # Sessions and OAuth states are now DB-backed (no in-memory dicts to clear)
        logger.info("  Sessions/OAuth states are DB-backed - no cache to clear")
        
        logger.warning("🧹 Wipe complete - ready for fresh start")
    
    # =========================================================================
    # STAGED SETUP PROCESS
    # =========================================================================
    
    TOTAL_STAGES = 6
    
    # Required packages for each feature area
    REQUIRED_PACKAGES = {
        # Core
        "fastapi": "Core Framework",
        "uvicorn": "ASGI Server",
        "pydantic": "Data Validation",
        "pydantic_settings": "Settings Management",
        # Database
        "sqlalchemy": "Database ORM",
        "aiosqlite": "SQLite Async Driver",
        # HTTP
        "httpx": "HTTP Client",
        # Security
        "cryptography": "Encryption (AES-256-GCM)",
        # PDF
        "reportlab": "PDF Generation",
        "PyPDF2": "PDF Manipulation",
        # Calendar
        "icalendar": "iCal Generation",
        # Templates
        "jinja2": "HTML Templates",
        "aiofiles": "Async File I/O",
    }
    
    # Optional packages (warn if missing, don't fail)
    OPTIONAL_PACKAGES = {
        "PIL": "Image Processing (Pillow)",
        "magic": "MIME Detection (python-magic)",
        "xhtml2pdf": "Advanced PDF (xhtml2pdf)",
        "asyncpg": "PostgreSQL Driver",
    }
    
    logger.info("=" * 60)
    logger.info("🚀 STARTING %s v%s", lifespan_settings.app_name, lifespan_settings.app_version)
    logger.info("   Security mode: %s", lifespan_settings.security_mode)
    logger.info("   Timeout: %ss | Retries per stage: %s", TOTAL_TIMEOUT, MAX_RETRIES)
    logger.info("=" * 60)
    
    try:
        # --- STAGE 1: Verify Requirements ---
        missing_required = []
        missing_optional = []
        
        def check_requirements():
            nonlocal missing_required, missing_optional
            import importlib
            
            # Clear lists before checking (fix for retry accumulation)
            missing_required.clear()
            missing_optional.clear()
            
            # Check required packages
            for pkg, desc in REQUIRED_PACKAGES.items():
                try:
                    importlib.import_module(pkg)
                except ImportError:
                    missing_required.append(f"{pkg} ({desc})")
            
            # Check optional packages
            for pkg, desc in OPTIONAL_PACKAGES.items():
                try:
                    importlib.import_module(pkg)
                except ImportError:
                    missing_optional.append(f"{pkg} ({desc})")
            
            if missing_required:
                raise ImportError(f"Missing required packages: {', '.join(missing_required)}")
        
        def verify_requirements():
            if missing_optional:
                for pkg in missing_optional:
                    logger.warning("   ⚠️  Optional: %s not installed", pkg)
            return len(missing_required) == 0
        
        await run_stage(1, TOTAL_STAGES, "Verify Requirements", check_requirements, verify_requirements)
        
        # --- STAGE 2: Create Runtime Directories ---
        runtime_dirs = ["uploads", "uploads/vault", "logs", "security", "data"]
        
        def create_directories():
            for dir_path in runtime_dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        def verify_directories():
            return all(Path(d).exists() for d in runtime_dirs)
        
        await run_stage(2, TOTAL_STAGES, "Create Directories", create_directories, verify_directories)
        
        # --- STAGE 3: Initialize Database ---
        async def init_database():
            await init_db()
        
        async def verify_database():
            # Quick DB check
            from app.core.database import get_db
            try:
                async for db in get_db():
                    from sqlalchemy import text
                    await db.execute(text("SELECT 1"))
                    return True
            except SQLAlchemyError:
                return False
        
        await run_stage(3, TOTAL_STAGES, "Initialize Database", init_database, verify_database)
        
        # --- STAGE 4: Load Configuration ---
        async def load_config():
            # Verify settings are accessible
            _ = lifespan_settings.app_name
            _ = lifespan_settings.security_mode
        
        def verify_config():
            return lifespan_settings.app_name is not None
        
        await run_stage(4, TOTAL_STAGES, "Load Configuration", load_config, verify_config)
        
        # --- STAGE 5: Initialize Services ---
        async def init_services():
            # DISABLED: Memory-heavy services not needed for core functionality
            # TODO: Re-enable after Phase 1 MVP is stable
            
            # Positronic Brain - DISABLED (memory hog)
            # from app.services.brain_integrations import initialize_brain_connections
            # await initialize_brain_connections()
            # logger.info("   🧠 Positronic Brain initialized with all modules")
            
            # Module Hub & Mesh - DISABLED (memory hog)
            # from app.services.module_registration import register_all_modules
            # from app.services.module_actions import register_all_actions
            # register_all_modules()
            # register_all_actions()
            # logger.info("   🔗 Module Hub initialized")
            
            # Location Service - DISABLED
            # from app.services.location_service import register_with_mesh
            # register_with_mesh()
            # logger.info("   📍 Location Service initialized")
            
            # Complaint Wizard - DISABLED
            # from app.modules.complaint_wizard_module import register_with_mesh as register_complaint_wizard
            # register_complaint_wizard()
            # logger.info("   📝 Complaint Wizard initialized")
            
            # Mesh Network - DISABLED (major memory consumer)
            # from app.services.mesh_handlers import register_all_mesh_handlers
            # mesh_stats = register_all_mesh_handlers()
            # logger.info("   🕸️ Mesh Network initialized")

            # Plugin System - DISABLED
            # from app.sdk.plugin_manager import plugin_manager
            # discovered_plugins = plugin_manager.discover_plugins()
            # plugin_stats = plugin_manager.load_all()
            
            logger.info("   ⚡ Core services only - mesh/brain/plugins DISABLED for memory optimization")
        
        await run_stage(5, TOTAL_STAGES, "Initialize Services", init_services)
        
        # --- STAGE 6: Final Verification ---
        async def final_check():
            # Verify critical paths exist
            assert Path("uploads/vault").exists(), "Vault directory missing"
            assert Path("data").exists(), "Data directory missing"
        
        async def verify_final():
            # Test a simple endpoint would work
            return True
        
        await run_stage(6, TOTAL_STAGES, "Final Verification", final_check, verify_final)
        
        # --- STAGE 7: PRODUCTION MODE VALIDATION (if enforced) ---
        if lifespan_settings.security_mode == "enforced":
            TOTAL_STAGES = 7
            
            async def validate_production():
                """Validate production security requirements."""
                from app.core.production_init import validate_production_mode
                # This will raise an error if any security requirement fails
                validate_production_mode()
            
            def verify_production():
                return True  # If we get here, validation passed
            
            await run_stage(7, TOTAL_STAGES, "Production Security Validation", validate_production, verify_production)
        
        # --- SETUP COMPLETE ---
        total_time = time.time() - start_time
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ ✅ ✅  ALL STAGES COMPLETE  ✅ ✅ ✅")
        logger.info("   Setup completed in %.2f seconds", total_time)
        logger.info("")
        if lifespan_settings.security_mode == "enforced":
            logger.info("   🔒 PRODUCTION MODE: ENFORCED SECURITY ACTIVE")
        logger.info("   🌐 Server: http://localhost:8000")
        logger.info("   📄 Welcome: http://localhost:8000/")
        logger.info("   📚 API Docs: http://localhost:8000/api/docs")
        logger.info("=" * 60)
        logger.info("")
        
    except TimeoutError as e:
        logger.error("❌ SETUP TIMEOUT: %s", e)
        await wipe_and_reset()
        raise SystemExit("Setup failed - timeout exceeded") from e
        
    except (RuntimeError, ValueError, ImportError, AssertionError, OSError) as e:
        logger.error("❌ SETUP FAILED: %s", e)
        await wipe_and_reset()
        raise SystemExit(f"Setup failed after retries: {e}") from e
    
    # Register graceful shutdown handler
    from app.core.shutdown import register_shutdown_handler, task_manager
    register_shutdown_handler()
    
    # DISABLED: Distributed mesh network (memory hog)
    # try:
    #     await start_mesh_network()
    #     logger.info("🌐 Distributed Mesh Network started")
    # except (OSError, RuntimeError, ValueError) as e:
    #     logger.warning("⚠️ Mesh network start warning: %s", e)

    yield  # Application runs here

    # --- GRACEFUL SHUTDOWN ---
    logger.info("")
    logger.info("=" * 50)
    logger.info("🛑 SHUTTING DOWN GRACEFULLY...")
    logger.info("=" * 50)
    
    # Wait for background tasks to complete
    await task_manager.wait_for_completion(timeout=10.0)
    logger.info("   Background tasks completed")

    # DISABLED: Distributed mesh network
    # try:
    #     await stop_mesh_network()
    #     logger.info("🌐 Distributed Mesh Network stopped")
    # except (OSError, RuntimeError, ValueError) as e:
    #     logger.warning("⚠️ Mesh network stop warning: %s", e)

    await close_db()
    logger.info("   Database connections closed")
    logger.info("   Goodbye! 👋")
    logger.info("=" * 50)
# =============================================================================
# HTML Page Generators for Legal Tools
# =============================================================================

def generate_law_library_html() -> str:
    """Generate law library HTML page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Law Library - Semptify</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #064e3b 0%, #065f46 100%);
            color: #fff;
            min-height: 100vh;
        }
        .header {
            background: rgba(0,0,0,0.2);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 1.5rem; font-weight: 700; }
        .nav-links { display: flex; gap: 1rem; }
        .nav-links a {
            color: #a7f3d0;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .nav-links a:hover { background: rgba(255,255,255,0.1); }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .page-title { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; }
        .page-subtitle { color: #a7f3d0; margin-bottom: 2rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s;
            cursor: pointer;
        }
        .card:hover { transform: translateY(-4px); background: rgba(255,255,255,0.15); }
        .card-icon { font-size: 2.5rem; margin-bottom: 1rem; }
        .card-title { font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; }
        .card-desc { color: #a7f3d0; font-size: 0.9rem; }
        .search-box {
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 2rem;
            display: flex;
            gap: 1rem;
        }
        .search-box input {
            flex: 1;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            color: white;
            font-size: 1rem;
        }
        .search-box input::placeholder { color: #a7f3d0; }
        .search-box button {
            background: #10b981;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
        }
        .search-box button:hover { background: #059669; }
        .librarian-chat {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            margin-top: 2rem;
        }
        .chat-title { font-size: 1.25rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
        .chat-messages {
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            padding: 1rem;
            height: 300px;
            overflow-y: auto;
            margin-bottom: 1rem;
        }
        .message { margin-bottom: 1rem; padding: 0.75rem; border-radius: 8px; }
        .message.user { background: #10b981; margin-left: 20%; }
        .message.bot { background: rgba(255,255,255,0.1); margin-right: 20%; }
        .chat-input {
            display: flex;
            gap: 0.5rem;
        }
        .chat-input input {
            flex: 1;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            color: white;
        }
        .chat-input button {
            background: #10b981;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
        }
        #results { margin-top: 2rem; }
        .result-item {
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .result-title { font-weight: 600; margin-bottom: 0.5rem; }
        .result-citation { color: #a7f3d0; font-size: 0.9rem; }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">📚 Semptify Law Library</div>
        <nav class="nav-links">
            <a href="/documents">📄 Documents</a>
            <a href="/timeline">📅 Timeline</a>
            <a href="/eviction-defense">⚖️ Eviction Defense</a>
            <a href="/zoom-court">💻 Zoom Court</a>
        </nav>
    </header>
    <div class="container">
        <h1 class="page-title">Law Library</h1>
        <p class="page-subtitle">Minnesota Tenant Rights & Housing Law Reference</p>
        
        <div class="search-box">
            <input type="text" id="search-input" placeholder="Search statutes, case law, rights...">
            <button onclick="searchLaw()">🔍 Search</button>
        </div>
        
        <div class="grid">
            <div class="card" onclick="browseCategory('tenant_rights')">
                <div class="card-icon">🏠</div>
                <div class="card-title">Tenant Rights</div>
                <div class="card-desc">Your fundamental rights as a tenant in Minnesota</div>
            </div>
            <div class="card" onclick="browseCategory('eviction')">
                <div class="card-icon">⚖️</div>
                <div class="card-title">Eviction Procedures</div>
                <div class="card-desc">Legal requirements for eviction in MN</div>
            </div>
            <div class="card" onclick="browseCategory('security_deposits')">
                <div class="card-icon">💰</div>
                <div class="card-title">Security Deposits</div>
                <div class="card-desc">Deposit limits, return requirements, deductions</div>
            </div>
            <div class="card" onclick="browseCategory('habitability')">
                <div class="card-icon">🔧</div>
                <div class="card-title">Habitability</div>
                <div class="card-desc">Landlord's duty to maintain livable conditions</div>
            </div>
            <div class="card" onclick="browseCategory('retaliation')">
                <div class="card-icon">🛡️</div>
                <div class="card-title">Retaliation Protection</div>
                <div class="card-desc">Protection against landlord retaliation</div>
            </div>
            <div class="card" onclick="browseCategory('discrimination')">
                <div class="card-icon">👥</div>
                <div class="card-title">Fair Housing</div>
                <div class="card-desc">Anti-discrimination protections</div>
            </div>
        </div>
        
        <div id="results"></div>
        
        <div class="librarian-chat">
            <div class="chat-title">🤖 AI Legal Librarian</div>
            <div class="chat-messages" id="chat-messages">
                <div class="message bot">Hello! I'm your AI legal librarian. I can help you find relevant statutes, case law, and understand your tenant rights. What would you like to know?</div>
            </div>
            <div class="chat-input">
                <input type="text" id="chat-input" placeholder="Ask about tenant rights, eviction, security deposits...">
                <button onclick="askLibrarian()">Send</button>
            </div>
        </div>
    </div>
    <script>
        async function searchLaw() {
            const query = document.getElementById('search-input').value;
            if (!query) return;
            const res = await fetch('/api/law-library/statutes?search=' + encodeURIComponent(query));
            const data = await res.json();
            displayResults(data);
        }
        
        async function browseCategory(cat) {
            const res = await fetch('/api/law-library/statutes?category=' + cat);
            const data = await res.json();
            displayResults(data);
        }
        
        function displayResults(data) {
            const container = document.getElementById('results');
            if (!data.length) {
                container.innerHTML = '<p style="text-align:center; color:#a7f3d0;">No results found</p>';
                return;
            }
            container.innerHTML = data.map(s => `
                <div class="result-item">
                    <div class="result-title">${s.title}</div>
                    <div class="result-citation">${s.citation}</div>
                    <p style="margin-top:0.5rem">${s.summary}</p>
                </div>
            `).join('');
        }
        
        async function askLibrarian() {
            const input = document.getElementById('chat-input');
            const messages = document.getElementById('chat-messages');
            const question = input.value.trim();
            if (!question) return;
            
            messages.innerHTML += '<div class="message user">' + question + '</div>';
            input.value = '';
            
            try {
                const res = await fetch('/api/law-library/librarian/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question })
                });
                const data = await res.json();
                messages.innerHTML += '<div class="message bot">' + data.answer + '</div>';
            } catch (e) {
                messages.innerHTML += '<div class="message bot">I apologize, I encountered an error. Please try again.</div>';
            }
            messages.scrollTop = messages.scrollHeight;
        }
        
        document.getElementById('chat-input').addEventListener('keypress', e => {
            if (e.key === 'Enter') askLibrarian();
        });
        document.getElementById('search-input').addEventListener('keypress', e => {
            if (e.key === 'Enter') searchLaw();
        });
    </script>
</body>
</html>"""


def generate_eviction_defense_html() -> str:
    """Generate eviction defense toolkit HTML page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eviction Defense - Semptify</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%);
            color: #fff;
            min-height: 100vh;
        }
        .header {
            background: rgba(0,0,0,0.2);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 1.5rem; font-weight: 700; }
        .nav-links { display: flex; gap: 1rem; }
        .nav-links a {
            color: #fecaca;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .nav-links a:hover { background: rgba(255,255,255,0.1); }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .page-title { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; }
        .page-subtitle { color: #fecaca; margin-bottom: 2rem; }
        .tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }
        .tab {
            background: rgba(255,255,255,0.1);
            border: none;
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        .tab:hover, .tab.active { background: #ef4444; }
        .content-panel { display: none; }
        .content-panel.active { display: block; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 1.5rem; }
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s;
        }
        .card:hover { transform: translateY(-4px); background: rgba(255,255,255,0.15); }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .card-title { font-size: 1.1rem; font-weight: 600; }
        .card-badge {
            background: #ef4444;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
        }
        .card-desc { color: #fecaca; font-size: 0.9rem; margin-bottom: 1rem; }
        .card-btn {
            background: #ef4444;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            width: 100%;
        }
        .card-btn:hover { background: #dc2626; }
        .timeline {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
        }
        .timeline-item {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            position: relative;
        }
        .timeline-item::before {
            content: '';
            position: absolute;
            left: 15px;
            top: 30px;
            bottom: -20px;
            width: 2px;
            background: rgba(255,255,255,0.2);
        }
        .timeline-item:last-child::before { display: none; }
        .timeline-dot {
            width: 32px;
            height: 32px;
            background: #ef4444;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            flex-shrink: 0;
        }
        .timeline-content { flex: 1; }
        .timeline-title { font-weight: 600; margin-bottom: 0.25rem; }
        .timeline-desc { color: #fecaca; font-size: 0.9rem; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
        .stat-card {
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
        }
        .stat-value { font-size: 2rem; font-weight: 700; }
        .stat-label { color: #fecaca; font-size: 0.85rem; }
        #motion-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal-content {
            background: #1f2937;
            border-radius: 16px;
            padding: 2rem;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            margin: 2rem;
        }
        .modal-close {
            float: right;
            background: none;
            border: none;
            color: white;
            font-size: 1.5rem;
            cursor: pointer;
        }
        .template-text {
            background: rgba(0,0,0,0.3);
            padding: 1rem;
            border-radius: 8px;
            font-family: monospace;
            white-space: pre-wrap;
            font-size: 0.85rem;
            margin-top: 1rem;
        }
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">⚖️ Eviction Defense Toolkit</div>
        <nav class="nav-links">
            <a href="/documents">📄 Documents</a>
            <a href="/timeline">📅 Timeline</a>
            <a href="/law-library">📚 Law Library</a>
            <a href="/zoom-court">💻 Zoom Court</a>
        </nav>
    </header>
    <div class="container">
        <h1 class="page-title">Dakota County Eviction Defense</h1>
        <p class="page-subtitle">Complete toolkit for defending against eviction in Dakota County, MN</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="stat-motions">6</div>
                <div class="stat-label">Motion Templates</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-forms">8</div>
                <div class="stat-label">Court Forms</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-defenses">12</div>
                <div class="stat-label">Defense Strategies</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-counterclaims">5</div>
                <div class="stat-label">Counterclaim Types</div>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showPanel('motions')">📋 Motions</button>
            <button class="tab" onclick="showPanel('forms')">📝 Forms</button>
            <button class="tab" onclick="showPanel('procedures')">📚 Procedures</button>
            <button class="tab" onclick="showPanel('defenses')">🛡️ Defenses</button>
            <button class="tab" onclick="showPanel('counterclaims')">⚔️ Counterclaims</button>
            <button class="tab" onclick="showPanel('timeline')">📅 Case Timeline</button>
        </div>
        
        <div id="motions" class="content-panel active">
            <div class="grid" id="motions-grid">Loading motions...</div>
        </div>
        
        <div id="forms" class="content-panel">
            <div class="grid" id="forms-grid">Loading forms...</div>
        </div>
        
        <div id="procedures" class="content-panel">
            <div class="timeline" id="procedures-list">Loading procedures...</div>
        </div>
        
        <div id="defenses" class="content-panel">
            <div class="grid" id="defenses-grid">Loading defenses...</div>
        </div>
        
        <div id="counterclaims" class="content-panel">
            <div class="grid" id="counterclaims-grid">Loading counterclaims...</div>
        </div>
        
        <div id="timeline" class="content-panel">
            <div class="timeline" id="case-timeline">Loading timeline...</div>
        </div>
    </div>
    
    <div id="motion-modal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">×</button>
            <div id="modal-body"></div>
        </div>
    </div>
    
    <script>
        async function loadData() {
            // Load motions
            const motions = await fetch('/api/eviction-defense/motions').then(r => r.json());
            document.getElementById('motions-grid').innerHTML = motions.map(m => `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">${m.title}</div>
                        <span class="card-badge">${m.success_rate || 'Standard'}</span>
                    </div>
                    <div class="card-desc">${m.description}</div>
                    <button class="card-btn" onclick="showMotion('${m.id}')">View Template</button>
                </div>
            `).join('');
            
            // Load forms
            const forms = await fetch('/api/eviction-defense/forms').then(r => r.json());
            document.getElementById('forms-grid').innerHTML = forms.map(f => `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">${f.name}</div>
                        <span class="card-badge">${f.court}</span>
                    </div>
                    <div class="card-desc">${f.description}</div>
                    <button class="card-btn" onclick="showForm('${f.id}')">View Form</button>
                </div>
            `).join('');
            
            // Load defenses
            const defenses = await fetch('/api/eviction-defense/defenses').then(r => r.json());
            document.getElementById('defenses-grid').innerHTML = defenses.map(d => `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">${d.name}</div>
                    </div>
                    <div class="card-desc">${d.description}</div>
                    <p style="margin-top:0.5rem;font-size:0.85rem;"><strong>Legal Basis:</strong> ${d.legal_basis}</p>
                </div>
            `).join('');
            
            // Load counterclaims
            const claims = await fetch('/api/eviction-defense/counterclaims').then(r => r.json());
            document.getElementById('counterclaims-grid').innerHTML = claims.map(c => `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">${c.title}</div>
                    </div>
                    <div class="card-desc">${c.description}</div>
                    <button class="card-btn" onclick="showCounterclaim('${c.id}')">Learn More</button>
                </div>
            `).join('');
            
            // Load procedures
            const procedures = await fetch('/api/eviction-defense/procedures').then(r => r.json());
            document.getElementById('procedures-list').innerHTML = procedures.map((p, i) => `
                <div class="timeline-item">
                    <div class="timeline-dot">${i + 1}</div>
                    <div class="timeline-content">
                        <div class="timeline-title">${p.title}</div>
                        <div class="timeline-desc">${p.description}</div>
                    </div>
                </div>
            `).join('');
        }
        
        function showPanel(panel) {
            document.querySelectorAll('.content-panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(panel).classList.add('active');
            event.target.classList.add('active');
        }
        
        async function showMotion(id) {
            const motions = await fetch('/api/eviction-defense/motions').then(r => r.json());
            const motion = motions.find(m => m.id === id);
            if (motion) {
                document.getElementById('modal-body').innerHTML = `
                    <h2 style="margin-bottom:1rem">${motion.title}</h2>
                    <p style="color:#fecaca;margin-bottom:1rem">${motion.description}</p>
                    <h3 style="margin:1rem 0 0.5rem">When to Use:</h3>
                    <ul style="margin-left:1.5rem;color:#fecaca">${motion.when_to_use.map(w => '<li>' + w + '</li>').join('')}</ul>
                    <h3 style="margin:1rem 0 0.5rem">Legal Basis:</h3>
                    <ul style="margin-left:1.5rem;color:#fecaca">${motion.legal_basis.map(l => '<li>' + l + '</li>').join('')}</ul>
                    <h3 style="margin:1rem 0 0.5rem">Template:</h3>
                    <div class="template-text">${motion.template_text}</div>
                `;
                document.getElementById('motion-modal').style.display = 'flex';
            }
        }
        
        async function showForm(id) {
            const forms = await fetch('/api/eviction-defense/forms').then(r => r.json());
            const form = forms.find(f => f.id === id);
            if (form) {
                document.getElementById('modal-body').innerHTML = `
                    <h2 style="margin-bottom:1rem">${form.name}</h2>
                    <p style="color:#fecaca;margin-bottom:1rem">${form.description}</p>
                    <p><strong>Court:</strong> ${form.court}</p>
                    <p><strong>Filing Fee:</strong> ${form.filing_fee || 'Varies'}</p>
                    <h3 style="margin:1rem 0 0.5rem">Instructions:</h3>
                    <ol style="margin-left:1.5rem;color:#fecaca">${form.instructions.map(i => '<li>' + i + '</li>').join('')}</ol>
                `;
                document.getElementById('motion-modal').style.display = 'flex';
            }
        }
        
        async function showCounterclaim(id) {
            const claims = await fetch('/api/eviction-defense/counterclaims').then(r => r.json());
            const claim = claims.find(c => c.id === id);
            if (claim) {
                document.getElementById('modal-body').innerHTML = `
                    <h2 style="margin-bottom:1rem">${claim.title}</h2>
                    <p style="color:#fecaca;margin-bottom:1rem">${claim.description}</p>
                    <h3 style="margin:1rem 0 0.5rem">Requirements:</h3>
                    <ul style="margin-left:1.5rem;color:#fecaca">${claim.requirements.map(r => '<li>' + r + '</li>').join('')}</ul>
                    <h3 style="margin:1rem 0 0.5rem">Potential Damages:</h3>
                    <ul style="margin-left:1.5rem;color:#fecaca">${claim.potential_damages.map(d => '<li>' + d + '</li>').join('')}</ul>
                `;
                document.getElementById('motion-modal').style.display = 'flex';
            }
        }
        
        function closeModal() {
            document.getElementById('motion-modal').style.display = 'none';
        }
        
        document.getElementById('motion-modal').addEventListener('click', e => {
            if (e.target.id === 'motion-modal') closeModal();
        });
        
        loadData();
    </script>
</body>
</html>"""


def generate_zoom_court_html() -> str:
    """Generate zoom court helper HTML page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zoom Court Helper - Semptify</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0c4a6e 0%, #075985 100%);
            color: #fff;
            min-height: 100vh;
        }
        .header {
            background: rgba(0,0,0,0.2);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo { font-size: 1.5rem; font-weight: 700; }
        .nav-links { display: flex; gap: 1rem; }
        .nav-links a {
            color: #bae6fd;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .nav-links a:hover { background: rgba(255,255,255,0.1); }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .page-title { font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; }
        .page-subtitle { color: #bae6fd; margin-bottom: 2rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
        .card {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s;
        }
        .card:hover { transform: translateY(-4px); background: rgba(255,255,255,0.15); }
        .card-icon { font-size: 2.5rem; margin-bottom: 1rem; }
        .card-title { font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; }
        .card-desc { color: #bae6fd; font-size: 0.9rem; }
        .checklist {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            margin-top: 2rem;
        }
        .checklist-title { font-size: 1.25rem; margin-bottom: 1rem; }
        .check-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-bottom: 0.5rem;
            cursor: pointer;
        }
        .check-item:hover { background: rgba(0,0,0,0.3); }
        .check-item input { width: 20px; height: 20px; }
        .check-item.critical { border-left: 4px solid #f59e0b; }
        .check-item label { flex: 1; cursor: pointer; }
        .check-item .fix { font-size: 0.85rem; color: #bae6fd; margin-top: 0.25rem; }
        .tips-section {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            margin-top: 2rem;
        }
        .tips-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
        .tip-category { margin-bottom: 1rem; }
        .tip-category h3 { font-size: 1rem; margin-bottom: 0.5rem; color: #0ea5e9; }
        .tip-list { list-style: none; }
        .tip-list li { padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 0.9rem; }
        .etiquette {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            margin-top: 2rem;
        }
        .rule-item {
            display: flex;
            gap: 1rem;
            padding: 1rem;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-bottom: 0.75rem;
        }
        .rule-icon { font-size: 1.5rem; }
        .rule-content { flex: 1; }
        .rule-title { font-weight: 600; margin-bottom: 0.25rem; }
        .rule-desc { color: #bae6fd; font-size: 0.9rem; }
        .phrases-section {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            margin-top: 2rem;
        }
        .phrase-category { margin-bottom: 1.5rem; }
        .phrase-category h3 { margin-bottom: 0.75rem; color: #0ea5e9; }
        .phrase-item {
            display: flex;
            gap: 1rem;
            padding: 0.75rem;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
        .phrase-situation { color: #bae6fd; min-width: 200px; }
        .phrase-text { font-style: italic; }
        @media (max-width: 768px) {
            .tips-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">💻 Zoom Court Helper</div>
        <nav class="nav-links">
            <a href="/documents">📄 Documents</a>
            <a href="/timeline">📅 Timeline</a>
            <a href="/law-library">📚 Law Library</a>
            <a href="/eviction-defense">⚖️ Eviction Defense</a>
        </nav>
    </header>
    <div class="container">
        <h1 class="page-title">Zoom Court Helper</h1>
        <p class="page-subtitle">Prepare for your virtual court hearing with confidence</p>
        
        <div class="grid">
            <div class="card" onclick="scrollTo('checklist')">
                <div class="card-icon">✅</div>
                <div class="card-title">Tech Checklist</div>
                <div class="card-desc">Ensure your technology is ready for court</div>
            </div>
            <div class="card" onclick="scrollTo('etiquette')">
                <div class="card-icon">🎩</div>
                <div class="card-title">Court Etiquette</div>
                <div class="card-desc">Proper behavior for virtual hearings</div>
            </div>
            <div class="card" onclick="scrollTo('phrases')">
                <div class="card-icon">🗣️</div>
                <div class="card-title">What to Say</div>
                <div class="card-desc">Phrases to use when addressing the court</div>
            </div>
            <div class="card" onclick="scrollTo('tips')">
                <div class="card-icon">💡</div>
                <div class="card-title">Quick Tips</div>
                <div class="card-desc">Essential tips for before, during, and after</div>
            </div>
        </div>
        
        <div class="checklist" id="checklist">
            <h2 class="checklist-title">📋 Technology Checklist</h2>
            <div id="tech-checklist">Loading checklist...</div>
        </div>
        
        <div class="etiquette" id="etiquette">
            <h2 class="checklist-title">🎩 Court Etiquette Rules</h2>
            <div id="etiquette-rules">Loading etiquette rules...</div>
        </div>
        
        <div class="phrases-section" id="phrases">
            <h2 class="checklist-title">🗣️ Helpful Phrases</h2>
            <div id="phrases-list">Loading phrases...</div>
        </div>
        
        <div class="tips-section" id="tips">
            <h2 class="checklist-title">💡 Quick Tips</h2>
            <div class="tips-grid" id="quick-tips">Loading tips...</div>
        </div>
    </div>
    
    <script>
        async function loadData() {
            // Load tech checklist
            const checklist = await fetch('/api/zoom-court/tech-checklist').then(r => r.json());
            document.getElementById('tech-checklist').innerHTML = checklist.map(item => `
                <div class="check-item ${item.critical ? 'critical' : ''}">
                    <input type="checkbox" id="check-${item.item.replace(/\\s/g, '-')}">
                    <label for="check-${item.item.replace(/\\s/g, '-')}">
                        <strong>${item.item}</strong>
                        <div class="fix">${item.description} — Fix: ${item.how_to_fix}</div>
                    </label>
                </div>
            `).join('');
            
            // Load etiquette
            const etiquette = await fetch('/api/zoom-court/etiquette').then(r => r.json());
            document.getElementById('etiquette-rules').innerHTML = etiquette.map(rule => `
                <div class="rule-item">
                    <div class="rule-icon">📌</div>
                    <div class="rule-text">${rule.rule}</div>
                </div>
            `).join('');
        }
        
        loadData();
    </script>
</body>
</html>"""


# Create FastAPI App
# =============================================================================

def create_app() -> FastAPI:
    """Application factory. Creates and configures the FastAPI application."""
    logger = logging.getLogger(__name__)
    
    app_settings = get_settings()
    setup_logging()
    validate_app_compliance(app_settings)

    # OpenAPI tags for documentation organization
    tags_metadata = [
        {
            "name": "Health",
            "description": "Health checks, readiness probes, and metrics endpoints.",
        },
        {
            "name": "Authentication",
            "description": "User authentication status and role management.",
        },
        {
            "name": "Storage Auth",
            "description": "OAuth2 flows for Google Drive, Dropbox, and OneDrive.",
        },
        {
            "name": "Document Vault",
            "description": "Secure document upload, certification, and retrieval.",
        },
        {
            "name": "Documents",
            "description": "Document processing, analysis, and classification.",
        },
        {
            "name": "Timeline",
            "description": "Chronological event tracking for evidence building.",
        },
        {
            "name": "Calendar",
            "description": "Deadline and appointment management.",
        },
        {
            "name": "Copilot",
            "description": "AI-powered tenant rights assistant.",
        },
        {
            "name": "Context Loop",
            "description": "Event processing and intensity engine.",
        },
        {
            "name": "Adaptive UI",
            "description": "Dynamic UI configuration based on user context.",
        },
        {
            "name": "Document Registry",
            "description": "Tamper-proof document management with chain of custody and forgery detection.",
        },
        {
            "name": "Eviction Case",
            "description": "Unified case builder - pulls from all Semptify data for court-ready packages.",
        },
        {
            "name": "Court Learning",
            "description": "Bidirectional learning - record outcomes, query patterns, get data-driven strategies.",
        },
        {
            "name": "Dakota Procedures",
            "description": "Court rules, motions, objections, counterclaims, and step-by-step procedures.",
        },
        {
            "name": "Eviction Defense",
            "description": "Dakota County eviction answer forms and motions.",
        },
        {
            "name": "Law Library",
            "description": "Legal research with AI librarian, statutes, case law, and deadline calculator.",
        },
        {
            "name": "Eviction Defense Toolkit",
            "description": "Complete eviction defense with motions, forms, procedures, counterclaims, and trial prep.",
        },
        {
            "name": "Zoom Courtroom",
            "description": "Virtual courtroom preparation, tech checklist, etiquette, and hearing guides.",
        },
    ]

    fastapi_app = FastAPI(  # pylint: disable=redefined-outer-name
        title=app_settings.app_name,
        description=f"""{app_settings.app_description}

## Authentication
Semptify uses **storage-based authentication**. Connect your cloud storage (Google Drive, Dropbox, or OneDrive) to authenticate. Your identity IS your storage access - no passwords required.

## Rate Limits
- Standard endpoints: 60 requests/minute
- AI endpoints: 10 requests/minute  
- Auth endpoints: 5 requests/minute
- File uploads: 20 requests/minute

## API Versioning
Current version: **v1**. Check `GET /api/version` for version info.

## Error Responses
All errors return JSON with `detail` field. Rate limit errors include `retry_after` header.
""",
        version=app_settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs" if app_settings.enable_docs else None,
        redoc_url="/api/redoc" if app_settings.enable_docs else None,
        openapi_url="/api/openapi.json" if app_settings.enable_docs else None,
        openapi_tags=tags_metadata,
        contact={
            "name": "Semptify Support",
            "url": "https://github.com/Semptify/Semptify-FastAPI",
            "email": "support@semptify.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        servers=[
            {"url": "/", "description": "Current server"},
        ],
    )
    
    # =========================================================================
    # Rate Limiting
    # =========================================================================
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.errors import RateLimitExceeded
    from app.core.rate_limit import limiter, rate_limit_exceeded_handler

    fastapi_app.state.limiter = limiter
    fastapi_app.add_middleware(SlowAPIMiddleware)
    fastapi_app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    # Initialize OAuth token manager
    from app.core.oauth_token_manager import init_oauth_token_manager
    init_oauth_token_manager()
    
    # DISABLED: Performance monitoring - causing high memory usage (85%+)
    # TODO: Re-enable after memory optimization
    # from app.core.performance_monitor import get_performance_monitor
    # performance_monitor = get_performance_monitor()
    # performance_monitor.start_monitoring()
    
    logger.info("Semptify 5.0 FastAPI application created successfully (performance monitoring disabled)")
    
    # =========================================================================
    # Global Exception Handlers
    # =========================================================================
    
    # Import error handling system
    from app.core.error_handling import (
        semptify_exception_handler,
        SemptifyError,
        UserError,
        StorageError,
        AuthenticationError,
        ValidationError
    )
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    
    # Register global exception handlers
    fastapi_app.add_exception_handler(Exception, semptify_exception_handler)
    fastapi_app.add_exception_handler(SemptifyError, semptify_exception_handler)
    fastapi_app.add_exception_handler(RequestValidationError, semptify_exception_handler)
    fastapi_app.add_exception_handler(StarletteHTTPException, semptify_exception_handler)
    
    logger.info("Global error handling system registered")
    
    # =========================================================================
    # Performance Monitoring Middleware - DISABLED
    # =========================================================================
    # DISABLED: Causing 85%+ memory usage
    # TODO: Re-enable after optimization
    
    # @fastapi_app.middleware("http")
    # async def performance_monitoring_middleware(request: Request, call_next):
    #     """Monitor request performance."""
    #     from app.core.performance_monitor import get_performance_monitor
    #     ...
    
    logger.info("Performance monitoring middleware DISABLED (memory optimization)")
    
    # =========================================================================
    # Offline Detection Middleware
    # =========================================================================
    
    @fastapi_app.middleware("http")
    async def offline_detection_middleware(request: Request, call_next):
        """Add offline detection to all responses."""
        response = await call_next(request)
        
        # Add offline indicators to HTML responses
        if response.headers.get("content-type", "").startswith("text/html"):
            from app.core.offline_manager import get_offline_indicators
            offline_indicators = get_offline_indicators()
            
            # Inject offline indicators into HTML
            if hasattr(response, 'body'):
                body = response.body.decode() if isinstance(response.body, bytes) else response.body
                if '<head>' in body:
                    # Insert after <head> tag
                    body = body.replace('<head>', f'<head>{offline_indicators}')
                elif '<html>' in body:
                    # Insert after <html> tag
                    body = body.replace('<html>', f'<html>{offline_indicators}')
                else:
                    # Insert at beginning of body
                    body = f'{offline_indicators}{body}'
                
                response.body = body.encode() if isinstance(response.body, bytes) else body
        
        return response
    
    logger.info("Offline detection middleware registered")
    
    # =========================================================================
    # Middleware (order matters - first added = last to run)
    # =========================================================================
    
    is_production = app_settings.security_mode == "enforced"
    logger = logging.getLogger(__name__)
    
    # PRODUCTION SECURITY MIDDLEWARE (if enforced mode)
    if is_production:
        try:
            from app.core.logging_middleware import RequestLoggingMiddleware as ProdRequestLogging
            
            # Request logging (security audit trail)
            fastapi_app.add_middleware(ProdRequestLogging)
            logger.info("🚀 Request logging middleware enabled (production mode)")
        except ImportError as e:
            logger.error("⚠️  Failed to load request logging middleware: %s", e)
            logger.warning("Request logging not available - continuing without it")
    
    # Smart Gate Checkpoint (enforces welcome page for new users)
    from app.core.checkpoint_middleware import SmartCheckpointMiddleware
    fastapi_app.add_middleware(SmartCheckpointMiddleware)
    logger.info("🚪 Smart checkpoint gate enabled (welcome page checkpoint)")
    
    # Storage requirement (CRITICAL: Enforces everyone has storage connected)
    from app.core.storage_middleware import StorageRequirementMiddleware
    fastapi_app.add_middleware(
        StorageRequirementMiddleware,
        enforce=is_production  # Only enforce in production
    )
    logger.info("🔒 Storage requirement middleware enabled (enforce=%s)", is_production)
    
    # Security headers (standard mode, adds headers to all responses)
    from app.core.security_headers import SecurityHeadersMiddleware
    fastapi_app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=is_production,  # HSTS only in production
    )
    
    # Request timeout (prevents hung requests)
    from app.core.timeout import TimeoutMiddleware
    fastapi_app.add_middleware(TimeoutMiddleware)
    
    # Request logging (all modes — audit trail is required for evidence integrity)
    from app.core.logging_middleware import RequestLoggingMiddleware
    fastapi_app.add_middleware(RequestLoggingMiddleware)
    
    # CORS (with stricter config in production)
    cors_config = {
        "allow_origins": app_settings.cors_origins_list,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"] if is_production else ["*"],
        "allow_headers": ["Content-Type", "Authorization", "X-Request-Id", "X-API-Key"] if is_production else ["*"],
    }
    fastapi_app.add_middleware(CORSMiddleware, **cors_config)
    logger.info("🔒 CORS middleware configured (production=%s)", is_production)
    
    # Request ID middleware
    @fastapi_app.middleware("http")
    async def add_request_id(request: Request, call_next):
        from app.core.id_gen import make_id
        request_id = request.headers.get("X-Request-Id", make_id("req"))
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
    
    # =========================================================================
    # Exception Handlers
    # =========================================================================
    from app.core.errors import setup_exception_handlers
    setup_exception_handlers(fastapi_app)
    
    # =========================================================================
    # Register Routers
    # =========================================================================

    def include_if(router_obj, **kwargs):
        if router_obj is not None:
            fastapi_app.include_router(router_obj, **kwargs)

    # API Version info (GET /api/version)
    from app.core.versioning import version_router
    if version_router:
        fastapi_app.include_router(version_router)

    # Health & metrics (no prefix)
    if health.router:
        fastapi_app.include_router(health.router, tags=["Health"])

    # Role-based UI routing (directs users to appropriate interface)
    if role_ui_router:
        fastapi_app.include_router(role_ui_router, tags=["Role UI"])

    # Workflow engine + page contract API
    if workflow_router:
        fastapi_app.include_router(workflow_router)
    
    # Workflow validator (admin diagnostic dashboard)
    if workflow_validator_router:
        fastapi_app.include_router(workflow_validator_router, tags=["Admin"])
    
    # Role upgrade/verification API
    if role_upgrade_router:
        fastapi_app.include_router(role_upgrade_router, tags=["Role Management"])
    
    # Guided Intake - Conversational intake like an attorney/advocate
    if guided_intake_router:
        fastapi_app.include_router(guided_intake_router, tags=["Guided Intake"])

    # Root route - serve welcome page from static/public (outside onboarding flow)
    @fastapi_app.get("/", response_class=HTMLResponse)
    async def root_welcome():
        """Serve welcome page as entry point."""
        welcome_path = BASE_PATH / "static" / "public" / "welcome.html"
        if welcome_path.exists():
            return FileResponse(welcome_path)
        return RedirectResponse(url="/onboarding", status_code=302)

    # Favicon - serve a simple SVG to prevent 404 errors
    @fastapi_app.get("/favicon.ico")
    async def favicon():
        """Serve favicon as SVG."""
        svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect width="100" height="100" rx="20" fill="#2c5aa0"/>
            <text x="50" y="70" font-size="50" text-anchor="middle" fill="white">S</text>
        </svg>'''
        from fastapi.responses import Response
        return Response(content=svg, media_type="image/svg+xml")

    # ==========================================================================
    # Role Home Routes — destinations from workflow_engine after auth/reconnect
    # ==========================================================================
    _ROLE_STATIC_MAP = {
        "/tenant/home":      "static/tenant/dashboard.html",
        "/tenant/documents": "static/tenant/index.html",
        "/tenant":           "static/tenant/index.html",
        "/advocate":         "static/advocate/index.html",
        "/advocate/home":    "static/advocate/dashboard.html",
        "/legal":            "static/legal/index.html",
        "/legal/home":       "static/legal/dashboard.html",
        "/manager":          "static/manager/index.html",
        "/manager/home":     "static/manager/dashboard.html",
        "/admin":            "static/admin/dashboard.html",
        "/admin/home":       "static/admin/dashboard.html",
        "/judge":            "static/legal/index.html",
        "/judge/home":       "static/legal/dashboard.html",
    }

    def _make_role_handler(rel_path: str):
        async def _handler():
            p = BASE_PATH / rel_path
            if p.exists():
                return FileResponse(str(p))
            return RedirectResponse(url="/", status_code=302)
        return _handler

    for _route, _file in _ROLE_STATIC_MAP.items():
        fastapi_app.add_api_route(
            _route,
            _make_role_handler(_file),
            methods=["GET"],
            response_class=HTMLResponse,
            tags=["Role Home"],
        )

    # Unified Onboarding (primary entry point for new users)
    # NOTE: onboarding.router already declares prefix="/onboarding" — no prefix here
    if onboarding.router:
        fastapi_app.include_router(onboarding.router, tags=["Onboarding"])

    # Storage OAuth (handles authentication)
    if storage.router:
        fastapi_app.include_router(storage.router, tags=["Storage Auth"])
    
    # Plugin System (extensible module architecture)
    if plugins.router:
        fastapi_app.include_router(plugins.router, tags=["Plugin System"])
    
    # Development Tools (crawler, analysis, debugging)
    if development.router:
        fastapi_app.include_router(development.router, tags=["Development Tools"])

    # API routes
    # app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    # app.include_router(vault.router, prefix="/api/vault", tags=["Document Vault"])
    # app.include_router(timeline.router, prefix="/api/timeline", tags=["Timeline"])
    # app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
    # app.include_router(copilot.router, prefix="/api/copilot", tags=["AI Copilot"])
    # app.include_router(tactics.router, prefix="/api/tactics", tags=["Proactive Tactics"])  # AI defense strategies
    # app.include_router(documents.router, tags=["Documents"])  # Fresh document processing API
    # app.include_router(adaptive_ui.router, tags=["Adaptive UI"])  # Self-building interface
    # app.include_router(context_loop.router, tags=["Context Loop"])  # Core processing engine
    include_if(documents_router, tags=["Documents"])  # Document upload, analysis, intelligence
    include_if(vault_router, prefix="/api/vault", tags=["Document Vault"])  # User storage vault API
    include_if(intake_router, tags=["Document Intake"])  # Document intake & extraction
    include_if(registry_router, tags=["Document Registry"])  # Tamper-proof chain of custody
    include_if(vault_engine_router, tags=["Vault Engine"])  # Centralized access control
    include_if(form_data_router, prefix="/api/form-data", tags=["Form Data Hub"])  # Central data integration
    include_if(setup_router, prefix="/api/setup", tags=["Setup Wizard"])  # Initial setup wizard
    include_if(auto_mode_router, tags=["Auto Mode"])  # Auto mode analysis & summaries
    include_if(functionx_router, tags=["FunctionX"])  # Action-set planning and execution scaffold
    include_if(unified_overlays_router, tags=["Unified Overlays"])  # Unified overlay system (cloud-only)
    include_if(document_delivery_router, tags=["Document Delivery"])  # Send/receive/sign documents
    include_if(communication_router, tags=["Communications"])  # Messaging and document collaboration
    include_if(websocket_router, prefix="/ws", tags=["WebSocket Events"])  # Real-time events
    include_if(module_hub_router, prefix="/api", tags=["Module Hub"])  # Central module communication
    include_if(positronic_mesh_router, prefix="/api", tags=["Positronic Mesh"])  # Workflow orchestration
    include_if(mesh_network_router, prefix="/api", tags=["Mesh Network"])  # True bidirectional module communication
    if location_router:
        fastapi_app.include_router(location_router, tags=["Location"])  # Location detection and state-specific resources
    if hud_funding_router:
        fastapi_app.include_router(hud_funding_router, tags=["HUD Funding Guide"])  # HUD funding programs, tax credits, landlord eligibility
    if fraud_exposure_router:
        fastapi_app.include_router(fraud_exposure_router, tags=["Fraud Exposure"])  # Fraud analysis and detection
    if public_exposure_router:
        fastapi_app.include_router(public_exposure_router, tags=["Public Exposure"])  # Press releases and media campaigns
    if plan_maker_router:
        fastapi_app.include_router(plan_maker_router, tags=["Plan Maker"])  # Accountability plan builder
    if campaign_router:
        fastapi_app.include_router(campaign_router, tags=["Campaign Orchestration"])  # Combined complaint, fraud, press campaigns
    if funding_search_router:
        fastapi_app.include_router(funding_search_router, tags=["Funding & Tax Credit Search"])  # LIHTC, NMTC, HUD funding search
    if research_router:
        fastapi_app.include_router(research_router, tags=["Research Module"])  # Landlord/property research and dossier
    if research_module_router:
        fastapi_app.include_router(research_module_router, tags=["Research Module SDK"])  # SDK-based landlord/property dossier
    if extraction_router:
        fastapi_app.include_router(extraction_router, tags=["Form Field Extraction"])  # Extract and map document data to form fields
    if tenancy_hub_router:
        fastapi_app.include_router(tenancy_hub_router, tags=["Tenancy Hub"])  # Central hub for all tenancy documentation
    if legal_analysis_router:
        fastapi_app.include_router(legal_analysis_router, tags=["Legal Analysis"])
    if legal_filing_router:
        fastapi_app.include_router(legal_filing_router, tags=["Legal Filing"])  # Legal merit, consistency, evidence analysis
    if legal_trails_router:
        fastapi_app.include_router(legal_trails_router, tags=["Legal Trails"])  # Track violations, claims, broker oversight, filing deadlines
    if state_laws_router:
        fastapi_app.include_router(state_laws_router, tags=["State Laws"])  # State-specific housing law information (MN-first)
    if contacts_router:
        fastapi_app.include_router(contacts_router, tags=["Contact Manager"])  # Track landlords, attorneys, witnesses, agencies
    if recognition_router:
        fastapi_app.include_router(recognition_router, tags=["Document Recognition"])  # World-class document recognition engine
    if search_router:
        fastapi_app.include_router(search_router, prefix="/api/search", tags=["Global Search"])  # Universal search across all content
    if mndes_router:
        fastapi_app.include_router(mndes_router, tags=["MNDES — Court Exhibit System"])  # MN Digital Exhibit System (Order ADM09-8010)
    if court_forms_router:
        fastapi_app.include_router(court_forms_router, tags=["Court Forms"])  # Auto-generate Minnesota court forms
    if zoom_court_prep_router:
        fastapi_app.include_router(zoom_court_prep_router, tags=["Zoom Court Prep"])  # Hearing preparation and tech checks
    if pdf_tools_router:
        fastapi_app.include_router(pdf_tools_router, tags=["PDF Tools"])  # PDF reader, viewer, page extractor
    if tools_api_router:
        fastapi_app.include_router(tools_api_router, tags=["Tools"])  # Calculators, generators, checklists wiring
    if briefcase_router:
        fastapi_app.include_router(briefcase_router, tags=["Briefcase"])  # Document & folder organization system
    if emotion_router:
        fastapi_app.include_router(emotion_router, tags=["Emotion Engine"])  # Adaptive UI emotion tracking
    if court_packet_router:
        fastapi_app.include_router(court_packet_router, tags=["Court Packet"])  # Export court-ready document packets
    if actions_router:
        fastapi_app.include_router(actions_router, tags=["Smart Actions"])  # Personalized action recommendations
    if progress_router:
        fastapi_app.include_router(progress_router, tags=["Progress Tracker"])  # User journey progress tracking
    if case_builder_router:
        fastapi_app.include_router(case_builder_router, tags=["Case Builder"])  # Case management & intake
    if document_converter_router:
        fastapi_app.include_router(document_converter_router, tags=["Document Converter"])  # Markdown to DOCX/HTML conversion
    if page_index_router:
        fastapi_app.include_router(page_index_router, tags=["Page Index"])  # HTML page index database

    if dashboard_router:
        fastapi_app.include_router(dashboard_router, tags=["Unified Dashboard"])  # Combined dashboard data
    if enterprise_dashboard_router:
        fastapi_app.include_router(enterprise_dashboard_router, tags=["Enterprise Dashboard"])  # Premium enterprise UI & API
    include_if(timeline_unified_router, prefix="/api/timeline", tags=["Unified Timeline"])  # Interactive timeline with date axis switching
    include_if(invite_codes_router, tags=["Invite Codes"])  # Advocate/Legal role validation codes
    
    # Storage OAuth (handles authentication)
    if storage.router:
        fastapi_app.include_router(storage.router, tags=["Storage Auth"])
    
    # Plugin System (extensible module architecture)
    if plugins.router:
        fastapi_app.include_router(plugins.router, tags=["Plugin System"])
    
    # Development Tools (crawler, analysis, debugging)
    if development.router:
        fastapi_app.include_router(development.router, tags=["Development Tools"])

    # Document Preview - Multi-format preview generation
    if preview_router:
        fastapi_app.include_router(preview_router, prefix="/api/preview", tags=["Document Preview"])
        logging.getLogger(__name__).info("📄 Document Preview router connected - Multi-format preview generation active")

    # Batch Operations - Bulk document management
    if batch_router:
        fastapi_app.include_router(batch_router, prefix="/api/batch", tags=["Batch Operations"])
        logging.getLogger(__name__).info("📦 Batch Operations router connected - Bulk document management active")

    # Analytics Systems - Usage and performance tracking
    if analytics_router:
        fastapi_app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
        logging.getLogger(__name__).info("📊 Analytics router connected - Usage and performance tracking active")

    # Tenant Defense Module - Evidence collection, sealing petitions, demand letters
    if tenant_defense_router:
        fastapi_app.include_router(tenant_defense_router, tags=["Tenant Defense"])
        logging.getLogger(__name__).info("⚖️ Tenant Defense module loaded - Evidence, petitions, and screening disputes")

    # Distributed Mesh Network - P2P Module Communication
    if distributed_mesh_router:
        fastapi_app.include_router(distributed_mesh_router, prefix="/api", tags=["Distributed Mesh"])
        logging.getLogger(__name__).info("🌐 Distributed Mesh router connected - P2P architecture active")

    # Dakota County Eviction Defense Module
    if DAKOTA_AVAILABLE:
        fastapi_app.include_router(dakota_case, prefix="/eviction", tags=["Eviction Case"])
        fastapi_app.include_router(dakota_learning, prefix="/eviction/learn", tags=["Court Learning"])
        fastapi_app.include_router(dakota_procedures, tags=["Dakota Procedures"])
        fastapi_app.include_router(dakota_flows, prefix="/eviction", tags=["Eviction Defense"])
        fastapi_app.include_router(dakota_forms, prefix="/eviction/forms", tags=["Court Forms"])
        logging.getLogger(__name__).info("✅ Dakota County Eviction Defense module loaded")
    else:
        logging.getLogger(__name__).warning("⚠️ Dakota County module not available")

    # New Legal Defense Modules
    if law_library_router:
        fastapi_app.include_router(law_library_router, tags=["Law Library"])
    if eviction_defense_router:
        fastapi_app.include_router(eviction_defense_router, tags=["Eviction Defense Toolkit"])
    if zoom_court_router:
        fastapi_app.include_router(zoom_court_router, tags=["Zoom Courtroom"])
    logging.getLogger(__name__).info("✅ Legal Defense modules loaded (Law Library, Eviction Defense, Zoom Court)")

    # Positronic Brain - Central Intelligence Hub
    if brain_router:
        fastapi_app.include_router(brain_router, prefix="/brain", tags=["Positronic Brain"])
        logging.getLogger(__name__).info("🧠 Positronic Brain connected - Central intelligence hub active")

    # Cloud Sync - User-Controlled Persistent Storage
    if cloud_sync_router:
        fastapi_app.include_router(cloud_sync_router, tags=["Cloud Sync"])
        logging.getLogger(__name__).info("☁️ Cloud Sync router connected - User-controlled data persistence active")

    # ALL-IN-ONE Unified Evidence Vault - Three-timestamp model with comprehensive metadata
    if vault_all_in_one_router:
        fastapi_app.include_router(vault_all_in_one_router, tags=["ALL-IN-ONE Vault"])
        logging.getLogger(__name__).info("🏛️ ALL-IN-ONE Vault router connected - Unified evidence vault with three-timestamp model active")

    # Document Overlays - Non-destructive annotations and processing
    if overlays_router:
        fastapi_app.include_router(overlays_router, tags=["Document Overlays"])
        logging.getLogger(__name__).info("📝 Document Overlays router connected - Non-destructive annotation system active")

    # Modular Components - New component system integration
    from app.routers import components
    if components.router:
        fastapi_app.include_router(components.router, tags=["Modular Components"])
        logging.getLogger(__name__).info("🧩 Modular Components router connected - Component system integration active")

    # Litigation Intelligence System (LIS) - Justice-Grade Legal Intelligence
    try:
        from app.routers import litigation_intelligence
        fastapi_app.include_router(litigation_intelligence.lis_router, tags=["Litigation Intelligence"])
        logging.getLogger(__name__).info("📊 Litigation Intelligence System router connected - Justice-grade legal intelligence active")
        logging.getLogger(__name__).info("?? Litigation Intelligence System router connected - Justice-grade legal intelligence active")
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Litigation Intelligence System not available: {e}")

    # Core System - System Infrastructure and Services
    try:
        from app.routers import core_system
        fastapi_app.include_router(core_system.core_router, tags=["Core System"])
        logging.getLogger(__name__).info("?? Core System router connected - System infrastructure active")
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Core System not available: {e}")

    # Housing Accountability - Regulatory Compliance & Oversight
    try:
        from app.routers import housing_accountability
        fastapi_app.include_router(housing_accountability.accountability_router, tags=["Housing Accountability"])
        logging.getLogger(__name__).info("?? Housing Accountability router connected - Regulatory compliance active")
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Housing Accountability not available: {e}")

    # Phase 2 Advanced Features Integration
    # =========================================================================

    # Document Preview System - Multi-format preview generation
    try:
        from app.routers import preview
        fastapi_app.include_router(preview.router, prefix="/api/preview", tags=["Document Preview"])
        logging.getLogger(__name__).info("📄 Document Preview router connected - Multi-format preview generation active")
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Document Preview router not available: {e}")

    # Batch Operations - Bulk document management
    try:
        from app.routers import batch
        fastapi_app.include_router(batch.router, prefix="/api/batch", tags=["Batch Operations"])
        logging.getLogger(__name__).info("📦 Batch Operations router connected - Bulk document management active")
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Batch Operations router not available: {e}")

    # Data Export/Import - GDPR-compliant data management
    try:
        from app.routers import export_import
        fastapi_app.include_router(export_import.router, prefix="/api/export-import", tags=["Data Export/Import"])
        logging.getLogger(__name__).info("📊 Data Export/Import router connected - GDPR-compliant data management active")
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Data Export/Import router not available: {e}")

    # Advanced Security - 2FA and session management
    try:
        from app.routers import security
        fastapi_app.include_router(security.router, prefix="/api/security", tags=["Advanced Security"])
        logging.getLogger(__name__).info("🔒 Advanced Security router connected - 2FA and session management active")
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Advanced Security router not available: {e}")

    # Automated Testing - Comprehensive testing framework
    try:
        from app.routers import testing
        fastapi_app.include_router(testing.router, prefix="/api/testing", tags=["Automated Testing"])
        logging.getLogger(__name__).info("🧪 Automated Testing router connected - Comprehensive testing framework active")
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Automated Testing router not available: {e}")

    # API Documentation - Developer portal and API docs
    try:
        from app.routers import documentation
        fastapi_app.include_router(documentation.router, prefix="/api/docs", tags=["API Documentation"])
        logging.getLogger(__name__).info("📚 API Documentation router connected - Developer portal active")
    except ImportError as e:
        logging.getLogger(__name__).warning(f"API Documentation router not available: {e}")

    # Free API Pack - Minnesota tenant rights APIs
    if free_api_router:
        fastapi_app.include_router(free_api_router)
        logging.getLogger(__name__).info("📈 Free API Pack connected - Minnesota tenant rights APIs active")
    logging.getLogger(__name__).info("🚀 Phase 2 Advanced Features Integration Complete")
    logging.getLogger(__name__).info("   - Document Preview: Multi-format preview generation")
    logging.getLogger(__name__).info("   - Batch Operations: Bulk document management")
    logging.getLogger(__name__).info("   - Data Export/Import: GDPR-compliant data management")
    logging.getLogger(__name__).info("   - Advanced Security: 2FA and session management")
    logging.getLogger(__name__).info("   - Automated Testing: Comprehensive testing framework")
    logging.getLogger(__name__).info("   - API Documentation: Developer portal and API docs")

    # Complaint Filing Wizard - Regulatory Accountability
    if complaints_router:
        fastapi_app.include_router(complaints_router, tags=["Complaint Wizard"])
        logging.getLogger(__name__).info("⚖️ Complaint Filing Wizard loaded - Regulatory accountability tools active")

    # app.include_router(complaints.router, prefix="/api/complaints", tags=["Complaints"])
    # app.include_router(ledger.router, prefix="/api/ledger", tags=["Rent Ledger"])
    # app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
    
    # =========================================================================
    # Static Files (for any frontend assets)
    # =========================================================================

    static_path = BASE_PATH / "static"
    if static_path.exists():
        fastapi_app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Mount /public to serve public-facing policy and info pages (privacy, terms, etc.)
    public_static_path = BASE_PATH / "static" / "public"
    if public_static_path.exists():
        fastapi_app.mount("/public", StaticFiles(directory=str(public_static_path)), name="public_static")

    # Mount onboarding static assets at /onboarding-assets to avoid shadowing the
    # /onboarding router. The router prefix /onboarding must take priority.
    onboarding_static_path = BASE_PATH / "static" / "onboarding"
    if onboarding_static_path.exists():
        fastapi_app.mount("/onboarding-assets", StaticFiles(directory=str(onboarding_static_path)), name="onboarding_static")

    # =========================================================================
    # Onboarding Redirect (before catch-all)
    # =========================================================================

        @fastapi_app.get("/onboarding", response_class=HTMLResponse)
        async def onboarding_redirect():
            """Redirect /onboarding to /onboarding/ for the router."""
            return RedirectResponse(url="/onboarding/", status_code=302)

        @fastapi_app.get("/welcome.html", response_class=HTMLResponse)
        async def welcome_html():
            """Serve welcome page — canonical entry point for new users."""
            welcome_path = BASE_PATH / "static" / "public" / "welcome.html"
            if welcome_path.exists():
                return FileResponse(welcome_path)
            return RedirectResponse(url="/", status_code=302)


    # =========================================================================
    # Root endpoint - Serve SPA
    # =========================================================================

    # Role-Specific Dashboard Pages
    @fastapi_app.get("/tenant/dashboard", response_class=HTMLResponse)
    async def tenant_dashboard_page(request: Request):
        """Serve the tenant dashboard with modular components."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return RedirectResponse(url="/storage/providers", status_code=302)

        tenant_dashboard_path = BASE_PATH / "app" / "templates" / "pages" / "tenant_dashboard.html"
        if tenant_dashboard_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/tenant_dashboard.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Tenant dashboard template error, falling back to static: %s", e)

        # Fallback to static dashboard
        static_fallback = BASE_PATH / "static" / "tenant" / "dashboard.html"
        if static_fallback.exists():
            return FileResponse(str(static_fallback))

        return HTMLResponse(content="<h1>Tenant Dashboard not found</h1>", status_code=404)

    @fastapi_app.get("/advocate/dashboard", response_class=HTMLResponse)
    async def advocate_dashboard_page(request: Request):
        """Serve the advocate dashboard with modular components."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return RedirectResponse(url="/storage/providers", status_code=302)

        advocate_dashboard_path = BASE_PATH / "app" / "templates" / "pages" / "advocate_dashboard.html"
        if advocate_dashboard_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/advocate_dashboard.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Advocate dashboard template error, falling back to static: %s", e)

        # Fallback to static dashboard
        static_fallback = BASE_PATH / "static" / "advocate" / "dashboard.html"
        if static_fallback.exists():
            return FileResponse(str(static_fallback))

        return HTMLResponse(content="<h1>Advocate Dashboard not found</h1>", status_code=404)

    @fastapi_app.get("/legal/dashboard", response_class=HTMLResponse)
    async def legal_dashboard_page(request: Request):
        """Serve the legal dashboard with modular components."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return RedirectResponse(url="/storage/providers", status_code=302)

        legal_dashboard_path = BASE_PATH / "app" / "templates" / "pages" / "legal_dashboard.html"
        if legal_dashboard_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/legal_dashboard.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Legal dashboard template error, falling back to static: %s", e)

        # Fallback to static dashboard
        static_fallback = BASE_PATH / "static" / "legal" / "dashboard.html"
        if static_fallback.exists():
            return FileResponse(str(static_fallback))

        return HTMLResponse(content="<h1>Legal Dashboard not found</h1>", status_code=404)

    @fastapi_app.get("/admin/dashboard", response_class=HTMLResponse)
    async def admin_dashboard_page(request: Request):
        """Serve the admin dashboard with modular components."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return RedirectResponse(url="/storage/providers", status_code=302)

        admin_dashboard_path = BASE_PATH / "app" / "templates" / "pages" / "admin_dashboard.html"
        if admin_dashboard_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/admin_dashboard.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Admin dashboard template error, falling back to static: %s", e)

        # Fallback to static dashboard
        static_fallback = BASE_PATH / "static" / "admin" / "dashboard.html"
        if static_fallback.exists():
            return FileResponse(str(static_fallback))

        return HTMLResponse(content="<h1>Admin Dashboard not found</h1>", status_code=404)

    @fastapi_app.get("/manager", response_class=HTMLResponse)
    async def manager_portal_page(request: Request):
        """Serve the manager portal for case workers and counselors."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID
        from app.core.user_context import get_role_from_user_id, UserRole

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return RedirectResponse(url="/storage/providers", status_code=302)

        # Verify MANAGER role
        role = get_role_from_user_id(user_id)
        if role != UserRole.MANAGER:
            return RedirectResponse(url="/", status_code=302)

        # Telemetry
        try:
            from app.core.telemetry_hooks import EMITTER
            EMITTER.emit("manager_portal_load", "manager", user_id)
        except Exception:
            pass

        # Try Jinja2 template first, then static fallback
        manager_template_path = BASE_PATH / "app" / "templates" / "pages" / "manager_dashboard.html"
        if manager_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/manager_dashboard.html")
            except Exception as e:
                logger.warning("Manager dashboard template error, falling back to static: %s", e)

        static_fallback = BASE_PATH / "static" / "manager" / "dashboard.html"
        if static_fallback.exists():
            return FileResponse(str(static_fallback))

        return HTMLResponse(content="<h1>Manager Portal not found</h1>", status_code=404)

    @fastapi_app.get("/manager/dashboard", response_class=HTMLResponse)
    async def manager_dashboard_page(request: Request):
        """Serve the manager dashboard (redirects to portal)."""
        return RedirectResponse(url="/manager", status_code=302)

    @fastapi_app.get("/api/manager/dashboard-stats")
    async def manager_dashboard_stats(request: Request):
        """API endpoint for manager dashboard statistics (auto-refresh)."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID
        from app.core.user_context import get_role_from_user_id, UserRole
        from app.core.database import get_db_session
        from app.core.manager_dashboard import get_dashboard_stats

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        # Verify MANAGER role
        role = get_role_from_user_id(user_id)
        if role != UserRole.MANAGER:
            return JSONResponse({"error": "Access denied"}, status_code=403)

        # Get organization ID from user ID prefix
        org_id = user_id[:12]

        try:
            with get_db_session() as db:
                stats = get_dashboard_stats(org_id, db)
                return JSONResponse(stats)
        except Exception as e:
            logger.warning("Dashboard stats query failed: %s", e)
            # Return fallback stats on error
            return JSONResponse({
                "total_cases": 0,
                "new_cases_this_week": 0,
                "pending_documents": 0,
                "urgent_documents": 0,
                "active_staff": 0,
                "total_staff": 0,
                "overdue_tasks": 0
            })

    @fastapi_app.get("/api/manager/cases")
    async def manager_cases(request: Request):
        """API endpoint for manager's organization cases."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID
        from app.core.user_context import get_role_from_user_id, UserRole
        from app.core.database import get_db_session
        from app.core.manager_dashboard import get_recent_cases

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        role = get_role_from_user_id(user_id)
        if role != UserRole.MANAGER:
            return JSONResponse({"error": "Access denied"}, status_code=403)

        org_id = user_id[:12]

        try:
            with get_db_session() as db:
                cases = get_recent_cases(org_id, db)
                return JSONResponse({"cases": cases})
        except Exception as e:
            logger.warning("Cases query failed: %s", e)
            return JSONResponse({"cases": []})

    @fastapi_app.get("/api/manager/staff")
    async def manager_staff(request: Request):
        """API endpoint for manager's organization staff."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID
        from app.core.user_context import get_role_from_user_id, UserRole
        from app.core.database import get_db_session
        from app.core.manager_dashboard import get_staff_list

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        role = get_role_from_user_id(user_id)
        if role != UserRole.MANAGER:
            return JSONResponse({"error": "Access denied"}, status_code=403)

        org_id = user_id[:12]

        try:
            with get_db_session() as db:
                staff = get_staff_list(org_id, db)
                return JSONResponse({"staff": staff})
        except Exception as e:
            logger.warning("Staff query failed: %s", e)
            return JSONResponse({"staff": []})

    @fastapi_app.get("/api/manager/activity")
    async def manager_activity(request: Request):
        """API endpoint for manager's organization activity feed."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID
        from app.core.user_context import get_role_from_user_id, UserRole
        from app.core.database import get_db_session
        from app.core.manager_dashboard import get_recent_activity

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        role = get_role_from_user_id(user_id)
        if role != UserRole.MANAGER:
            return JSONResponse({"error": "Access denied"}, status_code=403)

        org_id = user_id[:12]

        try:
            with get_db_session() as db:
                activity = get_recent_activity(org_id, db)
                return JSONResponse({"activity": activity})
        except Exception as e:
            logger.warning("Activity query failed: %s", e)
            return JSONResponse({"activity": []})

    @fastapi_app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page(request: Request):
        """Serve the main dashboard with onboarding modal for new users."""
        # Apply PageContract guard
        guard_redirect = _guard_by_contract("dashboard", request)
        if guard_redirect:
            return guard_redirect

        # Telemetry
        try:
            from app.core.telemetry_hooks import EMITTER
            from app.core.user_id import COOKIE_USER_ID
            EMITTER.emit("dashboard_load", "dashboard", request.cookies.get(COOKIE_USER_ID, "anon"))
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        dashboard_template_path = BASE_PATH / "app" / "templates" / "pages" / "dashboard.html"
        if dashboard_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/dashboard.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Dashboard template error, falling back to static: %s", e)

        dashboard_path = BASE_PATH / "static" / "dashboard.html"
        dashboard_fallback = _render_static_page(dashboard_path, inject_stage_model=True)
        if dashboard_fallback:
            return dashboard_fallback

        # Fallback to enterprise dashboard
        enterprise_template_path = BASE_PATH / "app" / "templates" / "pages" / "enterprise-dashboard.html"
        if enterprise_template_path.exists():
            return templates.TemplateResponse(request, "pages/enterprise-dashboard.html")

        enterprise_path = BASE_PATH / "static" / "enterprise-dashboard.html"
        enterprise_fallback = _render_static_page(enterprise_path, inject_stage_model=True)
        if enterprise_fallback:
            return enterprise_fallback

        return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)

    @fastapi_app.get("/gui", response_class=HTMLResponse)
    async def gui_navigation_hub(request: Request):
        """Serve the GUI Navigation Hub - central access to all interfaces."""
        gui_template_path = BASE_PATH / "app" / "templates" / "pages" / "gui_navigation_hub.html"
        if gui_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/gui_navigation_hub.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("GUI Navigation Hub template error, falling back to static: %s", e)

        # Fallback to static file
        gui_path = BASE_PATH / "static" / "admin" / "gui_navigation_hub.html"
        gui_fallback = _render_static_page(gui_path)
        if gui_fallback:
            return gui_fallback

        return HTMLResponse(content="<h1>GUI Navigation Hub not found</h1>", status_code=404)

    @fastapi_app.get("/home", response_class=HTMLResponse)
    async def semptify_home(request: Request):
        """Serve the Semptify Home — tenant front door."""
        return templates.TemplateResponse(request, "pages/semptify_hub.html")

    @fastapi_app.get("/auto-mode", response_class=HTMLResponse)
    async def auto_mode_panel(request: Request):
        """Serve the Auto Mode Control Panel."""
        auto_mode_template_path = BASE_PATH / "app" / "templates" / "pages" / "auto_mode_panel.html"
        if auto_mode_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/auto_mode_panel.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Auto Mode panel template error, falling back to static: %s", e)

        # Fallback to static file
        auto_mode_path = BASE_PATH / "static" / "components" / "auto_mode_panel.html"
        auto_mode_fallback = _render_static_page(auto_mode_path)
        if auto_mode_fallback:
            return auto_mode_fallback

        return HTMLResponse(content="<h1>Auto Mode panel not found</h1>", status_code=404)

    @fastapi_app.get("/auto-analysis", response_class=HTMLResponse)
    async def auto_analysis_summary(request: Request):
        """Serve the Auto Analysis Summary page."""
        auto_analysis_template_path = BASE_PATH / "app" / "templates" / "pages" / "auto_analysis_summary.html"
        if auto_analysis_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/auto_analysis_summary.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Auto Analysis Summary template error, falling back to static: %s", e)

        # Fallback to static file
        auto_analysis_path = BASE_PATH / "static" / "auto_analysis_summary.html"
        auto_analysis_fallback = _render_static_page(auto_analysis_path)
        if auto_analysis_fallback:
            return auto_analysis_fallback

        return HTMLResponse(content="<h1>Auto Analysis Summary not found</h1>", status_code=404)

    @fastapi_app.get("/mode-selector", response_class=HTMLResponse)
    async def mode_selector_page(request: Request):
        """Serve the Mode Selector page."""
        mode_selector_template_path = BASE_PATH / "app" / "templates" / "pages" / "mode_selector.html"
        if mode_selector_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/mode_selector.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Mode Selector template error, falling back to static: %s", e)

        # Fallback to static file
        mode_selector_path = BASE_PATH / "static" / "admin" / "mode_selector.html"
        mode_selector_fallback = _render_static_page(mode_selector_path)
        if mode_selector_fallback:
            return mode_selector_fallback

        return HTMLResponse(content="<h1>Mode Selector not found</h1>", status_code=404)

    @fastapi_app.get("/auto-mode-demo", response_class=HTMLResponse)
    async def auto_mode_demo_page(request: Request):
        """Serve the Auto Mode Demo page."""
        auto_mode_demo_template_path = BASE_PATH / "app" / "templates" / "pages" / "auto_mode_demo.html"
        if auto_mode_demo_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/auto_mode_demo.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Auto Mode Demo template error, falling back to static: %s", e)

        # Fallback to static file
        auto_mode_demo_path = BASE_PATH / "static" / "auto_mode_demo.html"
        auto_mode_demo_fallback = _render_static_page(auto_mode_demo_path)
        if auto_mode_demo_fallback:
            return auto_mode_demo_fallback

        return HTMLResponse(content="<h1>Auto Mode Demo not found</h1>", status_code=404)

    @fastapi_app.get("/batch-analysis-results", response_class=HTMLResponse)
    async def batch_analysis_results_page(request: Request):
        """Serve the Batch Analysis Results page."""
        batch_results_template_path = BASE_PATH / "app" / "templates" / "pages" / "batch_analysis_results.html"
        if batch_results_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/batch_analysis_results.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Batch Analysis Results template error, falling back to static: %s", e)

        # Fallback to static file
        batch_results_path = BASE_PATH / "static" / "batch_analysis_results.html"
        batch_results_fallback = _render_static_page(batch_results_path)
        if batch_results_fallback:
            return batch_results_fallback

        return HTMLResponse(content="<h1>Batch Analysis Results not found</h1>", status_code=404)

    @fastapi_app.get("/dev/elbow", response_class=HTMLResponse)
    async def elbow_dev():
        """
        Elbow UI - Development mode only.
        The experimental Elbow interface for legal flow assistance.
        """
        if not app_settings.debug:
            return HTMLResponse(
                content="<h1>404 - Not Found</h1><p>This page is only available in development mode.</p>",
                status_code=404
            )
        index_path = BASE_PATH / "static" / "index.html"
        index_fallback = _render_static_page(index_path)
        if index_fallback:
            return index_fallback
        return JSONResponse(content={"error": "Elbow UI not found"}, status_code=404)

    # =========================================================================
    # Vault UI Page (after OAuth redirect)
    # =========================================================================

    @fastapi_app.get("/vault", response_class=HTMLResponse)
    async def vault_page(request: Request):
        """
        Vault UI page - where users land after OAuth authentication.
        Shows their connected storage and vault documents.
        """
        # Apply PageContract guard
        guard_redirect = _guard_by_contract("vault", request)
        if guard_redirect:
            return guard_redirect

        # Telemetry
        try:
            from app.core.telemetry_hooks import EMITTER
            from app.core.user_id import COOKIE_USER_ID
            EMITTER.emit("vault_load", "vault", request.cookies.get(COOKIE_USER_ID, "anon"))
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        # Use template instead of embedded HTML to avoid syntax conflicts
        vault_template_path = BASE_PATH / "app" / "templates" / "pages" / "vault.html"
        if vault_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/vault.html", {
                    "app_name": app_settings.app_name
                })
            except Exception as e:
                logger.warning("Vault template error: %s", e)
        
        # Fallback to simple HTML if template fails
        vault_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Vault - {app_settings.app_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #064e3b 0%, #065f46 100%); 
               color: #fff; 
               min-height: 100vh; 
               padding: 2rem; }}
        .container {{ max-width: 800px; margin: 0 auto; 
                     background: rgba(255,255,255,0.05); 
                     border-radius: 16px; 
                     padding: 2rem; 
                     backdrop-filter: blur(10px); }}
        h1 {{ margin-bottom: 1rem; font-size: 2rem; }}
        .status {{ background: rgba(16, 185, 129, 0.1); 
                  border: 1px solid #10b981; 
                  border-radius: 8px; 
                  padding: 1rem; 
                  margin: 1rem 0; 
                  color: #d1fae5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📁 Document Vault</h1>
        <div class="status">
            ✅ Storage Connected - Your documents are secure in your cloud storage
        </div>
        <p>Vault interface is loading...</p>
        <p>Please ensure your storage is connected.</p>
    </div>
</body>
</html>
        """.format(app_name=app_settings.app_name)
        
        return HTMLResponse(content=vault_html)

    # =========================================================================
    # Calendar Page
    # =========================================================================

    @fastapi_app.get("/calendar", response_class=HTMLResponse)
    async def calendar_page(request: Request):
        """Serve the calendar page."""
        # Try template first
        calendar_template_path = BASE_PATH / "app" / "templates" / "pages" / "calendar.html"
        if calendar_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/calendar.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Calendar template error, falling back to static: %s", e)

        # Fallback to static file
        calendar_path = BASE_PATH / "static" / "tenant" / "calendar.html"
        calendar_fallback = _render_static_page(calendar_path, inject_stage_model=True)
        if calendar_fallback:
            return calendar_fallback
        return HTMLResponse(
            content="<h1>Calendar not found</h1>",
            status_code=404
        )

    # =========================================================================
    # Documents Page
    # =========================================================================

    @fastapi_app.get("/documents", response_class=HTMLResponse)
    async def documents_page(request: Request):
        """Serve the document intake page."""
        # Apply PageContract guard
        guard_redirect = _guard_by_contract("documents", request)
        if guard_redirect:
            return guard_redirect

        # Telemetry
        try:
            from app.core.telemetry_hooks import EMITTER
            from app.core.user_id import COOKIE_USER_ID
            EMITTER.emit("documents_page_load", "documents", request.cookies.get(COOKIE_USER_ID, "anon"))
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        # Try template first
        documents_template_path = BASE_PATH / "app" / "templates" / "pages" / "documents.html"
        if documents_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/documents.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Documents template error, falling back to static: %s", e)

        # Fallback to static file
        documents_path = BASE_PATH / "static" / "documents.html"
        documents_fallback = _render_static_page(documents_path, inject_stage_model=True)
        if documents_fallback:
            return documents_fallback
        return HTMLResponse(
            content="<h1>Documents page not found</h1>",
            status_code=404
        )

    # =========================================================================
    # Law Library Page
    # =========================================================================

    @fastapi_app.get("/law-library", response_class=HTMLResponse)
    async def law_library_page():
        """Serve the law library page."""
        return HTMLResponse(content=_inject_workspace_stage_model(generate_law_library_html()))

    # =========================================================================
    # Command Center Page
    # =========================================================================

    @fastapi_app.get("/command-center", response_class=HTMLResponse)
    async def command_center_page():
        """Serve the command center dashboard."""
        command_center_path = BASE_PATH / "static" / "command_center.html"
        command_center_content = _render_static_page(command_center_path)
        if command_center_content:
            return command_center_content
        return HTMLResponse(
            content="<h1>Command Center not found</h1>",
            status_code=404
        )

    @fastapi_app.get("/functionx", response_class=HTMLResponse)
    async def functionx_page(request: Request):
        """Serve FunctionX workspace page."""
        functionx_template_path = BASE_PATH / "app" / "templates" / "pages" / "functionx.html"
        if functionx_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/functionx.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("FunctionX template error, falling back to static: %s", e)

        fallback_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>FunctionX Workspace</title>
</head>
<body>
    <main style=\"padding: 1rem;\">
        <h1>FunctionX Workspace</h1>
        <p>FunctionX UI is loading fallback mode.</p>
        <a href=\"/api/functionx/sets\">Open FunctionX API</a>
    </main>
</body>
</html>
        """
        return HTMLResponse(content=_inject_workspace_stage_model(fallback_html))

    # =========================================================================
    # Eviction Defense Page
    # =========================================================================

    @fastapi_app.get("/eviction-defense", response_class=HTMLResponse)
    async def eviction_defense_page():
        """Serve the eviction defense toolkit page."""
        return HTMLResponse(content=_inject_workspace_stage_model(generate_eviction_defense_html()))

    # =========================================================================
    # Zoom Court Page
    # =========================================================================

    @fastapi_app.get("/zoom-court", response_class=HTMLResponse)
    async def zoom_court_page():
        """Serve the zoom court helper page."""
        return HTMLResponse(content=_inject_workspace_stage_model(generate_zoom_court_html()))

    # =========================================================================
    # Legal Analysis Page
    # =========================================================================

    @fastapi_app.get("/legal_analysis.html", response_class=HTMLResponse)
    @fastapi_app.get("/legal-analysis", response_class=HTMLResponse)
    async def legal_analysis_page(request: Request):
        """Serve the legal analysis page."""
        # Try template first
        legal_analysis_template_path = BASE_PATH / "app" / "templates" / "pages" / "legal-analysis.html"
        if legal_analysis_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/legal-analysis.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Legal analysis template error, falling back to static: %s", e)

        # Fallback to static file
        legal_analysis_path = BASE_PATH / "static" / "legal_analysis.html"
        legal_analysis_fallback = _render_static_page(legal_analysis_path, inject_stage_model=True)
        if legal_analysis_fallback:
            return legal_analysis_fallback
        return HTMLResponse(
            content="<h1>Legal Analysis page not found</h1>",
            status_code=404
        )

    # =========================================================================
    # My Tenancy Page
    # =========================================================================

    @fastapi_app.get("/my_tenancy.html", response_class=HTMLResponse)
    @fastapi_app.get("/my-tenancy", response_class=HTMLResponse)
    async def my_tenancy_page(request: Request):
        """Serve the my tenancy page."""
        # Try template first
        tenancy_template_path = BASE_PATH / "app" / "templates" / "pages" / "tenancy.html"
        if tenancy_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/tenancy.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Tenancy template error, falling back to static: %s", e)

        # Fallback to static file
        tenancy_path = BASE_PATH / "static" / "my_tenancy.html"
        tenancy_fallback = _render_static_page(tenancy_path)
        if tenancy_fallback:
            return tenancy_fallback
        return HTMLResponse(
            content="<h1>My Tenancy page not found</h1>",
            status_code=404
        )

    # =========================================================================
    # Invite Advocate Page (Tenant-facing)
    # =========================================================================

    @fastapi_app.get("/invite-advocate", response_class=HTMLResponse)
    async def invite_advocate_page():
        """Serve the invite advocate page for tenants."""
        invite_path = BASE_PATH / "static" / "invite-advocate.html"
        invite_fallback = _render_static_page(invite_path)
        if invite_fallback:
            return invite_fallback
        return HTMLResponse(
            content="<h1>Invite Advocate page not found</h1>",
            status_code=404
        )

    # =========================================================================
    # Document Delivery Pages (Professional Send Flow)
    # =========================================================================

    PROFESSIONAL_ROLES = {"advocate", "manager", "legal", "admin"}

    @fastapi_app.get("/delivery/send", response_class=HTMLResponse)
    async def delivery_send_page(request: Request):
        """Serve the document send page for professionals (Advocate, Manager, Legal, Admin)."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID, get_role_from_user_id

        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return RedirectResponse(url="/storage/providers", status_code=302)

        # Verify professional role
        role = get_role_from_user_id(user_id)
        if role not in PROFESSIONAL_ROLES:
            return RedirectResponse(url="/", status_code=302)

        send_path = BASE_PATH / "static" / "delivery_send.html"
        send_fallback = _render_static_page(send_path)
        if send_fallback:
            return send_fallback
        return HTMLResponse(
            content="<h1>Document Send page not found</h1>",
            status_code=404
        )

    # =========================================================================
    # Tenant Pages (My Case)
    # =========================================================================

    def _guard_role_page(request: Request, allowed_roles: set[str]) -> Optional[RedirectResponse]:
        """Lightweight guard: storage connected + expected role for portal page."""
        from app.core.cookie_auth import extract_user_id
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import get_role_from_user_id
        from app.core.workflow_engine import route_user as _route_user

        signed_cookie = request.cookies.get("semptify_uid", "")
        user_id = extract_user_id(request)
        if not user_id:
            # No cookie at all - new user to welcome page
            return RedirectResponse(url="/", status_code=302)
        if not is_valid_storage_user(signed_cookie):
            # Has cookie but invalid - returning user needs reconnect
            return RedirectResponse(url="/storage/reconnect", status_code=302)

        current_role = get_role_from_user_id(user_id) or ""
        if current_role not in allowed_roles:
            return RedirectResponse(url=_route_user(user_id), status_code=302)
        return None

    # =========================================================================
    # Page Contract-Based Route Guards (High-Priority Pages)
    # =========================================================================

    def _guard_by_contract(page_id: str, request: Request) -> Optional[RedirectResponse]:
        """
        Guard a page using its PageContract from route_guards.py.
        Returns RedirectResponse if access denied, None if allowed.
        """
        try:
            from app.core.route_guards import guard, GuardResult
            from app.core.page_contracts import PAGE_CONTRACTS, UserRole
            from app.core.storage_middleware import is_valid_storage_user
            from app.core.user_id import COOKIE_USER_ID, get_role_from_user_id
            from app.core.workflow_engine import route_user as _route_user

            contract = PAGE_CONTRACTS.get(page_id)
            if not contract:
                return None  # No contract = public access

            # Check if anonymous allowed
            if UserRole.ANONYMOUS in contract.roles_supported:
                return None

            # Must be authenticated
            user_id = request.cookies.get(COOKIE_USER_ID)
            if not user_id:
                # No cookie - new user to welcome page
                return RedirectResponse(url="/", status_code=302)
            if not is_valid_storage_user(user_id):
                # Has cookie but invalid - returning user needs reconnect
                return RedirectResponse(url="/storage/reconnect", status_code=302)

            # Check role
            current_role = get_role_from_user_id(user_id) or ""
            allowed_roles = {r.value for r in contract.roles_supported}

            if current_role not in allowed_roles:
                return RedirectResponse(url=_route_user(user_id), status_code=302)

            return None
        except ImportError:
            # Guards not available, allow through
            return None

    def _render_static_page(path: Path, inject_stage_model: bool = False) -> Optional[HTMLResponse]:
        """Read a static HTML page and optionally inject stage-model assets/markup."""
        if not path.exists():
            return None
        html = path.read_text(encoding="utf-8")
        if inject_stage_model:
            html = _inject_workspace_stage_model(html)
        return HTMLResponse(content=html)

    def _inject_workspace_stage_model(html: str) -> str:
        """Inject normalized workspace stage model shell into static role pages."""
        if "id=\"workspaceStageModel\"" in html:
            return html

        css_link = '<link rel="stylesheet" href="/static/css/workspace-stage-model.css">'
        script_tag = '<script src="/static/js/workspace-stage-model.js"></script>'

        if css_link not in html and "</head>" in html:
            html = html.replace("</head>", f"    {css_link}\n</head>")

        panel_html = """
    <section class="workspace-stage-panel" id="workspaceStageModel" style="margin: 1rem;">
        <div class="workspace-stage-header">
            <div>
                <h2>Workflow Stage Model</h2>
                <p>Normalized stage, urgency, next-step, and alerts for this workspace.</p>
            </div>
        </div>
        <div class="workspace-stage-status">
            <div class="workspace-stage-metric"><span>Current Stage</span><strong id="workspaceCaseStageValue">Loading...</strong></div>
            <div class="workspace-stage-metric"><span>Urgency</span><strong id="workspaceUrgencyValue">Loading...</strong></div>
            <div class="workspace-stage-metric"><span>Documents</span><strong id="workspaceDocumentCount">0</strong></div>
            <div class="workspace-stage-metric"><span>Timeline Events</span><strong id="workspaceTimelineCount">0</strong></div>
        </div>
        <div class="workspace-next-step">
            <div class="card">
                <span class="workspace-next-step-label">Recommended Next Step</span>
                <h3 id="workspaceNextStepTitle">Loading...</h3>
                <p id="workspaceNextStepReason">Analyzing workflow state.</p>
                <a class="btn btn--primary btn--sm" id="workspaceNextStepLink" href="/">Continue</a>
            </div>
        </div>
        <div class="workspace-stage-grid" id="workspaceStageCards"></div>
        <div class="workspace-alerts" id="workspaceAlerts"></div>
    </section>
        """

        payload = f"{panel_html}\n    {script_tag}\n"
        if "</body>" in html:
            return html.replace("</body>", f"{payload}</body>")

        return f"{html}\n{payload}"

    @fastapi_app.get("/tenant", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/", response_class=HTMLResponse)
    async def tenant_page(request: Request):
        """Serve the tenant My Case page."""
        guard_redirect = _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect

        # Try template first
        tenant_template_path = BASE_PATH / "app" / "templates" / "pages" / "tenant.html"
        if tenant_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/tenant.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Tenant template error, falling back to static: %s", e)

        # Fallback to static file
        tenant_path = BASE_PATH / "static" / "tenant" / "index.html"
        tenant_fallback = _render_static_page(tenant_path, inject_stage_model=True)
        if tenant_fallback:
            return tenant_fallback
        return HTMLResponse(
            content="<h1>Tenant page not found</h1>",
            status_code=404
        )

    @fastapi_app.get("/documents", response_class=HTMLResponse)
    async def documents_page(request: Request):
        """Universal document page - same process for all roles.
        
        Permission check: Only verify we can access user's cloud storage.
        No role-based restrictions - everyone uploads the same way.
        """
        from app.core.storage_middleware import is_valid_storage_user
        from app.database import get_db
        from app.models import User
        from sqlalchemy import select
        
        # Check 1: Can we access the user's cloud storage?
        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            # No storage access = can't read or write documents
            return RedirectResponse(url="/storage/providers", status_code=302)
        
        # Check 2: Fetch document list from user's cloud storage
        documents = []
        try:
            # Get user's storage session from database
            async for db in get_db():
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user and user.storage_session:
                    # Parse storage session to get provider and token
                    session = json.loads(user.storage_session)
                    provider = session.get("provider")
                    access_token = session.get("access_token")
                    
                    if provider == "google_drive" and access_token:
                        from app.services.storage.google_drive import GoogleDriveStorage
                        storage = GoogleDriveStorage(access_token)
                        vault_files = await storage.list_files("Semptify5.0/Vault/documents")
                        
                        # Convert to simple document list
                        for file in vault_files:
                            if not file.is_folder:
                                documents.append({
                                    "id": file.id,
                                    "filename": file.name,
                                    "uploaded_at": file.modified_at.strftime("%Y-%m-%d %H:%M"),
                                    "size": file.size
                                })
                    # TODO: Add Dropbox and OneDrive support
        except Exception as e:
            logger.warning(f"Failed to list documents: {e}")
            documents = []  # Empty list on error
        
        return templates.TemplateResponse(
            "pages/documents.html",
            {"request": request, "documents": documents, "user_id": user_id}
        )

    @fastapi_app.get("/timeline", response_class=HTMLResponse)
    async def timeline_page(request: Request):
        """Universal timeline page - same for all roles."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID
        from app.core.oauth_token_manager import get_valid_token_for_user
        from app.core.database import get_db_session
        from app.services.storage import get_provider
        from app.services.timeline_extraction import TimelineStore
        from app.services.timeline_chronology import build_timeline_chronology
        
        # Check: Can we access the user's cloud storage?
        user_id = request.cookies.get(COOKIE_USER_ID)
        if not is_valid_storage_user(user_id):
            return RedirectResponse(url="/storage/providers", status_code=302)
        
        events = []
        chronology_items = []
        provider_map = {"G": "google_drive", "D": "dropbox", "O": "onedrive"}
        provider_name = provider_map.get((user_id or "")[:1].upper())

        if provider_name:
            access_token = get_valid_token_for_user(user_id)
            if access_token:
                try:
                    storage = get_provider(provider_name, access_token=access_token)
                    timeline_store = TimelineStore(storage, access_token)
                    events = await timeline_store.get_timeline()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning("Failed to load timeline events from storage: %s", e)

        try:
            async with get_db_session() as db:
                chronology_items = await build_timeline_chronology(events, db)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to build timeline chronology: %s", e)
            chronology_items = []

        return templates.TemplateResponse(
            "pages/timeline.html",
            {
                "request": request,
                "events": events,
                "chronology_items": chronology_items,
                "user_id": user_id,
            }
        )

    async def _get_tenant_briefcase(user_id: str, user_name: Optional[str] = None):
        """Fetch complete tenant briefcase - unified vault, timeline, journal, inbox."""
        from app.core.tenant_briefcase import get_tenant_briefcase
        return await get_tenant_briefcase(user_id, user_name)

    @fastapi_app.get("/tenant/home", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/home/", response_class=HTMLResponse)
    async def tenant_home(request: Request):
        """Serve the tenant home hub page (lightweight entry point after onboarding)."""
        guard_redirect = _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        
        # Get user from cookie/session
        user_id = request.cookies.get("semptify_uid", "")
        briefcase = await _get_tenant_briefcase(user_id) if user_id else None
        
        # Try tenant home template first, then fall back to main tenant template
        tenant_home_template_path = BASE_PATH / "app" / "templates" / "pages" / "tenant_home.html"
        if tenant_home_template_path.exists():
            try:
                context = {"briefcase": briefcase} if briefcase else {
                    "briefcase": None,
                    "vault": {"total_documents": 0, "has_documents": False},
                    "timeline": {"has_timeline": False},
                    "journal": {"has_journal": False},
                    "inbox": {"unread_count": 0},
                    "has_any_data": False,
                    "is_new_tenant": True,
                }
                return templates.TemplateResponse(request, "pages/tenant_home.html", context)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Tenant home template error: %s", e)
        
        # Fallback to main tenant page
        return await tenant_page(request)

    @fastapi_app.get("/tenant/capture", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/capture/", response_class=HTMLResponse)
    async def tenant_capture(request: Request, type: str = None):
        """Quick capture page for recording events."""
        guard_redirect = _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        
        user_id = request.cookies.get("semptify_uid", "")
        briefcase = await _get_tenant_briefcase(user_id) if user_id else None
        
        context = {
            "briefcase": briefcase,
            "capture_type": type,
            "today": datetime.now().strftime("%Y-%m-%d"),
            "csrf_token": request.state.csrf_token if hasattr(request.state, "csrf_token") else "",
        }
        return templates.TemplateResponse(request, "pages/tenant_capture.html", context)

    @fastapi_app.get("/tenant/journal", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/journal/", response_class=HTMLResponse)
    async def tenant_journal(request: Request):
        """Journal page for viewing recorded entries."""
        guard_redirect = _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect

        user_id = request.cookies.get("semptify_uid", "")
        briefcase = await _get_tenant_briefcase(user_id) if user_id else None

        entries = []
        if briefcase and hasattr(briefcase, "journal_entries"):
            entries = briefcase.journal_entries or []

        context = {
            "briefcase": briefcase,
            "entries": entries,
            "total_entries": len(entries),
            "entries_this_month": sum(
                1 for e in entries
                if hasattr(e, "created_at") and e.created_at and
                e.created_at.month == datetime.now().month and
                e.created_at.year == datetime.now().year
            ) if entries else 0,
            "urgent_count": sum(1 for e in entries if getattr(e, "is_urgent", False)),
            "days_since_start": (
                (datetime.now() - min(e.created_at for e in entries if hasattr(e, "created_at") and e.created_at)).days
                if entries else 0
            ),
        }
        return templates.TemplateResponse(request, "pages/tenant_journal.html", context)

    @fastapi_app.get("/tenant/inbox", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/inbox/", response_class=HTMLResponse)
    async def tenant_inbox(request: Request):
        """Inbox for notifications and updates."""
        guard_redirect = _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        
        user_id = request.cookies.get("semptify_uid", "")
        briefcase = await _get_tenant_briefcase(user_id) if user_id else None
        
        context = {"briefcase": briefcase}
        return templates.TemplateResponse(request, "pages/tenant_inbox.html", context)

    @fastapi_app.get("/tenant/help", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/help/", response_class=HTMLResponse)
    async def tenant_help(request: Request):
        """Help and resources page for tenants."""
        guard_redirect = _guard_role_page(request, {"tenant", "user"})
        if guard_redirect:
            return guard_redirect

        user_id = request.cookies.get("semptify_uid", "")
        briefcase = await _get_tenant_briefcase(user_id) if user_id else None

        context = {"briefcase": briefcase}
        return templates.TemplateResponse(request, "pages/tenant_help.html", context)

    @fastapi_app.get("/tenant/tools/letters", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/tools/letters/", response_class=HTMLResponse)
    async def tenant_letters(request: Request):
        """Template letters page — maintenance request, deposit demand, etc."""
        guard_redirect = _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        letters_path = BASE_PATH / "static" / "tenant" / "tools" / "letters.html"
        static_page = _render_static_page(letters_path, inject_stage_model=True)
        if static_page:
            return static_page
        return RedirectResponse(url="/tenant/home", status_code=302)

    @fastapi_app.get("/tenant/tools/deadlines", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/tools/deadlines/", response_class=HTMLResponse)
    async def tenant_deadlines(request: Request):
        """Deadline tracker — rent due, lease end, response deadlines."""
        guard_redirect = _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        deadlines_path = BASE_PATH / "static" / "tenant" / "tools" / "deadlines.html"
        static_page = _render_static_page(deadlines_path, inject_stage_model=True)
        if static_page:
            return static_page
        return RedirectResponse(url="/tenant/home", status_code=302)

    @fastapi_app.get("/tenant/{subpage}", response_class=HTMLResponse)
    async def tenant_subpage(subpage: str, request: Request):
        """Catch-all for tenant sub-pages not matched by explicit routes above."""
        guard_redirect = _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect

        # Security: prevent directory traversal
        if ".." in subpage or "/" in subpage or "\\" in subpage:
            return HTMLResponse(content="<h1>400 - Invalid Request</h1>", status_code=400)

        # Try subpage.html first, then subpage/index.html
        subpage_path = BASE_PATH / "static" / "tenant" / f"{subpage}.html"
        subpage_fallback = _render_static_page(subpage_path, inject_stage_model=True)
        if subpage_fallback:
            return subpage_fallback

        subpage_index = BASE_PATH / "static" / "tenant" / subpage / "index.html"
        subpage_index_fallback = _render_static_page(subpage_index, inject_stage_model=True)
        if subpage_index_fallback:
            return subpage_index_fallback

        # Fallback: redirect to tenant home (not the old Case page)
        return RedirectResponse(url="/tenant/home", status_code=302)

    # =========================================================================
    # Advocate Pages
    # =========================================================================

    @fastapi_app.get("/advocate", response_class=HTMLResponse)
    @fastapi_app.get("/advocate/", response_class=HTMLResponse)
    async def advocate_page(request: Request):
        """Serve the advocate dashboard page."""
        guard_redirect = _guard_role_page(request, {"advocate"})
        if guard_redirect:
            return guard_redirect

        advocate_template_path = BASE_PATH / "app" / "templates" / "pages" / "advocate.html"
        if advocate_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/advocate.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Advocate template error, falling back to static: %s", e)

        advocate_path = BASE_PATH / "static" / "advocate" / "index.html"
        advocate_fallback = _render_static_page(advocate_path, inject_stage_model=True)
        if advocate_fallback:
            return advocate_fallback

        return HTMLResponse(content="<h1>Advocate page not found</h1>", status_code=404)

    @fastapi_app.get("/advocate/{subpage}", response_class=HTMLResponse)
    async def advocate_subpage(subpage: str, request: Request):
        """Serve advocate sub-pages."""
        guard_redirect = _guard_role_page(request, {"advocate"})
        if guard_redirect:
            return guard_redirect

        if ".." in subpage or "/" in subpage or "\\" in subpage:
            return HTMLResponse(content="<h1>400 - Invalid Request</h1>", status_code=400)

        subpage_path = BASE_PATH / "static" / "advocate" / f"{subpage}.html"
        subpage_fallback = _render_static_page(subpage_path, inject_stage_model=True)
        if subpage_fallback:
            return subpage_fallback

        subpage_index = BASE_PATH / "static" / "advocate" / subpage / "index.html"
        subpage_index_fallback = _render_static_page(subpage_index, inject_stage_model=True)
        if subpage_index_fallback:
            return subpage_index_fallback

        return RedirectResponse(url="/advocate", status_code=302)

    @fastapi_app.get("/advocate/home", response_class=HTMLResponse)
    @fastapi_app.get("/advocate/home/", response_class=HTMLResponse)
    async def advocate_home(request: Request):
        """Serve the advocate home hub page (lightweight entry point after onboarding)."""
        guard_redirect = _guard_role_page(request, {"advocate"})
        if guard_redirect:
            return guard_redirect
        
        # Try advocate home template first, then fall back to main advocate template
        advocate_home_template_path = BASE_PATH / "app" / "templates" / "pages" / "advocate_home.html"
        if advocate_home_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/advocate_home.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Advocate home template error: %s", e)
        
        # Fallback to main advocate page
        return await advocate_page(request)

    # =========================================================================
    # Legal Pages
    # =========================================================================

    @fastapi_app.get("/legal", response_class=HTMLResponse)
    @fastapi_app.get("/legal/", response_class=HTMLResponse)
    async def legal_page(request: Request):
        """Serve the legal dashboard page."""
        guard_redirect = _guard_role_page(request, {"legal"})
        if guard_redirect:
            return guard_redirect

        legal_template_path = BASE_PATH / "app" / "templates" / "pages" / "legal.html"
        if legal_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/legal.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Legal template error, falling back to static: %s", e)

        legal_path = BASE_PATH / "static" / "legal" / "index.html"
        legal_fallback = _render_static_page(legal_path, inject_stage_model=True)
        if legal_fallback:
            return legal_fallback

        return HTMLResponse(content="<h1>Legal page not found</h1>", status_code=404)

    @fastapi_app.get("/legal/{subpage}", response_class=HTMLResponse)
    async def legal_subpage(subpage: str, request: Request):
        """Serve legal sub-pages with compatibility aliases."""
        guard_redirect = _guard_role_page(request, {"legal"})
        if guard_redirect:
            return guard_redirect

        if ".." in subpage or "/" in subpage or "\\" in subpage:
            return HTMLResponse(content="<h1>400 - Invalid Request</h1>", status_code=400)

        subpage_aliases = {
            "clients": "cases",
            "queue": "cases",
            "calendar": "cases",
            "work-product": "privileged",
            "research": None,
            "library": None,
        }
        target = subpage_aliases.get(subpage, subpage)

        if target is None:
            return RedirectResponse(url="/law-library", status_code=302)

        subpage_path = BASE_PATH / "static" / "legal" / f"{target}.html"
        subpage_fallback = _render_static_page(subpage_path, inject_stage_model=True)
        if subpage_fallback:
            return subpage_fallback

        subpage_index = BASE_PATH / "static" / "legal" / target / "index.html"
        subpage_index_fallback = _render_static_page(subpage_index, inject_stage_model=True)
        if subpage_index_fallback:
            return subpage_index_fallback

        return RedirectResponse(url="/legal", status_code=302)

    @fastapi_app.get("/legal/home", response_class=HTMLResponse)
    @fastapi_app.get("/legal/home/", response_class=HTMLResponse)
    async def legal_home(request: Request):
        """Serve the legal home hub page (lightweight entry point after onboarding)."""
        guard_redirect = _guard_role_page(request, {"legal"})
        if guard_redirect:
            return guard_redirect
        
        # Try legal home template first, then fall back to main legal template
        legal_home_template_path = BASE_PATH / "app" / "templates" / "pages" / "legal_home.html"
        if legal_home_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/legal_home.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Legal home template error: %s", e)
        
        # Fallback to main legal page
        return await legal_page(request)

    # =========================================================================
    # Admin Pages
    # =========================================================================

    @fastapi_app.get("/admin", response_class=HTMLResponse)
    @fastapi_app.get("/admin/", response_class=HTMLResponse)
    async def admin_page(request: Request):
        """Serve the admin dashboard page."""
        guard_redirect = _guard_role_page(request, {"admin", "manager"})
        if guard_redirect:
            return guard_redirect

        admin_template_path = BASE_PATH / "app" / "templates" / "pages" / "admin.html"
        if admin_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/admin.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Admin template error, falling back to static: %s", e)

        admin_path = BASE_PATH / "static" / "admin" / "mission_control.html"
        admin_fallback = _render_static_page(admin_path, inject_stage_model=True)
        if admin_fallback:
            return admin_fallback

        return HTMLResponse(content="<h1>Admin page not found</h1>", status_code=404)

    @fastapi_app.get("/admin/{subpage}", response_class=HTMLResponse)
    async def admin_subpage(subpage: str, request: Request):
        """Serve admin sub-pages with aliases for compatibility."""
        guard_redirect = _guard_role_page(request, {"admin", "manager"})
        if guard_redirect:
            return guard_redirect

        if ".." in subpage or "/" in subpage or "\\" in subpage:
            return HTMLResponse(content="<h1>400 - Invalid Request</h1>", status_code=400)

        subpage_aliases = {
            "users": "gui_navigation_hub",
            "system": "mission_control",
            "analytics": "documentation_hub",
            "logs": "documentation_hub",
            "mission-control": "mission_control",
            "gui": "gui_navigation_hub",
            "mode-selector": "mode_selector",
            "easy-mode": "easy_mode_selector",
            "docs": "documentation_hub",
        }
        target = subpage_aliases.get(subpage, subpage)

        subpage_path = BASE_PATH / "static" / "admin" / f"{target}.html"
        subpage_fallback = _render_static_page(subpage_path, inject_stage_model=True)
        if subpage_fallback:
            return subpage_fallback

        subpage_index = BASE_PATH / "static" / "admin" / target / "index.html"
        subpage_index_fallback = _render_static_page(subpage_index, inject_stage_model=True)
        if subpage_index_fallback:
            return subpage_index_fallback

        return RedirectResponse(url="/admin", status_code=302)

    @fastapi_app.get("/admin/home", response_class=HTMLResponse)
    @fastapi_app.get("/admin/home/", response_class=HTMLResponse)
    async def admin_home(request: Request):
        """Serve the admin home hub page (lightweight entry point after onboarding)."""
        guard_redirect = _guard_role_page(request, {"admin"})
        if guard_redirect:
            return guard_redirect
        
        # Try admin home template first, then fall back to main admin template
        admin_home_template_path = BASE_PATH / "app" / "templates" / "pages" / "admin_home.html"
        if admin_home_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/admin_home.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Admin home template error: %s", e)
        
        # Fallback to main admin page
        return await admin_page(request)

    @fastapi_app.get("/manager/home", response_class=HTMLResponse)
    @fastapi_app.get("/manager/home/", response_class=HTMLResponse)
    async def manager_home(request: Request):
        """Serve the manager (case manager) home hub page (lightweight entry point after onboarding)."""
        guard_redirect = _guard_role_page(request, {"manager"})
        if guard_redirect:
            return guard_redirect
        
        # Try manager home template first, then fall back to admin template (manager uses admin UI)
        manager_home_template_path = BASE_PATH / "app" / "templates" / "pages" / "manager_home.html"
        if manager_home_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/manager_home.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Manager home template error: %s", e)
        
        # Fallback to main admin page (manager uses admin UI)
        return await admin_page(request)

    @fastapi_app.get("/onboarding/max-redirects", response_class=HTMLResponse)
    @fastapi_app.get("/onboarding/max-redirects/", response_class=HTMLResponse)
    async def onboarding_max_redirects(request: Request):
        """
        Special instructions page displayed when user has been redirected too many times.
        This happens when onboarding keeps getting interrupted (network issues, browser closes, etc).
        """
        return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Onboarding Assistance - Semptify</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 1rem;
                }
                .container {
                    background: white;
                    border-radius: 16px;
                    padding: 2rem;
                    max-width: 600px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                }
                .icon { font-size: 4rem; margin-bottom: 1rem; }
                h1 { color: #1f2937; font-size: 2rem; margin-bottom: 0.5rem; }
                .subtitle { color: #6b7280; font-size: 1.1rem; margin-bottom: 2rem; }
                .content {
                    background: #f9fafb;
                    border-radius: 12px;
                    padding: 1.5rem;
                    margin-bottom: 2rem;
                    text-align: left;
                }
                .content h2 { color: #1f2937; font-size: 1.1rem; margin-bottom: 1rem; }
                .content p { color: #4b5563; line-height: 1.6; margin-bottom: 0.75rem; }
                .content ul { list-style: none; margin-left: 0; }
                .content li { 
                    color: #4b5563; 
                    padding: 0.5rem 0;
                    padding-left: 1.75rem;
                    position: relative;
                }
                .content li::before {
                    content: '✓';
                    position: absolute;
                    left: 0;
                    color: #10b981;
                    font-weight: bold;
                }
                .buttons {
                    display: flex;
                    gap: 1rem;
                    margin-bottom: 1.5rem;
                }
                .btn {
                    flex: 1;
                    padding: 0.75rem 1.5rem;
                    border: none;
                    border-radius: 8px;
                    font-size: 1rem;
                    cursor: pointer;
                    font-weight: 600;
                    transition: all 0.2s;
                    display: inline-block;
                    text-decoration: none;
                    text-align: center;
                }
                a.btn-primary, .btn-primary {
                    background: #d97706;
                    color: white;
                }
                a.btn-primary:hover, .btn-primary:hover { background: #b45309; }
                a.btn-secondary, .btn-secondary {
                    background: #e5e7eb;
                    color: #1f2937;
                }
                a.btn-secondary:hover, .btn-secondary:hover { background: #d1d5db; }
                .footer {
                    font-size: 0.9rem;
                    color: #9ca3af;
                }
                .footer a {
                    color: #d97706;
                    text-decoration: none;
                }
                .footer a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">⚠️</div>
                <h1>Onboarding Needs Reset</h1>
                <p class="subtitle">We've noticed the setup is stuck. Let's get you back on track.</p>
                
                <div class="content">
                    <h2>What Happened?</h2>
                    <p>
                        We've tried to redirect you to complete onboarding multiple times, but something 
                        keeps interrupting the process. This can happen due to:
                    </p>
                    <ul>
                        <li>Network connection dropped during setup</li>
                        <li>Browser window was closed mid-setup</li>
                        <li>Storage provider connection issues</li>
                        <li>Browser cache conflicts</li>
                    </ul>
                </div>
                
                <div class="content">
                    <h2>Quick Fixes to Try</h2>
                    <ul>
                        <li><strong>Clear your browser cache:</strong> Try Ctrl+Shift+Delete or Cmd+Shift+Delete</li>
                        <li><strong>Try a fresh browser:</strong> Use Incognito or Private Browsing mode</li>
                        <li><strong>Check your internet:</strong> Ensure you have a stable connection</li>
                        <li><strong>Use a different device:</strong> If available, try another computer or phone</li>
                    </ul>
                </div>
                
                <div class="buttons">
                    <a href="/" class="btn btn-primary">Try Again</a>
                    <a href="/storage/logout-reset" class="btn btn-secondary">Clear Session & Restart</a>
                </div>
                
                <div class="footer">
                    Still stuck? <a href="mailto:support@semptify.com">Contact support</a> and we'll help you get started.
                </div>
            </div>
        </body>
        </html>
        """)

    # =========================================================================
    # Catch-All HTML Page Router
    # =========================================================================

    @fastapi_app.get("/{page_name}.html", response_class=HTMLResponse)
    async def serve_html_page(page_name: str, request: Request):
        """
        Serve any HTML page from the static folder.
        This catch-all route allows accessing pages like /dashboard.html, /documents.html, etc.
        
        High-priority pages are protected by PageContract guards.
        """
        # Security: prevent directory traversal
        if ".." in page_name or "/" in page_name or "\\" in page_name:
            return HTMLResponse(content="<h1>400 - Invalid Request</h1>", status_code=400)
        
        # Apply PageContract guards for high-priority pages
        # Map file names to page_ids
        high_priority_pages = {
            "court_packet": "court_packet",
            "eviction_answer": "eviction_answer",
            "hearing_prep": "hearing_prep",
            "storage_setup": "storage_setup",
            "crisis_intake": "crisis_intake",
        }
        
        if page_name in high_priority_pages:
            page_id = high_priority_pages[page_name]
            guard_redirect = _guard_by_contract(page_id, request)
            if guard_redirect:
                return guard_redirect
            # Telemetry — map page_name to its load event
            load_events = {
                "court_packet": "court_packet_load",
                "eviction_answer": "eviction_answer_load",
                "hearing_prep": "hearing_prep_load",
                "storage_setup": "storage_setup_load",
                "crisis_intake": "crisis_intake_load",
            }
            try:
                from app.core.telemetry_hooks import EMITTER
                from app.core.user_id import COOKIE_USER_ID
                EMITTER.emit(
                    load_events[page_name],
                    page_id,
                    request.cookies.get(COOKIE_USER_ID, "anon"),
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        page_path = BASE_PATH / "static" / f"{page_name}.html"
        page_fallback = _render_static_page(page_path)
        if page_fallback:
            return page_fallback
        
        return JSONResponse(
            content={"error": "not_found", "message": f"Page '{page_name}.html' not found"},
            status_code=404
        )

    return fastapi_app
# Create the app instance
app = create_app()


# =============================================================================
# Development Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    runtime_settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=runtime_settings.host,
        port=runtime_settings.port,
        reload=runtime_settings.debug,
    )


