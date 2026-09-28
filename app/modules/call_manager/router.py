"""Call Manager — proactive outreach desk.

ACT!-style call workflow for the tenant running their own case:
pick a contact -> run the interactive script -> tap the outcome ->
the module writes the follow-up into calendar, journal, and timeline
in one save.

Built tap-first: outcomes are buttons, script questions are checkboxes
with short fact fields, and every completed call lands on the timeline.
"""

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_user
from app.core.user_context import UserContext
from app.core.utc import utc_now
from app.models.models import CalendarEvent, JournalEntry, TimelineEvent
from app.modules.call_manager.models import CallLog
from app.modules.call_manager.scripts import SCRIPTS

router = APIRouter(prefix="/api/call-manager", tags=["Call Manager"])

OUTCOMES = (
    "no_answer",
    "voicemail",
    "spoke",
    "callback_scheduled",
    "accepted",
    "declined",
    "info_only",
    "refused",
)

OUTCOME_LABELS = {
    "no_answer": "No answer",
    "voicemail": "Left voicemail",
    "spoke": "Spoke with them",
    "callback_scheduled": "Call back later",
    "accepted": "Will take the case",
    "declined": "Declined",
    "info_only": "Got information",
    "refused": "Refused to talk",
}


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class KeyFact(BaseModel):
    label: str
    value: str


class CallLogCreate(BaseModel):
    contact_name: str = Field(..., max_length=255)
    contact_id: str | None = None
    contact_phone: str | None = None
    contact_role: str | None = None
    script_key: str | None = None
    direction: str = Field("outbound", pattern="^(outbound|inbound)$")
    outcome: str
    duration_seconds: int = 0
    summary: str | None = None
    key_facts: list[KeyFact] = Field(default_factory=list)
    follow_up_days: int | None = Field(None, ge=0, le=365)
    follow_up_note: str | None = Field(None, max_length=255)


# ---------------------------------------------------------------------------
# Scripts
# ---------------------------------------------------------------------------


@router.get("/scripts")
async def list_scripts(user: UserContext = Depends(require_user)):
    return {
        "scripts": [
            {"key": s["key"], "title": s["title"], "purpose": s["purpose"]}
            for s in SCRIPTS.values()
        ]
    }


@router.get("/scripts/{key}")
async def get_script(key: str, user: UserContext = Depends(require_user)):
    script = SCRIPTS.get(key)
    if not script:
        raise HTTPException(404, f"Unknown script '{key}'")
    return script


# ---------------------------------------------------------------------------
# Calls
# ---------------------------------------------------------------------------


