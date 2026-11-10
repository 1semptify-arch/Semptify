"""Executive Administration — the nonprofit's private back office on semptify.org.

Formation roadmap (Minnesota, then federal), compliance calendar, board and
meetings, policies, the books of record, and grant readiness. Admin-only:
every route requires the TOTP-verified admin elevation cookie (or a valid
admin token for scripted access) and answers 404 otherwise.

Mounted at /admin/executive by the product manifest.
"""

from __future__ import annotations

import secrets
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_elevation import ELEVATION_COOKIE_NAME, verify_elevation_cookie
from app.core.config import get_settings
from app.core.database import get_db
from app.core.navigation import navigation
from app.core.security import get_admin_token_from_request, get_admin_token_store, get_rate_limiter
from app.core.ssot_guard import ssot_redirect
from app.core.utc import utc_now
from app.modules.executive_admin import compliance, governance, ledger
from app.modules.executive_admin.knowledge import (
    FORMATION_STEPS,
    GRANT_READINESS,
    POLICIES,
    PHASES,
    knowledge_bundle,
    sources_for,
)
from app.modules.executive_admin.models import ExecLedgerEntry, ExecRecord

router = APIRouter()

PAGE_PATH = Path(__file__).resolve().parents[2] / "templates" / "admin" / "executive_admin.html"
_CHICAGO = ZoneInfo("America/Chicago")
STEP_STATUSES = ("not_started", "in_progress", "done", "not_needed")
POLICY_STATUSES = ("not_started", "drafted", "adopted")
PROFILE_FIELDS = (
    "legal_name",
    "mn_file_number",
    "formation_date",
    "fiscal_year_end",
    "ein",
    "form_1023ez_filed_on",
    "determination_date",
    "public_charity_basis",
    "ag_registered",
    "ag_registered_on",
    "sales_tax_exempt",
    "has_employees",
    "registered_office",
    "president_name",
    "treasurer_name",
    "secretary_name",
    "bylaws_quorum",
    "articles_allow_less_than_unanimous_written_action",
    "other_assets_cents",
    "budget_approved_on",
    "mission_written",
    "fiscal_sponsor",
)


def mn_today() -> date:
    return utc_now().astimezone(_CHICAGO).date()


# ---------------------------------------------------------------------------
# Access
# ---------------------------------------------------------------------------


def _elevated_uid(request: Request) -> str | None:
    cookie = request.cookies.get(ELEVATION_COOKIE_NAME)
    payload = verify_elevation_cookie(str(cookie) if cookie else None)
    return payload["uid"] if payload else None


async def require_executive_admin(request: Request) -> str:
    """Elevation cookie (password + TOTP) or a valid admin token; 404 otherwise."""
    uid = _elevated_uid(request)
    if uid:
        return uid
    token = get_admin_token_from_request(request)
    if token:
        settings = get_settings()
        ip = request.client.host if request.client else "unknown"
        allowed, _ = get_rate_limiter().check(
            f"exec_admin:{ip}", settings.admin_rate_limit_window, settings.admin_rate_limit_max_requests
        )
        if allowed:
            admin = get_admin_token_store().validate_admin_token(token)
            if admin:
                return str(admin.get("id", "admin"))
    raise HTTPException(status_code=404, detail="Not Found")


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


async def _get_record(db: AsyncSession, record_id: str) -> ExecRecord | None:
    return await db.get(ExecRecord, record_id)


async def _put_record(db: AsyncSession, record_id: str, kind: str, data: dict) -> dict:
    row = await _get_record(db, record_id)
    if row is None:
        row = ExecRecord(id=record_id, kind=kind, data=data)
        db.add(row)
    else:
        row.data = data
        row.updated_at = utc_now()
    await db.flush()
    return {"id": row.id, **row.data}


async def _records(db: AsyncSession, kind: str) -> list[dict]:
    rows = (await db.execute(select(ExecRecord).where(ExecRecord.kind == kind))).scalars().all()
    return [{"id": r.id, **(r.data or {})} for r in rows]


async def _delete_record(db: AsyncSession, record_id: str, kind: str) -> None:
    row = await _get_record(db, record_id)
    if row is None or row.kind != kind:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    await db.flush()


async def _profile(db: AsyncSession) -> dict:
    row = await _get_record(db, "profile")
    data = dict(row.data) if row else {}
    data.setdefault("fiscal_year_end", "12-31")
    return data


