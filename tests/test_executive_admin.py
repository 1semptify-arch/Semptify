"""Executive Administration — unit tests for the pure-function layer.

compliance.py / governance.py / ledger.py are deterministic and take plain
values, so the whole module's rule engine is tested without a database.
"""

from datetime import date

from app.modules.executive_admin import compliance, governance, ledger
from app.modules.executive_admin.knowledge import (
    FORMATION_STEPS,
    GRANT_READINESS,
    POLICIES,
    SOURCES,
    knowledge_bundle,
    sources_for,
)

TODAY = date(2026, 11, 8)


# ---------------------------------------------------------------------------
# compliance
# ---------------------------------------------------------------------------


def test_parse_fye_defaults_and_validates():
    assert compliance.parse_fye(None) == (12, 31)
    assert compliance.parse_fye("06-30") == (6, 30)
    for bad in ("13-01", "02-30", "x"):
        try:
            compliance.parse_fye(bad)
        except ValueError:
            pass
        else:  # noqa: B015 — explicit failure path, pytest.raises avoided per repo style
            raise AssertionError(f"parse_fye accepted {bad}")


def test_fiscal_year_helpers():
    assert compliance.fiscal_year_end_for(date(2026, 3, 1), "12-31") == date(2026, 12, 31)
    assert compliance.fiscal_year_end_for(date(2026, 3, 1), "06-30") == date(2026, 6, 30)
    assert compliance.fiscal_year_start(date(2026, 12, 31)) == date(2026, 1, 1)
    assert compliance.due_15th_of_month_after(date(2026, 12, 31), 5) == date(2027, 5, 15)
    assert compliance.due_15th_of_month_after(date(2026, 12, 31), 7) == date(2027, 7, 15)


def test_ez_retroactive_deadline_is_27_months_end_of_month():
    # Formation 2026-03-15 -> 27 months after 2026-03-01 = 2028-06-01 -> end of June
    assert compliance.ez_retroactive_deadline(date(2026, 3, 15)) == date(2028, 6, 30)


def test_form_990_thresholds():
    assert compliance.form_990_for(4_000_000, 1_000_000)["form"] == "990-N"
    assert compliance.form_990_for(10_000_000, 10_000_000)["form"] == "990-EZ"
    assert compliance.form_990_for(19_999_999, 50_000_000)["form"] == "990"  # asset cap is exclusive
    assert compliance.form_990_for(30_000_000, 0)["form"] == "990"


def test_ez_eligible():
    ok = compliance.ez_eligible([1_000_000, 2_000_000], 10_000_000)
    assert ok["eligible_so_far"] is True
    over = compliance.ez_eligible([6_000_000], 100_000)
    assert over["eligible_so_far"] is False
    over_assets = compliance.ez_eligible([1_000_000], 26_000_000)
    assert over_assets["eligible_so_far"] is False


def test_status_for():
    assert compliance.status_for(date(2026, 11, 1), TODAY, done=False) == "overdue"
    assert compliance.status_for(date(2026, 11, 20), TODAY, done=False) == "due_soon"
    assert compliance.status_for(date(2027, 6, 1), TODAY, done=False) == "upcoming"
    assert compliance.status_for(date(2026, 1, 1), TODAY, done=True) == "done"


def _blank_state():
    return {
        "profile": {},
        "fy_summaries": {},
        "filings": {},
        "custom_deadlines": [],
        "last_board_meeting": None,
        "today": TODAY,
    }


def test_calendar_before_formation():
    items = compliance.build_calendar(**_blank_state())
    assert len(items) == 1 and items[0]["id"] == "not_formed" and items[0]["due"] is None


def test_calendar_after_formation_has_mn_renewal_and_990_and_board_meeting():
    state = _blank_state()
    # Formation 2025-01-10: first renewal (year after filing) is 2026-12-31,
    # inside the 400-day horizon; board-meeting and 27-month dates land
    # inside the window too.
    state["profile"] = {"formation_date": "2025-01-10", "fiscal_year_end": "12-31"}
    items = compliance.build_calendar(**state)
    ids = [i["id"] for i in items]
    assert any(i.startswith("mn_renewal-") for i in ids)
    assert any(i.startswith("irs_990-") for i in ids)
    assert "irs_1023ez_27_months" in ids
    assert any(i.startswith("board_meeting-") for i in ids)


def test_calendar_first_renewal_is_year_after_filing():
    state = _blank_state()
    state["profile"] = {"formation_date": "2026-01-10"}
    items = compliance.build_calendar(**state)
    renewals = [i for i in items if i["id"].startswith("mn_renewal-")]
    assert renewals == [] or min(r["due"] for r in renewals) == "2027-12-31"


