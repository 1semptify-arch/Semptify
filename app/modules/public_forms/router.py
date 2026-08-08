"""
Public Forms Router
===================
Backend for the contact and feedback forms in static/public/.

Endpoints:
  POST /api/feedback   — feedback.html submits here
  POST /api/contact    — contact form submissions (future form)

Email is sent via Resend (app/services/email_service.py).
If RESEND_API_KEY is not set, submissions are logged and silently accepted
so the form still shows success to the user (no broken UX in dev).
"""
# Migrated from app/routers/public_forms.py into the public_forms SDK module.
# All imports remain absolute since public_forms is a CORE module.

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Public Forms"])


# =============================================================================
# Request Models
# =============================================================================


class FeedbackRequest(BaseModel):
    type: str
    message: str
    email: str | None = None
    page: str | None = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Feedback message cannot be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        allowed = {"bug", "missing", "confusing", "content", "positive", "other"}
        if v not in allowed:
            raise ValueError(f"Invalid feedback type. Must be one of: {sorted(allowed)}")
        return v


class ContactRequest(BaseModel):
    name: str
    email: str
    message: str
    subject: str | None = None

    @field_validator("name", "message")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest):
    """
    Receive a feedback form submission from /public/feedback.html.
    Forwards to support inbox via Resend. Always returns success so
    the form UX is not broken if email is unconfigured.
    """
    from app.services.email_service import send_feedback_email

    label_map = {
        "bug": "Bug Report",
        "missing": "Missing Feature",
        "confusing": "UX Issue",
        "content": "Content Issue",
        "positive": "Positive Feedback",
        "other": "General Feedback",
    }
    type_label = label_map.get(body.type, body.type)

    full_message = f"[{type_label}]\n\n{body.message}"

    sent = await send_feedback_email(
        user_email=body.email,
        feedback_text=full_message,
        page=body.page,
    )

    if not sent:
        logger.info(
            "Feedback logged (email not sent — RESEND_API_KEY not set): type=%s email=%s",
            body.type,
            body.email or "anonymous",
        )

    return JSONResponse({"status": "ok", "received": True})


async def load_tenant_autofill(user_id: str) -> dict:
    """
    Resolve pre-fill data for any form from the tenant's own cloud storage.

    Priority:
    1. Cloud vault — profile.json + case.json (PII lives here, not DB)
    2. DB Contact table — landlord name/address only (PII-free fallback)
    3. TenantBriefcase — user_name only (last resort)

    Returns a dict with keys: tenant_name, property_address, landlord_name,
    landlord_address, email. Empty string for any unresolved field.

    This function is callable from any module (e.g. court_forms router).
    The /tenant/autofill endpoint delegates to it.
    """
    result = {
        "tenant_name": "",
        "property_address": "",
        "landlord_name": "",
        "landlord_address": "",
        "email": "",
    }

    if not user_id:
        return result

    # -------------------------------------------------------------------------
    # Layer 1: Cloud vault — profile.json + case.json (PII lives here, not DB)
    # -------------------------------------------------------------------------
    cloud_loaded = False
    try:
        from app.core.database import get_db_session
        from app.modules.cloud_sync.service import UserCloudSync
        from app.modules.storage.router import get_valid_session

        async with get_db_session() as db:
            session = await get_valid_session(db, user_id)

        if session:
            provider = session.get("provider")
            access_token = session.get("access_token")
            storage = None

            if provider == "google_drive":
                from app.services.storage.google_drive import GoogleDriveProvider

                storage = GoogleDriveProvider(access_token)
            elif provider == "dropbox":
                from app.services.storage.dropbox import DropboxProvider

                storage = DropboxProvider(access_token)
            elif provider == "onedrive":
                from app.services.storage.onedrive import OneDriveProvider

                storage = OneDriveProvider(access_token)

            if storage:
                sync = UserCloudSync(storage, user_id)
                profile = await sync.load_profile()
                case = await sync.load_case()

                if profile:
                    if profile.display_name:
                        result["tenant_name"] = profile.display_name
                    if profile.email:
                        result["email"] = profile.email

                if case:
                    if case.tenant_name and not result["tenant_name"]:
                        result["tenant_name"] = case.tenant_name
                    if case.property_address:
                        result["property_address"] = case.property_address
                    if case.landlord_name:
                        result["landlord_name"] = case.landlord_name
                    if case.landlord_address:
                        result["landlord_address"] = case.landlord_address

                cloud_loaded = True
                logger.debug("autofill: cloud vault loaded for %s", user_id[:8])

    except Exception as exc:
        logger.debug("autofill: cloud vault unavailable for %s: %s", user_id[:8], exc)

    # -------------------------------------------------------------------------
    # Layer 2: DB Contact table — landlord only (no PII, fills any cloud gaps)
    # -------------------------------------------------------------------------
    if not result["landlord_name"] or not result["property_address"]:
        try:
            from sqlalchemy import select

            from app.core.database import get_db_session
            from app.models.models import Contact

            async with get_db_session() as db:
                contact_result = await db.execute(
                    select(Contact)
                    .where(Contact.user_id == user_id, Contact.contact_type == "landlord")
                    .order_by(Contact.created_at.desc())
                )
                landlord = contact_result.scalars().first()
                if landlord:
                    if landlord.name and not result["landlord_name"]:
                        result["landlord_name"] = landlord.name
                    if not result["property_address"]:
                        addr_parts = [
                            landlord.address_line1,
                            landlord.city,
                            landlord.state,
                            landlord.zip_code,
                        ]
                        addr = ", ".join(p for p in addr_parts if p)
                        if addr:
                            result["property_address"] = addr
        except Exception as exc:
            logger.warning("autofill: DB fallback error for %s: %s", user_id[:8], exc)

    # -------------------------------------------------------------------------
    # Layer 3: TenantBriefcase — user_name only (last resort for tenant name)
    # -------------------------------------------------------------------------
    if not result["tenant_name"]:
        try:
            from app.core.tenant_briefcase import get_tenant_briefcase

            briefcase = await get_tenant_briefcase(user_id)
            if briefcase and briefcase.user_name:
                result["tenant_name"] = briefcase.user_name
        except Exception as exc:
            logger.debug("autofill: briefcase unavailable for %s: %s", user_id[:8], exc)

    logger.debug(
        "autofill: resolved fields=%s cloud=%s user=%s",
        [k for k, v in result.items() if v],
        cloud_loaded,
        user_id[:8],
    )
    return result


@router.post("/tenant/autofill")
@limiter.limit("30/minute")
async def tenant_autofill(request: Request):
    """
    Return pre-fill data for letter forms from the tenant's own cloud storage.
    Delegates to load_tenant_autofill() — callable from any module.
    POST to prevent CSRF.
    """
    from app.core.cookie_auth import extract_user_id

    user_id = extract_user_id(request) or ""
    result = await load_tenant_autofill(user_id)
    return JSONResponse(result)


@router.post("/contact")
async def submit_contact(body: ContactRequest):
    """
    Receive a contact form submission.
    Forwards to support inbox via Resend.
    """
    from app.services.email_service import send_contact_email


    sent = await send_contact_email(
        sender_name=body.name,
        sender_email=body.email,
        message=body.message,
    )

    if not sent:
        logger.info(
            "Contact form logged (email not sent — RESEND_API_KEY not set): name=%s email=%s",
            body.name,
            body.email,
        )

    return JSONResponse({"status": "ok", "received": True})
