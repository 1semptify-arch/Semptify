"""Seed Brad's god-mode workspace — real case data for Crowe/Sazama v. Velair.

Idempotent: skips rows whose dedupe key already exists. Re-runnable.
Run: .\\venv311\\Scripts\\python.exe scripts\\seed_godmode_brad.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import get_session_factory  # noqa: E402
from app.core.id_gen import make_id  # noqa: E402
from sqlalchemy import text  # noqa: E402

USER_ID = "GUbGQUTpK6"


def dt(y, m, d, h=9):
    return datetime(y, m, d, h, tzinfo=timezone.utc)


CONTACTS = [
    # (type, role, name, org, phone, email, notes, starred)
    ("property_manager", "opposing_party", "Lisa Burg", "Velair Property Management", None, None,
     "On-site manager, Lexington Flats. Sent superseded Jan-31 settlement draft to Dena Jan 27-28 with writ threats. [DOC] emails in packet.", True),
    ("property_manager", "opposing_party", "Jodi Rossi", "Velair Property Management", None, None,
     "Regional manager. Sept 4, 2025 stated Velair proceeding with 'eviction for cause'.", False),
    ("attorney", "opposing_counsel", "Douglass E. Turner", "Hanbery & Turner", None, None,
     "Landlord-side eviction attorney. Signed Jan-31 draft + executed Feb-28 settlement. Career landlord-side counsel (Frenz evictions record).", True),
    ("attorney", "opposing_counsel", "Erica Stoffer", None, None, None,
     "Velair counsel — appeared at June 3, 2026 conciliation hearing.", False),
    ("legal_aid", "former_counsel", "Heather Mendiola", "SMRLS", None, None,
     "Prior legal-aid attorney. Last-modified executed settlement 2:33 PM Dec 23 (metadata). No counterclaims filed on our behalf.", False),
    ("legal_aid", "former_counsel", "Alena Carl", "SMRLS Metro Housing Unit", None, None,
     "PDF/Word metadata author of both settlement versions (template/provenance question for counsel).", False),
    ("tenant_org", "advocate", "Patty", "HOME Line", "612-728-5767", None,
     "Prospective attorney / referral contact. Packet shared via OneDrive (specific-person, view-only).", True),
    ("witness", "my_witness", "Kristine", "Former Velair manager", None, None,
     "Quit Velair the day Burg arrived at Lexington Flats. Friendly. POTENTIAL WITNESS — do NOT approach about testimony; counsel decides contact.", True),
    ("other", "co_tenant", "Dena Sazama", None, None, None,
     "Co-tenant and co-plaintiff. Head of household on LIHTC lease rider.", True),
    ("legal_aid", None, "Legal Assistance of Dakota County", "LADC", "952-431-3200", None,
     "Free, local, takes affirmative civil cases. dakotalegal.org. First call.", False),
    ("legal_aid", None, "Volunteer Lawyers Network", "VLN", "612-752-6677", None,
     "Housing + debt collection + conciliation appeals. Intake Mon-Thu 10a-1p.", False),
    ("tenant_org", None, "HOME Line", None, "612-728-5767", None,
     "Tenant hotline + private attorney referral list.", False),
    ("legal_aid", None, "LawHelpMN", None, "877-696-6529", None,
     "Statewide backup router.", False),
    ("legal_aid", None, "Mid-Minnesota Legal Aid", None, "612-334-5970", None,
     "Affirmative/systemic housing work — managing attorney fought Turner in Frenz coverage.", False),
    ("attorney", "prospective_counsel", "Consumer Justice Law Firm", None, None, None,
     "Edina. Consumer protection, fee-shifting (FDCPA/FCRA). Lead with false-collections claim; pull credit reports first.", False),
    ("agency", None, "MN Lawyers Professional Responsibility Board", "OLPR", None, None,
     "Ethics complaint venue for Turner / Mendiola if counsel supports. lawyersboard.mn.gov.", False),
    ("court", None, "Dakota County District Court", None, "651-377-7180", None,
     "Hastings. Cases: 19AV-CV-25-3477, 19HA-CV-26-3784, 19WS-CO-26-1394, 19HA-CV-26-3761.", True),
]

CALENDAR = [
    # (title, date, type, critical, reminder_days, desc)
    ("ELT: all motions filed AND heard", dt(2026, 10, 16), "deadline", True, 14,
     "Video-preservation / discovery-extension motion must be heard by this date. Discovery cutoff was Sept 9 — extendable 30d for good cause."),
    ("ELT: witness list + exhibit list + copies + ADR completed", dt(2026, 11, 2), "deadline", True, 14,
     "Joint statement + ADR done. Upload exhibits to MNDES separately. Mediators book weeks out — schedule immediately."),
    ("TRIAL — 19HA-CV-26-3784 (deposit appeal, de novo)", dt(2026, 11, 16), "hearing", True, 7,
     "9:00 AM, Dakota County, Hastings. Arrive 30 min early. Judge only. All evidence fresh."),
    ("Rule 60.02 motion deadline — 19AV-CV-25-3477", dt(2026, 12, 23), "deadline", True, 30,
     "1 year from Dec 23, 2025 order. Filing packet ready in vault."),
    ("Attorney calls + Patty email + credit reports", dt(2026, 9, 25, 9), "appointment", True, 0,
     "DO_TODAY list: OneDrive share link, EMAIL_TO_PATTY, call order per ATTORNEY_CONTACTS_TODAY."),
    ("Pull all 3 credit reports", dt(2026, 9, 26, 9), "reminder", False, 0,
     "annualcreditreport.com — needed before Consumer Justice call; documents the collections claim."),
    ("Request Eagan PD report (Aug 26-28, 2025 incident)", dt(2026, 9, 29, 9), "reminder", False, 0,
     "Records requests take weeks — start now."),
]

TIMELINE = [
    ("notice", "First 'Intent to Evict' notice (nonpayment)", dt(2024, 7, 10), "high",
     "[DOC] EVICTION_THREAT_2024-07-10_intent_to_evict_nonpayment.pdf", True),
    ("notice", "LIHTC lease begins — rider names Dena head of household", dt(2024, 11, 1), "normal",
     "[DOC] Lease summary and LIHTC.pdf — MN Low Income Housing Tax Credit Lease Rider.", True),
    ("notice", "Second eviction-related notice", dt(2024, 11, 6), "high", "[DOC]", True),
    ("communication", "Police called over alleged lease violation; Burg refused to show video", dt(2025, 8, 26), "high",
     "[ACCT][ALLEG] Aug 26-28 window. Violation alleged fabricated. Video-preservation motion target.", True),
    ("communication", "Tenants signed and returned offered lease — office received it", dt(2025, 8, 29), "normal", "[DOC]", True),
    ("communication", "Cease-and-desist sent", dt(2025, 9, 3), "high", "[DOC] Cease_and_Desist_Demand.docx", True),
    ("notice", "Rossi: Velair proceeding with 'eviction for cause'", dt(2025, 9, 4), "critical",
     "[DOC] EMAIL_Rossi_thread — 4-yr tenure + eviction threat.", True),
    ("court", "LIHTC lease rider filed in 19AV-CV-25-3477", dt(2025, 11, 17), "normal", "[DOC] court filing", True),
    ("court", "Hearing + settlement executed — Feb 28, 2026 move-out", dt(2025, 12, 23), "critical",
     "10:02 AM: SMRLS-side doc produces harsher Jan-31 draft (Turner signed, judge unsigned). 2:33 PM: Mendiola revises — Feb 28 version, both attorneys sign.", True),
    ("communication", "Tenants first receive the written agreement", dt(2026, 1, 7), "normal", "[DOC]", True),
    ("communication", "Text: 'You have been evicted in a court of law'", dt(2026, 1, 21), "high",
     "[DOC] TEXT_Velair_office_evicted_claim_Jan21.pdf — sent during lawful possession.", True),
    ("communication", "Burg emails Dena citing superseded Jan-31 draft + writ threat", dt(2026, 1, 27), "critical",
     "[DOC] EMAIL_Burg_to_Dena + doubles_down Jan 28. Claims 'court order sent by the court' — judge never signed.", True),
    ("court", "Moved out by noon per executed Feb-28 agreement", dt(2026, 2, 28), "normal", "[DOC] Declaration_MoveOut", True),
    ("payment", "Wyndham motel stay — displacement housing", dt(2026, 2, 28), "high",
     "[DOC] ~$716 total through Mar 9. Damages item.", True),
    ("court", "Conciliation hearing — Burg admits no itemized statement/receipt sent", dt(2026, 6, 3), "critical",
     "[ACCT] Admission on the record; ruling still went against tenants — factual-error appeal ground.", True),
    ("court", "Judgment: deposit claim dismissed w/ prejudice; $2,071.67 counterclaim to Velair", dt(2026, 6, 9), "critical",
     "[DOC] JUDGMENT_19WS_2026-06-09.pdf. Stoffer + Burg appeared.", True),
    ("court", "Appeal filed — same day the letter arrived", dt(2026, 6, 11), "high", "[DOC] APPEAL_Demand_for_Removal", True),
    ("court", "CCT402 good-faith affidavit filed (deficiency cured)", dt(2026, 7, 3), "normal", "[DOC]", True),
    ("court", "Expedited Litigation Track order issued — trial de novo set", dt(2026, 7, 9), "high", "[DOC] ELT order", True),
    ("communication", "Attorney packet staged + shared with Patty (OneDrive, view-only)", dt(2026, 9, 25), "normal",
     "66 files: framing docs, exhibits, key docs, 60.02 draft filings.", False),
]

INCIDENTS = [
    ("Police called over alleged lease violation; video withheld", "eviction", "high",
     dt(2025, 8, 26), dt(2025, 8, 28),
     "Burg refused to produce footage. Incident report request pending with Eagan PD."),
    ("Superseded Jan-31 draft enforced as 'court order'", "retaliation", "critical",
     dt(2026, 1, 27), dt(2026, 1, 28),
     "Burg's emails to Dena cite draft never adopted by the court; threats of writ. Draft metadata traces to SMRLS-side file."),
    ("Deposit dismissed with prejudice + $2,071.67 counterclaim judgment", "eviction", "high",
     dt(2026, 6, 9), None,
     "Appealed — trial de novo Nov 16. Collection active via judgment-debtor affidavit 19HA-CV-26-3761."),
]

RENT = [
    ("payment", 34200, dt(2026, 1, 4), "2026-01", "paid", "portal",
     "January rent via portal per executed agreement."),
    ("payment", 34200, dt(2026, 2, 4), "2026-02", "paid", "portal",
     "February rent $342 via portal per executed agreement."),
    ("charge", 71600, dt(2026, 2, 28), "2026-03", None, "card",
     "Wyndham motel 2/28-3/9 — displacement housing. DAMAGES item (receipt in packet)."),
]

JOURNAL = [
    ("note", "Attorney outreach + counsel packet — Sept 25, 2026", dt(2026, 9, 25),
     "OneDrive packet live (66 files, specific-person view-only). Email to Patty staged. Call order: LADC → VLN → HOME Line → LawHelpMN → Consumer Justice (after credit reports). Consumer Justice handles FDCPA/FCRA collections slice; landlord-tenant core needs a tenant-side litigator or legal aid. Kristine = friendly former Velair manager, potential witness — counsel decides contact."),
]


async def seed():
    async with get_session_factory()() as db:
        counts = {}
        # ---- contacts ----
        for ctype, role, name, org, phone, email, notes, starred in CONTACTS:
            ex = await db.execute(
                text("select 1 from contacts where user_id=:u and name=:n"), {"u": USER_ID, "n": name}
            )
            if ex.first():
                continue
            await db.execute(
                text(
                    "insert into contacts (id, user_id, contact_type, role, name, organization, phone, email, notes, source, is_starred, is_active, interaction_count, created_at, updated_at)"
                    " values (:id,:u,:ct,:r,:n,:o,:p,:e,:no,'manual',:s,true,0,now(),now())"
                ),
                {"id": make_id("contact"), "u": USER_ID, "ct": ctype, "r": role, "n": name, "o": org, "p": phone, "e": email, "no": notes, "s": starred},
            )
            counts["contacts"] = counts.get("contacts", 0) + 1

        # ---- calendar ----
        for title, when, etype, crit, rem, desc in CALENDAR:
            ex = await db.execute(
                text("select 1 from calendar_events where user_id=:u and title=:t"),
                {"u": USER_ID, "t": title},
            )
            if ex.first():
                continue
            await db.execute(
                text(
                    "insert into calendar_events (id, user_id, title, description, start_datetime, all_day, event_type, is_critical, reminder_days, source, created_at)"
                    " values (:id,:u,:t,:d,:w,false,:e,:c,:r,'manual',now())"
                ),
                {"id": make_id("cal"), "u": USER_ID, "t": title, "d": desc, "w": when, "e": etype, "c": crit, "r": rem},
            )
            counts["calendar"] = counts.get("calendar", 0) + 1

        # ---- timeline ----
        for etype, title, when, urg, desc, ev in TIMELINE:
            ex = await db.execute(
                text("select 1 from timeline_events where user_id=:u and title=:t"),
                {"u": USER_ID, "t": title},
            )
            if ex.first():
                continue
            await db.execute(
                text(
                    "insert into timeline_events (id, user_id, event_type, title, description, event_date, urgency, is_deadline, is_evidence, sequence_number, created_at)"
                    " values (:id,:u,:e,:t,:d,:w,:urg,false,:ev,0,now())"
                ),
                {"id": make_id("tl"), "u": USER_ID, "e": etype, "t": title, "d": desc, "w": when, "urg": urg, "ev": ev},
            )
            counts["timeline"] = counts.get("timeline", 0) + 1

        # ---- incidents ----
        for title, itype, sev, s, e, desc in INCIDENTS:
            ex = await db.execute(
                text("select 1 from incidents where user_id=:u and title=:t"),
                {"u": USER_ID, "t": title},
            )
            if ex.first():
                continue
            await db.execute(
                text(
                    "insert into incidents (user_id, title, description, start_date, end_date, status, incident_type, severity, created_at, updated_at)"
                    " values (:u,:t,:d,:s,:e,'active',:it,:sev,now(),now())"
                ),
                {"u": USER_ID, "t": title, "d": desc, "s": s, "e": e, "it": itype, "sev": sev},
            )
            counts["incidents"] = counts.get("incidents", 0) + 1

        # ---- rent/expense ledger ----
        for etype, cents, when, period, status, method, notes in RENT:
            ex = await db.execute(
                text("select 1 from rent_payments where user_id=:u and amount=:a and payment_date=:w"),
                {"u": USER_ID, "a": cents, "w": when},
            )
            if ex.first():
                continue
            await db.execute(
                text(
                    "insert into rent_payments (id, user_id, entry_type, amount, payment_date, period_covered, status, payment_method, source, notes, created_at)"
                    " values (:id,:u,:e,:a,:w,:p,:st,:m,'user_entered',:n,now())"
                ),
                {"id": make_id("rent"), "u": USER_ID, "e": etype, "a": cents, "w": when, "p": period, "st": status, "m": method, "n": notes},
            )
            counts["ledger"] = counts.get("ledger", 0) + 1

        # ---- journal ----
        for etype, title, when, content in JOURNAL:
            ex = await db.execute(
                text("select 1 from journal_entries where user_id=:u and title=:t"),
                {"u": USER_ID, "t": title},
            )
            if ex.first():
                continue
            await db.execute(
                text(
                    "insert into journal_entries (id, user_id, entry_type, title, content, occurred_at, is_urgent, source, created_at, updated_at)"
                    " values (:id,:u,:e,:t,:c,:w,false,'manual',now(),now())"
                ),
                {"id": make_id("jrnl"), "u": USER_ID, "e": etype, "t": title, "c": content, "w": when},
            )
            counts["journal"] = counts.get("journal", 0) + 1

        await db.commit()
        print("Seeded:", counts if counts else "nothing new (already seeded)")


if __name__ == "__main__":
    asyncio.run(seed())
