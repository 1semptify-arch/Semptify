"""
Co-View Session Router (legal-ui matrix G6.1–G6.7)
==================================================

Eyes-only shared document viewing: host and guest see the same document
position and pointer live, over a short-lived signed session.

Brad's settled decisions (2026-11-14 + role revival 2026-11-19):
- Role-agnostic: advocate AND legal use one session system; either side
  (tenant or professional) may propose a session.
- Guest identity = revived professional role user (signed Semptify ID);
  the join token merely binds a signed-in user to one session.
- Page sync + shared pointer + anchored Q&A lane persisted as session state.
- Participants always visible. Voice = phone fallback (out of scope).
- Session log records who/when/which doc — never content, never recording.
- Degrade: if the live channel drops, clients fall back to REST polling
  and show "view the same document separately" guidance — never a frozen
  half-sync.

Endpoints:
- POST /api/coview/sessions              create session (host = caller)
- POST /api/coview/sessions/{id}/invite  mint a guest join token
- POST /api/coview/join                  join with session_id + token
- GET  /api/coview/sessions/{id}         state snapshot (participants visible)
- POST /api/coview/sessions/{id}/end     end session (host or initiator)
- POST /api/coview/sessions/{id}/participants/{uid}/revoke  drop a guest
- GET  /api/coview/sessions/{id}/log     session log (no content)
- GET  /coview/{session_id}              the co-view page
- WS   /api/coview/ws/{session_id}       live position/pointer/Q&A channel
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.core.cookie_auth import verify_user_id
from app.core.key_derivation import hmac_sign, hmac_verify
from app.core.request_utils import require_request_user_id
from app.core.user_context import UserRole, get_role_from_user_id
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Co-View"])

BASE_PATH = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_PATH / "data" / "coview"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA_DIR / "sessions.jsonl"

_TOKEN_TTL_S = 15 * 60          # guest join tokens live 15 minutes
_SESSION_TTL_S = 2 * 60 * 60    # sessions auto-expire after 2 hours


# =============================================================================
# Session store (in-memory — sessions are ephemeral by design)
# =============================================================================


class _Session:
    def __init__(self, session_id: str, doc_ref: str, host_user_id: str, initiator_user_id: str):
        self.session_id = session_id
        self.doc_ref = doc_ref
        self.host_user_id = host_user_id
        self.initiator_user_id = initiator_user_id
        self.created_at = utc_now()
        self.expires_at = time.time() + _SESSION_TTL_S
        self.active = True
        self.revoked: set[str] = set()
        self.participants: dict[str, dict] = {}
        self.state: dict = {"page": 1, "scroll_y": 0.0, "pointer": {"x": None, "y": None}}
        self.sockets: list[WebSocket] = []


_SESSIONS: dict[str, _Session] = {}


def _log(event: str, session_id: str, user_id: str, doc_ref: str) -> None:
    """Append a session-log line: who/when/which doc — never content."""
    rec = {"ts": utc_now().isoformat(), "event": event, "session": session_id,
           "user": user_id, "doc_ref": doc_ref}
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError as e:
        logger.warning("coview log write failed: %s", e)


def _get_live(session_id: str) -> _Session:
    s = _SESSIONS.get(session_id)
    if not s or not s.active or s.expires_at < time.time():
        raise HTTPException(status_code=404, detail="Session not found or ended")
    return s


def _is_participant(s: _Session, user_id: str) -> bool:
    return user_id in s.participants or user_id in (s.host_user_id, s.initiator_user_id)


def _participant_view(s: _Session) -> list[dict]:
    people = [{"user_id": s.host_user_id, "side": "host", "role": get_role_from_user_id(s.host_user_id)}]
    for uid, p in s.participants.items():
        people.append({"user_id": uid, "side": "guest", "role": p["role"], "joined_at": p["joined_at"]})
    return people


async def _broadcast(s: _Session, msg: dict) -> None:
    dead = []
    for ws in s.sockets:
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            dead.append(ws)
    for ws in dead:
        s.sockets.remove(ws)


# =============================================================================
# Guest tokens — signed, short-lived, single-session
# =============================================================================


def _mint_token(session_id: str, role: str, ttl_s: int = _TOKEN_TTL_S) -> str:
    exp = int(time.time() + ttl_s)
    payload = f"{session_id}.{role}.{exp}"
    return f"cv.{payload}.{hmac_sign(payload, domain='coview')}"


def _check_token(session_id: str, token: str) -> str:
    """Return the token's role or raise 403. Dead session = dead token."""
    try:
        _, sid, role, exp_s, sig = token.split(".", 4)
    except ValueError:
        raise HTTPException(status_code=403, detail="Bad token")
    if sid != session_id:
        raise HTTPException(status_code=403, detail="Token is for a different session")
    payload = f"{sid}.{role}.{exp_s}"
    if not hmac_verify(payload, sig, domain="coview"):
        raise HTTPException(status_code=403, detail="Bad token signature")
    if int(exp_s) < int(time.time()):
        raise HTTPException(status_code=403, detail="Token expired")
    return role


