"""Compliance rules — dates and thresholds, as pure functions.

Every function here is deterministic and takes plain values, so the whole
calendar can be tested without a database. Sources are in ``knowledge.SOURCES``.
"""

from __future__ import annotations

import calendar as _cal
from datetime import date, timedelta

AG_CONTRIBUTION_THRESHOLD_CENTS = 2_500_000  # Minn. Stat. § 309.52 subd. 1a
AG_AUDIT_REVENUE_CENTS = 75_000_000  # Minn. Stat. § 309.53 subd. 3
FORM_990N_RECEIPTS_CENTS = 5_000_000
FORM_990EZ_RECEIPTS_CENTS = 20_000_000
FORM_990EZ_ASSETS_CENTS = 50_000_000
FORM_990T_UBI_CENTS = 100_000
EZ_RECEIPTS_CENTS = 5_000_000  # Form 1023-EZ eligibility
EZ_ASSETS_CENTS = 25_000_000
ACK_THRESHOLD_CENTS = 25_000  # IRS written acknowledgment, single gift
QUID_PRO_QUO_CENTS = 7_500  # IRS disclosure, payment over $75
DUE_SOON_DAYS = 30


def parse_fye(value: str | None) -> tuple[int, int]:
    """'MM-DD' fiscal year end → (month, day). Defaults to calendar year."""
    if not value:
        return 12, 31
    month_s, day_s = value.split("-")
    month, day = int(month_s), int(day_s)
    if not 1 <= month <= 12 or not 1 <= day <= _cal.monthrange(2001, month)[1]:
        raise ValueError(f"invalid fiscal year end: {value}")
    return month, day


def _clamp(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, _cal.monthrange(year, month)[1]))


