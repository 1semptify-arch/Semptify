from app.modules.admin_console.module_admin_console import register_admin_console_module
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

# Fix Vertex AI session ID collisions that block OAuth
try:
    from app.services.vertex_session_fix import patch_vertex_session_creation
    patch_vertex_session_creation()
except ImportError:
    pass  # Vertex AI not available

# Python version check - Semptify MANDATES Python 3.11.9 ONLY
# This is a hard requirement. Do NOT change without explicit approval.
# No add-ons, modules, or extensions may require a different Python version.
python_version = sys.version_info
if python_version[:2] != (3, 11):
    print("=" * 70)
    print("CRITICAL: Python 3.11.9 REQUIRED — HARD STOP")
    print("=" * 70)
    print(f"Detected Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    print("Semptify mandates Python 3.11.9. No other version is permitted.")
    print("This applies to ALL modules, add-ons, and extensions.")
    print("")
    print("Setup:")
    print("  1. Install Python 3.11.9: https://python.org/downloads/release/python-3119/")
    print("  2. python3.11 -m venv venv311")
    print("  3. .\\venv311\\Scripts\\Activate.ps1")
    print("  4. pip install -r requirements.txt")
    print("  5. python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    print("=" * 70)
    sys.exit(1)
else:
    print(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} - OK")

import asyncio
import datetime
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, APIRouter, Depends
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.compliance import validate_app_compliance
from app.core.cookie_auth import extract_user_id
from app.core.database import init_db, close_db
from app.core.navigation import navigation
from app.core.ssot_guard import ssot_redirect
from app.core.tenant_briefcase import get_tenant_briefcase

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

# Add custom Jinja2 filters
def format_date_filter(value):
    """Format datetime for display in templates."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            from datetime import datetime
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value
    return value.strftime("%B %d, %Y") if hasattr(value, "strftime") else str(value)

templates.env.filters["format_date"] = format_date_filter

# Product Manifest — replaces the 200+ line router-import block
from app.core.product_manifest import ProductTier, register_tiers
from app.core.utc import utc_now
from app.core.contract_loader import load_all_contracts


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
    lifespan_logger = logging.getLogger(__name__)
    
    # Configuration
    TOTAL_TIMEOUT = 120  # Total seconds allowed for setup (increased for slow migrations)
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
        bar = "â–ˆ" * stage_num + "â–‘" * (total - stage_num)
        lifespan_logger.info("[%s] Stage %s/%s: %s - %s (%.1fs elapsed, %.1fs remaining)", bar, stage_num, total, name, status, elapsed, remaining)
    
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
                
                log_stage(stage_num, total, name, "âœ… COMPLETE")
                return True
                
            except (ValueError, RuntimeError, ImportError, AssertionError, TimeoutError) as e:
                lifespan_logger.warning("Stage %s '%s' attempt %s failed: %s", stage_num, name, attempt, e)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(STAGE_DELAY)
                else:
                    raise RuntimeError(f"Stage {stage_num} '{name}' failed after {MAX_RETRIES} attempts: {e}") from e
        return False
    
    async def wipe_and_reset():
        """Wipe everything clean for fresh start."""
        lifespan_logger.warning("=" * 50)
        lifespan_logger.warning("âš ï¸  WIPING EVERYTHING FOR FRESH START...")
        lifespan_logger.warning("=" * 50)
        
        # Remove runtime directories
        dirs_to_wipe = ["uploads", "logs", "data/semptify.db"]
        for dir_path in dirs_to_wipe:
            path = Path(dir_path)
            if path.exists():
                if path.is_file():
                    path.unlink()
                    lifespan_logger.info("  Removed file: %s", dir_path)
                else:
                    shutil.rmtree(path, ignore_errors=True)
                    lifespan_logger.info("  Removed directory: %s", dir_path)
        
        # Sessions and OAuth states are now DB-backed (no in-memory dicts to clear)
        lifespan_logger.info("  Sessions/OAuth states are DB-backed - no cache to clear")
        
        lifespan_logger.warning("ðŸ§¹ Wipe complete - ready for fresh start")
    
    # =========================================================================
    # STAGED SETUP PROCESS
    # =========================================================================
    
    TOTAL_STAGES = 7
    
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
    
    lifespan_logger.info("=" * 60)
    lifespan_logger.info("ðŸš€ STARTING %s v%s", lifespan_settings.app_name, lifespan_settings.app_version)
    lifespan_logger.info("   Security mode: %s", lifespan_settings.security_mode)
    lifespan_logger.info("   Timeout: %ss | Retries per stage: %s", TOTAL_TIMEOUT, MAX_RETRIES)
    lifespan_logger.info("=" * 60)
    
    try:
        # --- STAGE 1: Verify Requirements ---
        missing_required: list[str] = []
        missing_optional: list[str] = []
        
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
                    lifespan_logger.warning("   âš ï¸  Optional: %s not installed", pkg)
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
        
        # --- STAGE 3b: Run Database Migrations (Alembic) ---
        async def run_migrations():
            """Auto-run Alembic migrations on startup for Render deploys."""
            import asyncio, os
            
            # Only run auto-migration in production (Render sets RENDER=true)
            if not os.environ.get("RENDER"):
                lifespan_logger.info("   â­ï¸  Auto-migration skipped (local dev)")
                return
            
            def _sync_migrate():
                from alembic.config import Config
                from alembic import command
                alembic_cfg = Config("alembic.ini")
                command.upgrade(alembic_cfg, "head")
            
            try:
                # Run in thread executor to avoid blocking the async event loop
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(loop.run_in_executor(None, _sync_migrate), timeout=120)
                lifespan_logger.info("   âœ… Database migrations applied")
                
            except asyncio.TimeoutError:
                lifespan_logger.warning("   âš ï¸  Migration timed out after 30s - continuing startup")
            except Exception as e:
                lifespan_logger.warning("   âš ï¸  Migration check failed (may be first run): %s", e)
                # Don't fail startup - migrations can be run manually if needed
        
        def verify_migrations():
            # Migrations are optional auto-step, always return True
            # App will work without them (though new features may fail)
            return True
        
        await run_stage(3, TOTAL_STAGES, "Database Migrations", run_migrations, verify_migrations)

        # --- STAGE 3b: Initialize module_overrides schema + warm cache ---
        async def init_module_overrides():
            from app.core.database import get_session_factory
            from app.core.module_overrides import ensure_schema, load_overrides
            factory = get_session_factory()
            async with factory() as db:
                await ensure_schema(db)
                await load_overrides(db)
            lifespan_logger.info("   Module overrides schema ensured and cache warmed")

        def verify_module_overrides():
            return True

        await run_stage(3, TOTAL_STAGES, "Module Overrides Init", init_module_overrides, verify_module_overrides)

        # --- STAGE 3.5: Load Module Contracts ---
        async def load_contracts():
            result = load_all_contracts()
            lifespan_logger.info("   Contracts: %s loaded, %s failed, %s total",
                                 result["loaded"], result["failed"], result["total_contracts"])

        def verify_contracts():
            from app.core.module_contracts import contract_registry
            return len(contract_registry.list_contracts()) > 0

        await run_stage(4, TOTAL_STAGES, "Load Module Contracts", load_contracts, verify_contracts)

        # --- STAGE 4: Load Configuration ---
        async def load_config():
            # Verify settings are accessible
            _ = lifespan_settings.app_name
            _ = lifespan_settings.security_mode

        def verify_config():
            return lifespan_settings.app_name is not None

        await run_stage(5, TOTAL_STAGES, "Load Configuration", load_config, verify_config)
        
        # --- STAGE 5: Initialize Services ---
        async def init_services():
            # Heavy services re-enabled with memory fixes (deque bounds, no net_connections).
            # Guard with ENABLE_HEAVY_SERVICES=false for emergency rollback.
            enable_heavy = os.getenv("ENABLE_HEAVY_SERVICES", "true").lower() != "false"
            if not enable_heavy:
                logger.info("   Heavy services skipped (ENABLE_HEAVY_SERVICES=false)")

            # Positronic Brain - re-enabled (event_history was already capped at 1000)
            if enable_heavy:
                try:
                    from app.services.brain_integrations import initialize_brain_connections
                    await initialize_brain_connections()
                    logger.info("   Positronic Brain initialized with all modules")
                except Exception as e:
                    logger.warning(f"   Positronic Brain init failed (non-fatal): {e}")

            # Module Hub - re-enabled (unbounded lists replaced with deque(maxlen=N))
            if enable_heavy:
                try:
                    from app.services.module_registration import register_all_modules
                    from app.services.module_actions import register_all_actions
                    register_all_modules()
                    register_all_actions()
                    logger.info("   Module Hub initialized")
                except Exception as e:
                    logger.warning(f"   Module Hub init failed (non-fatal): {e}")

            # Location Service - re-enabled
            if enable_heavy:
                try:
                    from app.services.location_service import register_with_mesh
                    register_with_mesh()
                    logger.info("   Location Service initialized")
                except Exception as e:
                    logger.warning(f"   Location Service init failed (non-fatal): {e}")

            # Complaint Wizard - DISABLED
            # from app.modules.complaint_wizard_module import register_with_mesh as register_complaint_wizard
            # register_complaint_wizard()
            # logger.info("   ðŸ“ Complaint Wizard initialized")
            
            # Mesh Network - DISABLED (major memory consumer)
            # from app.services.mesh_handlers import register_all_mesh_handlers
            # mesh_stats = register_all_mesh_handlers()
            # logger.info("   ðŸ•¸ï¸ Mesh Network initialized")

            # Plugin System - DISABLED
            # from app.sdk.plugin_manager import plugin_manager
            # discovered_plugins = plugin_manager.discover_plugins()
            # plugin_stats = plugin_manager.load_all()
            
            logger.info("   âš¡ Core services only - mesh/brain/plugins DISABLED for memory optimization")

            from app.core.event_subscribers import register_all_subscribers
            register_all_subscribers()
            logger.info("   Event subscribers registered")
        
        await run_stage(6, TOTAL_STAGES, "Initialize Services", init_services)

        # --- STAGE 7: Final Verification ---
        async def final_check():
            # Verify critical paths exist
            assert Path("uploads/vault").exists(), "Vault directory missing"
            assert Path("data").exists(), "Data directory missing"
        
        async def verify_final():
            # Test a simple endpoint would work
            return True
        
        await run_stage(7, TOTAL_STAGES, "Final Verification", final_check, verify_final)

        # --- STAGE 8: PRODUCTION MODE VALIDATION (if enforced) ---
        if lifespan_settings.security_mode == "enforced":
            TOTAL_STAGES = 8
            
            async def validate_production():
                """Validate production security requirements."""
                from app.core.production_init import validate_production_mode
                # This will raise an error if any security requirement fails
                validate_production_mode()
            
            def verify_production():
                return True  # If we get here, validation passed
            
            await run_stage(8, TOTAL_STAGES, "Production Security Validation", validate_production, verify_production)
        
        # --- SETUP COMPLETE ---
        total_time = time.time() - start_time
        
        lifespan_logger.info("")
        lifespan_logger.info("=" * 60)
        lifespan_logger.info("âœ… âœ… âœ…  ALL STAGES COMPLETE  âœ… âœ… âœ…")
        lifespan_logger.info("   Setup completed in %.2f seconds", total_time)
        lifespan_logger.info("")
        if lifespan_settings.security_mode == "enforced":
            lifespan_logger.info("   ðŸ”’ PRODUCTION MODE: ENFORCED SECURITY ACTIVE")
        lifespan_logger.info("   ðŸŒ Server: http://localhost:8000")
        lifespan_logger.info("   ðŸ“„ Welcome: http://localhost:8000/")
        lifespan_logger.info("   ðŸ“š API Docs: http://localhost:8000/api/docs")
        lifespan_logger.info("=" * 60)
        lifespan_logger.info("")
        
    except TimeoutError as e:
        lifespan_logger.error("âŒ SETUP TIMEOUT: %s", e)
        await wipe_and_reset()
        raise SystemExit("Setup failed - timeout exceeded") from e
        
    except (RuntimeError, ValueError, ImportError, AssertionError, OSError) as e:
        lifespan_logger.error("âŒ SETUP FAILED: %s", e)
        await wipe_and_reset()
        raise SystemExit(f"Setup failed after retries: {e}") from e
    
    # Register graceful shutdown handler
    from app.core.shutdown import register_shutdown_handler, task_manager
    register_shutdown_handler()
    
    # DISABLED: Distributed mesh network (memory hog)
    # try:
    #     await start_mesh_network()
    #     lifespan_logger.info("ðŸŒ Distributed Mesh Network started")
    # except (OSError, RuntimeError, ValueError) as e:
    #     lifespan_logger.warning("âš ï¸ Mesh network start warning: %s", e)

    yield  # Application runs here

    # --- GRACEFUL SHUTDOWN ---
    lifespan_logger.info("")
    lifespan_logger.info("=" * 50)
    lifespan_logger.info("ðŸ›‘ SHUTTING DOWN GRACEFULLY...")
    lifespan_logger.info("=" * 50)
    
    # Wait for background tasks to complete
    await task_manager.wait_for_completion(timeout=10.0)
    lifespan_logger.info("   Background tasks completed")

    # DISABLED: Distributed mesh network
    # try:
    #     await stop_mesh_network()
    #     lifespan_logger.info("ðŸŒ Distributed Mesh Network stopped")
    # except (OSError, RuntimeError, ValueError) as e:
    #     lifespan_logger.warning("âš ï¸ Mesh network stop warning: %s", e)

    await close_db()
    lifespan_logger.info("   Database connections closed")
    lifespan_logger.info("   Goodbye! ðŸ‘‹")
    lifespan_logger.info("=" * 50)
# =============================================================================
# HTML Page Generators for Legal Tools
# =============================================================================


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
        <div class="logo">âš–ï¸ Eviction Defense Toolkit</div>
        <nav class="nav-links">
            <a href="/documents">ðŸ“„ Documents</a>
            <a href="/timeline">ðŸ“… Timeline</a>
            <a href="/law-library">ðŸ“š Law Library</a>
            <a href="/zoom-court">ðŸ’» Zoom Court</a>
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
            <button class="tab active" onclick="showPanel('motions')">ðŸ“‹ Motions</button>
            <button class="tab" onclick="showPanel('forms')">ðŸ“ Forms</button>
            <button class="tab" onclick="showPanel('procedures')">ðŸ“š Procedures</button>
            <button class="tab" onclick="showPanel('defenses')">ðŸ›¡ï¸ Defenses</button>
            <button class="tab" onclick="showPanel('counterclaims')">âš”ï¸ Counterclaims</button>
            <button class="tab" onclick="showPanel('timeline')">ðŸ“… Case Timeline</button>
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
            <button class="modal-close" onclick="closeModal()">Ã—</button>
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
        <div class="logo">ðŸ’» Zoom Court Helper</div>
        <nav class="nav-links">
            <a href="/documents">ðŸ“„ Documents</a>
            <a href="/timeline">ðŸ“… Timeline</a>
            <a href="/law-library">ðŸ“š Law Library</a>
            <a href="/eviction-defense">âš–ï¸ Eviction Defense</a>
        </nav>
    </header>
    <div class="container">
        <h1 class="page-title">Zoom Court Helper</h1>
        <p class="page-subtitle">Prepare for your virtual court hearing with confidence</p>
        
        <div class="grid">
            <div class="card" onclick="scrollTo('checklist')">
                <div class="card-icon">âœ…</div>
                <div class="card-title">Tech Checklist</div>
                <div class="card-desc">Ensure your technology is ready for court</div>
            </div>
            <div class="card" onclick="scrollTo('etiquette')">
                <div class="card-icon">ðŸŽ©</div>
                <div class="card-title">Court Etiquette</div>
                <div class="card-desc">Proper behavior for virtual hearings</div>
            </div>
            <div class="card" onclick="scrollTo('phrases')">
                <div class="card-icon">ðŸ—£ï¸</div>
                <div class="card-title">What to Say</div>
                <div class="card-desc">Phrases to use when addressing the court</div>
            </div>
            <div class="card" onclick="scrollTo('tips')">
                <div class="card-icon">ðŸ’¡</div>
                <div class="card-title">Quick Tips</div>
                <div class="card-desc">Essential tips for before, during, and after</div>
            </div>
        </div>
        
        <div class="checklist" id="checklist">
            <h2 class="checklist-title">ðŸ“‹ Technology Checklist</h2>
            <div id="tech-checklist">Loading checklist...</div>
        </div>
        
        <div class="etiquette" id="etiquette">
            <h2 class="checklist-title">ðŸŽ© Court Etiquette Rules</h2>
            <div id="etiquette-rules">Loading etiquette rules...</div>
        </div>
        
        <div class="phrases-section" id="phrases">
            <h2 class="checklist-title">ðŸ—£ï¸ Helpful Phrases</h2>
            <div id="phrases-list">Loading phrases...</div>
        </div>
        
        <div class="tips-section" id="tips">
            <h2 class="checklist-title">ðŸ’¡ Quick Tips</h2>
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
                        <div class="fix">${item.description} â€” Fix: ${item.how_to_fix}</div>
                    </label>
                </div>
            `).join('');
            
            // Load etiquette
            const etiquette = await fetch('/api/zoom-court/etiquette').then(r => r.json());
            document.getElementById('etiquette-rules').innerHTML = etiquette.map(rule => `
                <div class="rule-item">
                    <div class="rule-icon">ðŸ“Œ</div>
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

# Module-level logger for middleware functions
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Application factory. Creates and configures the FastAPI application."""
    # Use module-level logger for create_app
    app_logger = logger
    
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
            "email": "support@semptify.org",
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
    # Onboarding Module (self-contained, config-driven onboarding system)
    # =========================================================================
    from app.modules.onboarding import register_onboarding, OnboardingConfig

    onboarding_config = OnboardingConfig(
        product_name="Semptify Tenant Rights",
        allowed_roles=["tenant", "admin"],
        allowed_providers=["google_drive", "dropbox", "onedrive"],
        on_complete_redirect="/home",
        # Disable duplicate gate middleware â€” StorageRequirementMiddleware already
        # enforces all gates via app/core/onboarding_state.py (single source of truth).
        # Running both causes redirect loops.
        enable_gate_middleware=False,
    )
    register_onboarding(fastapi_app, onboarding_config)

    # =========================================================================
    # Vault Installer - Simple Direct Installation
    # =========================================================================
    from app.modules.vault_installer import register_vault_installer
    register_vault_installer(fastapi_app)

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

    # =========================================================================
    # Dev Mode Middleware — strict logging for modules in development
    # =========================================================================
    from app.core.dev_mode_middleware import DevModeMiddleware
    fastapi_app.add_middleware(DevModeMiddleware)
    
    # Initialize OAuth token manager
    from app.core.oauth_token_manager import init_oauth_token_manager
    init_oauth_token_manager()
    
    # Initialize Event Bus (central nervous system)
    from app.core.event_bus import event_bus, EventType
    logger.info("ðŸ“¢ Event Bus initialized with %d event types", len(EventType))
    
    # Initialize Context Loop (background processing engine)
    # Wire up event subscribers
    try:
        from app.modules.context_loop.service import subscribe_context_loop_events
        subscribe_context_loop_events()
        logger.info("ðŸ§ Context Loop event subscribers wired")
    except ImportError:
        logger.warning("Context Loop not available (optional module)")

    # Wire filedored on-demand folder creation + document sorting
    try:
        from app.services.filedored_service import process_uploaded_document
        from app.core.event_bus import EventType as _ET

        async def _on_document_added(event, data: dict = None):
            if data is None:
                data = event.data if hasattr(event, "data") else {}
            vault_id = data.get("vault_id")
            user_id = data.get("user_id")
            filename = data.get("filename", "")
            if not vault_id or not user_id:
                return
            try:
                from app.services.vault_upload_service import VaultUploadService
                from app.services.filedored_service import ensure_filedored_folders
                from app.core.oauth_token_manager import get_valid_token_for_user
                vault_svc = VaultUploadService()
                doc = await vault_svc.get_document(vault_id, user_id)
                content = b""
                if doc:
                    try:
                        content = await vault_svc._get_document_content(doc) or b""
                    except Exception:
                        pass
                    # Ensure filedored folders exist on-demand (lazy, first upload only)
                    try:
                        from app.sdk.vault.client import VaultClient
                        from app.sdk.vault.folder_spec import BASE_VAULT
                        from app.services.storage import get_provider
                        access_token = get_valid_token_for_user(user_id)
                        if access_token and doc.storage_provider not in ("local", None):
                            storage = get_provider(doc.storage_provider, access_token=access_token)
                            vault_client = VaultClient(
                                provider=storage,
                                access_token=access_token,
                                user_id=user_id,
                                folder_spec=BASE_VAULT,
                            )
                            await ensure_filedored_folders(vault_client)
                    except Exception as _fe2:
                        logger.debug("Filedored folder ensure skipped: %s", _fe2)
                await process_uploaded_document(
                    vault_id=vault_id,
                    user_id=user_id,
                    filename=filename,
                    content=content,
                    sha256_hash=data.get("sha256_hash", ""),
                    enable_ai=False,
                )
                logger.debug("Filedored: sorted %s for user %s", vault_id, user_id[:6])
            except Exception as _fe:
                logger.warning("Filedored post-process failed for %s: %s", vault_id, _fe)

        event_bus.subscribe_async(_ET.DOCUMENT_ADDED, _on_document_added)
        logger.info("📂 Filedored event subscriber wired")
    except ImportError:
        logger.warning("Filedored service not available (optional module)")
    
    # Performance monitoring - re-enabled with memory fixes
    # (removed psutil.net_connections(), shrank deques, 60s sampling)
    if os.getenv("ENABLE_HEAVY_SERVICES", "true").lower() != "false":
        try:
            from app.core.performance_monitor import get_performance_monitor
            performance_monitor = get_performance_monitor()
            performance_monitor.start_monitoring()
            logger.info("Performance monitoring started (slim mode)")
        except Exception as e:
            logger.warning(f"Performance monitoring init failed (non-fatal): {e}")
    else:
        logger.info("Performance monitoring skipped (ENABLE_HEAVY_SERVICES=false)")

    logger.info("Semptify 5.0 FastAPI application created successfully")

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
    # Middleware (order matters - first added = last to run)
    # =========================================================================
    
    is_production = app_settings.security_mode == "enforced"
    
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
    
    # PRODUCTION SECURITY MIDDLEWARE (if enforced mode)
    if is_production:
        try:
            from app.core.logging_middleware import RequestLoggingMiddleware as ProdRequestLogging
            
            # Request logging (security audit trail)
            fastapi_app.add_middleware(ProdRequestLogging)
            logger.info("ðŸš€ Request logging middleware enabled (production mode)")
        except ImportError as e:
            logger.error("âš ï¸  Failed to load request logging middleware: %s", e)
            logger.warning("Request logging not available - continuing without it")
    
    # Smart Gate Checkpoint (enforces welcome page for new users)
    from app.core.checkpoint_middleware import SmartCheckpointMiddleware
    fastapi_app.add_middleware(SmartCheckpointMiddleware)
    logger.info("ðŸšª Smart checkpoint gate enabled (welcome page checkpoint)")
    
    # Storage requirement (CRITICAL: Enforces everyone has storage connected)
    from app.core.storage_middleware import StorageRequirementMiddleware
    fastapi_app.add_middleware(
        StorageRequirementMiddleware,
        enforce=is_production  # Only enforce in production
    )
    logger.info("ðŸ”’ Storage requirement middleware enabled (enforce=%s)", is_production)
    
    # Module Gate Middleware (role + jurisdiction module activation)
    from app.core.module_gate import ModuleGateMiddleware
    fastapi_app.add_middleware(ModuleGateMiddleware)
    logger.info("ðŸšª Module gate middleware enabled (role + jurisdiction activation)")

    # Jurisdiction Engine — auto-detects user state/county from IP (once per session)
    from app.core.jurisdiction_middleware import JurisdictionMiddleware
    fastapi_app.add_middleware(JurisdictionMiddleware)
    logger.info("📍 Jurisdiction middleware enabled (auto-detect state from IP)")

    # Security headers (standard mode, adds headers to all responses)
    from app.core.security_headers import SecurityHeadersMiddleware
    fastapi_app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=is_production,  # HSTS only in production
    )
    
    # Request timeout (prevents hung requests)
    from app.core.timeout import TimeoutMiddleware
    fastapi_app.add_middleware(TimeoutMiddleware)
    
    # Request logging (all modes â€” audit trail is required for evidence integrity)
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
    logger.info("ðŸ”’ CORS middleware configured (production=%s)", is_production)
    
    # Request ID middleware
    @fastapi_app.middleware("http")
    async def add_request_id(request: Request, call_next):
        from app.core.id_gen import make_id
        request_id = request.headers.get("X-Request-Id", make_id("req"))
        if "/admin/api" in request.url.path:
            logger.info(f"=== ADMIN API REQUEST: {request.method} {request.url.path} ===")
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
    
    # =========================================================================
    # Exception Handlers
    # =========================================================================
    # NOTE: Exception handlers are already registered above (lines 1517-1521)
    # from app.core.error_handling import semptify_exception_handler
    # The setup_exception_handlers from app.core.errors is NOT called here
    # because it would overwrite the detailed error handlers.
    
    # =========================================================================
    # Register Routers via Product Manifest
    # =========================================================================

    # ALL TIERS ENABLED - Full live deployment
    # CORE + EXTENDED + ADVOCATE + ADMIN + RESEARCH + DEV
    register_tiers(
        fastapi_app,
        ProductTier.CORE,
        ProductTier.EXTENDED,
        ProductTier.ADVOCATE,
        ProductTier.ADMIN,
        ProductTier.RESEARCH,
        ProductTier.DEV
    )

    # Root route — serve the public guest portal (services catalog + branch routing).
    # The portal is server-rendered via Jinja2 for SEO. The services catalog comes
    # from app.modules.portal.registry (SSOT — additive, not rewrite).
    # User clicks a service CTA → /preamble (routing logic) or a direct branch path.
    @fastapi_app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
    async def root_portal(request: Request):
        """Serve the public guest portal at /. Preamble is the routing decision, not the entry."""
        # HEAD probes from uptime monitors (Render/Cloudflare/UptimeRobot) — return empty 200.
        if request.method == "HEAD":
            return Response(status_code=200)
        # Render the portal via Jinja2 with the services catalog from the registry
        portal_template_path = BASE_PATH / "app" / "templates" / "public" / "portal.html"
        if portal_template_path.exists():
            try:
                from app.modules.portal.service import get_portal_catalog
                from app.modules.portal.pages import portal_pages as _pp
                catalog = get_portal_catalog()
                return templates.TemplateResponse(
                    request,
                    "public/portal.html",
                    {
                        "services": catalog["services"],
                        "categories": catalog["categories"],
                        "total_services": catalog["total_services"],
                        "footer_pages": _pp.get_footer_pages(),
                    },
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Portal template error, falling back to static welcome: %s", e)
        # Fallback: serve the static welcome page if the portal template is missing
        welcome_path = BASE_PATH / "static" / "public" / "welcome.html"
        if welcome_path.exists():
            return FileResponse(str(welcome_path))
        # Final fallback: redirect to preamble
        preamble_stage = navigation.get_stage("preamble")
        preamble_path = preamble_stage.path if preamble_stage else "/preamble"
        return ssot_redirect(preamble_path, context="root_portal fallback")

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

    # ------------------------------------------------------------------
    # Public Website Sub-Pages (semptify.org)
    #
    # Routes are generated from the PortalPageRegistry (SSOT).
    # To add a new public page: register it in app.modules.portal.pages
    # and create its template in app/templates/public/. No other changes needed.
    #
    # NOTE: Paths already registered elsewhere in the app (e.g. /help, /tools)
    # are skipped here — they stay in the registry for footer/sitemap, but
    # the existing app routes handle serving. FastAPI uses first-registered
    # route wins, so we skip to avoid silent overrides.
    # ------------------------------------------------------------------
    from app.modules.portal.pages import portal_pages as _portal_pages
    from app.modules.portal.service import get_portal_catalog as _get_catalog

    # Paths that already have routes registered elsewhere in the app
    _existing_public_paths = {"/help", "/tools", "/library"}

    for _page in _portal_pages.PAGES:
        # Capture loop variables correctly for closure
        _pg = _page

        # Skip paths that already have routes — they stay in registry for footer/sitemap
        if _pg.path in _existing_public_paths:
            continue

        @fastapi_app.get(_pg.path, response_class=HTMLResponse)
        async def _serve_public_page(request: Request, _p=_pg):
            """Serve a public website page from the portal pages registry."""
            # HEAD probes from uptime monitors — return empty 200.
            if request.method == "HEAD":
                return Response(status_code=200)
            template_path = BASE_PATH / "app" / "templates" / _p.template
            if not template_path.exists():
                # Template missing — fall back to portal root
                logger.warning("Public page template missing: %s", _p.template)
                root_stage = navigation.get_stage("root")
                root_path = root_stage.path if root_stage else "/"
                return ssot_redirect(root_path, context=f"missing template {_p.template}")
            try:
                # Services page needs the catalog; other pages just need page meta
                context = {
                    "page": _p,
                    "footer_pages": _portal_pages.get_footer_pages(),
                }
                if _p.id == "services":
                    catalog = _get_catalog()
                    context["services"] = catalog["services"]
                    context["categories"] = catalog["categories"]
                    context["total_services"] = catalog["total_services"]
                return templates.TemplateResponse(request, _p.template, context)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Public page template error (%s): %s", _p.template, e)
                root_stage = navigation.get_stage("root")
                root_path = root_stage.path if root_stage else "/"
                return ssot_redirect(root_path, context=f"template error {_p.template}")

    DAKOTA_AVAILABLE = False
    if DAKOTA_AVAILABLE:
        from app.routers.eviction import (
            flows_router as dakota_flows,
            forms_router as dakota_forms,
            case_router as dakota_case,
            learning_router as dakota_learning,
            procedures_router as dakota_procedures,
        )
        fastapi_app.include_router(dakota_case, prefix="/eviction", tags=["Eviction Case"])
        fastapi_app.include_router(dakota_learning, prefix="/eviction/learn", tags=["Court Learning"])
        fastapi_app.include_router(dakota_procedures, tags=["Dakota Procedures"])
        fastapi_app.include_router(dakota_flows, prefix="/eviction", tags=["Eviction Defense"])
        fastapi_app.include_router(dakota_forms, prefix="/eviction/forms", tags=["Court Forms"])
        logging.getLogger(__name__).info("âœ… Dakota County Eviction Defense module loaded")
    else:
        logging.getLogger(__name__).info("â„¹ï¸  Dakota County module not available (optional)")

    logging.getLogger(__name__).info("ðŸš€ Product Manifest router registration complete")
    
    # =========================================================================
    # Static Files (for any frontend assets)
    # =========================================================================

    # Block direct HTML access from /static/ (except /static/public/ and /static/components/)
    # All authenticated pages must use rendered routes, not raw static HTML.
    @fastapi_app.middleware("http")
    async def block_static_html(request: Request, call_next):
        path = request.url.path
        if (
            path.startswith("/static/")
            and path.endswith(".html")
            and not path.startswith("/static/public/")
            and not path.startswith("/static/components/")
        ):
            return JSONResponse(
                content={"error": "forbidden", "message": "Static HTML pages are not served directly. Use the rendered route."},
                status_code=403,
            )
        return await call_next(request)

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

    # Shortcut mounts so pages can use /js/... and /css/... without /static prefix
    js_path = BASE_PATH / "static" / "js"
    if js_path.exists():
        fastapi_app.mount("/js", StaticFiles(directory=str(js_path)), name="js_static")

    css_path = BASE_PATH / "static" / "css"
    if css_path.exists():
        fastapi_app.mount("/css", StaticFiles(directory=str(css_path)), name="css_static")

    # =========================================================================
    # Onboarding Redirect (before catch-all)
    # =========================================================================

        @fastapi_app.get("/onboarding", response_class=HTMLResponse)
        async def onboarding_redirect():
            """Redirect /onboarding to /onboarding/ for the router."""
            onboarding_stage = navigation.get_stage("onboarding_start")
            onboarding_path = (onboarding_stage.path if onboarding_stage else "/onboarding")
            if not onboarding_path.endswith("/"):
                onboarding_path += "/"
            return ssot_redirect(onboarding_path, context="onboarding_redirect trailing slash")

        @fastapi_app.get("/welcome.html", response_class=HTMLResponse)
        async def welcome_html():
            """Serve welcome page â€” canonical entry point for new users."""
            welcome_path = BASE_PATH / "static" / "public" / "welcome.html"
            if welcome_path.exists():
                return FileResponse(welcome_path)
            root_stage = navigation.get_stage("root")
            root_path = root_stage.path if root_stage else "/"
            return ssot_redirect(root_path, context="welcome_html fallback")

        # Onboarding pages - bypass static HTML block middleware
        @fastapi_app.get("/onboarding/select-role", response_class=HTMLResponse)
        @fastapi_app.get("/onboarding/select-role.html", response_class=HTMLResponse)
        async def role_select_page():
            """Serve role selection page with no-cache headers."""
            # Try new file first (bypasses any caching issues)
            pick_role_path = BASE_PATH / "static" / "onboarding" / "pick-role.html"
            if pick_role_path.exists():
                return FileResponse(
                    pick_role_path,
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
            # Fallback to old file
            page_path = BASE_PATH / "static" / "onboarding" / "role-select.html"
            if page_path.exists():
                return FileResponse(
                    page_path,
                    headers={
                        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "Cloudflare-CDN-Cache-Control": "no-cache"
                    }
                )
            # Fallback to providers if role-select doesn't exist
            providers_stage = navigation.get_stage("providers")
            providers_path = providers_stage.path if providers_stage else "/storage/providers"
            return ssot_redirect(providers_path, context="role_select fallback")

        @fastapi_app.get("/storage/providers", response_class=HTMLResponse)
        @fastapi_app.get("/storage/providers.html", response_class=HTMLResponse)
        async def storage_providers_page():
            """Serve storage providers selection page."""
            page_path = BASE_PATH / "static" / "onboarding" / "providers.html"
            if page_path.exists():
                return FileResponse(page_path)
            # Fallback to OAuth if providers page doesn't exist
            return ssot_redirect("/onboarding/auth/google_drive?force_fresh=true", context="providers fallback")

        # Register page redirect - Semptify uses OAuth-based auth, no username/password registration
        @fastapi_app.get("/register", response_class=HTMLResponse)
        async def register_redirect(request: Request):
            """Redirect to OAuth-based onboarding. Semptify has no username/password registration."""
            from app.core.navigation import navigation
            providers_stage = navigation.get_stage("providers")
            providers_path = providers_stage.path if providers_stage else "/storage/providers"
            return ssot_redirect(providers_path, context="register redirect to OAuth onboarding")

    # =========================================================================
    # Root endpoint - Serve SPA
    # =========================================================================

    # Role-Specific Dashboard Pages
    @fastapi_app.get("/tenant/dashboard", response_class=HTMLResponse)
    async def tenant_dashboard_page(request: Request):
        """Serve the tenant dashboard with modular components."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
        if not is_valid_storage_user(user_id):
            providers_stage = navigation.get_stage("providers")
            providers_path = providers_stage.path if providers_stage else "/storage/providers"
            return ssot_redirect(providers_path, context="role dashboard unauthenticated")

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

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
        if not is_valid_storage_user(user_id):
            providers_stage = navigation.get_stage("providers")
            providers_path = providers_stage.path if providers_stage else "/storage/providers"
            return ssot_redirect(providers_path, context="role dashboard unauthenticated")

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

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
        if not is_valid_storage_user(user_id):
            providers_stage = navigation.get_stage("providers")
            providers_path = providers_stage.path if providers_stage else "/storage/providers"
            return ssot_redirect(providers_path, context="role dashboard unauthenticated")

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

    # =========================================================================
    # Admin Routes (Protected - ADMIN role required)
    # =========================================================================

    from app.core.security import require_role, get_current_user
    from app.core.user_context import UserRole, UserContext

    # Admin credentials from environment (set in Render dashboard)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")  # Must be set in production
    ADMIN_TOTP_SECRET = os.getenv("ADMIN_TOTP_SECRET")  # Base32 secret for 2FA
    
    @fastapi_app.get("/admin/login", response_class=HTMLResponse)
    async def admin_login_page(request: Request):
        """Admin elevation prompt — requires existing OAuth session."""
        from app.core.admin_elevation import ELEVATION_COOKIE_NAME, verify_elevation_cookie
        from app.core.cookie_auth import extract_user_id
        logger.info("=== ADMIN ELEVATION PAGE REQUESTED ===")
        # If already elevated, go straight to dashboard
        elev_cookie = request.cookies.get(ELEVATION_COOKIE_NAME)
        if verify_elevation_cookie(str(elev_cookie) if elev_cookie else None):
            return RedirectResponse(url="/admin/dashboard")
        # Check if user has an OAuth session
        oauth_uid = extract_user_id(request)
        has_session = oauth_uid is not None
        has_session_js = 'true' if has_session else 'false'
        # Build page — simplified prompt if OAuth session exists, full login if not
        session_hint = f'<p class="session-badge">&#x2713; Connected as {oauth_uid[:6]}...</p>' if has_session else ''
        username_field = '' if has_session else '''
            <div class="input-group">
                <label>Username</label>
                <input type="text" id="username" placeholder="admin" autocomplete="username">
            </div>'''
        return HTMLResponse(content=f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Access</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
        .box {{ background: #1e293b; padding: 2rem; border-radius: 12px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); width: 100%; max-width: 360px; }}
        .lock {{ text-align: center; font-size: 2rem; margin-bottom: 0.5rem; }}
        h1 {{ text-align: center; margin-bottom: 1.5rem; color: #94a3b8; font-size: 1rem; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase; }}
        .session-badge {{ text-align: center; color: #34d399; font-size: 0.8rem; margin-bottom: 1.25rem; }}
        .input-group {{ margin-bottom: 1rem; }}
        label {{ display: block; margin-bottom: 0.4rem; font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }}
        input {{ width: 100%; padding: 0.75rem; border: 1px solid #334155; border-radius: 8px; background: #0f172a; color: #e2e8f0; font-size: 1rem; }}
        input:focus {{ outline: none; border-color: #475569; }}
        input[type=text] {{ letter-spacing: 0.25em; font-size: 1.25rem; text-align: center; }}
        button {{ width: 100%; padding: 0.75rem; background: #1e40af; color: #bfdbfe; border: none; border-radius: 8px; font-size: 0.9rem; cursor: pointer; margin-top: 0.5rem; letter-spacing: 0.05em; }}
        button:hover {{ background: #1d4ed8; }}
        button:disabled {{ background: #1e293b; color: #475569; cursor: not-allowed; border: 1px solid #334155; }}
        .error {{ color: #f87171; text-align: center; margin-top: 1rem; font-size: 0.85rem; min-height: 1.2rem; }}
        .step2 {{ display: none; }}
    </style>
</head>
<body>
    <div class="box">
        <div class="lock">&#x1F512;</div>
        <h1>Secure Access</h1>
        {session_hint}
        <form id="step1" onsubmit="loginStep1(); return false;">
            {username_field}
            <div class="input-group">
                <label>Password</label>
                <input type="password" id="password" placeholder="&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;&#x2022;" autocomplete="current-password">
            </div>
            <button type="submit" id="btn1">Continue &rarr;</button>
        </form>
        <form id="step2" class="step2" onsubmit="loginStep2(); return false;">
            <div class="input-group">
                <label>6-Digit Code</label>
                <input type="text" id="totp" placeholder="000000" maxlength="6" pattern="[0-9]*" inputmode="numeric" autocomplete="one-time-code">
            </div>
            <button type="submit" id="btn2">Verify &rarr;</button>
        </form>
        <div id="error" class="error"></div>
    </div>
    <script>
        var HAS_SESSION = {has_session_js};
        var SESSION_USERNAME = "{ADMIN_USERNAME}";
        document.addEventListener("keydown", function(e) {{
            if (e.key === "Enter") {{
                var s2 = document.getElementById("step2");
                if (s2.style.display === "block") loginStep2();
                else loginStep1();
            }}
        }});
        function getUsername() {{
            if (HAS_SESSION) return SESSION_USERNAME;
            var el = document.getElementById("username");
            return el ? el.value : "";
        }}
        async function loginStep1() {{
            document.getElementById("error").textContent = "";
            document.getElementById("btn1").disabled = true;
            var username = getUsername();
            var res = await fetch("/admin/api/login-step1", {{
                method: "POST",
                headers: {{"Content-Type": "application/json"}},
                body: JSON.stringify({{ username: username, password: document.getElementById("password").value }})
            }});
            var data = await res.json();
            if (data.success) {{
                document.getElementById("step1").style.display = "none";
                document.getElementById("step2").style.display = "block";
                document.getElementById("totp").focus();
            }} else {{
                document.getElementById("error").textContent = data.detail || data.error || "Access denied";
                document.getElementById("btn1").disabled = false;
            }}
        }}
        async function loginStep2() {{
            document.getElementById("error").textContent = "";
            document.getElementById("btn2").disabled = true;
            var username = getUsername();
            var res = await fetch("/admin/api/login-step2", {{
                method: "POST",
                headers: {{"Content-Type": "application/json"}},
                body: JSON.stringify({{ username: username, password: document.getElementById("password").value, totp_code: document.getElementById("totp").value }})
            }});
            var data = await res.json();
            if (data.success) {{
                window.location.href = data.redirect || "/admin/dashboard";
            }} else {{
                document.getElementById("error").textContent = data.detail || data.error || "Invalid code";
                document.getElementById("btn2").disabled = false;
                document.getElementById("totp").value = "";
                document.getElementById("totp").focus();
            }}
        }}
    </script>
</body>
</html>''')
    
    @fastapi_app.post("/admin/api/login-step1")
    async def admin_login_step1(request: Request):
        """
        Step 1: Validate username/password.
        Returns step2_required=true if 2FA is enabled.
        """
        logger.info("=== ADMIN LOGIN STEP 1 CALLED ===")
        try:
            data = await request.json()
            username = data.get("username", "").strip()
            password = data.get("password", "")
        except Exception as e:
            logger.error(f"JSON parse error: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Debug: Log credential status (without logging actual passwords)
        logger.info(f"Admin login attempt - Username: {username}, ADMIN_USERNAME set: {bool(ADMIN_USERNAME)}, ADMIN_PASSWORD set: {bool(ADMIN_PASSWORD)}, ADMIN_TOTP_SECRET set: {bool(ADMIN_TOTP_SECRET)}")
        
        # Validate credentials
        if not ADMIN_PASSWORD:
            logger.error("ADMIN_PASSWORD not set - admin login disabled")
            raise HTTPException(status_code=503, detail="Admin login not configured")
        
        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            logger.warning(f"Failed admin login step 1: {username} (expected: {ADMIN_USERNAME})")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if 2FA is enabled
        if ADMIN_TOTP_SECRET:
            return {
                "success": True,
                "step2_required": True,
                "message": "Two-step verification required"
            }
        else:
            # No 2FA configured - skip to step 2 directly
            return {
                "success": True,
                "step2_required": True,
                "message": "Two-step verification required"
            }
    
    @fastapi_app.post("/admin/api/login-step2")
    async def admin_login_step2(request: Request, response: Response):
        """
        Step 2: Validate 2FA code and issue elevation cookie.
        Requires existing OAuth session. Issues a 4-hour elevation cookie.
        """
        import pyotp
        from app.core.admin_elevation import set_elevation_cookie
        from app.core.cookie_auth import extract_user_id
        
        try:
            data = await request.json()
            username = data.get("username", "").strip()
            password = data.get("password", "")
            totp_code = data.get("totp_code", "").strip()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Re-validate credentials
        if not ADMIN_PASSWORD or username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Validate TOTP code if 2FA is configured
        if ADMIN_TOTP_SECRET:
            totp = pyotp.TOTP(ADMIN_TOTP_SECRET)
            if not totp.verify(totp_code, valid_window=2):  # Allow 60sec drift
                logger.warning(f"Failed 2FA attempt for admin: {username}")
                raise HTTPException(status_code=401, detail="Invalid two-step code")
        elif totp_code != "000000":
            pass
        
        # Get OAuth user_id for the elevation token (may be None if no OAuth session yet)
        oauth_uid = extract_user_id(request) or f"admin_{username}"
        
        # Issue 4-hour elevation cookie
        set_elevation_cookie(response, oauth_uid)
        logger.info(f"Admin elevation granted for {oauth_uid[:6]}...")
        
        # If no OAuth session yet, redirect to onboarding to connect storage
        has_oauth = extract_user_id(request) is not None
        if not has_oauth:
            return {
                "success": True,
                "redirect": "/onboarding/providers?role=admin",
                "message": "Please connect your storage to continue"
            }
        
        return {
            "success": True,
            "redirect": "/admin/dashboard"
        }
    
    @fastapi_app.get("/admin/logout")
    async def admin_logout(response: Response):
        """Clear admin elevation (not the OAuth session)."""
        from app.core.admin_elevation import clear_elevation_cookie
        clear_elevation_cookie(response)
        return RedirectResponse(url="/admin/login")

    @fastapi_app.get("/admin/home", response_class=HTMLResponse)
    @fastapi_app.get("/admin/home.html", response_class=HTMLResponse)
    async def admin_home_page():
        """Admin home page - shown after onboarding, leads to admin sign in."""
        home_path = BASE_PATH / "static" / "admin" / "home.html"
        if home_path.exists():
            return FileResponse(str(home_path))
        # Fallback to login if home.html missing
        return RedirectResponse(url="/admin/login")

    # Admin guard - checks elevation cookie (time-limited TOTP-verified elevation)
    # Does NOT check OAuth role — elevation is separate from storage identity
    async def _require_elevation(request: Request) -> str:
        """
        Stealth admin guard — redirects to /admin/login on missing/expired elevation.
        Requires a valid admin elevation cookie issued by /admin/api/login-step2.
        Elevation is valid for 2 hours and requires TOTP re-verification.
        """
        from app.core.admin_elevation import ELEVATION_COOKIE_NAME, verify_elevation_cookie
        elev_cookie = request.cookies.get(ELEVATION_COOKIE_NAME)
        payload = verify_elevation_cookie(str(elev_cookie) if elev_cookie else None)
        if not payload:
            # Redirect to elevation prompt — stealth: looks like a normal login page
            return RedirectResponse(url="/admin/login", status_code=302)
        return payload["uid"]

    require_admin = _require_elevation

    @fastapi_app.get("/admin/dashboard", response_class=HTMLResponse)
    async def admin_dashboard_page(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve the admin dashboard - elevation required."""
        logger.info(f"Admin elevation active for {admin_uid[:6]}... accessing dashboard")

        # Serve static dashboard
        static_fallback = BASE_PATH / "static" / "admin" / "dashboard.html"
        if static_fallback.exists():
            return FileResponse(str(static_fallback))

        return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)

    # Secret admin entry - obfuscated URL, not linked anywhere public
    @fastapi_app.get("/sys/portal", response_class=HTMLResponse)
    async def secret_admin_entry(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Secret admin portal - not discoverable via public URLs."""
        admin_dashboard_path = BASE_PATH / "static" / "admin" / "dashboard.html"
        if admin_dashboard_path.exists():
            content = admin_dashboard_path.read_text(encoding="utf-8")
            return HTMLResponse(content=content)
        return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)

    # Legacy /admin/dashboard.html - 404 for non-admins (stealth mode)
    @fastapi_app.get("/admin/dashboard.html", response_class=HTMLResponse)
    async def admin_dashboard_html(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve admin dashboard HTML - ADMIN role required."""
        dashboard_path = BASE_PATH / "static" / "admin" / "dashboard.html"
        if dashboard_path.exists():
            return FileResponse(str(dashboard_path))
        return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)

    @fastapi_app.get("/admin/contract-browser.html", response_class=HTMLResponse)
    async def admin_contract_browser(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve contract browser - ADMIN role required."""
        page_path = BASE_PATH / "static" / "admin" / "contract-browser.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Contract Browser not found</h1>", status_code=404)

    @fastapi_app.get("/admin/function-browser.html", response_class=HTMLResponse)
    async def admin_function_browser(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve function browser - ADMIN role required."""
        page_path = BASE_PATH / "static" / "admin" / "function-browser.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Function Browser not found</h1>", status_code=404)

    @fastapi_app.get("/admin/page-editor.html", response_class=HTMLResponse)
    async def admin_page_editor(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve page editor - ADMIN role required."""
        page_path = BASE_PATH / "static" / "admin" / "page-editor.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Page Editor not found</h1>", status_code=404)

    @fastapi_app.get("/admin/review-checklist.html", response_class=HTMLResponse)
    async def admin_review_checklist(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve review checklist - ADMIN role required."""
        page_path = BASE_PATH / "static" / "admin" / "review-checklist.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Review Checklist not found</h1>", status_code=404)

    @fastapi_app.get("/admin/manual.html", response_class=HTMLResponse)
    async def admin_manual(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve admin manual - ADMIN role required."""
        page_path = BASE_PATH / "static" / "admin" / "manual.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Admin Manual not found</h1>", status_code=404)

    @fastapi_app.get("/admin/api-workbook.html", response_class=HTMLResponse)
    async def admin_api_workbook(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve API workbook - ADMIN role required."""
        page_path = BASE_PATH / "static" / "admin" / "api_workbook.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>API Workbook not found</h1>", status_code=404)

    @fastapi_app.get("/admin/module-flags.html", response_class=HTMLResponse)
    async def admin_module_flags_page(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve Module Flag Overlay admin page - ADMIN role required."""
        page_path = BASE_PATH / "static" / "admin" / "module_flags.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Module Flags not found</h1>", status_code=404)

    @fastapi_app.get("/admin/forge.html", response_class=HTMLResponse)
    async def admin_forge_page(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve Semptify Forge admin page - ADMIN role required.

        The Forge is the canonical module development system. Alias /admin/dev-lab.html
        kept for backward compatibility.
        """
        page_path = BASE_PATH / "static" / "admin" / "dev_lab.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Semptify Forge not found</h1>", status_code=404)

    @fastapi_app.get("/admin/dev-lab.html", response_class=HTMLResponse)
    async def admin_dev_lab_page(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve Dev Lab admin page (alias for /admin/forge.html)."""
        return await admin_forge_page(request, admin_uid)

    @fastapi_app.get("/docs/component-inventory.html", response_class=HTMLResponse)
    async def docs_component_inventory(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve component inventory docs - ADMIN role required."""
        page_path = BASE_PATH / "static" / "docs" / "component-inventory.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Component Inventory not found</h1>", status_code=404)

    @fastapi_app.get("/docs/navigation-structure.html", response_class=HTMLResponse)
    async def docs_navigation_structure(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Serve navigation structure docs - ADMIN role required."""
        page_path = BASE_PATH / "static" / "docs" / "navigation-structure.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Navigation Structure not found</h1>", status_code=404)

    @fastapi_app.get("/overlays/viewer", response_class=HTMLResponse)
    async def overlay_viewer_page(request: Request):
        """Serve the overlay viewer page — storage-user auth required."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
        if not is_valid_storage_user(user_id):
            providers_stage = navigation.get_stage("providers")
            providers_path = providers_stage.path if providers_stage else "/storage/providers"
            return ssot_redirect(providers_path, context="overlay_viewer unauthenticated")

        page_path = BASE_PATH / "static" / "overlays" / "viewer.html"
        if page_path.exists():
            return FileResponse(str(page_path))
        return HTMLResponse(content="<h1>Overlay Viewer not found</h1>", status_code=404)

    @fastapi_app.get("/admin", response_class=HTMLResponse)
    async def admin_root_redirect(
        request: Request,
        admin_uid: str = Depends(require_admin),
    ):
        """Redirect /admin to dashboard - ADMIN role required."""
        return RedirectResponse(url="/admin/dashboard.html")

    @fastapi_app.get("/manager", response_class=HTMLResponse)
    async def manager_portal_page(request: Request):
        """Serve the manager portal for case workers and counselors."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID
        from app.core.user_context import get_role_from_user_id, UserRole

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
        if not is_valid_storage_user(user_id):
            providers_stage = navigation.get_stage("providers")
            providers_path = providers_stage.path if providers_stage else "/storage/providers"
            return ssot_redirect(providers_path, context="role dashboard unauthenticated")

        # Verify MANAGER role
        role = get_role_from_user_id(user_id)
        if role != UserRole.MANAGER:
            root_stage = navigation.get_stage("root")
            root_path = root_stage.path if root_stage else "/"
            return ssot_redirect(root_path, context="manager_portal role mismatch")

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
        manager_stage = navigation.get_stage("manager_portal")
        manager_path = manager_stage.path if manager_stage else "/manager"
        return ssot_redirect(manager_path, context="manager_dashboard redirect to portal")

    @fastapi_app.get("/api/manager/dashboard-stats")
    async def manager_dashboard_stats(request: Request):
        """API endpoint for manager dashboard statistics (auto-refresh)."""
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import COOKIE_USER_ID
        from app.core.user_context import get_role_from_user_id, UserRole
        from app.core.database import get_db_session
        from app.core.manager_dashboard import get_dashboard_stats

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
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

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
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

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
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

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
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

    @fastapi_app.get("/dashboard")
    async def dashboard_page(request: Request):
        """Redirect /dashboard to role-specific dashboard."""
        return RedirectResponse(url="/tenant/dashboard", status_code=302)

    @fastapi_app.get("/home", response_class=HTMLResponse)
    async def semptify_home(request: Request):
        """Serve the Semptify Home â€” tenant front door."""
        user_id = extract_user_id(request) or ""
        user_name = None
        briefcase = None
        if user_id:
            try:
                briefcase = await _get_tenant_briefcase(user_id)
                user_name = briefcase.user_name
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        ctx = {
            "user_name": user_name,
            "next_deadline": None,
            "document_count": 0,
            "last_document_date": None,
            "journal_count": 0,
            "last_journal_date": None,
            "recent_activity": [],
        }
        if briefcase:
            ctx["user_name"] = briefcase.user_name
            ctx["document_count"] = briefcase.vault.total_documents if briefcase.vault else 0
            ctx["journal_count"] = briefcase.journal.total_entries if briefcase.journal else 0
            if briefcase.timeline and briefcase.timeline.next_deadline:
                ctx["next_deadline"] = {
                    "title": briefcase.timeline.next_deadline.title,
                    "date": briefcase.timeline.next_deadline.date,
                    "days_remaining": briefcase.timeline.next_deadline.days_until,
                }
            activity = []
            if briefcase.vault and briefcase.vault.documents:
                for doc in briefcase.vault.documents[:3]:
                    activity.append({
                        "icon": "ðŸ“„",
                        "description": f"Document: {doc.get('title', 'Uploaded')}",
                        "time_ago": doc.get("uploaded_at", "Recently"),
                    })
            if briefcase.journal and briefcase.journal.recent_entries:
                for entry in briefcase.journal.recent_entries[:3]:
                    activity.append({
                        "icon": entry.icon or "ðŸ“",
                        "description": entry.description,
                        "time_ago": entry.created_at,
                    })
            if briefcase.timeline and briefcase.timeline.recent_events:
                for event in briefcase.timeline.recent_events[:3]:
                    activity.append({
                        "icon": event.icon or "ðŸ“…",
                        "description": event.title,
                        "time_ago": event.date or "Recently",
                    })
            ctx["recent_activity"] = activity[:5]

        return templates.TemplateResponse(request, "pages/tenant_home.html", ctx)

    # ------------------------------------------------------------------
    # Main Navigation Routes (SSOT) â€” /office, /library, /tools, /help
    # These are the 5 core nav links (Home is above). All rendered.
    # ------------------------------------------------------------------

    @fastapi_app.get("/office", response_class=HTMLResponse)
    async def office_page(request: Request):
        """Serve the Office â€” case management center."""
        return templates.TemplateResponse(request, "pages/office.html")

    @fastapi_app.get("/library", response_class=HTMLResponse)
    async def library_page(request: Request):
        """Serve the Library â€” legal resources and guides."""
        return templates.TemplateResponse(request, "pages/library.html")

    @fastapi_app.get("/tools", response_class=HTMLResponse)
    async def tools_page(request: Request):
        """Serve Tools â€” document generators and case utilities."""
        return templates.TemplateResponse(request, "pages/tools.html")

    @fastapi_app.get("/help", response_class=HTMLResponse)
    async def help_page(request: Request):
        """Serve Help â€” support, resources, and emergency contacts."""
        return templates.TemplateResponse(request, "pages/help.html")

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
            _rc = request.cookies.get(COOKIE_USER_ID, "anon")
            EMITTER.emit("vault_load", "vault", str(_rc) if _rc is not None else "anon")
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
        <h1>ðŸ“ Document Vault</h1>
        <div class="status">
            âœ… Storage Connected - Your documents are secure in your cloud storage
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
    # Temporary Debug Endpoint â€” remove after vault issue is resolved
    # =========================================================================

    @fastapi_app.get("/debug/status")
    async def debug_status(request: Request):
        """Temporary: show user/gate/middleware state for debugging."""
        import traceback as _tb
        info = {"step": "init"}
        try:
            from app.core.user_id import COOKIE_USER_ID
            _rc = request.cookies.get(COOKIE_USER_ID, "")
            raw_cookie = str(_rc) if _rc is not None else ""
            info["cookie_present"] = bool(raw_cookie)
            info["cookie_prefix"] = raw_cookie[:12] + "..." if raw_cookie else "NONE"

            from app.core.cookie_auth import verify_user_id
            raw_uid = verify_user_id(raw_cookie)
            info["hmac_valid"] = raw_uid is not None
            info["raw_user_id"] = raw_uid[:6] + "***" if raw_uid else "NONE"

            from app.core.storage_middleware import is_valid_storage_user
            info["is_valid_storage_user"] = is_valid_storage_user(raw_cookie)

            if raw_uid:
                from app.core.database import get_session_factory
                from app.core.onboarding_state import get_onboarding_state
                factory = get_session_factory()
                async with factory() as db:
                    ob = await get_onboarding_state(raw_uid, db)
                    info["storage_connected"] = ob.storage_connected
                    info["vault_initialized"] = ob.vault_initialized
                    info["is_fully_onboarded"] = ob.is_fully_onboarded
                    info["next_gate"] = ob.next_required_gate
                    info["next_path"] = ob.next_required_path

                    from app.models.models import User
                    from sqlalchemy import select
                    result = await db.execute(select(User).where(User.id == raw_uid))
                    user = result.scalar_one_or_none()
                    if user:
                        info["user_found"] = True
                        info["completed_groups"] = user.completed_groups
                        info["primary_provider"] = user.primary_provider
                    else:
                        info["user_found"] = False

            info["step"] = "done"
        except Exception as exc:
            info["error"] = str(exc)
            info["traceback"] = _tb.format_exc()
        return JSONResponse(content=info)

    @fastapi_app.get("/debug/create-vault")
    async def debug_create_vault(request: Request):
        """Temporary: force vault folder creation for debugging."""
        import traceback as _tb
        info = {"step": "init"}
        try:
            from app.core.user_id import COOKIE_USER_ID
            from app.core.cookie_auth import verify_user_id
            raw_cookie = request.cookies.get(COOKIE_USER_ID, "")
            raw_uid = verify_user_id(raw_cookie)
            if not raw_uid:
                return JSONResponse(content={"error": "no valid cookie"})

            info["user_id"] = raw_uid[:6] + "***"

            # Get token from token_manager
            from app.core.oauth_token_manager import token_manager
            cached = token_manager.get_token(raw_uid)
            if cached:
                access_token = cached.access_token
                provider = cached.provider
                info["token_source"] = "cache"
                info["token_len"] = len(access_token)
            else:
                # Try DB
                from app.core.database import get_session_factory
                factory = get_session_factory()
                async with factory() as db:
                    from app.models.models import User
                    from sqlalchemy import select
                    result = await db.execute(select(User).where(User.id == raw_uid))
                    user = result.scalar_one_or_none()
                    provider = user.primary_provider if user else None
                info["token_source"] = "none"
                info["provider"] = provider
                return JSONResponse(content={**info, "error": "no cached token â€” need fresh OAuth sign-in"})

            info["provider"] = provider

            # Use Vault SDK â€” isolated, no gate/DB dependencies
            from app.sdk.vault import VaultClient, TENANT_VAULT
            vault = VaultClient(
                provider=provider,
                access_token=access_token,
                user_id=raw_uid,
                folder_spec=TENANT_VAULT,
            )
            info["sdk_version"] = VaultClient.__version__
            info["vault_folders"] = vault.list_expected_folders()

            vault_result = await vault.create_folders()
            info["folder_results"] = vault_result.to_dict()

            # Only mark gate if ALL folders were created
            if vault_result.all_ok:
                from app.core.database import get_session_factory
                from app.modules.onboarding.gates import mark_gate
                factory2 = get_session_factory()
                async with factory2() as db2:
                    await mark_gate(db2, raw_uid, "vault_initialized")
                info["gate_marked"] = True
            else:
                info["gate_marked"] = False
                info["gate_reason"] = "folders failed â€” gate not marked"

            info["step"] = "done"
        except Exception as exc:
            info["error"] = str(exc)
            info["traceback"] = _tb.format_exc()
        return JSONResponse(content=info)

    # =========================================================================
    # Documents Page
    # =========================================================================

    @fastapi_app.get("/documents", response_class=HTMLResponse)
    async def documents_page(request: Request):
        """Serve the document intake page."""
        import traceback as _tb
        try:
            # Apply PageContract guard
            guard_redirect = _guard_by_contract("documents", request)
            if guard_redirect:
                return guard_redirect

            # Telemetry
            try:
                from app.core.telemetry_hooks import EMITTER
                from app.core.user_id import COOKIE_USER_ID
                _rc = request.cookies.get(COOKIE_USER_ID, "anon")
                EMITTER.emit("documents_page_load", "documents", str(_rc) if _rc is not None else "anon")
            except Exception:  # pylint: disable=broad-exception-caught
                pass

            # Try template first
            documents_template_path = BASE_PATH / "app" / "templates" / "pages" / "documents.html"
            if documents_template_path.exists():
                try:
                    # Fetch documents from vault for the authenticated user
                    documents_data = []
                    try:
                        from app.services.vault_upload_service import get_vault_service
                        from app.core.cookie_auth import verify_user_id
                        from app.core.user_id import COOKIE_USER_ID

                        cookie_value = request.cookies.get(COOKIE_USER_ID)
                        if cookie_value:
                            raw_uid = verify_user_id(cookie_value)
                            if raw_uid:
                                vault_service = get_vault_service()
                                vault_docs = await vault_service.get_user_documents(raw_uid)
                                documents_data = [
                                    {
                                        "id": doc.vault_id,
                                        "filename": doc.filename,
                                        "uploaded_at": doc.uploaded_at if isinstance(doc.uploaded_at, str) else doc.uploaded_at.isoformat() if hasattr(doc.uploaded_at, 'isoformat') else str(doc.uploaded_at),
                                        "document_type": doc.document_type or "document",
                                    }
                                    for doc in vault_docs
                                ]
                    except Exception as doc_err:
                        logger.warning("Failed to fetch documents for page: %s", doc_err)
                    
                    return templates.TemplateResponse(request, "pages/documents.html", {"documents": documents_data})
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
        except Exception as exc:
            logger.error("DOCUMENTS_DEBUG: %s\n%s", exc, _tb.format_exc())
            return JSONResponse(
                status_code=500,
                content={"error": "documents_crash", "detail": str(exc), "traceback": _tb.format_exc()},
            )


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

        _raw = request.cookies.get(COOKIE_USER_ID)
        user_id = str(_raw) if _raw is not None else None
        if not is_valid_storage_user(user_id):
            providers_stage = navigation.get_stage("providers")
            providers_path = providers_stage.path if providers_stage else "/storage/providers"
            return ssot_redirect(providers_path, context="role dashboard unauthenticated")

        # Verify professional role
        role = get_role_from_user_id(user_id)
        if role not in PROFESSIONAL_ROLES:
            root_stage = navigation.get_stage("root")
            root_path = root_stage.path if root_stage else "/"
            return ssot_redirect(root_path, context="delivery_send role mismatch")

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

    async def _guard_role_page(request: Request, allowed_roles: set[str]) -> Optional[RedirectResponse]:
        """Lightweight guard: storage connected + expected role for portal page."""
        from app.core.cookie_auth import extract_user_id
        from app.core.storage_middleware import is_valid_storage_user
        from app.core.user_id import get_role_from_user_id
        from app.core.workflow_engine import route_user as _route_user

        signed_cookie = request.cookies.get("semptify_uid", "")
        user_id = extract_user_id(request)
        if not user_id:
            # No cookie at all - new user to welcome page
            root_stage = navigation.get_stage("root")
            root_path = root_stage.path if root_stage else "/"
            return ssot_redirect(root_path, context="document_delivery no user cookie")
        if not is_valid_storage_user(signed_cookie):
            # Has cookie but invalid - returning user needs reconnect
            reconnect_stage = navigation.get_stage("storage_reconnect")
            reconnect_path = reconnect_stage.path if reconnect_stage else "/storage/reconnect"
            return ssot_redirect(reconnect_path, context="document_delivery reconnect required")

        current_role = get_role_from_user_id(user_id) or ""
        if current_role not in allowed_roles:
            return RedirectResponse(url=await _route_user(user_id), status_code=302)
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

            # Must be authenticated
            _raw = request.cookies.get(COOKIE_USER_ID)
            user_id = str(_raw) if _raw is not None else None
            if not user_id:
                # No cookie - new user to welcome page
                root_stage = navigation.get_stage("root")
                root_path = root_stage.path if root_stage else "/"
                return ssot_redirect(root_path, context="page_contract no user cookie")
            if not is_valid_storage_user(user_id):
                # Has cookie but invalid - returning user needs reconnect
                reconnect_stage = navigation.get_stage("storage_reconnect")
                reconnect_path = reconnect_stage.path if reconnect_stage else "/storage/reconnect"
                return ssot_redirect(reconnect_path, context="page_contract reconnect required")

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
        guard_redirect = await _guard_role_page(request, {"tenant"})
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

    @fastapi_app.get("/timeline", response_class=HTMLResponse)
    async def timeline_page(request: Request):
        """Universal timeline page - read-only GUI over database records. No auth gate, no cloud fetch."""
        return HTMLResponse(content="<h1>Timeline</h1><p>Timeline page - under construction</p>")

    async def _get_tenant_briefcase(user_id: str, user_name: Optional[str] = None):
        """Fetch complete tenant briefcase - unified vault, timeline, journal, inbox."""
        return await get_tenant_briefcase(user_id, user_name)

    @fastapi_app.get("/tenant/home", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/home/", response_class=HTMLResponse)
    async def tenant_home(request: Request):
        """Serve the tenant home hub page (lightweight entry point after onboarding)."""
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        
        # Get user from cookie/session
        user_id = extract_user_id(request) or ""
        briefcase = None
        if user_id:
            try:
                briefcase = await _get_tenant_briefcase(user_id)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Tenant briefcase load failed for %s: %s", user_id[:6] + "***", e)
        
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
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        
        user_id = extract_user_id(request) or ""
        briefcase = await _get_tenant_briefcase(user_id) if user_id else None
        
        context = {
            "briefcase": briefcase,
            "capture_type": type,
            "today": utc_now().strftime("%Y-%m-%d"),
            "csrf_token": request.state.csrf_token if hasattr(request.state, "csrf_token") else "",
        }
        return templates.TemplateResponse(request, "pages/tenant_capture.html", context)

    @fastapi_app.post("/api/tenant/capture")
    async def tenant_capture_post(request: Request):
        """Create a timeline event from quick capture form."""
        from app.models.models import TimelineEvent
        from app.core.database import get_db_session
        
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        
        user_id = extract_user_id(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        form_data = await request.form()
        
        capture_type = form_data.get("capture_type", "other")
        is_urgent = form_data.get("is_urgent") == "true"
        description = form_data.get("description", "")
        event_date_str = form_data.get("event_date", "")
        event_time_str = form_data.get("event_time", "")
        who_involved = form_data.get("who_involved", "")
        location = form_data.get("location", "")
        
        if not description:
            raise HTTPException(status_code=400, detail="Description is required")
        
        if not event_date_str:
            raise HTTPException(status_code=400, detail="Date is required")
        
        # Parse date/time (must be UTC-aware — event_date is DateTimeTZ)
        try:
            event_date = datetime.datetime.strptime(event_date_str, "%Y-%m-%d").date()
            if event_time_str:
                event_datetime = datetime.datetime.combine(
                    event_date,
                    datetime.datetime.strptime(event_time_str, "%H:%M").time(),
                    tzinfo=datetime.timezone.utc,
                )
            else:
                event_datetime = datetime.datetime.combine(
                    event_date, datetime.datetime.min.time(), tzinfo=datetime.timezone.utc
                )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date or time format")
        
        # Map capture types to event types
        type_mapping = {
            "notice": "notice",
            "conversation": "communication",
            "repair": "maintenance",
            "harassment": "communication",
            "payment": "payment",
            "other": "other"
        }
        event_type = type_mapping.get(capture_type, "other")
        
        async with get_db_session() as db:
            event = TimelineEvent(
                user_id=user_id,
                event_type=event_type,
                title=f"{capture_type.title()} Event",
                description=description,
                event_date=event_datetime,
                is_urgent=is_urgent,
                who_involved=who_involved,
                location=location,
                is_evidence=False,
                created_at=utc_now()
            )
            db.add(event)
            await db.commit()
        
        return {"success": True, "event_id": event.id}

    @fastapi_app.get("/tenant/journal", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/journal/", response_class=HTMLResponse)
    async def tenant_journal(request: Request):
        """Journal page for viewing recorded entries."""
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect

        user_id = extract_user_id(request) or ""
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
                e.created_at.month == utc_now().month and
                e.created_at.year == utc_now().year
            ) if entries else 0,
            "urgent_count": sum(1 for e in entries if getattr(e, "is_urgent", False)),
            "days_since_start": (
                (utc_now() - min(e.created_at for e in entries if hasattr(e, "created_at") and e.created_at)).days
                if entries else 0
            ),
        }
        return templates.TemplateResponse(request, "pages/tenant_journal.html", context)

    @fastapi_app.get("/tenant/inbox", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/inbox/", response_class=HTMLResponse)
    async def tenant_inbox(request: Request):
        """Inbox for notifications and updates."""
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        
        user_id = extract_user_id(request) or ""
        briefcase = await _get_tenant_briefcase(user_id) if user_id else None
        
        context = {"briefcase": briefcase}
        return templates.TemplateResponse(request, "pages/tenant_inbox.html", context)

    @fastapi_app.get("/tenant/help", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/help/", response_class=HTMLResponse)
    async def tenant_help(request: Request):
        """Help and resources page for tenants."""
        guard_redirect = await _guard_role_page(request, {"tenant", "user"})
        if guard_redirect:
            return guard_redirect

        user_id = extract_user_id(request) or ""
        briefcase = await _get_tenant_briefcase(user_id) if user_id else None

        context = {"briefcase": briefcase}
        return templates.TemplateResponse(request, "pages/tenant_help.html", context)

    @fastapi_app.get("/tenant/tools/letters", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/tools/letters/", response_class=HTMLResponse)
    async def tenant_letters(request: Request):
        """Template letters page â€” maintenance request, deposit demand, etc."""
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        letters_path = BASE_PATH / "static" / "tenant" / "tools" / "letters.html"
        static_page = _render_static_page(letters_path, inject_stage_model=True)
        if static_page:
            return static_page
        tenant_home_stage = navigation.get_stage("tenant_home")
        tenant_home_path = tenant_home_stage.path if tenant_home_stage else "/tenant/home"
        return ssot_redirect(tenant_home_path, context="tenant_letters fallback")

    @fastapi_app.get("/tenant/tools/deadlines", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/tools/deadlines/", response_class=HTMLResponse)
    async def tenant_deadlines(request: Request):
        """Deadline tracker â€” rent due, lease end, response deadlines."""
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        deadlines_path = BASE_PATH / "static" / "tenant" / "tools" / "deadlines.html"
        static_page = _render_static_page(deadlines_path, inject_stage_model=True)
        if static_page:
            return static_page
        tenant_home_stage = navigation.get_stage("tenant_home")
        tenant_home_path = tenant_home_stage.path if tenant_home_stage else "/tenant/home"
        return ssot_redirect(tenant_home_path, context="tenant_deadlines fallback")

    @fastapi_app.get("/ui/tool/complaints", response_class=HTMLResponse)
    @fastapi_app.get("/ui/tool/complaints/", response_class=HTMLResponse)
    async def complaints_page(request: Request):
        """Complaint filing tool - where to file housing complaints in Minnesota."""
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        return templates.TemplateResponse(request, "pages/complaints.html", {"request": request})

    @fastapi_app.get("/ui/tool/case-builder", response_class=HTMLResponse)
    @fastapi_app.get("/ui/tool/case-builder/", response_class=HTMLResponse)
    async def case_builder_page(request: Request):
        """Case builder tool - organize documents and evidence."""
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        return templates.TemplateResponse(request, "pages/case_builder.html", {"request": request})

    @fastapi_app.get("/ui/tool/plan-maker", response_class=HTMLResponse)
    @fastapi_app.get("/ui/tool/plan-maker/", response_class=HTMLResponse)
    async def action_plan_page(request: Request):
        """Action plan tool - prioritized next steps."""
        guard_redirect = await _guard_role_page(request, {"tenant"})
        if guard_redirect:
            return guard_redirect
        return templates.TemplateResponse(request, "pages/action_plan.html", {"request": request})

    # Generic Module Page Route — renders any module from its PageContract
    @fastapi_app.get("/tool/{page_id}", response_class=HTMLResponse)
    async def module_tool_page(page_id: str, request: Request):
        """
        Generic module page renderer.
        Looks up the PageContract by page_id and renders module_page.html
        with contract metadata. This allows any module with a PageContract
        to have a UI without creating a dedicated route.
        """
        from app.core.page_contracts import get_contract, PAGE_CONTRACTS
        from app.core.user_context import UserRole
        
        # Validate page_id exists
        if page_id not in PAGE_CONTRACTS:
            return HTMLResponse(
                content=f"<h1>Module '{page_id}' not found</h1><p>Available modules: {', '.join(list(PAGE_CONTRACTS.keys())[:20])}...</p>",
                status_code=404
            )
        
        contract = get_contract(page_id)
        
        # Check role access
        guard_redirect = await _guard_role_page(
            request, 
            {role.value for role in contract.roles_supported}
        )
        if guard_redirect:
            return guard_redirect
        
        # Build template context from PageContract
        # Map PageContract fields to template expectations
        
        # Module-specific action definitions
        MODULE_ACTIONS = {
            "eviction_answer": [
                {"icon": "📋", "label": "Start Answer", "description": "Begin filling out eviction answer form", "endpoint": "/start", "method": "POST"},
                {"icon": "📄", "label": "Load Template", "description": "Load eviction answer template", "endpoint": "/template", "method": "GET"},
                {"icon": "💾", "label": "Save Draft", "description": "Save current progress", "endpoint": "/save", "method": "POST"},
            ],
            "counterclaim": [
                {"icon": "⚖️", "label": "Build Counterclaim", "description": "Create a counterclaim against landlord", "endpoint": "/build", "method": "POST"},
                {"icon": "📚", "label": "Legal Grounds", "description": "Browse valid counterclaim grounds", "endpoint": "/grounds", "method": "GET"},
                {"icon": "📎", "label": "Attach Evidence", "description": "Link supporting documents", "endpoint": "/attach", "method": "POST"},
            ],
            "complaints": [
                {"icon": "📝", "label": "File Complaint", "description": "Submit a new housing complaint", "endpoint": "/file", "method": "POST"},
                {"icon": "📊", "label": "Track Status", "description": "Check complaint status", "endpoint": "/status", "method": "GET"},
                {"icon": "🏛️", "label": "Agency Guide", "description": "Find the right agency to complain to", "endpoint": "/agencies", "method": "GET"},
            ],
            "case_builder": [
                {"icon": "🏗️", "label": "Add Fact", "description": "Add case fact or event", "endpoint": "/facts", "method": "POST"},
                {"icon": "📎", "label": "Link Evidence", "description": "Attach documents to facts", "endpoint": "/evidence", "method": "POST"},
                {"icon": "📋", "label": "View Timeline", "description": "See case chronology", "endpoint": "/timeline", "method": "GET"},
            ],
            "timeline": [
                {"icon": "➕", "label": "Add Event", "description": "Add event to timeline", "endpoint": "/events", "method": "POST"},
                {"icon": "📅", "label": "View Calendar", "description": "See deadline calendar", "endpoint": "/calendar", "method": "GET"},
                {"icon": "🔔", "label": "Set Reminder", "description": "Set deadline reminders", "endpoint": "/remind", "method": "POST"},
            ],
        }
        
        # Icon mapping for common modules
        ICON_MAP = {
            "eviction_answer": "🏠",
            "counterclaim": "⚖️",
            "complaints": "📢",
            "case_builder": "🏗️",
            "timeline": "📅",
            "vault": "🔐",
            "documents": "📄",
            "law_library": "📚",
            "hearing_prep": "🎤",
            "dakota_defense": "🏛️",
        }
        
        template_contract = {
            "title": contract.title,
            "description": contract.expectations or contract.qualification,
            "icon": ICON_MAP.get(page_id, "🔧"),
            "tags": contract.primary_groups + contract.secondary_groups,
            "disclaimer": "This is a legal self-help tool. Consult an attorney for your specific situation.",
            "actions": MODULE_ACTIONS.get(page_id, [
                {"icon": "▶️", "label": "Get Started", "description": "Begin using this tool", "endpoint": "/start", "method": "POST"},
                {"icon": "📖", "label": "Learn More", "description": "Read documentation", "endpoint": "/docs", "method": "GET"},
            ]),
            "api_base": f"/api/modules/{page_id}",
            "sections": [
                {"title": "Entry Criteria", "body": "\n".join(f"• {c}" for c in contract.entry_criteria) or "None specified"},
                {"title": "Exit Criteria", "body": "\n".join(f"• {c}" for c in contract.exit_criteria) or "None specified"},
            ] if contract.entry_criteria or contract.exit_criteria else [],
            "page_id": page_id,
            "route": contract.route,
            "status": contract.status,
            "roles_supported": [r.value for r in contract.roles_supported],
            "primary_groups": contract.primary_groups,
            "telemetry_events": contract.telemetry_events,
        }
        
        return templates.TemplateResponse(
            request, 
            "pages/module_page.html", 
            {
                "request": request,
                "contract": template_contract,
            }
        )

    # Module Access API — Returns which modules are accessible to current user
    @fastapi_app.get("/api/modules/access")
    async def get_module_access_api(request: Request):
        """
        Get module access for current user based on role + jurisdiction.
        
        Returns active modules and any restrictions.
        """
        from app.core.module_gate import get_module_access, get_jurisdiction
        
        access = get_module_access(request)
        jurisdiction = get_jurisdiction(request)
        
        return {
            "user_role": access.user_role.value,
            "jurisdiction": {
                "country": jurisdiction.country,
                "state": jurisdiction.state,
                "county": jurisdiction.county,
            },
            "active_modules": sorted(access.active_modules),
            "restricted": access.restricted_modules,
            "timestamp": utc_now().isoformat(),
        }

    @fastapi_app.get("/tenant/my-advocate", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/my-advocate/", response_class=HTMLResponse)
    async def tenant_my_advocate_page(request: Request):
        """Serve the tenant's advocate management page (case sharing)."""
        guard_redirect = await _guard_role_page(request, {"tenant", "user"})
        if guard_redirect:
            return guard_redirect

        my_advocate_template_path = BASE_PATH / "app" / "templates" / "pages" / "tenant_my_advocate.html"
        if my_advocate_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/tenant_my_advocate.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Tenant my-advocate template error: %s", e)

        return HTMLResponse(content="<h1>My Advocate page not found</h1>", status_code=404)

    # ----------------------------------------------------------------------
    # Phase 1B/1C — Self-Assembling Tenant GUI (UI Composer)
    #
    # /tenant/timeline — RECORD pillar (merged feed via tenant_feed aggregator)
    # /tenant/library  — KNOW pillar (subject grid → Page Composer facts)
    #
    # These pages are assembled by the UI Composer from the component library
    # (app/templates/components/ui_composer.html) via the generic template
    # (app/templates/generic_page.html). No static page templates — the page
    # builds itself from the user's context.
    # ----------------------------------------------------------------------
    @fastapi_app.get("/tenant/timeline", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/timeline/", response_class=HTMLResponse)
    async def tenant_timeline_page(request: Request):
        """RECORD pillar — timeline of everything, assembled by UI Composer."""
        guard_redirect = await _guard_role_page(request, {"tenant", "user"})
        if guard_redirect:
            return guard_redirect

        try:
            from app.services.ui_composer import compose_page
            from app.modules.tenant_feed.service import aggregate_feed_async
            from app.core.user_id import parse_user_id

            # Get user_id for feed aggregation
            user_id_cookie = request.cookies.get("semptify_uid", "")
            user_id = ""
            if user_id_cookie:
                parsed = parse_user_id(user_id_cookie)
                user_id = parsed.user_id if parsed else ""

            # Aggregate the real feed (async — uses vault service + DB)
            feed_items = await aggregate_feed_async(user_id) if user_id else []

            # Compose the page structure
            page = compose_page(user_id, "timeline", context={
                "document_count": len([i for i in feed_items if i["type"] == "document"]),
                "upcoming_deadlines": len([i for i in feed_items if i["type"] == "deadline"]),
            })

            # Inject the real feed into the timeline_group component
            for component in page["components"]:
                if component["type"] == "timeline_group":
                    component["data"]["events"] = feed_items
                    component["data"]["empty"] = len(feed_items) == 0

            return templates.TemplateResponse(
                request,
                "generic_page.html",
                {
                    "page_title": page["page_title"],
                    "pillar": page["pillar"],
                    "components": page["components"],
                },
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("UI Composer timeline error, falling back to old timeline: %s", e)
            # Fallback to the existing timeline page
            return templates.TemplateResponse(request, "pages/timeline.html")

    @fastapi_app.get("/tenant/library", response_class=HTMLResponse)
    @fastapi_app.get("/tenant/library/", response_class=HTMLResponse)
    async def tenant_library_page(request: Request):
        """KNOW pillar — library of verified facts, assembled by UI Composer."""
        guard_redirect = await _guard_role_page(request, {"tenant", "user"})
        if guard_redirect:
            return guard_redirect

        try:
            from app.services.ui_composer import compose_page
            from app.core.user_id import parse_user_id

            user_id_cookie = request.cookies.get("semptify_uid", "")
            user_id = ""
            if user_id_cookie:
                parsed = parse_user_id(user_id_cookie)
                user_id = parsed.user_id if parsed else ""

            page = compose_page(user_id, "library", context={})

            return templates.TemplateResponse(
                request,
                "generic_page.html",
                {
                    "page_title": page["page_title"],
                    "pillar": page["pillar"],
                    "components": page["components"],
                },
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("UI Composer library error, falling back to law-library: %s", e)
            # Fallback to the existing law library page
            return templates.TemplateResponse(request, "pages/law_library.html")

    @fastapi_app.get("/tenant/{subpage}", response_class=HTMLResponse)
    async def tenant_subpage(subpage: str, request: Request):
        """Catch-all for tenant sub-pages not matched by explicit routes above."""
        guard_redirect = await _guard_role_page(request, {"tenant"})
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
        tenant_home_stage = navigation.get_stage("tenant_home")
        tenant_home_path = tenant_home_stage.path if tenant_home_stage else "/tenant/home"
        return ssot_redirect(tenant_home_path, context="tenant_subpage fallback")

    # =========================================================================
    # Advocate Pages
    # =========================================================================

    @fastapi_app.get("/advocate", response_class=HTMLResponse)
    @fastapi_app.get("/advocate/", response_class=HTMLResponse)
    async def advocate_page(request: Request):
        """Serve the advocate dashboard page."""
        guard_redirect = await _guard_role_page(request, {"advocate"})
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

    @fastapi_app.get("/advocate/clients/{client_id}", response_class=HTMLResponse)
    async def advocate_client_detail_page(client_id: str, request: Request):
        """Serve the advocate client detail page for a specific client."""
        guard_redirect = await _guard_role_page(request, {"advocate"})
        if guard_redirect:
            return guard_redirect

        client_template_path = BASE_PATH / "app" / "templates" / "pages" / "advocate_client_detail.html"
        if client_template_path.exists():
            try:
                return templates.TemplateResponse(
                    request,
                    "pages/advocate_client_detail.html",
                    {"client_id": client_id},
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Advocate client detail template error: %s", e)

        return HTMLResponse(content="<h1>Client detail page not found</h1>", status_code=404)

    @fastapi_app.get("/advocate/invite", response_class=HTMLResponse)
    async def advocate_invite_page(request: Request):
        """Serve the advocate invite codes page."""
        guard_redirect = await _guard_role_page(request, {"advocate"})
        if guard_redirect:
            return guard_redirect

        invite_template_path = BASE_PATH / "app" / "templates" / "pages" / "advocate_invite.html"
        if invite_template_path.exists():
            try:
                return templates.TemplateResponse(request, "pages/advocate_invite.html")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Advocate invite template error: %s", e)

        return HTMLResponse(content="<h1>Invite page not found</h1>", status_code=404)

    @fastapi_app.get("/advocate/{subpage}", response_class=HTMLResponse)
    async def advocate_subpage(subpage: str, request: Request):
        """Serve advocate sub-pages."""
        guard_redirect = await _guard_role_page(request, {"advocate"})
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

        advocate_stage = navigation.get_stage("advocate_portal")
        advocate_path = advocate_stage.path if advocate_stage else "/advocate"
        return ssot_redirect(advocate_path, context="advocate_subpage fallback")

    @fastapi_app.get("/advocate/home", response_class=HTMLResponse)
    @fastapi_app.get("/advocate/home/", response_class=HTMLResponse)
    async def advocate_home(request: Request):
        """Serve the advocate home hub page (lightweight entry point after onboarding)."""
        guard_redirect = await _guard_role_page(request, {"advocate"})
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
        guard_redirect = await _guard_role_page(request, {"legal"})
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
        guard_redirect = await _guard_role_page(request, {"legal"})
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
            law_library_stage = navigation.get_stage("law_library")
            law_library_path = law_library_stage.path if law_library_stage else "/law-library"
            return ssot_redirect(law_library_path, context="legal_subpage alias redirect")

        subpage_path = BASE_PATH / "static" / "legal" / f"{target}.html"
        subpage_fallback = _render_static_page(subpage_path, inject_stage_model=True)
        if subpage_fallback:
            return subpage_fallback

        subpage_index = BASE_PATH / "static" / "legal" / target / "index.html"
        subpage_index_fallback = _render_static_page(subpage_index, inject_stage_model=True)
        if subpage_index_fallback:
            return subpage_index_fallback

        legal_stage = navigation.get_stage("legal_portal")
        legal_path = legal_stage.path if legal_stage else "/legal"
        return ssot_redirect(legal_path, context="legal_subpage fallback")

    @fastapi_app.get("/legal/home", response_class=HTMLResponse)
    @fastapi_app.get("/legal/home/", response_class=HTMLResponse)
    async def legal_home(request: Request):
        """Serve the legal home hub page (lightweight entry point after onboarding)."""
        guard_redirect = await _guard_role_page(request, {"legal"})
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
    # Onboarding Support Pages
    # =========================================================================

    # Note: Admin routes with 2FA are defined earlier in this file (lines ~1700)

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
            <title>Onboarding Help - Semptify</title>
            <style>
                body { font-family: system-ui, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; line-height: 1.6; }
                h1 { color: #1e40af; }
                .help-box { background: #f0f9ff; border-left: 4px solid #3b82f6; padding: 20px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <h1>Having trouble getting started?</h1>
            <div class="help-box">
                <p>It looks like your setup process was interrupted a few times. This can happen due to:</p>
                <ul>
                    <li>Network connection issues</li>
                    <li>Browser closing unexpectedly</li>
                    <li>Switching between devices</li>
                </ul>
                <p><strong>What to do:</strong></p>
                <ol>
                    <li>Make sure you have a stable internet connection</li>
                    <li>Complete each step without closing the browser</li>
                    <li>If you get stuck, clear your browser cookies and start fresh</li>
                </ol>
            </div>
            <p><a href="/">← Back to start</a></p>
        </body>
        </html>
        """)

    # =========================================================================
    # Gate Debug Endpoint (dev only - blocked in production)
    # =========================================================================

    @fastapi_app.get("/api/debug/gates")
    async def debug_gates(request: Request):
        """
        Dev-only: Show current onboarding gate state for the authenticated user.
        Returns 404 in production. Use this to diagnose redirect loops.
        """
        if is_production:
            from fastapi import HTTPException as _HTTPException
            raise _HTTPException(status_code=404, detail="Not found")

        from app.core.cookie_auth import verify_user_id as _verify
        from app.core.user_id import COOKIE_USER_ID as _COOKIE
        from app.core.onboarding_state import get_onboarding_state as _get_state
        from app.core.database import get_session_factory as _factory

        raw_cookie = request.cookies.get(_COOKIE)
        if not raw_cookie:
            return {"error": "no_cookie", "hint": "No semptify_uid cookie found"}

        raw_uid = _verify(raw_cookie)
        if not raw_uid:
            return {"error": "invalid_cookie", "hint": "Cookie signature invalid or expired"}

        try:
            _sf = _factory()
            async with _sf() as _db:
                state = await _get_state(raw_uid, _db)
            return {
                "user_id_prefix": raw_uid[:6] + "***",
                "storage_connected": state.storage_connected,
                "vault_initialized": state.vault_initialized,
                "is_fully_onboarded": state.is_fully_onboarded,
                "next_required_gate": state.next_required_gate,
                "next_required_path": state.next_required_path,
            }
        except Exception as exc:
            return {"error": "db_error", "detail": str(exc)}

    # =========================================================================
    # Catch-All HTML Page Router (PUBLIC PAGES ONLY)
    # =========================================================================
    # SSOT RULE: Only unauthenticated public pages are served as static HTML.
    # All authenticated pages MUST go through rendered routes with auth + gates.
    # Allowed: welcome, terms, privacy, disclaimer, about, contact, credits
    # Everything else â†’ 404 (must have a proper rendered route)
    # =========================================================================

    ALLOWED_STATIC_PAGES = frozenset({
        "welcome", "terms", "privacy", "disclaimer",
        "about", "contact", "credits",
    })

    @fastapi_app.get("/{page_name}.html", response_class=HTMLResponse)
    async def serve_html_page(page_name: str, request: Request):
        """
        Serve ONLY public static HTML pages (no auth required).
        All other pages must use rendered template routes.
        """
        if ".." in page_name or "/" in page_name or "\\" in page_name:
            return HTMLResponse(content="<h1>400 - Invalid Request</h1>", status_code=400)

        if page_name not in ALLOWED_STATIC_PAGES:
            return JSONResponse(
                content={"error": "not_found", "message": f"Page '{page_name}.html' is not a public page. Use the rendered route instead."},
                status_code=404,
            )

        page_path = BASE_PATH / "static" / "public" / f"{page_name}.html"
        if not page_path.exists():
            page_path = BASE_PATH / "static" / f"{page_name}.html"
        page_fallback = _render_static_page(page_path)
        if page_fallback:
            return page_fallback

        return JSONResponse(
            content={"error": "not_found", "message": f"Page '{page_name}.html' not found"},
            status_code=404,
        )

    # Vault Activation Page
    @fastapi_app.get("/activate-vault", response_class=HTMLResponse)
    async def activate_vault_page():
        """Serve the vault activation page."""
        from fastapi.responses import FileResponse
        from pathlib import Path
        
        page_path = BASE_PATH / "static" / "onboarding" / "activate-vault.html"
        if page_path.exists():
            return FileResponse(page_path)
        
        return HTMLResponse("<h1>Vault activation page not found</h1>", status_code=404)

    # =========================================================================
    # Health check â€” must return JSON, never HTML
    # =========================================================================
    @fastapi_app.get("/health", tags=["system"])
    async def health_check():
        from app.core.utc import utc_now
        return {"status": "ok", "ts": utc_now().isoformat()}

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