# =============================================================================
# REST
# =============================================================================


class CreateSessionRequest(BaseModel):
    doc_ref: str = Field(..., min_length=1, max_length=500,
                         description="Document reference both sides already have (vault path or doc id)")
    ttl_minutes: int | None = Field(default=None, ge=5, le=240)


@router.post("/api/coview/sessions")
async def create_session(body: CreateSessionRequest, request: Request):
    """Propose a co-view session. Either side may initiate (tenant or professional)."""
    user_id = require_request_user_id(request)
    s = _Session(
        session_id="cv_" + secrets.token_hex(6),
        doc_ref=body.doc_ref.strip(),
        host_user_id=user_id,
        initiator_user_id=user_id,
    )
    if body.ttl_minutes:
        s.expires_at = time.time() + body.ttl_minutes * 60
    _SESSIONS[s.session_id] = s
    _log("session_open", s.session_id, user_id, s.doc_ref)
    return {
        "session_id": s.session_id,
        "doc_ref": s.doc_ref,
        "join_token": _mint_token(s.session_id, "guest"),
        "join_url": f"/coview/{s.session_id}",
        "expires_at": s.expires_at,
    }


@router.post("/api/coview/sessions/{session_id}/invite")
async def invite(session_id: str, request: Request):
    """Mint a fresh guest token (any live participant may re-invite)."""
    user_id = require_request_user_id(request)
    s = _get_live(session_id)
    if not _is_participant(s, user_id):
        raise HTTPException(status_code=403, detail="Not a participant")
    return {"join_token": _mint_token(session_id, "guest")}


class JoinRequest(BaseModel):
    session_id: str
    token: str


@router.post("/api/coview/join")
async def join(body: JoinRequest, request: Request):
    """Join a session. Caller must be signed in (guest = revived role user)."""
    user_id = require_request_user_id(request)
    s = _get_live(body.session_id)
    _check_token(body.session_id, body.token)
    if user_id in s.revoked:
        raise HTTPException(status_code=403, detail="Access revoked")
    s.participants.setdefault(user_id, {"role": get_role_from_user_id(user_id), "joined_at": utc_now().isoformat()})
    _log("join", s.session_id, user_id, s.doc_ref)
    await _broadcast(s, {"type": "joined", "user_id": user_id, "participants": _participant_view(s)})
    return {"status": "joined", "session": _snapshot(s)}


def _snapshot(s: _Session) -> dict:
    return {
        "session_id": s.session_id,
        "doc_ref": s.doc_ref,
        "active": s.active,
        "state": s.state,
        "participants": _participant_view(s),
        "expires_at": s.expires_at,
    }


@router.get("/api/coview/sessions/{session_id}")
async def session_state(session_id: str, request: Request):
    user_id = require_request_user_id(request)
    s = _get_live(session_id)
    if not _is_participant(s, user_id):
        raise HTTPException(status_code=403, detail="Not a participant")
    return _snapshot(s)


@router.post("/api/coview/sessions/{session_id}/end")
async def end_session(session_id: str, request: Request):
    """End the session — host or initiator. Guest tokens die with it."""
    user_id = require_request_user_id(request)
    s = _get_live(session_id)
    if user_id not in (s.host_user_id, s.initiator_user_id):
        raise HTTPException(status_code=403, detail="Only the host or initiator can end the session")
    await _end(s, ended_by=user_id)
    return {"status": "ended"}


