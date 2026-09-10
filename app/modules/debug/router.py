"""Debug router — development-only maintenance endpoints.

All handlers return 404 when SECURITY_MODE is not "open". These routes are
disabled in production and are only meant for local development and test setup.
"""

from __future__ import annotations

import asyncio
import logging
import traceback as _tb

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.cookie_auth import set_auth_cookie
from app.core.database import get_session_factory
from app.core.ssot_guard import ssot_redirect
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(tags=["debug"])


def _security_open() -> bool:
    return get_settings().security_mode == "open"


def _not_found():
    return JSONResponse({"error": "not found"}, status_code=404)


@router.post("/debug/force-migrate")
async def debug_force_migrate(request: Request):
    """Force alembic to stamp pre-legal_sub_role then upgrade head."""
    if not _security_open():
        return _not_found()

    info = {"step": "init"}
    try:

        def _sync_fix():
            from alembic.config import Config
            from alembic import command

            cfg = Config("alembic.ini")
            # Stamp to the revision before legal_sub_role was added
            command.stamp(cfg, "20260618_add_admin_error_queue")
            # Now upgrade to head — this will run the legal_sub_role migration
            command.upgrade(cfg, "head")
            # Return current version
            from alembic.runtime.migration import MigrationContext
            from sqlalchemy import create_engine

            sync_url = cfg.get_main_option("sqlalchemy.url")
            eng = create_engine(sync_url)
            with eng.connect() as conn:
                mc = MigrationContext.configure(conn)
                return mc.get_current_revision()

        loop = asyncio.get_event_loop()
        final_rev = await loop.run_in_executor(None, _sync_fix)
        info["final_revision"] = str(final_rev)
        info["step"] = "done"
    except Exception as exc:
        info["error"] = str(exc)
        info["traceback"] = _tb.format_exc()
    return JSONResponse(content=info)


@router.post("/debug/add-legal-columns")
async def debug_add_legal_columns(request: Request):
    """Directly add missing legal_sub_role and bar_license_number columns."""
    if not _security_open():
        return _not_found()

    info = {"step": "init"}
    try:
        factory = get_session_factory()
        async with factory() as db:
            # Check current state
            result = await db.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='users' AND column_name IN ('legal_sub_role','bar_license_number')"
                )
            )
            existing = [r[0] for r in result.fetchall()]
            info["before"] = existing

            if "legal_sub_role" not in existing:
                await db.execute(text("ALTER TABLE users ADD COLUMN legal_sub_role VARCHAR(20) NULL"))
                info["added_legal_sub_role"] = True
            else:
                info["added_legal_sub_role"] = False

            if "bar_license_number" not in existing:
                await db.execute(text("ALTER TABLE users ADD COLUMN bar_license_number VARCHAR(50) NULL"))
                info["added_bar_license_number"] = True
            else:
                info["added_bar_license_number"] = False

            # Add indexes if missing
            try:
                await db.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_users_legal_sub_role ON users (legal_sub_role)")
                )
                await db.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_users_bar_license_number ON users (bar_license_number)")
                )
            except Exception as ie:
                info["index_warning"] = str(ie)

            await db.commit()

            # Verify
            result = await db.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='users' AND column_name IN ('legal_sub_role','bar_license_number')"
                )
            )
            after = [r[0] for r in result.fetchall()]
            info["after"] = after

        info["step"] = "done"
    except Exception as exc:
        info["error"] = str(exc)
        info["traceback"] = _tb.format_exc()
    return JSONResponse(content=info)


@router.post("/debug/stamp-alembic-head")
async def debug_stamp_alembic_head(request: Request):
    """Stamp alembic_version to head without running migrations."""
    if not _security_open():
        return _not_found()

    info = {"step": "init"}
    try:

        def _sync_stamp():
            from alembic.config import Config
            from alembic import command

            cfg = Config("alembic.ini")
            command.stamp(cfg, "head")
            from alembic.runtime.migration import MigrationContext
            from sqlalchemy import create_engine

            sync_url = cfg.get_main_option("sqlalchemy.url")
            eng = create_engine(sync_url)
            with eng.connect() as conn:
                mc = MigrationContext.configure(conn)
                return mc.get_current_revision()

        loop = asyncio.get_event_loop()
        final_rev = await loop.run_in_executor(None, _sync_stamp)
        info["stamped_to"] = str(final_rev)
        info["step"] = "done"
    except Exception as exc:
        info["error"] = str(exc)
        info["traceback"] = _tb.format_exc()
    return JSONResponse(content=info)


@router.post("/debug/seed-test-user")
async def debug_seed_test_user(request: Request):
    """Dev-only: seed a local tenant user and log the browser in."""
    if not _security_open():
        return _not_found()

    info = {"step": "init"}
    try:
        now = utc_now()
        factory = get_session_factory()
        async with factory() as db:
            # Check if user exists
            result = await db.execute(text("SELECT id FROM users WHERE id = :uid"), {"uid": "GUbGQUTpK6"})
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing user to be fully onboarded
                await db.execute(
                    text(
                        "UPDATE users SET "
                        "primary_provider = 'google_drive', "
                        "default_role = 'tenant', "
                        "completed_groups = :groups, "
                        "updated_at = :now "
                        "WHERE id = :uid"
                    ),
                    {"uid": "GUbGQUTpK6", "groups": "storage_connected,vault_initialized", "now": now},
                )
                info["action"] = "updated"
            else:
                # Insert new user
                await db.execute(
                    text(
                        "INSERT INTO users (id, primary_provider, storage_user_id, "
                        "default_role, intensity_level, completed_groups, created_at, updated_at) "
                        "VALUES (:uid, 'google_drive', :sid, 'tenant', 'low', "
                        ":groups, :now1, :now2)"
                    ),
                    {
                        "uid": "GUbGQUTpK6",
                        "sid": "test-storage-user-id",
                        "groups": "storage_connected,vault_initialized",
                        "now1": now,
                        "now2": now,
                    },
                )
                info["action"] = "inserted"

            await db.commit()

            # Verify
            result = await db.execute(
                text(
                    "SELECT id, primary_provider, default_role, completed_groups FROM users WHERE id = :uid"
                ),
                {"uid": "GUbGQUTpK6"},
            )
            row = result.fetchone()
            if row:
                info["user"] = {
                    "id": str(row[0]),
                    "primary_provider": str(row[1]),
                    "default_role": str(row[2]),
                    "completed_groups": list(row[3]) if row[3] else [],
                }

        info["step"] = "done"

        # Log the browser in as the seeded user.
        redirect = ssot_redirect("/gui/record/journal/create", context="debug seed-test-user")
        set_auth_cookie(redirect, "GUbGQUTpK6")
        return redirect

    except Exception as exc:
        info["error"] = str(exc)
        info["traceback"] = _tb.format_exc()
        return JSONResponse(content=info)
