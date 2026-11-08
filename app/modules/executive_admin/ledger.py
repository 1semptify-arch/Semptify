"""Bookkeeping — fiscal-year summaries, donor acknowledgments, CSV export.

Works on plain dicts (one per ledger row) so it is testable without a
database. Amounts are integer cents throughout; nothing here rounds.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date

from app.modules.executive_admin import compliance
from app.modules.executive_admin.knowledge import EXPENSE_CATEGORIES, FUNCTIONAL_CLASSES, INCOME_CATEGORIES

CONTRIBUTION_CATEGORIES = ("contribution", "grant")

CSV_FIELDS = (
    "entry_date",
    "kind",
    "amount",
    "category",
    "functional_class",
    "fund",
    "counterparty",
    "description",
    "goods_services_value",
    "acknowledged_on",
    "reference",
    "id",
)


def _d(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def dollars(cents: int | None) -> str:
    if cents is None:
        return "varies"
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100:,}.{cents % 100:02d}"


def validate_entry(entry: dict) -> list[str]:
    """Return a list of plain-language problems; empty means valid."""
    problems: list[str] = []
    kind = entry.get("kind")
    if kind not in ("income", "expense"):
        problems.append("Kind must be income or expense.")
    amount = entry.get("amount_cents")
    if not isinstance(amount, int) or amount <= 0:
        problems.append("Amount must be more than zero.")
    category = entry.get("category")
    if kind == "income" and category not in INCOME_CATEGORIES:
        problems.append("Pick an income category.")
    if kind == "expense":
        if category not in EXPENSE_CATEGORIES:
            problems.append("Pick an expense category.")
        if entry.get("functional_class") not in FUNCTIONAL_CLASSES:
            problems.append("Pick program, management and general, or fundraising.")
    goods = entry.get("goods_services_cents") or 0
    if goods < 0 or (isinstance(amount, int) and goods > amount):
        problems.append("Goods or services value must be between zero and the amount.")
    try:
        _d(entry.get("entry_date"))
    except (TypeError, ValueError):
        problems.append("Date is missing or not a real date.")
    return problems


def summarize(entries: list[dict], fy_end: date, *, other_assets_cents: int = 0) -> dict:
    """Summary of one fiscal year, shaped like the Form 990 money sections."""
    fy_start = compliance.fiscal_year_start(fy_end)
    in_year = sorted((e for e in entries if fy_start <= _d(e["entry_date"]) <= fy_end), key=lambda e: _d(e["entry_date"]))

    revenue_by_category: dict[str, int] = defaultdict(int)
    expense_by_class: dict[str, int] = defaultdict(int)
    expense_by_category: dict[str, int] = defaultdict(int)
    contributions = 0
    crossed_on: str | None = None

    for e in in_year:
        amt = e["amount_cents"]
        if e["kind"] == "income":
            revenue_by_category[e["category"]] += amt
            if e["category"] in CONTRIBUTION_CATEGORIES:
                before = contributions
                contributions += amt
                if before <= compliance.AG_CONTRIBUTION_THRESHOLD_CENTS < contributions and crossed_on is None:
                    crossed_on = _d(e["entry_date"]).isoformat()
        else:
            expense_by_class[e.get("functional_class") or "management_general"] += amt
            expense_by_category[e["category"]] += amt

    total_revenue = sum(revenue_by_category.values())
    total_expenses = sum(expense_by_class.values())

    fund_balances: dict[str, int] = defaultdict(int)
    for e in entries:
        if _d(e["entry_date"]) <= fy_end:
            sign = 1 if e["kind"] == "income" else -1
            fund_balances[e.get("fund") or "unrestricted"] += sign * e["amount_cents"]
    cash = sum(fund_balances.values())
    total_assets = max(cash, 0) + (other_assets_cents or 0)

    program = expense_by_class.get("program", 0)
    return {
        "fiscal_year_start": fy_start.isoformat(),
        "fiscal_year_end": fy_end.isoformat(),
        "entry_count": len(in_year),
        "revenue_by_category": dict(revenue_by_category),
        "expense_by_functional_class": dict(expense_by_class),
        "expense_by_category": dict(expense_by_category),
        "total_revenue_cents": total_revenue,
        "total_expenses_cents": total_expenses,
        "net_cents": total_revenue - total_expenses,
        "gross_receipts_cents": total_revenue,
        "contributions_cents": contributions,
        "contributions_note": "Gifts and grants are counted together toward the $25,000 Attorney General line, to be safe (see Minn. Stat. § 309.50 definitions).",
        "contributions_crossed_threshold_on": crossed_on,
        "program_share_pct": round(100 * program / total_expenses, 1) if total_expenses else None,
        "fund_balances_cents": dict(fund_balances),
        "cash_balance_cents": cash,
        "total_assets_cents": total_assets,
        "assets_note": "Assets = cash from these books plus the non-cash assets entered on the Profile.",
        "form_990": compliance.form_990_for(total_revenue, total_assets),
        "ag_registration_required": contributions > compliance.AG_CONTRIBUTION_THRESHOLD_CENTS,
        "ag_audit_required": total_revenue > compliance.AG_AUDIT_REVENUE_CENTS,
        "form_990t_required": revenue_by_category.get("unrelated_business", 0) >= compliance.FORM_990T_UBI_CENTS,
    }


def gifts_needing_acknowledgment(entries: list[dict]) -> list[dict]:
    out = []
    for e in entries:
        if e["kind"] != "income" or e["category"] != "contribution" or e.get("acknowledged_on"):
            continue
        goods = e.get("goods_services_cents") or 0
        needs_ack = e["amount_cents"] >= compliance.ACK_THRESHOLD_CENTS
        needs_disclosure = goods > 0 and e["amount_cents"] > compliance.QUID_PRO_QUO_CENTS
        if needs_ack or needs_disclosure:
            out.append(
                {
                    "id": e["id"],
                    "entry_date": _d(e["entry_date"]).isoformat(),
                    "counterparty": e.get("counterparty"),
                    "amount_cents": e["amount_cents"],
                    "reason": "written acknowledgment ($250+)" if needs_ack else "quid pro quo disclosure (over $75 with goods/services)",
                }
            )
    return out


def acknowledgment_letter(entry: dict, profile: dict) -> str:
    """Plain-text donor acknowledgment with the IRS-required statements."""
    org = profile.get("legal_name") or "[Organization name]"
    ein = profile.get("ein") or "[EIN]"
    donor = entry.get("counterparty") or "[Donor name]"
    amount = entry["amount_cents"]
    goods = entry.get("goods_services_cents") or 0
    when = _d(entry["entry_date"]).strftime("%B %d, %Y").replace(" 0", " ")
    lines = [
        org,
        f"EIN {ein}",
        "",
        f"Dear {donor},",
        "",
        f"Thank you for your gift of {dollars(amount)} received on {when}.",
    ]
    if goods > 0:
        lines.append(
            f"In return you received goods or services with a good-faith estimated value of {dollars(goods)}. "
            f"The amount you may be able to deduct for federal income tax purposes is limited to the amount of your gift "
            f"over that value: {dollars(amount - goods)}."
        )
    else:
        lines.append("No goods or services were provided in exchange for this gift.")
    if profile.get("determination_date"):
        lines.append(
            f"{org} is recognized by the IRS as a 501(c)(3) public charity "
            f"(determination dated {profile['determination_date']})."
        )
    else:
        lines.append(
            f"{org}'s recognition as a 501(c)(3) organization is pending with the IRS. "
            "Whether this gift is tax-deductible depends on that recognition."
        )
    lines += ["", "With thanks,", "", profile.get("treasurer_name") or "[Treasurer]", "Treasurer"]
    return "\n".join(lines)


def to_csv(entries: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for e in sorted(entries, key=lambda e: (_d(e["entry_date"]), e["id"])):
        writer.writerow(
            {
                "entry_date": _d(e["entry_date"]).isoformat(),
                "kind": e["kind"],
                "amount": f"{e['amount_cents'] / 100:.2f}",
                "category": e["category"],
                "functional_class": e.get("functional_class") or "",
                "fund": e.get("fund") or "unrestricted",
                "counterparty": e.get("counterparty") or "",
                "description": e.get("description") or "",
                "goods_services_value": f"{(e.get('goods_services_cents') or 0) / 100:.2f}",
                "acknowledged_on": e.get("acknowledged_on") or "",
                "reference": e.get("reference") or "",
                "id": e["id"],
            }
        )
    return buf.getvalue()