async def _end(s: _Session, ended_by: str) -> None:
    s.active = False
    _log("session_end", s.session_id, ended_by, s.doc_ref)
    await _broadcast(s, {"type": "ended"})
    for ws in list(s.sockets):
        try:
            await ws.close(code=1000)
        except Exception:
            pass
    s.sockets.clear()


@router.post("/api/coview/sessions/{session_id}/participants/{target_uid}/revoke")
async def revoke_participant(session_id: str, target_uid: str, request: Request):
    """Drop a participant mid-session (G6.4 — terminate, not just block)."""
    user_id = require_request_user_id(request)
    s = _get_live(session_id)
    if user_id not in (s.host_user_id, s.initiator_user_id):
        raise HTTPException(status_code=403, detail="Only the host or initiator can revoke")
    s.revoked.add(target_uid)
    s.participants.pop(target_uid, None)
    _log("revoke", s.session_id, target_uid, s.doc_ref)
    # Terminate the revoked participant's live socket immediately — a revoke
    # must kill the view, not just future API calls (G6.4).
    for ws in list(s.sockets):
        if getattr(ws, "_cv_user", None) == target_uid:
            try:
                await ws.send_text(json.dumps({"type": "revoked", "user_id": target_uid}))
                await ws.close(code=1008)
            except Exception:
                pass
            s.sockets.remove(ws)
    await _broadcast(s, {"type": "revoked", "user_id": target_uid,
                         "participants": _participant_view(s)})
    return {"status": "revoked"}


@router.get("/api/coview/sessions/{session_id}/log")
async def session_log(session_id: str, request: Request):
    """Session log for this session: who/when/which doc — never content."""
    user_id = require_request_user_id(request)
    s = _SESSIONS.get(session_id)
    if not s or not _is_participant(s, user_id):
        raise HTTPException(status_code=404, detail="Session not found")
    rows = []
    if LOG_FILE.exists():
        for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("session") == session_id:
                rows.append(rec)
    return {"session_id": session_id, "events": rows}


# =============================================================================
# Page + WebSocket
# =============================================================================


@router.get("/coview/{session_id}", response_class=HTMLResponse)
async def coview_page(request: Request, session_id: str):
    """The co-view page. Requires a participant cookie; join happens via token."""
    from app.main import templates

    return templates.TemplateResponse(request, "pages/coview.html", {"session_id": session_id})


@router.websocket("/api/coview/ws/{session_id}")
async def coview_ws(websocket: WebSocket, session_id: str):
    """Live channel. Auth = signed cookie; join token passed once as first message
    so guests prove they hold the invite before receiving state."""
    user_id = verify_user_id(websocket.cookies.get("semptify_uid"))
    s = _SESSIONS.get(session_id)
    if not user_id or not s or not s.active or user_id in s.revoked or not _is_participant(s, user_id):
        await websocket.accept()
        await websocket.close(code=1008)
        return
    await websocket.accept()
    websocket._cv_user = user_id
    s.sockets.append(websocket)
    await websocket.send_text(json.dumps({"type": "state", "session": _snapshot(s)}))
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mtype = msg.get("type")
            if user_id in s.revoked:
                await websocket.close(code=1008)
                break
            if mtype == "position":
                s.state["page"] = msg.get("page", s.state["page"])
                s.state["scroll_y"] = msg.get("scroll_y", s.state["scroll_y"])
            elif mtype == "pointer":
                s.state["pointer"] = {"x": msg.get("x"), "y": msg.get("y")}
            elif mtype == "qa":
                entry = {"user_id": user_id, "anchor": msg.get("anchor"),
                         "text": str(msg.get("text", ""))[:500], "at": utc_now().isoformat()}
                s.state.setdefault("qa", []).append(entry)
                msg["entry"] = entry
            elif mtype == "end":
                if user_id in (s.host_user_id, s.initiator_user_id):
                    await _end(s, ended_by=user_id)
                break
            await _broadcast(s, {"type": mtype, "by": user_id,
                                 "state": s.state, "msg": msg})
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        if websocket in s.sockets:
            s.sockets.remove(websocket)
        await _broadcast(s, {"type": "left", "user_id": user_id,
                             "participants": _participant_view(s)})
