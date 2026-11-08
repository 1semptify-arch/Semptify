"""Board governance rules — quorum, notice, votes, written actions, minutes.

Pure functions over plain dicts. Statute references are in knowledge.SOURCES
(Minn. Stat. §§ 317A.231, .235, .237, .239, .255).
"""

from __future__ import annotations

import math
from datetime import date

from app.modules.executive_admin.knowledge import AGENDA_TEMPLATE, ORGANIZATIONAL_AGENDA
from app.modules.executive_admin.ledger import dollars

NOTICE_DAYS = 5


def active_directors(board: list[dict], on: date | None = None) -> list[dict]:
    """Directors in office on a date (no end date, or end date after it)."""
    out = []
    for m in board:
        if not m.get("is_director", True):
            continue
        start = m.get("term_start")
        end = m.get("term_end")
        if on and start and date.fromisoformat(start) > on:
            continue
        if on and end and date.fromisoformat(end) < on:
            continue
        out.append(m)
    return out


def quorum_needed(directors_in_office: int, bylaws_quorum: int | None = None) -> int:
    """Majority by default; bylaws may set another number, never under one-third (§ 317A.235)."""
    if directors_in_office <= 0:
        return 0
    floor = math.ceil(directors_in_office / 3)
    if bylaws_quorum:
        return max(int(bylaws_quorum), floor)
    return directors_in_office // 2 + 1


def notice_check(meeting_date: date, notice_sent_on: date | None, schedule_announced: bool) -> dict:
    """Five days' notice unless the date was fixed in the bylaws or announced at a prior meeting (§ 317A.231 subd. 4)."""
    if schedule_announced:
        return {"ok": True, "why": "Date was set in advance, so separate notice is not required."}
    if notice_sent_on is None:
        return {"ok": False, "why": "No notice date recorded. Directors need 5 days' notice."}
    days = (meeting_date - notice_sent_on).days
    if days >= NOTICE_DAYS:
        return {"ok": True, "why": f"Notice went out {days} days before the meeting."}
    return {"ok": False, "why": f"Notice went out only {days} day(s) before; 5 are required unless every director waives it."}


def motion_result(motion: dict, present_ids: list[str]) -> dict:
    """Majority of directors present and entitled to vote (§ 317A.237). Recused directors are not entitled to vote."""
    recused = set(motion.get("recused", []))
    entitled = [p for p in present_ids if p not in recused]
    yes = int(motion.get("yes", 0))
    no = int(motion.get("no", 0))
    abstain = int(motion.get("abstain", 0))
    needed = len(entitled) // 2 + 1 if entitled else 1
    problems = []
    if yes + no + abstain > len(entitled):
        problems.append("More votes recorded than directors present and entitled to vote.")
    passed = yes >= needed and not problems
    return {
        "passed": passed,
        "needed": needed,
        "entitled": len(entitled),
        "why": (
            f"{yes} yes of {len(entitled)} entitled to vote; {needed} needed."
            + (" Recused directors did not count." if recused else "")
        ),
        "problems": problems,
    }


def meeting_check(meeting: dict, board: list[dict], bylaws_quorum: int | None = None) -> dict:
    when = date.fromisoformat(meeting["meeting_date"])
    directors = active_directors(board, when)
    present = [p for p in meeting.get("present", []) if any(d["id"] == p for d in directors)]
    needed = quorum_needed(len(directors), bylaws_quorum)
    notice = notice_check(
        when,
        date.fromisoformat(meeting["notice_sent_on"]) if meeting.get("notice_sent_on") else None,
        bool(meeting.get("schedule_announced")),
    )
    motions = [{**m, "result": motion_result(m, present)} for m in meeting.get("motions", [])]
    return {
        "directors_in_office": len(directors),
        "present": len(present),
        "quorum_needed": needed,
        "quorum_met": len(directors) > 0 and len(present) >= needed,
        "notice": notice,
        "motions": motions,
        "board_size_ok": len(directors) >= 3,
    }