def test_calendar_ag_registration_trigger():
    state = _blank_state()
    state["profile"] = {"formation_date": "2026-01-10"}
    state["fy_summaries"] = {
        "2026-12-31": {
            "gross_receipts_cents": 3_000_000,
            "total_assets_cents": 0,
            "contributions_cents": 3_000_000,
            "total_revenue_cents": 3_000_000,
            "revenue_by_category": {"contribution": 3_000_000},
            "contributions_crossed_threshold_on": "2026-10-01",
        }
    }
    items = compliance.build_calendar(**state)
    ag = next(i for i in items if i["id"] == "mn_ag_register")
    assert ag["due"] == "2026-10-31" and ag["status"] == "overdue"
    assert any(i["id"].startswith("mn_ag_report-") for i in items)


def test_calendar_done_filing_marked():
    state = _blank_state()
    state["profile"] = {"formation_date": "2025-06-01"}
    state["filings"] = {"mn_renewal-2026": "2026-11-01"}
    items = compliance.build_calendar(**state)
    renewal = next(i for i in items if i["id"] == "mn_renewal-2026")
    assert renewal["status"] == "done" and renewal["done_on"] == "2026-11-01"


def test_calendar_990t_when_ubi_crosses_threshold():
    state = _blank_state()
    state["profile"] = {"formation_date": "2026-01-10"}
    state["fy_summaries"] = {
        "2026-12-31": {
            "gross_receipts_cents": 200_000,
            "total_assets_cents": 0,
            "contributions_cents": 0,
            "total_revenue_cents": 200_000,
            "revenue_by_category": {"unrelated_business": 150_000},
        }
    }
    items = compliance.build_calendar(**state)
    assert any(i["id"].startswith("irs_990t-") for i in items)


# ---------------------------------------------------------------------------
# governance
# ---------------------------------------------------------------------------


def _board(n=3):
    return [
        {"id": f"m{i}", "name": f"Director {i}", "is_director": True, "term_start": "2026-01-01"}
        for i in range(n)
    ]


def test_quorum_rules():
    assert governance.quorum_needed(3) == 2
    assert governance.quorum_needed(4) == 3
    # bylaws quorum can never drop below one-third
    assert governance.quorum_needed(6, bylaws_quorum=1) == 2
    assert governance.quorum_needed(6, bylaws_quorum=5) == 5
    assert governance.quorum_needed(0) == 0


def test_notice_check():
    ok = governance.notice_check(date(2026, 11, 20), date(2026, 11, 10), schedule_announced=False)
    assert ok["ok"] is True
    short = governance.notice_check(date(2026, 11, 12), date(2026, 11, 10), schedule_announced=False)
    assert short["ok"] is False
    sched = governance.notice_check(date(2026, 11, 12), None, schedule_announced=True)
    assert sched["ok"] is True
    missing = governance.notice_check(date(2026, 11, 12), None, schedule_announced=False)
    assert missing["ok"] is False


def test_motion_result_majority_of_entitled():
    motion = {"text": "adopt bylaws", "yes": 2, "no": 1, "abstain": 0}
    result = governance.motion_result(motion, ["m0", "m1", "m2"])
    assert result["passed"] is True and result["needed"] == 2
    recused = {"text": "pay director", "yes": 1, "no": 0, "abstain": 0, "recused": ["m2"]}
    r2 = governance.motion_result(recused, ["m0", "m1", "m2"])
    assert r2["entitled"] == 2 and r2["needed"] == 2 and r2["passed"] is False


def test_meeting_check_quorum_and_minutes():
    board = _board(3)
    meeting = {
        "meeting_date": "2026-11-08",
        "kind": "regular",
        "present": ["m0", "m1"],
        "notice_sent_on": "2026-10-30",
        "motions": [{"text": "Approve minutes", "moved_by": "m0", "seconded_by": "m1", "yes": 2, "no": 0, "abstain": 0}],
    }
    check = governance.meeting_check(meeting, board)
    assert check["quorum_met"] is True and check["notice"]["ok"] is True
    assert check["motions"][0]["result"]["passed"] is True
    minutes = governance.minutes_draft(meeting, board, check, "Semptify")
    assert "Semptify" in minutes and "PASSED" in minutes and "Director 2" in minutes


def test_written_action_requires_all_directors():
    board = _board(3)
    action = {"action_date": "2026-11-08", "signed_by": ["m0", "m1"], "text": "x"}
    check = governance.written_action_check(action, board, articles_allow_less=False)
    assert check["effective"] is False and check["needed"] == 3
    action["signed_by"].append("m2")
    assert governance.written_action_check(action, board)["effective"] is True
    partial = {"action_date": "2026-11-08", "signed_by": ["m0", "m1"], "text": "x"}
    assert governance.written_action_check(partial, board, articles_allow_less=True)["effective"] is True


def test_agenda_templates_used():
    org = governance.agenda_for({"kind": "organizational"}, None, [])
    assert any("bylaws" in line for line in org)
    reg = governance.agenda_for({"kind": "regular"}, None, [])
    assert reg[0].startswith("Call to order")


# ---------------------------------------------------------------------------
# ledger
# ---------------------------------------------------------------------------


def _entry(**kw):
    base = {
        "id": "e1",
        "entry_date": "2026-06-01",
        "kind": "income",
        "amount_cents": 10_000,
        "category": "contribution",
        "functional_class": None,
        "fund": "unrestricted",
    }
    base.update(kw)
    return base