def add_months(d: date, months: int) -> date:
    idx = d.month - 1 + months
    return _clamp(d.year + idx // 12, idx % 12 + 1, d.day)


def end_of_month(d: date) -> date:
    return date(d.year, d.month, _cal.monthrange(d.year, d.month)[1])


def fiscal_year_end_for(d: date, fye: str | None) -> date:
    """The fiscal-year end date of the fiscal year containing ``d``."""
    month, day = parse_fye(fye)
    candidate = _clamp(d.year, month, day)
    return candidate if d <= candidate else _clamp(d.year + 1, month, day)


def fiscal_year_start(fy_end: date) -> date:
    return _clamp(fy_end.year - 1, fy_end.month, fy_end.day) + timedelta(days=1)


def due_15th_of_month_after(fy_end: date, months_after: int) -> date:
    """'15th day of the Nth month after the end of the year' (IRS and MN AG)."""
    target = add_months(date(fy_end.year, fy_end.month, 1), months_after)
    return date(target.year, target.month, 15)


def ez_retroactive_deadline(formation: date) -> date:
    """Last day to file 1023-EZ and keep exemption back to formation (27 months)."""
    return end_of_month(add_months(date(formation.year, formation.month, 1), 27))


def form_990_for(gross_receipts_cents: int, total_assets_cents: int) -> dict:
    if gross_receipts_cents <= FORM_990N_RECEIPTS_CENTS:
        form, why = "990-N", "Gross receipts normally $50,000 or less — the e-Postcard."
    elif gross_receipts_cents < FORM_990EZ_RECEIPTS_CENTS and total_assets_cents < FORM_990EZ_ASSETS_CENTS:
        form, why = "990-EZ", "Gross receipts under $200,000 and assets under $500,000."
    else:
        form, why = "990", "Gross receipts $200,000+ or assets $500,000+."
    return {
        "form": form,
        "why": why,
        "note": "'Normally' is a multi-year average under IRS rules; confirm with the 990-N guide in early years.",
    }


def ez_eligible(receipts_by_year_cents: list[int], total_assets_cents: int) -> dict:
    over = [r for r in receipts_by_year_cents if r > EZ_RECEIPTS_CENTS]
    ok = not over and total_assets_cents <= EZ_ASSETS_CENTS
    return {
        "eligible_so_far": ok,
        "why": (
            "Actual receipts and assets are within the 1023-EZ limits. You must also project $50,000 or less for each of the next 3 years."
            if ok
            else "A year over $50,000 in receipts or assets over $250,000 rules out the short form; use Form 1023."
        ),
    }


def status_for(due: date, today: date, done: bool) -> str:
    if done:
        return "done"
    if due < today:
        return "overdue"
    if (due - today).days <= DUE_SOON_DAYS:
        return "due_soon"
    return "upcoming"


def _item(item_id: str, title: str, due: date, today: date, filings: dict, **extra) -> dict:
    done_on = filings.get(item_id)
    return {
        "id": item_id,
        "title": title,
        "due": due.isoformat(),
        "status": status_for(due, today, bool(done_on)),
        "done_on": done_on,
        **extra,
    }


def build_calendar(
    *,
    profile: dict,
    fy_summaries: dict[str, dict],
    filings: dict[str, str],
    custom_deadlines: list[dict],
    last_board_meeting: date | None,
    today: date,
    horizon_days: int = 400,
) -> list[dict]:
    """Every dated obligation that applies, sorted by due date.

    ``fy_summaries`` maps a fiscal-year-end ISO date to the ledger summary for
    that year (see ledger.summarize). Items already done stay listed with
    status ``done`` until they fall out of the look-back window.
    """
    fye = profile.get("fiscal_year_end") or "12-31"
    formation = date.fromisoformat(profile["formation_date"]) if profile.get("formation_date") else None
    horizon = today + timedelta(days=horizon_days)
    lookback = today - timedelta(days=120)
    items: list[dict] = []

    if formation is None:
        items.append(
            {
                "id": "not_formed",
                "title": "No dated filings yet — they start when the Minnesota articles are filed",
                "due": None,
                "status": "upcoming",
                "done_on": None,
                "why": "Enter the formation date on the Profile once the Secretary of State returns the filed articles.",
                "source_ids": ["mn_sos_fees"],
                "verified": True,
            }
        )
    else:
        for year in range(max(formation.year + 1, today.year - 1), horizon.year + 1):
            items.append(
                _item(
                    f"mn_renewal-{year}",
                    f"Minnesota annual renewal for {year}",
                    date(year, 12, 31),
                    today,
                    filings,
                    why="Secretary of State, no fee. Missing it dissolves the corporation.",
                    cost_cents=0,
                    source_ids=["mn_sos_renewal"],
                    verified=True,
                )
            )

        first_fy_end = fiscal_year_end_for(formation, fye)
        fy_end = first_fy_end
        while due_15th_of_month_after(fy_end, 5) <= horizon:
            summary = fy_summaries.get(fy_end.isoformat(), {})
            receipts = summary.get("gross_receipts_cents", 0)
            assets = summary.get("total_assets_cents", 0)
            contributions = summary.get("contributions_cents", 0)
            ubi = summary.get("revenue_by_category", {}).get("unrelated_business", 0)
            choice = form_990_for(receipts, assets)
            label = f"fiscal year ending {fy_end.isoformat()}"
            items.append(
                _item(
                    f"irs_990-{fy_end.isoformat()}",
                    f"IRS Form {choice['form']} for the {label}",
                    due_15th_of_month_after(fy_end, 5),
                    today,
                    filings,
                    why=f"{choice['why']} Three missed years in a row revoke exemption automatically.",
                    cost_cents=0,
                    source_ids=["irs_990_which", "irs_990_due", "irs_revocation"],
                    verified=True,
                )
            )
            if ubi >= FORM_990T_UBI_CENTS:
                items.append(
                    _item(
                        f"irs_990t-{fy_end.isoformat()}",
                        f"IRS Form 990-T (unrelated business income) for the {label}",
                        due_15th_of_month_after(fy_end, 5),
                        today,
                        filings,
                        why="Unrelated business gross income reached $1,000.",
                        source_ids=["irs_990t"],
                        verified=True,
                    )
                )
            if profile.get("ag_registered") or contributions > AG_CONTRIBUTION_THRESHOLD_CENTS:
                audit = summary.get("total_revenue_cents", 0) > AG_AUDIT_REVENUE_CENTS
                items.append(
                    _item(
                        f"mn_ag_report-{fy_end.isoformat()}",
                        f"Minnesota Attorney General charity annual report for the {label}",
                        due_15th_of_month_after(fy_end, 7),
                        today,
                        filings,
                        why=(
                            "Include the IRS 990 (without the donor schedule) and the board list. $50 late fee."
                            + (" Revenue over $750,000 — an audited financial statement is required." if audit else "")
                        ),
                        source_ids=["mn_309_53", "mn_ag_due_dates"],
                        verified=True,
                    )
                )
            fy_end = fiscal_year_end_for(fy_end + timedelta(days=1), fye)

        if not profile.get("form_1023ez_filed_on") and not profile.get("determination_date"):
            items.append(
                _item(
                    "irs_1023ez_27_months",
                    "File Form 1023-EZ by this date to keep exemption back to the formation date",
                    ez_retroactive_deadline(formation),
                    today,
                    filings,
                    why="Filed later, exemption starts only on the filing date.",
                    cost_cents=27500,
                    source_ids=["irs_1023ez_instr"],
                    verified=True,
                )
            )

        anchor = last_board_meeting or formation
        items.append(
            _item(
                f"board_meeting-after-{anchor.isoformat()}",
                "Hold a board meeting (at least once a year)",
                add_months(anchor, 12),
                today,
                filings,
                why="Minnesota requires at least one board meeting per year unless the bylaws say otherwise.",
                source_ids=["mn_317a_231"],
                verified=True,
            )
        )

    current_fy_end = fiscal_year_end_for(today, fye).isoformat()
    crossing = fy_summaries.get(current_fy_end, {}).get("contributions_crossed_threshold_on")
    if crossing and not profile.get("ag_registered"):
        items.append(
            _item(
                "mn_ag_register",
                "Register with the Minnesota Attorney General ($25)",
                date.fromisoformat(crossing) + timedelta(days=30),
                today,
                filings,
                why="Contributions passed $25,000 this year; registration is due within 30 days.",
                cost_cents=2500,
                source_ids=["mn_309_52"],
                verified=True,
            )
        )

    if profile.get("has_employees"):
        for year in (today.year, today.year + 1):
            for q_due, q_label in ((date(year, 4, 30), "Q1"), (date(year, 7, 31), "Q2"), (date(year, 10, 31), "Q3"), (date(year + 1, 1, 31), "Q4")):
                items.append(
                    _item(
                        f"irs_941-{year}-{q_label}",
                        f"IRS Form 941 payroll return, {year} {q_label}",
                        q_due,
                        today,
                        filings,
                        why="Quarterly federal payroll return while there are employees. Confirm on the IRS source.",
                        source_ids=["irs_employment"],
                        verified=False,
                    )
                )
            items.append(
                _item(
                    f"irs_w2-{year}",
                    f"W-2 forms to employees and SSA for {year}",
                    date(year + 1, 1, 31),
                    today,
                    filings,
                    why="Confirm on the IRS source.",
                    source_ids=["irs_employment"],
                    verified=False,
                )
            )

    for c in custom_deadlines:
        items.append(
            _item(
                c["id"],
                c.get("title", "Deadline"),
                date.fromisoformat(c["due"]),
                today,
                filings,
                why=c.get("note", ""),
                source_ids=[],
                verified=True,
                custom=True,
            )
        )

    def keep(it: dict) -> bool:
        if it.get("due") is None:
            return True
        due = date.fromisoformat(it["due"])
        if it["status"] == "overdue":
            return True
        return lookback <= due <= horizon

    items = [it for it in items if keep(it)]
    items.sort(key=lambda it: (it["due"] is None, it["due"] or ""))
    return items