def _entry_dict(row: ExecLedgerEntry) -> dict:
    return {
        "id": row.id,
        "entry_date": row.entry_date.isoformat(),
        "kind": row.kind,
        "amount_cents": row.amount_cents,
        "category": row.category,
        "functional_class": row.functional_class,
        "fund": row.fund,
        "counterparty": row.counterparty,
        "description": row.description,
        "goods_services_cents": row.goods_services_cents,
        "acknowledged_on": row.acknowledged_on.isoformat() if row.acknowledged_on else None,
        "reference": row.reference,
    }


async def _entries(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(ExecLedgerEntry).order_by(ExecLedgerEntry.entry_date))).scalars().all()
    return [_entry_dict(r) for r in rows]


async def _state(db: AsyncSession) -> dict:
    """Everything the computed views need, loaded once."""
    profile = await _profile(db)
    entries = await _entries(db)
    board = await _records(db, "board_member")
    meetings = sorted(await _records(db, "meeting"), key=lambda m: m.get("meeting_date", ""))
    filings_rows = await _records(db, "filing")
    filings = {f["obligation_id"]: f["done_on"] for f in filings_rows}
    steps = {s["step_id"]: s for s in await _records(db, "step")}
    policies = {p["policy_id"]: p for p in await _records(db, "policy")}
    deadlines = await _records(db, "deadline")
    written = await _records(db, "written_action")
    return {
        "profile": profile,
        "entries": entries,
        "board": board,
        "meetings": meetings,
        "filings": filings,
        "steps": steps,
        "policies": policies,
        "deadlines": deadlines,
        "written_actions": written,
    }


def _fy_summaries(state: dict, today: date) -> dict[str, dict]:
    profile = state["profile"]
    fye = profile.get("fiscal_year_end") or "12-31"
    other_assets = int(profile.get("other_assets_cents") or 0)
    dates = [date.fromisoformat(e["entry_date"]) for e in state["entries"]]
    if profile.get("formation_date"):
        dates.append(date.fromisoformat(profile["formation_date"]))
    dates.append(today)
    out: dict[str, dict] = {}
    fy_end = compliance.fiscal_year_end_for(min(dates), fye)
    last = compliance.fiscal_year_end_for(today, fye)
    while fy_end <= last:
        out[fy_end.isoformat()] = ledger.summarize(state["entries"], fy_end, other_assets_cents=other_assets)
        fy_end = compliance.fiscal_year_end_for(fy_end + timedelta(days=1), fye)
    return out


def _calendar(state: dict, today: date) -> list[dict]:
    held = [date.fromisoformat(m["meeting_date"]) for m in state["meetings"] if m.get("status") in ("held", "approved") and m["meeting_date"] <= today.isoformat()]
    return compliance.build_calendar(
        profile=state["profile"],
        fy_summaries=_fy_summaries(state, today),
        filings=state["filings"],
        custom_deadlines=state["deadlines"],
        last_board_meeting=max(held) if held else None,
        today=today,
    )


def _roadmap(state: dict) -> list[dict]:
    out = []
    for phase in PHASES:
        steps = []
        for s in FORMATION_STEPS:
            if s["phase"] != phase["id"]:
                continue
            saved = state["steps"].get(s["id"], {})
            steps.append(
                {
                    **{k: v for k, v in s.items() if k != "source_ids"},
                    "sources": sources_for(s["source_ids"]),
                    "status": saved.get("status", "not_started"),
                    "done_on": saved.get("done_on"),
                    "note": saved.get("note", ""),
                }
            )
        out.append({**phase, "steps": steps})
    return out


def _readiness(state: dict, today: date) -> list[dict]:
    p = state["profile"]
    steps = state["steps"]
    pol = state["policies"]
    directors = governance.active_directors(state["board"], today)
    current = ledger.summarize(state["entries"], compliance.fiscal_year_end_for(today, p.get("fiscal_year_end")))
    done = {
        "entity": bool(p.get("formation_date")),
        "ein": bool(p.get("ein")),
        "exemption": bool(p.get("determination_date") or p.get("fiscal_sponsor")),
        "board": len(directors) >= 3,
        "bylaws": pol.get("bylaws", {}).get("status") == "adopted",
        "coi": pol.get("conflict_of_interest", {}).get("status") == "adopted",
        "bank": steps.get("bank_account", {}).get("status") == "done",
        "budget": bool(p.get("budget_approved_on")),
        "books": current["entry_count"] > 0,
        "ag": bool(p.get("ag_registered")) or not current["ag_registration_required"],
        "mission": bool(p.get("mission_written")),
    }
    return [{**{k: v for k, v in g.items() if k != "source_ids"}, "sources": sources_for(g["source_ids"]), "ready": done[g["id"]]} for g in GRANT_READINESS]