def agenda_for(meeting: dict, treasurer_summary: dict | None, upcoming: list[dict]) -> list[str]:
    base = ORGANIZATIONAL_AGENDA if meeting.get("kind") == "organizational" else AGENDA_TEMPLATE
    lines = list(base)
    if treasurer_summary and meeting.get("kind") != "organizational":
        t = treasurer_summary
        detail = (
            f"Treasurer's report: revenue {dollars(t['total_revenue_cents'])}, "
            f"expenses {dollars(t['total_expenses_cents'])}, net {dollars(t['net_cents'])}, "
            f"cash {dollars(t['cash_balance_cents'])} (fiscal year to date)"
        )
        lines = [detail if line.startswith("Treasurer's report") else line for line in lines]
    due = [u for u in upcoming if u.get("status") in ("overdue", "due_soon")]
    if due:
        joined = "; ".join(f"{u['title']} (due {u['due']})" for u in due[:5])
        lines = [f"Compliance calendar: {joined}" if line.startswith("Compliance calendar") else line for line in lines]
    for item in meeting.get("extra_agenda", []):
        lines.insert(len(lines) - 2, item)
    return lines


def minutes_draft(meeting: dict, board: list[dict], check: dict, org_name: str) -> str:
    names = {m["id"]: m.get("name", "?") for m in board}
    present = [names.get(p, "?") for p in meeting.get("present", [])]
    absent = [d.get("name", "?") for d in active_directors(board, date.fromisoformat(meeting["meeting_date"])) if d["id"] not in meeting.get("present", [])]
    lines = [
        f"Minutes of the {meeting.get('kind', 'regular')} meeting of the Board of Directors of {org_name or '[Organization]'}",
        f"Date: {meeting['meeting_date']}    Place: {meeting.get('location') or '[place or remote link]'}",
        "",
        f"Directors present: {', '.join(present) or 'none recorded'}",
        f"Directors absent: {', '.join(absent) or 'none'}",
        f"Quorum: {check['present']} of {check['directors_in_office']} present; {check['quorum_needed']} needed — {'met' if check['quorum_met'] else 'NOT met'}.",
        f"Notice: {check['notice']['why']}",
        "",
        "Conflict-of-interest disclosures: " + (meeting.get("disclosures") or "none made."),
        "",
    ]
    for i, m in enumerate(check["motions"], 1):
        r = m["result"]
        recused = [names.get(x, "?") for x in m.get("recused", [])]
        lines.append(f"Motion {i}: {m.get('text', '')}")
        lines.append(
            f"  Moved by {names.get(m.get('moved_by'), m.get('moved_by') or '?')}; seconded by {names.get(m.get('seconded_by'), m.get('seconded_by') or '?')}."
        )
        lines.append(f"  Vote: {m.get('yes', 0)} yes, {m.get('no', 0)} no, {m.get('abstain', 0)} abstain. {'PASSED' if r['passed'] else 'FAILED'}.")
        if recused:
            lines.append(f"  Recused (conflict of interest, left the vote): {', '.join(recused)}.")
    if meeting.get("notes"):
        lines += ["", "Discussion:", meeting["notes"]]
    lines += ["", f"Next meeting: {meeting.get('next_meeting') or '[date]'}", "", "Respectfully submitted,", "", "[Secretary]"]
    return "\n".join(lines)


def written_action_check(action: dict, board: list[dict], articles_allow_less: bool = False) -> dict:
    """All directors must sign unless the articles allow fewer (§ 317A.239)."""
    when = date.fromisoformat(action["action_date"]) if action.get("action_date") else None
    directors = active_directors(board, when)
    ids = {d["id"] for d in directors}
    signed = [s for s in action.get("signed_by", []) if s in ids]
    if articles_allow_less:
        needed = len(ids) // 2 + 1 if ids else 1
        rule = "Articles allow written action by the number needed at a full meeting; all directors must be told right away."
    else:
        needed = len(ids)
        rule = "Every director in office must sign or consent electronically."
    return {
        "effective": len(ids) > 0 and len(signed) >= needed,
        "signed": len(signed),
        "needed": needed,
        "why": rule,
        "missing": [d.get("name", "?") for d in directors if d["id"] not in signed],
    }
