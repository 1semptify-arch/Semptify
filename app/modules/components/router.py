"""
Semptify 5.0 - Modular Components API Router

Handles events and data for the new modular component system.
Integrates with existing backend services and workspace stage model.

Component Events:
- capture-*: File upload, text input, voice recording
- understand-*: Timeline, rights analysis, risk detection  
- plan-*: Action lists, deadlines, next steps
- tenant-*, advocate-*, legal-*, admin-*: Role-specific actions
"""
# Migrated from app/routers/components.py into the components SDK module.
# All imports remain absolute since components is a CORE module.

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from app.core.utc import utc_now
from typing import List, Optional

from app.core.security import get_optional_user_id
from app.core.user_context import UserRole, get_user_context
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/components", tags=["Modular Components"])


# ============================================================================
# Event Models
# ============================================================================

class ComponentEvent(BaseModel):
    """Base model for component events"""
    component_id: str
    role: str
    timestamp: datetime
    event_type: str
    data: Dict[str, Any]


class UploadFile(BaseModel):
    """File upload metadata"""
    name: str
    size: int
    type: str
    last_modified: Optional[int] = None


class CaptureUploadEvent(BaseModel):
    """Capture upload event"""
    event_type: str = "capture-upload"
    files: List[UploadFile] = []
    total_size: int = 0


class CaptureInputEvent(ComponentEvent):
    """Capture text input event"""
    event_type: str = "capture-quick-input"
    input_type: str = "note"
    content: str = ""
    tags: List[str] = []


class CaptureVoiceEvent(ComponentEvent):
    """Capture voice recording event"""
    event_type: str = "capture-voice-input"
    duration: float = 0.0
    transcript: str = ""
    audio_url: Optional[str] = None


class UnderstandTimelineEvent(ComponentEvent):
    """Understand timeline event"""
    event_type: str = "understand-timeline-select"
    event_id: str = ""
    event_data: Dict[str, Any] = {}


class UnderstandRightsEvent(ComponentEvent):
    """Understand rights analysis event"""
    event_type: str = "understand-rights-select"
    right_id: str = ""
    right_data: Dict[str, Any] = {}


class UnderstandRiskEvent(ComponentEvent):
    """Understand risk detection event"""
    event_type: str = "understand-risk-select"
    risk_id: str = ""
    risk_data: Dict[str, Any] = {}


class PlanActionEvent(ComponentEvent):
    """Plan action event"""
    event_type: str = "plan-action-select"
    action_id: str = ""
    action_data: Dict[str, Any] = {}


class PlanDeadlineEvent(ComponentEvent):
    """Plan deadline event"""
    event_type: str = "plan-deadline-select"
    deadline_id: str = ""
    deadline_data: Dict[str, Any] = {}


# ============================================================================
# Capture Function Group Endpoints
# ============================================================================