def _next_action(roadmap: list[dict], calendar_items: list[dict]) -> dict:
    urgent = [c for c in calendar_items if c["status"] in ("overdue", "due_soon")]
    if urgent:
        c = urgent[0]
        return {"kind": "deadline", "title": c["title"], "detail": c.get("why", ""), "due": c["due"], "ref": c["id"]}
    for phase in roadmap:
        for s in phase["steps"]:
            if s["status"] not in ("done", "not_needed"):
                return {"kind": "step", "title": s["title"], "detail": s["how"], "due": None, "ref": s["id"]}
    upcoming = [c for c in calendar_items if c["status"] == "upcoming" and c.get("due")]
    if upcoming:
        c = upcoming[0]
        return {"kind": "deadline", "title": c["title"], "detail": c.get("why", ""), "due": c["due"], "ref": c["id"]}
    return {"kind": "none", "title": "Nothing is due. Record money as it moves.", "detail": "", "due": None, "ref": None}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ProfileUpdate(BaseModel):
    values: dict = Field(default_factory=dict)


class StepUpdate(BaseModel):
    status: str
    done_on: str | None = None
    note: str = ""


class DeadlineCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due: str
    note: str = ""


class FilingDone(BaseModel):
    done_on: str | None = None
    note: str = ""


class BoardMember(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    office: str = ""
    is_director: bool = True
    term_start: str | None = None
    term_end: str | None = None
    email: str = ""
    coi_statement_signed_on: str | None = None


class Motion(BaseModel):
    text: str
    moved_by: str | None = None
    seconded_by: str | None = None
    yes: int = 0
    no: int = 0
    abstain: int = 0
    recused: list[str] = Field(default_factory=list)


class Meeting(BaseModel):
    meeting_date: str
    kind: str = "regular"
    location: str = ""
    notice_sent_on: str | None = None
    schedule_announced: bool = False
    present: list[str] = Field(default_factory=list)
    disclosures: str = ""
    motions: list[Motion] = Field(default_factory=list)
    notes: str = ""
    next_meeting: str = ""
    status: str = "planned"
    extra_agenda: list[str] = Field(default_factory=list)


class WrittenAction(BaseModel):
    text: str = Field(min_length=1)
    action_date: str | None = None
    signed_by: list[str] = Field(default_factory=list)


class PolicyUpdate(BaseModel):
    status: str
    adopted_on: str | None = None
    location: str = ""
    next_review: str | None = None


class LedgerEntryIn(BaseModel):
    entry_date: str
    kind: str
    amount_cents: int
    category: str
    functional_class: str | None = None
    fund: str = "unrestricted"
    counterparty: str | None = None
    description: str | None = None
    goods_services_cents: int = 0
    acknowledged_on: str | None = None
    reference: str | None = None


def _check_date(value: str | None, field: str) -> None:
    if value:
        try:
            date.fromisoformat(value)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"{field} must be a date like 2026-11-08") from None


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "module": "executive_admin"}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
async def executive_page(request: Request) -> Response:
    if not _elevated_uid(request):
        try:
            await require_executive_admin(request)
        except HTTPException:
            stage = navigation.get_stage("admin_login")
            login = stage.path if stage else "/admin/login"
            return ssot_redirect(
                f"{login}?next=/admin/executive/",
                context="executive_admin page gate",
                status_code=303,
            )
    return HTMLResponse(PAGE_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Overview + knowledge
# ---------------------------------------------------------------------------


@router.get("/api/overview", dependencies=[Depends(require_executive_admin)])
async def overview(db: AsyncSession = Depends(get_db)) -> dict:
    today = mn_today()
    state = await _state(db)
    roadmap = _roadmap(state)
    cal = _calendar(state, today)
    total = sum(len(p["steps"]) for p in roadmap)
    finished = sum(1 for p in roadmap for s in p["steps"] if s["status"] in ("done", "not_needed"))
    fy_end = compliance.fiscal_year_end_for(today, state["profile"].get("fiscal_year_end"))
    summary = ledger.summarize(state["entries"], fy_end, other_assets_cents=int(state["profile"].get("other_assets_cents") or 0))
    attention = []
    overdue = [c for c in cal if c["status"] == "overdue"]
    if overdue:
        attention.append(f"{len(overdue)} filing(s) overdue.")
    acks = ledger.gifts_needing_acknowledgment(state["entries"])
    if acks:
        attention.append(f"{len(acks)} gift(s) need a written acknowledgment.")
    directors = governance.active_directors(state["board"], today)
    if len(directors) < 3:
        attention.append(f"Board has {len(directors)} director(s); Minnesota requires 3.")
    if summary["ag_registration_required"] and not state["profile"].get("ag_registered"):
        attention.append("Contributions passed $25,000 — Attorney General registration is due within 30 days.")
    return {
        "today": today.isoformat(),
        "objective": "Run Semptify as a Minnesota nonprofit corporation recognized under 501(c)(3), in good standing, ready to receive grants.",
        "where_it_stands": f"Formation {finished} of {total} steps done. Fiscal year to date: revenue {ledger.dollars(summary['total_revenue_cents'])}, expenses {ledger.dollars(summary['total_expenses_cents'])}.",
        "next_action": _next_action(roadmap, cal),
        "attention": attention,
        "formation_progress": {"done": finished, "total": total},
        "profile": state["profile"],
        "roadmap": roadmap,
        "calendar": cal,
        "ledger_summary": summary,
        "grant_readiness": _readiness(state, today),
    }


@router.get("/api/knowledge", dependencies=[Depends(require_executive_admin)])
async def knowledge() -> dict:
    return knowledge_bundle()


# ---------------------------------------------------------------------------
# Profile + formation steps
# ---------------------------------------------------------------------------


@router.get("/api/profile", dependencies=[Depends(require_executive_admin)])
async def get_profile(db: AsyncSession = Depends(get_db)) -> dict:
    return await _profile(db)


@router.put("/api/profile", dependencies=[Depends(require_executive_admin)])
async def put_profile(body: ProfileUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    unknown = set(body.values) - set(PROFILE_FIELDS)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown profile field(s): {sorted(unknown)}")
    for f in ("formation_date", "form_1023ez_filed_on", "determination_date", "ag_registered_on", "budget_approved_on"):
        _check_date(body.values.get(f), f)
    if body.values.get("fiscal_year_end"):
        try:
            compliance.parse_fye(body.values["fiscal_year_end"])
        except ValueError:
            raise HTTPException(status_code=422, detail="fiscal_year_end must look like 12-31") from None
    current = await _profile(db)
    current.update(body.values)
    return await _put_record(db, "profile", "profile", current)


@router.put("/api/steps/{step_id}", dependencies=[Depends(require_executive_admin)])
async def put_step(step_id: str, body: StepUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    if step_id not in {s["id"] for s in FORMATION_STEPS}:
        raise HTTPException(status_code=404, detail="Unknown step")
    if body.status not in STEP_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {STEP_STATUSES}")
    _check_date(body.done_on, "done_on")
    done_on = body.done_on or (mn_today().isoformat() if body.status == "done" else None)
    return await _put_record(db, f"step_{step_id}", "step", {"step_id": step_id, "status": body.status, "done_on": done_on, "note": body.note})


# ---------------------------------------------------------------------------
# Compliance calendar
# ---------------------------------------------------------------------------


@router.get("/api/calendar", dependencies=[Depends(require_executive_admin)])
async def get_calendar(db: AsyncSession = Depends(get_db)) -> dict:
    today = mn_today()
    return {"today": today.isoformat(), "items": _calendar(await _state(db), today)}


@router.post("/api/calendar/{obligation_id}/done", dependencies=[Depends(require_executive_admin)])
async def mark_filed(obligation_id: str, body: FilingDone, db: AsyncSession = Depends(get_db)) -> dict:
    _check_date(body.done_on, "done_on")
    done_on = body.done_on or mn_today().isoformat()
    return await _put_record(db, f"filing_{obligation_id}"[:64], "filing", {"obligation_id": obligation_id, "done_on": done_on, "note": body.note})


@router.post("/api/deadlines", dependencies=[Depends(require_executive_admin)])
async def add_deadline(body: DeadlineCreate, db: AsyncSession = Depends(get_db)) -> dict:
    _check_date(body.due, "due")
    return await _put_record(db, _new_id("deadline"), "deadline", body.model_dump())


@router.delete("/api/deadlines/{deadline_id}", dependencies=[Depends(require_executive_admin)])
async def delete_deadline(deadline_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    await _delete_record(db, deadline_id, "deadline")
    return {"deleted": deadline_id}


# ---------------------------------------------------------------------------
# Board, meetings, written actions
# ---------------------------------------------------------------------------


@router.get("/api/board", dependencies=[Depends(require_executive_admin)])
async def get_board(db: AsyncSession = Depends(get_db)) -> dict:
    today = mn_today()
    board = await _records(db, "board_member")
    directors = governance.active_directors(board, today)
    profile = await _profile(db)
    return {
        "members": board,
        "directors_in_office": len(directors),
        "size_ok": len(directors) >= 3,
        "quorum_needed": governance.quorum_needed(len(directors), profile.get("bylaws_quorum")),
    }


@router.post("/api/board", dependencies=[Depends(require_executive_admin)])
async def add_board_member(body: BoardMember, db: AsyncSession = Depends(get_db)) -> dict:
    for f in ("term_start", "term_end", "coi_statement_signed_on"):
        _check_date(getattr(body, f), f)
    return await _put_record(db, _new_id("member"), "board_member", body.model_dump())


@router.put("/api/board/{member_id}", dependencies=[Depends(require_executive_admin)])
async def update_board_member(member_id: str, body: BoardMember, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _get_record(db, member_id)
    if row is None or row.kind != "board_member":
        raise HTTPException(status_code=404, detail="Not found")
    for f in ("term_start", "term_end", "coi_statement_signed_on"):
        _check_date(getattr(body, f), f)
    return await _put_record(db, member_id, "board_member", body.model_dump())


@router.delete("/api/board/{member_id}", dependencies=[Depends(require_executive_admin)])
async def delete_board_member(member_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    await _delete_record(db, member_id, "board_member")
    return {"deleted": member_id}


async def _meeting_view(db: AsyncSession, meeting: dict) -> dict:
    board = await _records(db, "board_member")
    profile = await _profile(db)
    return {**meeting, "check": governance.meeting_check(meeting, board, profile.get("bylaws_quorum"))}


@router.get("/api/meetings", dependencies=[Depends(require_executive_admin)])
async def list_meetings(db: AsyncSession = Depends(get_db)) -> dict:
    meetings = sorted(await _records(db, "meeting"), key=lambda m: m.get("meeting_date", ""), reverse=True)
    return {"meetings": [await _meeting_view(db, m) for m in meetings]}


def _validate_meeting(body: Meeting) -> None:
    _check_date(body.meeting_date, "meeting_date")
    _check_date(body.notice_sent_on, "notice_sent_on")
    if body.kind not in ("organizational", "regular", "annual", "special"):
        raise HTTPException(status_code=422, detail="kind must be organizational, regular, annual, or special")
    if body.status not in ("planned", "held", "approved"):
        raise HTTPException(status_code=422, detail="status must be planned, held, or approved")


@router.post("/api/meetings", dependencies=[Depends(require_executive_admin)])
async def create_meeting(body: Meeting, db: AsyncSession = Depends(get_db)) -> dict:
    _validate_meeting(body)
    saved = await _put_record(db, _new_id("meeting"), "meeting", body.model_dump())
    return await _meeting_view(db, saved)


@router.put("/api/meetings/{meeting_id}", dependencies=[Depends(require_executive_admin)])
async def update_meeting(meeting_id: str, body: Meeting, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _get_record(db, meeting_id)
    if row is None or row.kind != "meeting":
        raise HTTPException(status_code=404, detail="Not found")
    _validate_meeting(body)
    saved = await _put_record(db, meeting_id, "meeting", body.model_dump())
    return await _meeting_view(db, saved)


async def _meeting_or_404(db: AsyncSession, meeting_id: str) -> dict:
    row = await _get_record(db, meeting_id)
    if row is None or row.kind != "meeting":
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": row.id, **row.data}


@router.get("/api/meetings/{meeting_id}/agenda", dependencies=[Depends(require_executive_admin)])
async def meeting_agenda(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    meeting = await _meeting_or_404(db, meeting_id)
    today = mn_today()
    state = await _state(db)
    fy_end = compliance.fiscal_year_end_for(today, state["profile"].get("fiscal_year_end"))
    summary = ledger.summarize(state["entries"], fy_end)
    return {"meeting_id": meeting_id, "agenda": governance.agenda_for(meeting, summary, _calendar(state, today))}


@router.get("/api/meetings/{meeting_id}/minutes", dependencies=[Depends(require_executive_admin)])
async def meeting_minutes(meeting_id: str, db: AsyncSession = Depends(get_db)) -> PlainTextResponse:
    meeting = await _meeting_or_404(db, meeting_id)
    board = await _records(db, "board_member")
    profile = await _profile(db)
    check = governance.meeting_check(meeting, board, profile.get("bylaws_quorum"))
    return PlainTextResponse(governance.minutes_draft(meeting, board, check, profile.get("legal_name", "")))


@router.get("/api/written-actions", dependencies=[Depends(require_executive_admin)])
async def list_written_actions(db: AsyncSession = Depends(get_db)) -> dict:
    board = await _records(db, "board_member")
    profile = await _profile(db)
    allow = bool(profile.get("articles_allow_less_than_unanimous_written_action"))
    actions = await _records(db, "written_action")
    return {"actions": [{**a, "check": governance.written_action_check(a, board, allow)} for a in actions]}


@router.post("/api/written-actions", dependencies=[Depends(require_executive_admin)])
async def create_written_action(body: WrittenAction, db: AsyncSession = Depends(get_db)) -> dict:
    _check_date(body.action_date, "action_date")
    return await _put_record(db, _new_id("action"), "written_action", body.model_dump())


@router.put("/api/written-actions/{action_id}", dependencies=[Depends(require_executive_admin)])
async def update_written_action(action_id: str, body: WrittenAction, db: AsyncSession = Depends(get_db)) -> dict:
    row = await _get_record(db, action_id)
    if row is None or row.kind != "written_action":
        raise HTTPException(status_code=404, detail="Not found")
    _check_date(body.action_date, "action_date")
    return await _put_record(db, action_id, "written_action", body.model_dump())


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


@router.put("/api/policies/{policy_id}", dependencies=[Depends(require_executive_admin)])
async def put_policy(policy_id: str, body: PolicyUpdate, db: AsyncSession = Depends(get_db)) -> dict:
    if policy_id not in {p["id"] for p in POLICIES}:
        raise HTTPException(status_code=404, detail="Unknown policy")
    if body.status not in POLICY_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {POLICY_STATUSES}")
    _check_date(body.adopted_on, "adopted_on")
    _check_date(body.next_review, "next_review")
    return await _put_record(db, f"policy_{policy_id}", "policy", {"policy_id": policy_id, **body.model_dump()})


@router.get("/api/policies", dependencies=[Depends(require_executive_admin)])
async def get_policies(db: AsyncSession = Depends(get_db)) -> dict:
    saved = {p["policy_id"]: p for p in await _records(db, "policy")}
    return {
        "policies": [
            {
                **{k: v for k, v in p.items() if k != "source_ids"},
                "sources": sources_for(p["source_ids"]),
                "status": saved.get(p["id"], {}).get("status", "not_started"),
                "adopted_on": saved.get(p["id"], {}).get("adopted_on"),
                "location": saved.get(p["id"], {}).get("location", ""),
            }
            for p in POLICIES
        ]
    }


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------


def _entry_problems(body: LedgerEntryIn) -> None:
    data = body.model_dump()
    problems = ledger.validate_entry(data)
    if body.acknowledged_on:
        try:
            date.fromisoformat(body.acknowledged_on)
        except ValueError:
            problems.append("Acknowledged-on must be a date.")
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))


def _apply_entry(row: ExecLedgerEntry, body: LedgerEntryIn) -> None:
    row.entry_date = date.fromisoformat(body.entry_date)
    row.kind = body.kind
    row.amount_cents = body.amount_cents
    row.category = body.category
    row.functional_class = body.functional_class if body.kind == "expense" else None
    row.fund = (body.fund or "unrestricted").strip() or "unrestricted"
    row.counterparty = body.counterparty
    row.description = body.description
    row.goods_services_cents = body.goods_services_cents or 0
    row.acknowledged_on = date.fromisoformat(body.acknowledged_on) if body.acknowledged_on else None
    row.reference = body.reference
    row.updated_at = utc_now()


@router.get("/api/ledger", dependencies=[Depends(require_executive_admin)])
async def list_ledger(db: AsyncSession = Depends(get_db)) -> dict:
    entries = await _entries(db)
    return {"entries": list(reversed(entries)), "needs_acknowledgment": ledger.gifts_needing_acknowledgment(entries)}


@router.post("/api/ledger", dependencies=[Depends(require_executive_admin)])
async def add_ledger_entry(body: LedgerEntryIn, db: AsyncSession = Depends(get_db)) -> dict:
    _entry_problems(body)
    row = ExecLedgerEntry(id=_new_id("led"))
    _apply_entry(row, body)
    db.add(row)
    await db.flush()
    return _entry_dict(row)


@router.put("/api/ledger/{entry_id}", dependencies=[Depends(require_executive_admin)])
async def update_ledger_entry(entry_id: str, body: LedgerEntryIn, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(ExecLedgerEntry, entry_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    _entry_problems(body)
    _apply_entry(row, body)
    await db.flush()
    return _entry_dict(row)


@router.delete("/api/ledger/{entry_id}", dependencies=[Depends(require_executive_admin)])
async def delete_ledger_entry(entry_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    row = await db.get(ExecLedgerEntry, entry_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    await db.flush()
    return {"deleted": entry_id}


@router.get("/api/ledger/summary", dependencies=[Depends(require_executive_admin)])
async def ledger_summary(fiscal_year_end: str | None = None, db: AsyncSession = Depends(get_db)) -> dict:
    profile = await _profile(db)
    if fiscal_year_end:
        _check_date(fiscal_year_end, "fiscal_year_end")
        fy_end = date.fromisoformat(fiscal_year_end)
    else:
        fy_end = compliance.fiscal_year_end_for(mn_today(), profile.get("fiscal_year_end"))
    entries = await _entries(db)
    years = {}
    if entries:
        first = compliance.fiscal_year_end_for(date.fromisoformat(entries[0]["entry_date"]), profile.get("fiscal_year_end"))
        cursor = first
        while cursor <= fy_end:
            years[cursor.isoformat()] = ledger.summarize(entries, cursor)["gross_receipts_cents"]
            cursor = compliance.fiscal_year_end_for(cursor + timedelta(days=1), profile.get("fiscal_year_end"))
    summary = ledger.summarize(entries, fy_end, other_assets_cents=int(profile.get("other_assets_cents") or 0))
    return {
        **summary,
        "receipts_by_fiscal_year": years,
        "form_1023ez_check": compliance.ez_eligible(list(years.values()), summary["total_assets_cents"]),
    }


@router.get("/api/ledger/export.csv", dependencies=[Depends(require_executive_admin)])
async def export_ledger(db: AsyncSession = Depends(get_db)) -> Response:
    body = ledger.to_csv(await _entries(db))
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="semptify-books-{mn_today().isoformat()}.csv"'},
    )


@router.get("/api/ledger/{entry_id}/acknowledgment", dependencies=[Depends(require_executive_admin)])
async def acknowledgment(entry_id: str, db: AsyncSession = Depends(get_db)) -> PlainTextResponse:
    row = await db.get(ExecLedgerEntry, entry_id)
    if row is None or row.kind != "income":
        raise HTTPException(status_code=404, detail="Not found")
    return PlainTextResponse(ledger.acknowledgment_letter(_entry_dict(row), await _profile(db)))


# ---------------------------------------------------------------------------
# Grant readiness
# ---------------------------------------------------------------------------


@router.get("/api/grant-readiness", dependencies=[Depends(require_executive_admin)])
async def grant_readiness(db: AsyncSession = Depends(get_db)) -> dict:
    items = _readiness(await _state(db), mn_today())
    return {
        "items": items,
        "ready": sum(1 for i in items if i["ready"]),
        "total": len(items),
        "pipeline_note": "Track individual grant applications in Funding Forge; record awarded money here in the books, in its own fund if restricted.",
    }