def test_validate_entry():
    assert ledger.validate_entry(_entry()) == []
    problems = ledger.validate_entry(_entry(kind="expense", category="hosting_software", functional_class=None))
    assert problems  # functional class required for expenses
    assert ledger.validate_entry(_entry(kind="expense", category="hosting_software", functional_class="program")) == []
    assert ledger.validate_entry(_entry(amount_cents=0))
    assert ledger.validate_entry(_entry(entry_date="not-a-date"))
    assert ledger.validate_entry(_entry(goods_services_cents=999999))


def test_summarize_fiscal_year_and_ag_trigger():
    entries = [
        _entry(id="a", amount_cents=2_000_000, entry_date="2026-01-15"),
        _entry(id="b", amount_cents=1_000_000, entry_date="2026-10-15"),
        _entry(id="c", kind="expense", category="hosting_software", functional_class="program", amount_cents=500_00, entry_date="2026-07-01"),
    ]
    s = ledger.summarize(entries, date(2026, 12, 31))
    assert s["total_revenue_cents"] == 3_000_000
    assert s["contributions_cents"] == 3_000_000
    assert s["ag_registration_required"] is True
    assert s["contributions_crossed_threshold_on"] == "2026-10-15"
    assert s["expense_by_functional_class"]["program"] == 500_00
    assert s["program_share_pct"] == 100.0
    assert s["form_990"]["form"] == "990-N"
    assert s["cash_balance_cents"] == 2_950_000


def test_restricted_fund_balances():
    entries = [
        _entry(id="a", amount_cents=100_000, fund="restricted:grant-x"),
        _entry(id="b", kind="expense", category="supplies", functional_class="program", amount_cents=40_000, fund="restricted:grant-x"),
    ]
    s = ledger.summarize(entries, date(2026, 12, 31))
    assert s["fund_balances_cents"]["restricted:grant-x"] == 60_000


def test_gifts_needing_acknowledgment():
    entries = [
        _entry(id="small", amount_cents=10_000),
        _entry(id="big", amount_cents=30_000),
        _entry(id="done", amount_cents=30_000, acknowledged_on="2026-06-05"),
        _entry(id="quid", amount_cents=10_000, goods_services_cents=2_000),
    ]
    needs = ledger.gifts_needing_acknowledgment(entries)
    ids = {g["id"] for g in needs}
    assert ids == {"big", "quid"}
    assert next(g for g in needs if g["id"] == "big")["reason"].startswith("written acknowledgment")
    assert next(g for g in needs if g["id"] == "quid")["reason"].startswith("quid pro quo")


def test_acknowledgment_letter_required_statements():
    entry = _entry(amount_cents=30_000, counterparty="A Friend")
    letter = ledger.acknowledgment_letter(entry, {"legal_name": "Semptify", "ein": "12-3456789"})
    assert "No goods or services were provided" in letter
    assert "pending with the IRS" in letter  # no determination yet
    quid = _entry(amount_cents=30_000, goods_services_cents=5_000, counterparty="A Friend")
    letter2 = ledger.acknowledgment_letter(quid, {"legal_name": "Semptify", "determination_date": "2026-09-01"})
    assert "$250.00" in letter2 and "501(c)(3) public charity" in letter2


def test_csv_export_shape():
    out = ledger.to_csv([_entry()])
    lines = out.strip().splitlines()
    assert lines[0].startswith("entry_date,kind,amount")
    assert "100.00" in lines[1] and "contribution" in lines[1]


def test_dollars_formatting():
    assert ledger.dollars(123456) == "$1,234.56"
    assert ledger.dollars(-500) == "-$5.00"
    assert ledger.dollars(None) == "varies"


# ---------------------------------------------------------------------------
# knowledge integrity — every referenced source exists
# ---------------------------------------------------------------------------


def test_all_source_ids_resolve():
    for coll in (FORMATION_STEPS, POLICIES, GRANT_READINESS):
        for item in coll:
            for sid in item.get("source_ids", []):
                assert sid in SOURCES, f"{item['id']} references missing source {sid}"


def test_knowledge_bundle_complete():
    bundle = knowledge_bundle()
    for key in ("phases", "steps", "cost_paths", "policies", "grant_readiness", "agenda_template", "organizational_agenda", "income_categories", "functional_classes", "expense_categories", "honesty_notes", "sources"):
        assert key in bundle
    assert all(s["sources"] is not None for s in bundle["steps"])
    assert sources_for(["mn_309_52"])[0]["url"].startswith("https://")


def test_router_imports_and_surface():
    from app.modules.executive_admin.router import router

    paths = {r.path for r in router.routes}
    for required in (
        "/",
        "/health",
        "/api/overview",
        "/api/profile",
        "/api/calendar",
        "/api/board",
        "/api/meetings",
        "/api/written-actions",
        "/api/policies",
        "/api/ledger",
        "/api/ledger/export.csv",
        "/api/grant-readiness",
    ):
        assert required in paths, f"missing route {required}"