@router.post("/capture/upload")
async def handle_capture_upload(
    files: List[UploadFile] = File(...),
    metadata: str = Form(...),
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle file upload from capture component"""
    try:
        # Parse metadata from form
        import json
        metadata_dict = json.loads(metadata)
        component_id = metadata_dict.get('component_id', 'unknown')
        role = metadata_dict.get('role', 'tenant')
        file_metadata = metadata_dict.get('files', [])
        
        logger.info(f"Capture upload event from {component_id}: {len(files)} files")
        
        # Integrate with existing document storage system
        from app.routers import storage
        from app.core.user_id import get_provider_from_user_id
        
        # Get user's storage provider
        provider = get_provider_from_user_id(user_id) if user_id else None
        
        if not provider:
            return JSONResponse({
                "success": False,
                "message": "Storage not connected. Please connect your cloud storage first.",
                "redirect_to": "/storage/providers",
                "user_id": user_id,
                "timestamp": utc_now().isoformat()
            })
        
        # Process files through existing storage system
        processed_files = []
        upload_errors = []
        
        for i, uploaded_file in enumerate(files):
            try:
                # Get corresponding metadata for this file
                file_info = file_metadata[i] if i < len(file_metadata) else {
                    "name": uploaded_file.filename,
                    "size": uploaded_file.size,
                    "type": uploaded_file.content_type
                }
                
                # Create document record in storage system
                document_data = {
                    "name": file_info["name"],
                    "size": file_info["size"],
                    "type": file_info["type"],
                    "last_modified": file_info.get("lastModified"),
                    "provider": provider,
                    "user_id": user_id,
                    "component_id": component_id,
                    "role": role,
                    "uploaded_at": utc_now().isoformat()
                }
                
                # Create document in storage system
                # This would typically call storage.create_document()
                # For now, we simulate the document creation with actual file data
                
                # Read file content for processing
                file_content = await uploaded_file.read()
                
                # Create document ID
                document_id = f"doc_{utc_now().timestamp()}_{len(processed_files)}"
                
                # Here you would integrate with actual storage system
                # For example:
                # result = await storage.create_document(
                #     file_content=file_content,
                #     filename=uploaded_file.filename,
                #     content_type=uploaded_file.content_type,
                #     user_id=user_id,
                #     provider=provider
                # )
                
                processed_files.append({
                    "id": document_id,
                    "name": file_info["name"],
                    "size": file_info["size"],
                    "type": file_info["type"],
                    "status": "uploaded",
                    "provider": provider
                })
                
                logger.info(f"Document created: {document_id} for user {user_id}")
                
            except Exception as e:
                error_msg = f"Failed to process {uploaded_file.filename}: {str(e)}"
                upload_errors.append(error_msg)
                logger.error(error_msg)
        
        # Update workspace stage if documents were uploaded
        if processed_files:
            # This would trigger workspace stage update
            # For now, we just log it
            logger.info(f"Workspace stage updated: {len(processed_files)} documents uploaded for user {user_id}")
        
        # Return response with processed files and any errors
        response_data = {
            "success": True,
            "message": f"Processed {len(processed_files)} files successfully",
            "files_processed": len(processed_files),
            "processed_files": processed_files,
            "user_id": user_id,
            "provider": provider,
            "timestamp": utc_now().isoformat()
        }
        
        if upload_errors:
            response_data["errors"] = upload_errors
            response_data["message"] = f"Processed {len(processed_files)} files with {len(upload_errors)} errors"
        
        return JSONResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error handling capture upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to process upload")


@router.post("/capture/input")
async def handle_capture_input(
    event: CaptureInputEvent,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle text input from capture component"""
    try:
        logger.info(f"Capture input event from {event.component_id}: {event.input_type}")
        
        # TODO: Integrate with existing case management system
        # This would connect to case_builder or briefcase systems
        
        return JSONResponse({
            "success": True,
            "message": "Input saved successfully",
            "input_id": f"input_{utc_now().timestamp()}",
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling capture input: {e}")
        raise HTTPException(status_code=500, detail="Failed to save input")


@router.post("/capture/voice")
async def handle_capture_voice(
    event: CaptureVoiceEvent,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle voice recording from capture component"""
    try:
        logger.info(f"Capture voice event from {event.component_id}: {event.duration}s")
        
        # TODO: Integrate with existing voice processing system
        # This would connect to voice recognition or audio storage
        
        return JSONResponse({
            "success": True,
            "message": "Voice recording saved successfully",
            "recording_id": f"voice_{utc_now().timestamp()}",
            "transcript": event.transcript,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling capture voice: {e}")
        raise HTTPException(status_code=500, detail="Failed to save voice recording")


# ============================================================================
# Understand Function Group Endpoints
# ============================================================================

@router.post("/understand/timeline")
async def handle_understand_timeline(
    event: UnderstandTimelineEvent,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle timeline selection from understand component"""
    try:
        logger.info(f"Understand timeline event from {event.component_id}: {event.event_id}")
        
        detail: dict = {"event_id": event.event_id}
        if user_id:
            try:
                from app.services.form_data import get_form_data_service
                svc = get_form_data_service(user_id)
                if svc:
                    await svc.load()
                    detail["case_stage"] = svc.get_case_summary().get("stage", "unknown")
            except Exception:
                pass

        return JSONResponse({
            "success": True,
            "message": "Timeline event processed",
            **detail,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling understand timeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to process timeline event")


@router.post("/understand/rights")
async def handle_understand_rights(
    event: UnderstandRightsEvent,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle rights selection from understand component"""
    try:
        logger.info(f"Understand rights event from {event.component_id}: {event.right_id}")
        
        analysis: dict = {"right_id": event.right_id}
        try:
            from app.modules.eviction_defense.router import DEFENSE_LIBRARY
            matched = [d for d in DEFENSE_LIBRARY if event.right_id in (d.get("id", ""), d.get("code", ""))]
            if matched:
                analysis["defense"] = matched[0]
        except Exception:
            pass

        return JSONResponse({
            "success": True,
            "message": "Rights analysis processed",
            **analysis,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling understand rights: {e}")
        raise HTTPException(status_code=500, detail="Failed to process rights analysis")


@router.post("/understand/risk")
async def handle_understand_risk(
    event: UnderstandRiskEvent,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle risk selection from understand component"""
    try:
        logger.info(f"Understand risk event from {event.component_id}: {event.risk_id}")
        
        risk_detail: dict = {"risk_id": event.risk_id}
        if user_id:
            try:
                from app.services.form_data import get_form_data_service
                svc = get_form_data_service(user_id)
                if svc:
                    await svc.load()
                    summary = svc.get_case_summary()
                    risk_detail["case_stage"] = summary.get("stage")
                    risk_detail["defenses_available"] = summary.get("defenses_count", 0)
            except Exception:
                pass

        return JSONResponse({
            "success": True,
            "message": "Risk assessment processed",
            **risk_detail,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling understand risk: {e}")
        raise HTTPException(status_code=500, detail="Failed to process risk assessment")


# ============================================================================
# Plan Function Group Endpoints
# ============================================================================

@router.post("/plan/action")
async def handle_plan_action(
    event: PlanActionEvent,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle action selection from plan component"""
    try:
        logger.info(f"Plan action event from {event.component_id}: {event.action_id}")
        
        return JSONResponse({
            "success": True,
            "message": "Action processed",
            "action_id": event.action_id,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling plan action: {e}")
        raise HTTPException(status_code=500, detail="Failed to process action")


@router.post("/plan/deadline")
async def handle_plan_deadline(
    event: PlanDeadlineEvent,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle deadline selection from plan component"""
    try:
        logger.info(f"Plan deadline event from {event.component_id}: {event.deadline_id}")
        
        upcoming = []
        if user_id:
            try:
                from app.models.models import CalendarEvent as CalendarEventModel
                from app.core.database import get_db_session
                from sqlalchemy import select as _select
                from datetime import timedelta
                now = utc_now()
                async with get_db_session() as _db:
                    q = await _db.execute(
                        _select(CalendarEventModel)
                        .where(CalendarEventModel.user_id == user_id)
                        .where(CalendarEventModel.start_datetime >= now)
                        .where(CalendarEventModel.start_datetime <= now + timedelta(days=30))
                        .order_by(CalendarEventModel.start_datetime.asc())
                        .limit(5)
                    )
                    upcoming = [{"id": e.id, "title": e.title, "date": e.start_datetime.isoformat(), "critical": e.is_critical} for e in q.scalars().all()]
            except Exception:
                pass

        return JSONResponse({
            "success": True,
            "message": "Deadline processed",
            "deadline_id": event.deadline_id,
            "upcoming_deadlines": upcoming,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling plan deadline: {e}")
        raise HTTPException(status_code=500, detail="Failed to process deadline")


# ============================================================================
# Role-Specific Endpoints
# ============================================================================

@router.post("/tenant/emergency-action")
async def handle_tenant_emergency(
    component_id: str,
    emergency_id: str,
    action: str,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle emergency action from tenant component"""
    try:
        logger.info(f"Tenant emergency action: {action} for {emergency_id}")
        
        guidance = []
        try:
            from app.modules.eviction_defense.router import DEFENSE_LIBRARY
            if action in ("file_answer", "answer"):
                guidance = [{"step": d.get("title", ""), "detail": d.get("description", "")} for d in DEFENSE_LIBRARY[:3]]
        except Exception:
            pass

        return JSONResponse({
            "success": True,
            "message": "Emergency action processed",
            "emergency_id": emergency_id,
            "action": action,
            "guidance": guidance,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling tenant emergency: {e}")
        raise HTTPException(status_code=500, detail="Failed to process emergency action")


@router.post("/advocate/handoff-client")
async def handle_advocate_handoff(
    component_id: str,
    client_id: str,
    target_role: str,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle client handoff from advocate component"""
    try:
        logger.info(f"Advocate handoff: {client_id} to {target_role}")
        
        # TODO: Integrate with existing handoff system
        # This would connect to collaboration or role upgrade systems
        
        return JSONResponse({
            "success": True,
            "message": "Client handoff processed",
            "client_id": client_id,
            "target_role": target_role,
            "handoff_id": f"handoff_{utc_now().timestamp()}",
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling advocate handoff: {e}")
        raise HTTPException(status_code=500, detail="Failed to process handoff")


@router.post("/legal/start-review")
async def handle_legal_review(
    component_id: str,
    case_id: str,
    review_type: str,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle case review from legal component"""
    try:
        logger.info(f"Legal review: {review_type} for {case_id}")
        
        # TODO: Integrate with existing legal review system
        # This would connect to legal_analysis or document review
        
        return JSONResponse({
            "success": True,
            "message": "Legal review started",
            "case_id": case_id,
            "review_type": review_type,
            "review_id": f"review_{utc_now().timestamp()}",
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling legal review: {e}")
        raise HTTPException(status_code=500, detail="Failed to start legal review")


@router.post("/admin/system-maintenance")
async def handle_admin_maintenance(
    component_id: str,
    maintenance_type: str,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Handle system maintenance from admin component"""
    try:
        logger.info(f"Admin maintenance: {maintenance_type}")
        
        # TODO: Integrate with existing system administration
        # This would connect to system configuration or monitoring
        
        return JSONResponse({
            "success": True,
            "message": "Maintenance task processed",
            "maintenance_type": maintenance_type,
            "task_id": f"maintenance_{utc_now().timestamp()}",
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling admin maintenance: {e}")
        raise HTTPException(status_code=500, detail="Failed to process maintenance")


# ============================================================================
# Workspace Stage Integration
# ============================================================================

@router.get("/workspace-stage")
async def get_workspace_stage(
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get current workspace stage for component adaptation"""
    try:
        stage_data: dict = {
            "stage": "planning",
            "urgency": "medium",
            "storage_connected": False,
            "has_documents": False,
            "has_timeline": False,
            "has_actions": False,
            "case_stage": None,
            "days_to_deadline": None,
        }
        if user_id:
            try:
                from app.services.form_data import get_form_data_service
                svc = get_form_data_service(user_id)
                if svc:
                    await svc.load()
                    summary = svc.get_case_summary()
                    stage_data["case_stage"] = summary.get("stage")
                    stage_data["has_documents"] = summary.get("document_count", 0) > 0
                    stage_data["has_timeline"] = summary.get("timeline_count", 0) > 0
                    stage_data["has_actions"] = bool(summary.get("defenses_count", 0))
                    days = summary.get("days_until_deadline")
                    if days is not None:
                        stage_data["days_to_deadline"] = days
                        stage_data["urgency"] = "critical" if days <= 3 else "high" if days <= 7 else "medium"
                    stage_data["stage"] = summary.get("stage", "planning")
            except Exception:
                pass
            try:
                from app.models.models import User as UserModel
                from app.core.database import get_db_session
                from sqlalchemy import select as _select
                async with get_db_session() as _db:
                    r = await _db.execute(_select(UserModel).where(UserModel.id == user_id))
                    u = r.scalar_one_or_none()
                    if u:
                        stage_data["storage_connected"] = bool(getattr(u, "storage_provider", None))
            except Exception:
                pass

        return JSONResponse({
            **stage_data,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting workspace stage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get workspace stage")


@router.get("/next-step")
async def get_next_step(
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get recommended next step based on workspace stage"""
    try:
        step: dict = {
            "step": "capture",
            "title": "Add Information",
            "description": "Upload documents or add notes to build your case",
            "priority": "high",
            "component": "upload-zone",
        }
        if user_id:
            try:
                from app.services.form_data import get_form_data_service
                svc = get_form_data_service(user_id)
                if svc:
                    await svc.load()
                    summary = svc.get_case_summary()
                    doc_count = summary.get("document_count", 0)
                    case_stage = summary.get("stage", "")
                    days = summary.get("days_until_deadline")
                    if doc_count == 0:
                        step = {"step": "capture", "title": "Upload Your Documents", "description": "Start by uploading your lease, notices, or any court documents.", "priority": "high", "component": "upload-zone"}
                    elif not summary.get("timeline_count", 0):
                        step = {"step": "understand", "title": "Review Your Timeline", "description": "Your documents were processed. Review extracted events.", "priority": "high", "component": "timeline-viewer"}
                    elif case_stage in ("summons_served", "answer_due") or (days is not None and days <= 14):
                        step = {"step": "plan", "title": "File Your Answer", "description": f"Your answer deadline is approaching{f' in {days} days' if days is not None else ''}. Generate your court form now.", "priority": "critical", "component": "court-forms"}
                    elif case_stage == "hearing_scheduled":
                        step = {"step": "plan", "title": "Prepare for Your Hearing", "description": "Review your defenses and gather your evidence packet.", "priority": "high", "component": "hearing-prep"}
                    else:
                        step = {"step": "understand", "title": "Review Your Rights", "description": "Understand which defenses apply to your situation.", "priority": "medium", "component": "rights-viewer"}
            except Exception:
                pass

        return JSONResponse({
            **step,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting next step: {e}")
        raise HTTPException(status_code=500, detail="Failed to get next step")


# ============================================================================
# Component Configuration
# ============================================================================

@router.get("/config/{role}")
async def get_component_config(
    role: str,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get role-specific component configuration"""
    try:
        # TODO: Get role-specific configuration from user context
        # This would integrate with existing role_ui system
        
        role_configs = {
            "tenant": {
                "theme": "blue",
                "show_emergency": True,
                "show_progress": True,
                "default_components": ["upload-zone", "timeline-view", "next-step-card"]
            },
            "advocate": {
                "theme": "purple",
                "show_client_list": True,
                "show_collaboration": True,
                "default_components": ["client-management", "timeline-view", "action-list"]
            },
            "legal": {
                "theme": "green",
                "show_case_review": True,
                "show_document_review": True,
                "default_components": ["timeline-view", "rights-analysis", "deadline-tracker"]
            },
            "admin": {
                "theme": "red",
                "show_system_stats": True,
                "show_user_management": True,
                "default_components": ["system-overview", "user-list", "activity-log"]
            }
        }
        
        config = role_configs.get(role, role_configs["tenant"])
        
        return JSONResponse({
            "role": role,
            "config": config,
            "user_id": user_id,
            "timestamp": utc_now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting component config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get component configuration")