@router.post("/calls", status_code=201)
async def log_call(
    body: CallLogCreate,
    user: UserContext = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    if body.outcome not in OUTCOMES:
        raise HTTPException(422, f"outcome must be one of {OUTCOMES}")

    uid = user.get_effective_user_id()
    now = utc_now()
    follow_up_at = (
        (now + timedelta(days=body.follow_up_days)).replace(hour=9, minute=0, second=0, microsecond=0)
        if body.follow_up_days is not None
        else None
    )

    call = CallLog(
        id=_new_id("call"),
        user_id=uid,
        contact_id=body.contact_id,
        contact_name=body.contact_name,
        contact_phone=body.contact_phone,
        contact_role=body.contact_role,
        script_key=body.script_key,
        direction=body.direction,
        outcome=body.outcome,
        duration_seconds=body.duration_seconds,
        summary=body.summary,
        key_facts=[f.model_dump() for f in body.key_facts] or None,
        follow_up_at=follow_up_at,
        follow_up_note=body.follow_up_note,
        created_at=now,
    )
    db.add(call)

    # One save lands the call everywhere: journal + timeline always,
    # calendar gets the follow-up commitment when one was set.
    facts_text = "; ".join(f"{f.label}: {f.value}" for f in body.key_facts if f.value)
    content = body.summary or ""
    if facts_text:
        content = f"{content}\n\nCaptured: {facts_text}".strip()

    db.add(
        JournalEntry(
            id=_new_id("jrnl"),
            user_id=uid,
            entry_type="conversation",
            title=f"Call — {body.contact_name}",
            content=content or None,
            occurred_at=now,
            is_urgent=False,
            involved_party=body.contact_name,
            tags=f"call,{body.outcome}",
            source="call_manager",
            created_at=now,
            updated_at=now,
        )
    )
    db.add(
        TimelineEvent(
            id=_new_id("tl"),
            user_id=uid,
            event_type="communication",
            title=f"Call: {body.contact_name} — {OUTCOME_LABELS.get(body.outcome, body.outcome)}",
            description=content or None,
            event_date=now,
            who_involved=body.contact_name,
            urgency="normal",
            is_deadline=False,
            is_evidence=False,
            created_at=now,
        )
    )
    if follow_up_at is not None:
        db.add(
            CalendarEvent(
                id=_new_id("cal"),
                user_id=uid,
                title=f"Call back: {body.contact_name}",
                description=body.follow_up_note
                or f"Follow-up from {OUTCOME_LABELS.get(body.outcome, body.outcome)} call",
                start_datetime=follow_up_at,
                all_day=True,
                event_type="reminder",
                is_critical=False,
                reminder_days=0,
                source="call_manager",
                linked_record_id=call.id,
                created_at=now,
            )
        )

    await db.commit()
    return {"id": call.id, "follow_up_at": follow_up_at, "outcome": call.outcome}


@router.get("/calls")
async def list_calls(
    contact_id: str | None = None,
    outcome: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    user: UserContext = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    uid = user.get_effective_user_id()
    stmt = select(CallLog).where(CallLog.user_id == uid)
    if contact_id:
        stmt = stmt.where(CallLog.contact_id == contact_id)
    if outcome:
        stmt = stmt.where(CallLog.outcome == outcome)
    stmt = stmt.order_by(CallLog.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "calls": [
            {
                "id": c.id,
                "contact_id": c.contact_id,
                "contact_name": c.contact_name,
                "contact_phone": c.contact_phone,
                "contact_role": c.contact_role,
                "script_key": c.script_key,
                "direction": c.direction,
                "outcome": c.outcome,
                "summary": c.summary,
                "key_facts": c.key_facts,
                "follow_up_at": c.follow_up_at,
                "follow_up_note": c.follow_up_note,
                "created_at": c.created_at,
            }
            for c in rows
        ],
        "total": len(rows),
    }


@router.get("/follow-ups")
async def follow_ups(
    user: UserContext = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    uid = user.get_effective_user_id()
    rows = (
        (
            await db.execute(
                select(CallLog)
                .where(CallLog.user_id == uid, CallLog.follow_up_at.isnot(None))
                .order_by(CallLog.follow_up_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "follow_ups": [
            {
                "call_id": c.id,
                "contact_name": c.contact_name,
                "contact_phone": c.contact_phone,
                "follow_up_at": c.follow_up_at,
                "follow_up_note": c.follow_up_note,
                "last_outcome": c.outcome,
            }
            for c in rows
        ]
    }


# ---------------------------------------------------------------------------
# Desk page — the tap-first call desk UI
# ---------------------------------------------------------------------------


@router.get("/desk", response_class=HTMLResponse)
async def desk_page():
    return HTMLResponse(_DESK_HTML)


_DESK_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Call Desk</title>
<style>
:root{--pri:#3a4f66;--acc:#8b0000;--bg:#f7f6f2;--zone:#efeee8;--line:#ddd9ce;--ink:#24231f}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:var(--bg);color:var(--ink)}
.desk{display:grid;grid-template-columns:280px 1fr 300px;min-height:100vh}
.col{padding:16px;overflow-y:auto;max-height:100vh}
.queue{background:var(--zone);border-right:1px solid var(--line)}
.rail{background:var(--zone);border-left:1px solid var(--line)}
h1{font-size:1.05rem;margin:0 0 4px}
h2{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:#6a675e;margin:18px 0 8px}
.hint{font-size:.75rem;color:#6a675e;margin-bottom:10px}
.contact{display:block;width:100%;text-align:left;background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:8px;cursor:pointer;font-size:.92rem}
.contact:hover{border-color:var(--acc)}
.contact.on{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc)}
.contact .ph{display:block;font-size:.78rem;color:#6a675e;margin-top:2px}
.contact .role{font-size:.66rem;color:var(--acc);text-transform:uppercase;letter-spacing:.05em}
.duebox{background:#fdf0f0;border:1px solid #e2b6b6;border-radius:10px;padding:10px;margin-bottom:8px;font-size:.82rem;cursor:pointer}
.duebox:hover{border-color:var(--acc)}
.say{background:#fbf6e9;border-left:4px solid #c9a227;padding:12px 14px;border-radius:8px;font-size:1.02rem;line-height:1.55;margin:10px 0}
.q{display:flex;gap:10px;align-items:flex-start;background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:8px}
.q input[type=checkbox]{margin-top:3px;transform:scale(1.3)}
.q label{flex:2;font-size:.88rem;line-height:1.4}
.q input[type=text]{flex:1.4;border:none;border-bottom:1px dashed #b9b4a6;font-size:.85rem;padding:2px;background:transparent}
.outcomes{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0}
.outcome{padding:14px 4px;border:2px solid var(--line);border-radius:12px;background:#fff;cursor:pointer;font-size:.82rem;text-align:center}
.outcome.sel{border-color:var(--acc);background:#fdf0f0;font-weight:600}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.chip{padding:10px 18px;border-radius:20px;border:1px solid var(--line);background:#fff;cursor:pointer;font-size:.85rem}
.chip.sel{background:var(--acc);color:#fff;border-color:var(--acc)}
textarea{width:100%;border:1px solid var(--line);border-radius:8px;padding:10px;font-size:.9rem;min-height:52px;font-family:inherit}
.save{width:100%;padding:16px;border:none;border-radius:12px;background:var(--acc);color:#fff;font-size:1.02rem;cursor:pointer;margin-top:12px}
.save:disabled{background:#a9a397;cursor:default}
.saved{background:#e8f3ea;border:1px solid #9ec9a8;border-radius:8px;padding:10px;margin-top:10px;font-size:.85rem}
.callrow{font-size:.78rem;border-bottom:1px solid var(--line);padding:8px 0}
.callrow b{display:block;font-size:.82rem}
.callrow .facts{color:#6a675e;margin-top:3px}
.pick{border:1px dashed var(--line);border-radius:10px;padding:24px;text-align:center;color:#6a675e;font-size:.9rem}
@media(max-width:900px){.desk{grid-template-columns:1fr}.col{max-height:none}}
</style></head>
<body>
<div class="desk">
  <div class="col queue">
    <h1>Call Desk</h1>
    <div class="hint">Tap a name. Script loads. Tap the outcome. Done.</div>
    <h2>Follow-ups due</h2><div id="dues"></div>
    <h2>Who to call</h2><div id="contacts"></div>
  </div>
  <div class="col" id="center">
    <div class="pick" id="empty">Pick someone on the left — their name, number, and a script for the call type will load here.</div>
    <div id="work" style="display:none">
      <div id="whom"></div>
      <h2>Script</h2>
      <select id="scriptsel" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font-size:.9rem;margin-bottom:8px"></select>
      <div id="script"></div>
      <h2>How did it go?</h2>
      <div class="outcomes" id="outcomes"></div>
      <h2>Follow up</h2>
      <div class="chips" id="chips"></div>
      <textarea id="note" placeholder="One line about the call (optional — the checked answers above are already saved)"></textarea>
      <button class="save" id="save" disabled>Save call</button>
      <div id="savedmsg"></div>
    </div>
  </div>
  <div class="col rail">
    <h2 id="railname">Recent calls</h2>
    <div id="history"><div class="hint">Calls for whoever you pick show here.</div></div>
  </div>
</div>
<script>
let me=null, contacts=[], calls=[], sel=null, scriptData=null;
const oc={no_answer:'No answer',voicemail:'Left voicemail',spoke:'Spoke',callback_scheduled:'Call back later',accepted:'Took the case',declined:'Declined',info_only:'Got info',refused:'Refused'};
const roleScript={attorney:'attorney_intake',legal:'attorney_intake',agency:'agency_call',court:'court_clerk',clerk:'court_clerk'};

async function load(){
  const [c,f,cl]=await Promise.all([
    fetch('/api/contacts/').then(r=>r.json()).catch(()=>({contacts:[]})),
    fetch('/api/call-manager/follow-ups').then(r=>r.json()).catch(()=>({follow_ups:[]})),
    fetch('/api/call-manager/calls?limit=50').then(r=>r.json()).catch(()=>({calls:[]})),
  ]);
  contacts=c.contacts||[]; calls=cl.calls||[];
  renderDues(f.follow_ups||[]); renderContacts();
}
function renderDues(dues){
  const el=document.getElementById('dues');
  el.innerHTML=dues.length?dues.map(d=>{
    const when=(d.follow_up_at||'').slice(0,10);
    return `<div class="duebox" onclick="pickName('${(d.contact_name||'').replace(/'/g,"\\'")}')">
      <b>${d.contact_name}</b> — due ${when}<br>${d.follow_up_note||'follow-up'} <span style="color:#8b0000">(${d.last_outcome})</span></div>`;
  }).join(''):'<div class="hint">Nothing scheduled.</div>';
}
function renderContacts(){
  const el=document.getElementById('contacts');
  el.innerHTML=contacts.map((c,i)=>`
    <button class="contact" id="ct${i}" onclick="pick(${i})">
      <span class="role">${c.contact_type||''}${c.role?' · '+c.role:''}</span>
      ${c.name}
      <span class="ph">${c.phone||'no number'}${c.organization?' · '+c.organization:''}</span>
    </button>`).join('');
}
function pickName(n){const i=contacts.findIndex(c=>c.name===n); if(i>=0)pick(i);}
async function pick(i){
  sel=contacts[i];
  document.querySelectorAll('.contact').forEach(e=>e.classList.remove('on'));
  document.getElementById('ct'+i).classList.add('on');
  document.getElementById('empty').style.display='none';
  document.getElementById('work').style.display='block';
  document.getElementById('whom').innerHTML=`<h1 style="margin-bottom:2px">${sel.name}</h1>
    <div class="hint">${sel.phone||''}${sel.organization?' · '+sel.organization:''}</div>`;
  // script picker
  const ss=await fetch('/api/call-manager/scripts').then(r=>r.json());
  const dflt=roleScript[(sel.contact_type||'').toLowerCase()]||'attorney_intake';
  document.getElementById('scriptsel').innerHTML=ss.scripts.map(s=>
    `<option value="${s.key}" ${s.key===dflt?'selected':''}>${s.title}</option>`).join('');
  loadScript(dflt);
  // history rail
  document.getElementById('railname').textContent='Calls: '+sel.name;
  const mine=calls.filter(c=>c.contact_name===sel.name);
  document.getElementById('history').innerHTML=mine.length?mine.map(c=>`
    <div class="callrow"><b>${oc[c.outcome]||c.outcome}</b>${(c.created_at||'').slice(0,10)}
    ${c.key_facts?'<div class="facts">'+c.key_facts.map(f=>f.label+': '+f.value).join('<br>')+'</div>':''}
    ${c.follow_up_at?'<div class="facts">Follow-up '+(c.follow_up_at||'').slice(0,10)+'</div>':''}</div>`).join('')
    :'<div class="hint">No calls logged yet.</div>';
}
async function loadScript(key){
  scriptData=await fetch('/api/call-manager/scripts/'+key).then(r=>r.json());
  document.getElementById('script').innerHTML=scriptData.sections.map((s,si)=>`
    <h2>${s.name}</h2>
    ${s.say?`<div class="say">${s.say}</div>`:''}
    ${(s.items||[]).map((it,ii)=>`<div class="q">
      <input type="checkbox" id="q${si}_${ii}" onchange="tog(${si},${ii})">
      <label for="q${si}_${ii}">${it.label}</label>
      ${it.capture?`<input type="text" id="f${si}_${ii}" placeholder="${it.capture}" style="display:none">`:''}
    </div>`).join('')}
  `).join('');
}
function tog(si,ii){const f=document.getElementById('f'+si+'_'+ii); if(f)f.style.display=document.getElementById('q'+si+'_'+ii).checked?'block':'none';}
document.getElementById('scriptsel').addEventListener('change',e=>loadScript(e.target.value));
document.getElementById('outcomes').innerHTML=Object.entries(oc).map(([k,v])=>
  `<button class="outcome" data-k="${k}" onclick="selOc(this)">${v}</button>`).join('');
function selOc(b){document.querySelectorAll('.outcome').forEach(e=>e.classList.remove('sel'));b.classList.add('sel');arm();}
document.getElementById('chips').innerHTML=[['none','No follow-up'],[1,'Tomorrow'],[3,'+3 days'],[7,'+1 week']].map(([k,v])=>
  `<button class="chip" data-k="${k}" onclick="selChip(this)">${v}</button>`).join('');
function selChip(b){document.querySelectorAll('.chip').forEach(e=>e.classList.remove('sel'));b.classList.add('sel');arm();}
function arm(){document.getElementById('save').disabled=!document.querySelector('.outcome.sel');}
document.getElementById('save').addEventListener('click',async()=>{
  const ocBtn=document.querySelector('.outcome.sel'); if(!ocBtn||!sel)return;
  const chip=document.querySelector('.chip.sel');
  const days=chip?chip.dataset.k:'none';
  const facts=[];
  scriptData.sections.forEach((s,si)=>(s.items||[]).forEach((it,ii)=>{
    if(it.capture){const f=document.getElementById('f'+si+'_'+ii);const q=document.getElementById('q'+si+'_'+ii);
      if(q&&q.checked&&f&&f.value)facts.push({label:it.capture,value:f.value});}
  }));
  const r=await fetch('/api/call-manager/calls',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({contact_id:sel.id,contact_name:sel.name,contact_phone:sel.phone,contact_role:sel.contact_type,
      script_key:scriptData.key,outcome:ocBtn.dataset.k,summary:document.getElementById('note').value||null,
      key_facts:facts,follow_up_days:days==='none'?null:parseInt(days)})});
  if(r.ok){
    document.getElementById('savedmsg').innerHTML=`<div class="saved">Saved — call is in your journal, timeline${days!=='none'?', and calendar':''}.</div>`;
    document.getElementById('note').value='';
    document.querySelectorAll('.outcome,.chip').forEach(e=>e.classList.remove('sel'));
    setTimeout(load,800);
  } else { document.getElementById('savedmsg').innerHTML='<div class="saved" style="background:#fbeaea;border-color:#d99">Save failed — try again.</div>'; }
});
load();
</script>
</body></html>"""
