"""
Semptify 5.0 - Workflow & Contract API Router
Exposes the workflow engine and page contract registry as API endpoints.

Endpoints:
  POST /api/workflow/route       — deterministic routing decision
  GET  /api/workflow/groups      — all 8 process groups
  GET  /api/workflow/contracts   — all page contracts
  GET  /api/workflow/contracts/{page_id} — single contract
  GET  /api/workflow/health      — contract + registry validation report
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any, Optional
from collections import Counter
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError

from app.core.workflow_engine import ProcessCode, evaluate_from_params
from app.core.process_registry import PROCESS_GROUPS, get_groups_for_role
from app.core.page_contracts import PAGE_CONTRACTS, get_contract, validate_all_contracts
from app.core.user_context import UserRole
from app.core.database import get_db_session
from app.models.models import CalendarEvent as CalendarEventModel, TimelineEvent, Document
from app.services.positronic_brain import get_brain

router = APIRouter(prefix="/api/workflow", tags=["Workflow Engine"])


# =============================================================================
# Request / Response Models
# =============================================================================

# =============================================================================
# Case-State Helpers
# =============================================================================

_ROLE_MAP: dict[str, str] = {
    "U": "user",
    "V": "advocate",
    "L": "legal",
    "A": "admin",
    "M": "manager",
}

_PROCESS_TITLES: dict[str, str] = {
    ProcessCode.A.value: "A - Welcome",
    ProcessCode.B1.value: "B1 - Documents",
    ProcessCode.B2.value: "B2 - Timeline",
    ProcessCode.B3.value: "B3 - Filing",
    ProcessCode.B4.value: "B4 - Hearing / Review",
}


def _scan_user_cases(user_id: str) -> tuple[bool, bool]:
    """Return (defense_started, court_packet_ready) from case-builder JSON files.

    defense_started  — any case file has a non-empty ``defenses`` list.
    court_packet_ready — defense is started AND the case also has ``motions``
                         or ``evidence`` assembled (materials ready to packet).
    """
    safe_uid = "".join(c for c in user_id if c.isalnum() or c in "_-")
    cases_dir = Path(os.getcwd()) / "data" / "cases" / safe_uid
    defense_started = False
    court_packet_ready = False
    if cases_dir.exists():
        for case_file in cases_dir.glob("*.json"):
            try:
                case = json.loads(case_file.read_text(encoding="utf-8"))
                if case.get("defenses"):
                    defense_started = True
                if case.get("defenses") and (case.get("motions") or case.get("evidence")):
                    court_packet_ready = True
            except (OSError, json.JSONDecodeError, TypeError):
                continue
    return defense_started, court_packet_ready


def _derive_current_process(
    role: str,
    storage_connected: bool,
    documents_present: bool,
    timeline_events: int,
    defense_started: bool,
    court_packet_ready: bool,
    hearing_scheduled: bool,
) -> str:
    if not storage_connected:
        return ProcessCode.A.value

    if role != UserRole.USER.value:
        return ProcessCode.B4.value

    if not documents_present:
        return ProcessCode.B1.value

    if timeline_events <= 0:
        return ProcessCode.B2.value

    if not court_packet_ready or defense_started:
        return ProcessCode.B3.value

    if hearing_scheduled:
        return ProcessCode.B4.value

    return ProcessCode.B4.value


def _derive_urgency(
    documents_present: bool,
    timeline_events: int,
    hearing_scheduled: bool,
    nearest_critical_days: int | None,
    timeline_urgencies: list[str],
    has_deadline: bool,
) -> tuple[str, str]:
    normalized = {value.strip().lower() for value in timeline_urgencies if value and value.strip()}

    if hearing_scheduled:
        return "Critical", "A hearing is scheduled. Prioritize hearing readiness and deadline review."

    if nearest_critical_days is not None and nearest_critical_days <= 3:
        return "Critical", "A critical calendar event is within 3 days."

    if "critical" in normalized:
        return "Critical", "Timeline includes a critical event or deadline."

    if nearest_critical_days is not None and nearest_critical_days <= 7:
        return "High", "A critical calendar event is approaching within 7 days."

    if has_deadline or "high" in normalized:
        return "High", "An upcoming deadline or high-urgency timeline item needs attention."

    if documents_present or timeline_events > 0:
        return "Moderate", "Case work is active, but no immediate critical event is scheduled."

    return "Low", "No active deadlines or urgent case events were found."


class RouteRequest(BaseModel):
    role: str
    storage_state: str
    documents_present: bool = False
    overlay_record_ids: list[str] = []
    has_active_case: bool = False


class RouteResponse(BaseModel):
    next_process: str
    next_route: str
    allowed_actions: list[str]
    blocked_actions: list[str]
    deterministic_reason: str
    block_reason: Optional[str] = None
    warnings: list[str]


class AdvanceRequest(BaseModel):
    current_page: str = "welcome"
    role: str
    storage_state: str
    completed_actions: list[str] = []
    documents_present: bool = False
    overlay_record_ids: list[str] = []
    has_active_case: bool = False


class AdvanceResponse(BaseModel):
    status: str
    current_page: str
    missing_requirements: list[str]
    next_process: Optional[str] = None
    next_route: Optional[str] = None
    allowed_actions: list[str] = []
    blocked_actions: list[str] = []
    deterministic_reason: Optional[str] = None
    warnings: list[str] = []


class NextStepRequest(BaseModel):
    role: str
    storage_state: str
    documents_present: bool = False
    has_active_case: bool = False
    timeline_events: int = 0
    defense_started: bool = False
    court_packet_ready: bool = False
    hearing_scheduled: bool = False


class CaseStateResponse(BaseModel):
    user_id: str
    role: str
    storage_connected: bool
    current_process: str
    current_stage_title: str
    urgency_level: str
    urgency_reason: str
    document_count: int
    documents_present: bool
    timeline_events: int
    defense_started: bool
    court_packet_ready: bool
    hearing_scheduled: bool
    stage_cards: list[dict]
    alerts: list[dict]
    computed_at: str


class HomeStageCard(BaseModel):
    card_id: str
    title: str
    description: str
    route: str
    state: str
    button_label: str
    button_variant: str = "primary"


class HomeAlert(BaseModel):
    level: str
    message: str


class NextStepResponse(BaseModel):
    next_process: str
    next_route: str
    next_action: str
    deterministic_reason: str
    warnings: list[str] = []


def _normalize_stage_cards(stage_cards: list[Any] | None) -> list[dict]:
    """Normalize stage cards to a UI-safe schema with deterministic defaults."""
    if not stage_cards:
        return []

    normalized: list[dict] = []
    for index, item in enumerate(stage_cards, start=1):
        data = item.model_dump() if isinstance(item, HomeStageCard) else item if isinstance(item, dict) else {}
        state = str(data.get("state") or "Available")
        normalized.append(
            {
                "card_id": str(data.get("card_id") or f"stage_{index}"),
                "title": str(data.get("title") or f"Stage {index}"),
                "description": str(data.get("description") or "No description provided."),
                "route": str(data.get("route") or "/"),
                "state": state,
                "button_label": str(data.get("button_label") or ("Continue" if state == "Current" else "Open")),
                "button_variant": str(data.get("button_variant") or "primary"),
            }
        )

    return normalized


def _normalize_alerts(alerts: list[Any] | None) -> list[dict]:
    """Normalize alerts to ensure message/level fields are always present."""
    if not alerts:
        return []

    normalized: list[dict] = []
    for item in alerts:
        data = item.model_dump() if isinstance(item, HomeAlert) else item if isinstance(item, dict) else {}
        normalized.append(
            {
                "level": str(data.get("level") or "good"),
                "message": str(data.get("message") or "No active alerts right now."),
            }
        )

    return normalized


def _progress_state_label(current_process: str, process: str) -> tuple[str, str]:
    order = [ProcessCode.B1.value, ProcessCode.B2.value, ProcessCode.B3.value, ProcessCode.B4.value]
    current_index = order.index(current_process) if current_process in order else -1
    target_index = order.index(process) if process in order else -1

    if current_index >= 0 and target_index >= 0:
        if target_index < current_index:
            return "Complete", "Review"
        if target_index == current_index:
            return "Current", "Continue"
    return "Upcoming", "Open"


def _build_home_stage_cards(
    role: str,
    current_process: str,
    documents_present: bool,
    timeline_events: int,
    hearing_scheduled: bool,
    court_packet_ready: bool,
) -> list[HomeStageCard]:
    if role == UserRole.USER.value:
        b1_state, b1_button = _progress_state_label(current_process, ProcessCode.B1.value)
        b2_state, b2_button = _progress_state_label(current_process, ProcessCode.B2.value)
        b3_state, b3_button = _progress_state_label(current_process, ProcessCode.B3.value)
        research_state = "Available" if documents_present else "Upcoming"

        return [
            HomeStageCard(
                card_id="documents",
                title="1. Upload Documents",
                description="Add lease, notices, receipts, and communications to establish the case record.",
                route="/tenant/documents",
                state=b1_state,
                button_label=b1_button,
            ),
            HomeStageCard(
                card_id="timeline",
                title="2. Review Timeline",
                description="Confirm extracted dates and events before moving into filings and hearing prep.",
                route="/tenant/timeline",
                state=b2_state,
                button_label=b2_button,
            ),
            HomeStageCard(
                card_id="research",
                title="3. Research & Knowledge",
                description="Open legal analysis to review statutes, evidence framing, and issue patterns before filing.",
                route="/legal-analysis",
                state=research_state,
                button_label="Open" if research_state == "Upcoming" else "Review",
                button_variant="secondary",
            ),
            HomeStageCard(
                card_id="filing",
                title="4. Filing & Packet Prep",
                description="Build the eviction answer, assemble the packet, and prepare for hearing readiness.",
                route="/static/eviction_answer.html" if not court_packet_ready else "/static/court_packet.html",
                state=b3_state,
                button_label=b3_button,
            ),
            HomeStageCard(
                card_id="help",
                title="5. Help & Contacts",
                description="Reach legal aid, emergency housing contacts, and support resources when you need human help.",
                route="/tenant/help",
                state="Available",
                button_label="Open",
                button_variant="secondary",
            ),
        ]

    workspace_route = {
        UserRole.ADVOCATE.value: "/advocate",
        UserRole.LEGAL.value: "/legal",
        UserRole.ADMIN.value: "/admin",
        UserRole.MANAGER.value: "/admin",
    }.get(role, "/advocate")

    output_route = "/zoom-court" if hearing_scheduled else "/static/court_packet.html"
    output_state = "Available" if documents_present or timeline_events > 0 else "Upcoming"

    return [
        HomeStageCard(
            card_id="workspace",
            title="1. Professional Workspace",
            description="Open the role-specific dashboard to select a case, review status, and coordinate next actions.",
            route=workspace_route,
            state="Current",
            button_label="Open",
        ),
        HomeStageCard(
            card_id="research",
            title="2. Research & Knowledge",
            description="Run legal analysis and evidence review before drafting filings or escalation plans.",
            route="/legal-analysis",
            state="Available" if documents_present else "Upcoming",
            button_label="Open",
            button_variant="secondary",
        ),
        HomeStageCard(
            card_id="actions",
            title="3. Functions & Actions",
            description="Use FunctionX to build action sets, draft work, and execute deterministic case operations.",
            route="/functionx",
            state="Available",
            button_label="Open",
        ),
        HomeStageCard(
            card_id="output",
            title="4. Output & Delivery",
            description="Package filings, hearing materials, and export bundles once case work is ready for delivery.",
            route=output_route,
            state=output_state,
            button_label="Open",
            button_variant="secondary",
        ),
    ]


def _build_home_alerts(
    role: str,
    urgency_level: str,
    urgency_reason: str,
    documents_present: bool,
    timeline_events: int,
    defense_started: bool,
    court_packet_ready: bool,
    hearing_scheduled: bool,
) -> list[HomeAlert]:
    alerts: list[HomeAlert] = []

    if urgency_level == "Critical":
        alerts.append(HomeAlert(level="danger", message=urgency_reason))
    elif urgency_level == "High":
        alerts.append(HomeAlert(level="warning", message=urgency_reason))
    else:
        alerts.append(HomeAlert(level="good", message=urgency_reason))

    if role == UserRole.USER.value:
        if not documents_present:
            alerts.append(HomeAlert(level="warning", message="No case documents found. Upload notices and lease records first."))
        elif timeline_events <= 0:
            alerts.append(HomeAlert(level="warning", message="Timeline is empty. Review extracted dates before drafting defenses."))
        elif defense_started and not court_packet_ready:
            alerts.append(HomeAlert(level="good", message="Defense work has started. Build the court packet to move into hearing prep."))
        else:
            alerts.append(HomeAlert(level="good", message="Evidence is available. Use Research & Knowledge to pressure-test the filing path."))

        alerts.append(HomeAlert(
            level="danger" if hearing_scheduled else "good",
            message="Hearing is on calendar. Finish Zoom Court readiness now." if hearing_scheduled else "Help & Contacts stays available if you need advocate or legal-aid escalation.",
        ))
        return alerts[:3]

    if not documents_present:
        alerts.append(HomeAlert(level="warning", message="No documents are attached to the active case context yet."))
    elif timeline_events <= 0:
        alerts.append(HomeAlert(level="warning", message="Case documents are present, but timeline review has not been completed."))
    else:
        alerts.append(HomeAlert(level="good", message="Case context is loaded. Move from research into FunctionX actions or output prep."))

    alerts.append(HomeAlert(
        level="danger" if hearing_scheduled else "good",
        message="A hearing is scheduled. Prioritize output delivery and readiness checks." if hearing_scheduled else "Output & Delivery is available when you need to package filings or handoff materials.",
    ))
    return alerts[:3]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/route", response_model=RouteResponse)
async def get_route_decision(body: RouteRequest) -> RouteResponse:
    """
    Return a deterministic routing decision for the given role + storage state.
    This is the core workflow engine — no AI, fully predictable.
    """
    try:
        documents_present = body.documents_present or bool(body.overlay_record_ids)
        decision = evaluate_from_params(
            role=body.role,
            storage_state=body.storage_state,
            documents_present=documents_present,
            has_active_case=body.has_active_case,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return RouteResponse(
        next_process=decision.next_process.value,
        next_route=decision.next_route,
        allowed_actions=decision.allowed_actions,
        blocked_actions=decision.blocked_actions,
        deterministic_reason=decision.deterministic_reason,
        block_reason=decision.block_reason,
        warnings=decision.warnings,
    )


@router.post("/advance", response_model=AdvanceResponse)
async def advance_workflow(body: AdvanceRequest) -> AdvanceResponse:
    """
    Gate-based transition endpoint.
    For now, enforces full welcome requirements before allowing Process A -> Process B routing.
    """
    page = body.current_page.strip().lower()
    completed = {action.strip() for action in body.completed_actions if action and action.strip()}

    if page != "welcome":
        raise HTTPException(status_code=422, detail="Only current_page='welcome' is supported at this time")

    missing_requirements: list[str] = []

    if not body.role.strip():
        missing_requirements.append("role_selected")
    else:
        if "role_selected" not in completed:
            missing_requirements.append("role_selected")

    if not body.storage_state.strip():
        missing_requirements.append("storage_status_set")
    else:
        if "storage_status_set" not in completed:
            missing_requirements.append("storage_status_set")

    if "process_start_clicked" not in completed:
        missing_requirements.append("process_start_clicked")

    if missing_requirements:
        return AdvanceResponse(
            status="blocked",
            current_page=page,
            missing_requirements=missing_requirements,
            warnings=[
                "Complete required welcome actions before advancing.",
            ],
        )

    try:
        documents_present = body.documents_present or bool(body.overlay_record_ids)
        decision = evaluate_from_params(
            role=body.role,
            storage_state=body.storage_state,
            documents_present=documents_present,
            has_active_case=body.has_active_case,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AdvanceResponse(
        status="advance",
        current_page=page,
        missing_requirements=[],
        next_process=decision.next_process.value,
        next_route=decision.next_route,
        allowed_actions=decision.allowed_actions,
        blocked_actions=decision.blocked_actions,
        deterministic_reason=decision.deterministic_reason,
        warnings=decision.warnings,
    )


@router.post("/next-step", response_model=NextStepResponse)
async def get_next_step(body: NextStepRequest) -> NextStepResponse:
    """
    Determine the single best deterministic next step from current case state.
    """
    try:
        role_enum = UserRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown role: '{body.role}'") from exc

    try:
        # Validate enums and normalize role-specific base route using existing engine.
        baseline = evaluate_from_params(
            role=body.role,
            storage_state=body.storage_state,
            documents_present=body.documents_present,
            has_active_case=body.has_active_case,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    warnings: list[str] = []

    if body.storage_state == "need_connect":
        return NextStepResponse(
            next_process="A",
            next_route="/storage/providers",
            next_action="connect_storage",
            deterministic_reason="Storage is not connected. Connect storage before any case workflow step.",
            warnings=warnings,
        )

    if role_enum != UserRole.USER:
        if not body.has_active_case:
            return NextStepResponse(
                next_process="B4",
                next_route=baseline.next_route,
                next_action="open_case_queue",
                deterministic_reason="Professional role with no active case context. Open your role workspace and select a case.",
                warnings=warnings,
            )

        if not body.documents_present:
            return NextStepResponse(
                next_process="B4",
                next_route="/static/briefcase.html",
                next_action="collect_case_documents",
                deterministic_reason="Active case found but no case documents detected. Gather documents in Briefcase first.",
                warnings=warnings,
            )

        if body.timeline_events <= 0:
            return NextStepResponse(
                next_process="B2",
                next_route="/tenant/timeline",
                next_action="build_timeline",
                deterministic_reason="Documents are present but no timeline events exist. Build timeline before drafting filings.",
                warnings=warnings,
            )

        return NextStepResponse(
            next_process="B4",
            next_route="/static/court_packet.html",
            next_action="prepare_court_packet",
            deterministic_reason="Case context is available. Continue to packet preparation for filing and hearing readiness.",
            warnings=warnings,
        )

    # Tenant deterministic routing
    if not body.documents_present:
        return NextStepResponse(
            next_process="B1",
            next_route="/tenant/documents",
            next_action="upload_documents",
            deterministic_reason="No documents found. Upload notices and lease documents first.",
            warnings=warnings,
        )

    if body.timeline_events <= 0:
        return NextStepResponse(
            next_process="B2",
            next_route="/tenant/timeline",
            next_action="review_timeline",
            deterministic_reason="Documents are present but timeline is empty. Confirm events before defense drafting.",
            warnings=warnings,
        )

    if not body.defense_started:
        return NextStepResponse(
            next_process="B3",
            next_route="/static/eviction_answer.html",
            next_action="start_defense",
            deterministic_reason="Timeline exists. Begin the defense filing flow with an eviction answer.",
            warnings=warnings,
        )

    if not body.court_packet_ready:
        return NextStepResponse(
            next_process="B3",
            next_route="/static/court_packet.html",
            next_action="build_court_packet",
            deterministic_reason="Defense has started. Generate the court packet before hearing prep.",
            warnings=warnings,
        )

    if body.hearing_scheduled:
        return NextStepResponse(
            next_process="B4",
            next_route="/zoom-court",
            next_action="run_zoom_court_prep",
            deterministic_reason="Hearing is scheduled and packet is ready. Complete Zoom Court readiness checks.",
            warnings=warnings,
        )

    return NextStepResponse(
        next_process="B4",
        next_route="/static/hearing_prep.html",
        next_action="hearing_prep",
        deterministic_reason="Packet is ready. Continue with hearing preparation and scheduling checklist.",
        warnings=warnings,
    )


@router.get("/case-state", response_model=CaseStateResponse)
async def get_case_state(request: Request) -> CaseStateResponse:
    """
    Derive real case-state signals from persisted artifacts.

    Reads from three sources:
    - DB ``calendar_events``: determines ``hearing_scheduled``
    - DB ``documents`` + ``timeline_events``: counts ``document_count`` / ``timeline_events``
    - File ``data/cases/{user_id}/*.json``: determines ``defense_started`` / ``court_packet_ready``

    Called by home.html to supply data-backed inputs to the next-step card
    instead of relying on client-side heuristics.
    """
    user_id = request.cookies.get("semptify_uid", "")
    role = _ROLE_MAP.get(user_id[1:2].upper(), "user") if len(user_id) >= 2 else "user"
    storage_connected = user_id[:1].upper() in {"G", "D", "O"} if user_id else False

    now_utc = datetime.now(timezone.utc)
    doc_count = 0
    timeline_count = 0
    hearing_count = 0
    nearest_critical_days: int | None = None
    timeline_urgencies: list[str] = []
    has_deadline = False

    try:
        async with get_db_session() as db:
            doc_count = len((await db.execute(
                select(Document.id).where(Document.user_id == user_id)
            )).scalars().all())

            timeline_count = len((await db.execute(
                select(TimelineEvent.id).where(
                    TimelineEvent.user_id == user_id
                )
            )).scalars().all())

            hearing_count = len((await db.execute(
                select(CalendarEventModel.id).where(
                    and_(
                        CalendarEventModel.user_id == user_id,
                        CalendarEventModel.event_type == "hearing",
                        CalendarEventModel.start_datetime > now_utc,
                    )
                )
            )).scalars().all())

            critical_dates = (await db.execute(
                select(CalendarEventModel.start_datetime).where(
                    and_(
                        CalendarEventModel.user_id == user_id,
                        CalendarEventModel.is_critical.is_(True),
                        CalendarEventModel.start_datetime > now_utc,
                    )
                )
            )).scalars().all()

            if critical_dates:
                nearest_critical = min(critical_dates)
                nearest_critical_days = max(0, (nearest_critical - now_utc).days)

            timeline_rows = (await db.execute(
                select(TimelineEvent.urgency, TimelineEvent.is_deadline).where(
                    TimelineEvent.user_id == user_id
                )
            )).all()

            timeline_urgencies = [row[0] for row in timeline_rows if row[0]]
            has_deadline = any(bool(row[1]) for row in timeline_rows)
    except SQLAlchemyError:
        pass  # DB unavailable; file-based signals still returned

    defense_started, court_packet_ready = _scan_user_cases(user_id)

    current_process = _derive_current_process(
        role=role,
        storage_connected=storage_connected,
        documents_present=int(doc_count) > 0,
        timeline_events=int(timeline_count),
        defense_started=defense_started,
        court_packet_ready=court_packet_ready,
        hearing_scheduled=int(hearing_count) > 0,
    )

    urgency_level, urgency_reason = _derive_urgency(
        documents_present=int(doc_count) > 0,
        timeline_events=int(timeline_count),
        hearing_scheduled=int(hearing_count) > 0,
        nearest_critical_days=nearest_critical_days,
        timeline_urgencies=timeline_urgencies,
        has_deadline=has_deadline,
    )

    stage_cards = _build_home_stage_cards(
        role=role,
        current_process=current_process,
        documents_present=int(doc_count) > 0,
        timeline_events=int(timeline_count),
        hearing_scheduled=int(hearing_count) > 0,
        court_packet_ready=court_packet_ready,
    )

    alerts = _build_home_alerts(
        role=role,
        urgency_level=urgency_level,
        urgency_reason=urgency_reason,
        documents_present=int(doc_count) > 0,
        timeline_events=int(timeline_count),
        defense_started=defense_started,
        court_packet_ready=court_packet_ready,
        hearing_scheduled=int(hearing_count) > 0,
    )

    stage_cards_payload = _normalize_stage_cards(stage_cards)
    alerts_payload = _normalize_alerts(alerts)

    return CaseStateResponse(
        user_id=user_id,
        role=role,
        storage_connected=storage_connected,
        current_process=current_process,
        current_stage_title=_PROCESS_TITLES[current_process],
        urgency_level=urgency_level,
        urgency_reason=urgency_reason,
        document_count=int(doc_count),
        documents_present=int(doc_count) > 0,
        timeline_events=int(timeline_count),
        defense_started=defense_started,
        court_packet_ready=court_packet_ready,
        hearing_scheduled=int(hearing_count) > 0,
        stage_cards=stage_cards_payload,
        alerts=alerts_payload,
        computed_at=now_utc.isoformat(),
    )


@router.get("/groups")
async def list_process_groups(role: Optional[str] = None) -> dict:
    """
    Return all 8 process groups, optionally filtered by role.
    """
    if role:
        try:
            role_enum = UserRole(role)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Unknown role: '{role}'") from exc
        groups = get_groups_for_role(role_enum)
    else:
        groups = list(PROCESS_GROUPS)

    return {
        "groups": [
            {
                "group_id": g.group_id,
                "name": g.name,
                "title": g.title,
                "purpose": g.purpose,
                "scope_includes": list(g.scope_includes),
                "scope_excludes": list(g.scope_excludes),
                "entry_criteria": list(g.entry_criteria),
                "exit_criteria": list(g.exit_criteria),
                "success_metrics": list(g.success_metrics),
                "roles_with_access": [r.value for r in g.roles_with_access],
            }
            for g in groups
        ],
        "total": len(groups),
    }


@router.get("/contracts")
async def list_contracts() -> dict:
    """Return all registered page contracts (summary view)."""
    return {
        "contracts": [
            {
                "page_id": c.page_id,
                "title": c.title,
                "route": c.route,
                "roles_supported": [r.value for r in c.roles_supported],
                "primary_groups": c.primary_groups,
                "secondary_groups": c.secondary_groups,
                "group_coverage": c.group_coverage,
            }
            for c in PAGE_CONTRACTS.values()
        ],
        "total": len(PAGE_CONTRACTS),
    }


@router.get("/contracts/{page_id}")
async def get_page_contract(page_id: str) -> dict:
    """Return the full page contract for a specific page."""
    try:
        contract = get_contract(page_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=(
            f"No contract registered for page_id='{page_id}'. Available: {sorted(PAGE_CONTRACTS.keys())}"
        )) from exc
    return {
        "page_id": contract.page_id,
        "title": contract.title,
        "route": contract.route,
        "roles_supported": [r.value for r in contract.roles_supported],
        "primary_groups": contract.primary_groups,
        "secondary_groups": contract.secondary_groups,
        "group_coverage": contract.group_coverage,
        "qualification": contract.qualification,
        "expectations": contract.expectations,
        "scope_of_use": contract.scope_of_use,
        "entry_criteria": contract.entry_criteria,
        "exit_criteria": contract.exit_criteria,
        "telemetry_events": contract.telemetry_events,
    }


@router.get("/health")
async def contract_health() -> dict:
    """
    Run the contract validation suite and return a health report.
    Useful for admin dashboards and CI status checks.
    """
    violations = validate_all_contracts()
    total_contracts = len(PAGE_CONTRACTS)
    total_groups = len(PROCESS_GROUPS)
    failed_contracts = len(violations)
    passed_contracts = total_contracts - failed_contracts

    return {
        "status": "pass" if failed_contracts == 0 else "fail",
        "summary": {
            "total_contracts": total_contracts,
            "passed": passed_contracts,
            "failed": failed_contracts,
            "total_groups": total_groups,
        },
        "violations": violations,
    }


def _is_help_action(page: str, action: str) -> bool:
    page_value = page.lower()
    action_value = action.lower()

    if page_value in {"tenant_help", "public_help", "welcome"}:
        return True

    help_markers = (
        "help",
        "hotline",
        "county_",
        "rent_help",
        "welcome_call_",
        "welcome_open_",
        "semptify_",
        "open_external_help_link",
        "open_internal_help_link",
    )
    return any(marker in action_value for marker in help_markers)


def _event_day(timestamp: str) -> str:
    normalized = timestamp.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return "unknown"
    return dt.date().isoformat()


@router.get("/help-telemetry-summary")
async def help_telemetry_summary(limit: int = 1000, page: Optional[str] = None) -> dict:
    """
    Aggregate help-related click telemetry from the positronic brain event history.
    Useful for admin dashboards that need day-by-day and resource-level usage trends.
    """
    if limit < 1 or limit > 5000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 5000")

    page_filter = page.lower() if page else None
    events = get_brain().get_recent_events(limit=limit)

    total_user_actions = 0
    help_events = 0
    by_day: Counter[str] = Counter()
    by_action: Counter[str] = Counter()
    by_page: Counter[str] = Counter()
    by_href: Counter[str] = Counter()

    for event in events:
        if event.get("event_type") != "user.action":
            continue

        total_user_actions += 1
        data = event.get("data") or {}
        action = str(data.get("action") or "unknown")
        page_name = str(data.get("page") or "unknown")
        href = str(data.get("href") or "")

        if page_filter and page_name.lower() != page_filter:
            continue

        if not _is_help_action(page_name, action):
            continue

        help_events += 1
        by_day[_event_day(str(event.get("timestamp") or ""))] += 1
        by_action[action] += 1
        by_page[page_name] += 1
        if href:
            by_href[href] += 1

    return {
        "status": "ok",
        "window": {
            "requested_limit": limit,
            "page_filter": page,
            "events_scanned": len(events),
            "user_actions_scanned": total_user_actions,
        },
        "summary": {
            "help_events_total": help_events,
            "active_days": len(by_day),
            "unique_actions": len(by_action),
            "unique_pages": len(by_page),
            "unique_links": len(by_href),
        },
        "by_day": [
            {"day": day, "count": count}
            for day, count in sorted(by_day.items())
        ],
        "top_actions": [
            {"action": action_name, "count": count}
            for action_name, count in by_action.most_common(25)
        ],
        "top_pages": [
            {"page": page_name, "count": count}
            for page_name, count in by_page.most_common(10)
        ],
        "top_links": [
            {"href": href_value, "count": count}
            for href_value, count in by_href.most_common(25)
        ],
    }
