"""Generate per-module content_request.json files (the 'words needed' contract).

Each tenant-facing module gets a content_request.json declaring the two
articles it needs (one statistical/facts piece, one about-with-usage-examples)
plus subject-level requests under app/data/articles/.

Usage: venv311 python tools/generate_content_requests.py
Idempotent — overwrites request files, never touches articles.json.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = ROOT / "app" / "modules"
SUBJECTS_DIR = ROOT / "app" / "data" / "articles"
TODAY = "2026-09-19"

# module -> (display_name, pillar, stats topic brief, usage topic brief, upl_tier)
MODULES: dict[str, tuple[str, str, str, str, str]] = {
    "vault": ("Vault", "record",
        "Why tenant-owned cloud storage matters: how document loss affects renters in disputes; source: legal-aid guidance on record-keeping + eviction-defense outcomes.",
        "What the Vault is — the tenant's own cloud folder (Dropbox/Google Drive) where Semptify stores their documents, not on Semptify servers. Example: tenant uploads a photo of a leak + the landlord's text, both land in their own drive."),
    "documents": ("Documents", "record",
        "How document classification works; what metadata (dates, amounts, parties) gets extracted; source: OCR/document-processing documentation.",
        "What the Documents pipeline does — upload a file, it classifies it (notice, lease, letter), pulls out dates/amounts/parties. Example: a scanned eviction notice gets its deadline extracted automatically."),
    "document_center": ("Document Center", "record",
        "How in-browser document viewing + field overlays work for tenants; source: module docs.",
        "What the Document Center is — view a vault document with extracted fields highlighted on the page. Example: open a lease, see the rent amount and dates marked."),
    "document_delivery": ("Document Delivery", "record",
        "How tenants receive documents (notices from court, landlord letters) into Semptify; source: module docs.",
        "What Document Delivery does — an inbox for documents sent to the tenant. Example: a court notice arrives and shows up in the tenant's delivery inbox."),
    "briefcase": ("Briefcase", "record",
        "Why organizing documents into folders matters before a dispute; source: legal-aid self-help guidance.",
        "What the Briefcase is — the tenant's own folder structure inside the vault for organizing documents by issue. Example: all repair-request documents in one folder."),
    "packet_builder": ("Packet Builder", "act",
        "How a curated document packet helps in court/agency filings; source: legal-aid guidance on evidence organization.",
        "What Packet Builder does — assemble selected vault documents into one organized packet for a filing or a meeting with an advocate. Example: gather all rent receipts + the repair photos into one PDF packet."),
    "export_import": ("Export & Import", "record",
        "Data portability for tenants — why keeping your own copy matters; source: data-portability principles.",
        "What Export/Import does — download all your Semptify data or move it. Example: tenant exports their full vault index and timeline as files they keep."),
    "journal": ("Journal", "record",
        "Why contemporaneous notes matter in disputes — records made at the time carry more weight than memory; source: legal-aid record-keeping guidance.",
        "What the Journal is — free-form dated notes about conversations, incidents, and requests. Example: after a call with the landlord, the tenant logs what was said while it's fresh."),
    "timeline": ("Timeline", "record",
        "Why a chronological record matters — dates establish notice periods and cure windows; source: housing-law practice guides.",
        "What the Timeline does — automatically builds a dated sequence of events from the tenant's documents and journal. Example: the notice, the repair request, and the filing all appear in order."),
    "calendar": ("Calendar", "record",
        "Why deadline tracking prevents the most common tenant losses — missed cure and response windows; source: court self-help materials.",
        "What the Calendar is — the tenant's own deadline and event tracker (court dates, response windows, inspection appointments). Example: the answer deadline appears on the calendar the day the notice is scanned."),
    "sticky_notes": ("Sticky Notes", "record",
        "Lightweight annotations for documents; source: module docs.",
        "What Sticky Notes are — quick notes attached to a document or page. Example: mark a lease clause to ask an advocate about."),
    "contacts": ("Contacts", "record",
        "Why keeping advocate/agency contact info with case records matters; source: module docs.",
        "What Contacts is — the tenant's saved contacts for landlords, advocates, agencies. Example: the housing inspector's number stored next to the complaint."),
    "case_builder": ("Case Builder", "act",
        "How organized case data changes outcomes — documentation is the core of most housing disputes; source: legal-aid guidance.",
        "What Case Builder does — groups the tenant's documents, events, and notes into a case around one issue. Example: everything about the broken heater becomes one case."),
    "guided_intake": ("Guided Intake", "act",
        "Why structured intake beats a blank page — it captures the details agencies ask for; source: intake-design practice.",
        "What Guided Intake does — walks the tenant through the facts step by step instead of handing them a form. Example: it asks 'when did you first tell the landlord?' and files the answer."),
    "plan_maker": ("Plan Maker", "act",
        "How a written plan helps tenants sequence legal steps in the right order; source: housing self-help guidance.",
        "What Plan Maker does — turns a situation into an ordered list of steps with deadlines. Example: 'repair request → 14-day wait → escrow filing' becomes a plan."),
    "court_forms": ("Court Forms", "act",
        "How many tenants face filings without a lawyer; the role of correct forms; source: court self-representation statistics (e.g., NCSC/state court data).",
        "What Court Forms does — fills official court forms from the tenant's saved information into a document in their vault. Example: an answer form pre-filled with the tenant's details."),
    "court_packet": ("Court Packet", "act",
        "What a filing packet needs — form, supporting documents, organized record; source: court self-help guides.",
        "What Court Packet does — tracks what's ready and what's missing for a court filing. Example: shows 'answer done, receipts attached, still need the notice photo.'"),
    "eviction_defense": ("Eviction Defense", "act",
        "Eviction filing volumes and self-representation rates; the share of tenants who default by missing deadlines; source: state court statistics / Eviction Lab.",
        "What Eviction Defense is — the forms and steps for responding to an eviction filing. Example: tenant files an answer asserting the landlord skipped the required notice."),
    "eviction_timeline": ("Eviction Timeline", "act",
        "How fast eviction cases move — the compressed deadlines tenants face; source: state unlawful-detainer statutes.",
        "What Eviction Timeline does — maps an eviction case's real deadlines onto the tenant's calendar. Example: 'hearing in 7 days' shows as a countdown."),
    "dispute_tracker": ("Dispute Tracker", "act",
        "How tracking an open dispute prevents missed steps; source: module docs.",
        "What Dispute Tracker does — follows an active dispute (repair, deposit, notice) through its stages. Example: shows a deposit dispute at 'demand letter sent, 21 days remain.'"),
    "complaints": ("Complaints", "act",
        "Which agencies handle which housing complaints — code enforcement vs. AG vs. HUD; source: agency jurisdictions.",
        "What Complaints does — points the tenant to the right agency and tracks the complaint. Example: a no-heat complaint routed to the city inspector."),
    "correspondence": ("Correspondence", "act",
        "Why written landlord communication matters — notices must often be in writing to count; source: statute notice requirements.",
        "What Correspondence does — helps the tenant write and send landlord letters (repair requests, notices) with the right content. Example: a repair-request letter citing the duty-to-maintain statute."),
    "communication": ("Communication", "act",
        "Keeping a record of conversations with landlords/advocates; source: module docs.",
        "What Communication does — the tenant's message history with advocates and contacts in one place. Example: the advocate's advice thread stays attached to the case."),
    "rent": ("Rent & Payments", "act",
        "Rent-payment records and their role in disputes; escrow vs. withholding varies by state; source: state statutes.",
        "What the Rent tools do — track payments and, where the law allows, escrow arrangements. Example: payment history exported for a dispute."),
    "zoom_court_prep": ("Remote Court Prep", "act",
        "The growth of remote hearings since 2020 and what tenants need for them; source: court remote-hearing guidance.",
        "What Zoom Court Prep does — checklists and steps for appearing by video. Example: test the link, have the packet open, know where to sit."),
    "law_library": ("Law Library", "know",
        "What jurisdiction-aware legal information covers vs. what it can't do (UPL boundary); source: library scope docs.",
        "What the Law Library is — official-source-only statutes and rules, filtered to the tenant's state. Example: looking up the exact repair remedy for Minnesota."),
    "state_laws": ("State Laws", "know",
        "How landlord-tenant remedies differ state to state — escrow vs. repair-deduct vs. no self-help; source: the verified 50-state dataset.",
        "What State Laws shows — the tenant's own state's deposit deadline, notice period, and repair remedies with citations. Example: a Minnesota tenant sees rent escrow, not repair-and-deduct."),
    "legal_trails": ("Legal Trails", "know",
        "How legal topics connect — statute → remedy → filing; source: module docs.",
        "What Legal Trails does — guided paths through a legal topic showing each step's authority. Example: the habitability trail from the repair request to the escrow filing."),
    "search": ("Search", "know",
        "Why search across the whole library matters for a tenant who doesn't know the right term; source: module docs.",
        "What Search does — finds statutes, guides, and the tenant's own records from one box. Example: 'heat' finds the habitability statute and the tenant's journal entries."),
    "resource_directory": ("Resource Directory", "know",
        "The role of legal aid and tenant organizations — most tenants qualify for free help; source: LSC/justice-gap data.",
        "What the Resource Directory is — the list of legal-aid offices, tenant groups, and agencies by jurisdiction. Example: a Minneapolis tenant finds LawHelpMN and HOME Line."),
    "dashboard": ("Dashboard", "record",
        "How a single at-a-glance view reduces missed deadlines; source: module docs.",
        "What the Dashboard shows — documents, deadlines, urgent issues, and next steps in one place. Example: 'answer due in 3 days' pinned at the top."),
    "portal": ("Public Portal", "know",
        "What public no-login services exist and why they're offered before any account; source: portal catalog.",
        "What the Portal is — the public services page at semptify.org for people who haven't set up a vault. Example: look up state law without signing in."),
    "public_forms": ("Public Forms", "know",
        "Public feedback and autofill forms; source: module docs.",
        "What Public Forms does — open forms anyone can use (feedback, autofill help). Example: a tenant autofills a repair letter from a public form."),
    "progress": ("Progress", "record",
        "Why visible milestones keep a multi-week legal process from stalling; source: module docs.",
        "What Progress shows — milestones and readiness for the tenant's current process. Example: 'case packet 80% ready.'"),
    "intake": ("Intake", "record",
        "First-file upload — the starting point of a tenant's record; source: module docs.",
        "What Intake does — the first step where a document gets uploaded and queued for processing. Example: drop the notice photo here to start."),
    "advocate": ("Advocate", "act",
        "How advocates multiply a tenant's capacity — the role of non-lawyer advocates; source: tenant-advocacy programs.",
        "What the Advocate tools do — let a helper see the tenant's linked cases and documents. Example: a HOME Line counselor reviews the tenant's timeline."),
    "manager": ("Manager", "govern",
        "How caseworker/manager oversight works for multi-tenant programs; source: module docs.",
        "What Manager does — assigns advocates and reviews case summaries for a program. Example: a legal-aid supervisor assigns an advocate to a filing."),
    "housing_accountability": ("Housing Accountability", "govern",
        "Pattern detection across a tenant's documents — repeated violations matter; source: module docs.",
        "What Housing Accountability does — scans the tenant's documents for repeated landlord violations. Example: three ignored repair requests flagged as a pattern."),
    "mndes": ("MN DES Guide", "know",
        "What Minnesota's DEED/DES reporting requires; source: state guidance.",
        "What the MNDES guide covers — step-by-step submission help for Minnesota's program. Example: the compliance checklist for a submission."),
}

# Per-module UPL risk tier (modules table above omits it; mapped here).
MODULE_UPL: dict[str, str] = {
    "eviction_defense": "high", "eviction_timeline": "high",
    "court_forms": "high", "court_packet": "high", "zoom_court_prep": "high",
    "plan_maker": "medium", "rent": "medium", "dispute_tracker": "medium",
    "correspondence": "medium", "legal_trails": "medium", "mndes": "medium",
    "law_library": "medium", "state_laws": "medium", "complaints": "medium",
    "housing_accountability": "medium",
}

# 17 composer subjects -> (pillar, stats brief, usage brief, upl tier)
SUBJECTS: dict[str, tuple[str, str, str, str]] = {
    "eviction": ("act",
        "Eviction filing volumes, self-representation rates, default-judgment share from missed deadlines; source: Eviction Lab + state court stats.",
        "What a tenant can do when an eviction filing arrives — the answer deadline, what the court looks at, where help is. Example path: notice → answer → hearing.",
        "high"),
    "repair": ("act",
        "How habitability repair duties work and how remedies differ by state (escrow/deduct/court only); source: state-law dataset.",
        "How to request a repair properly — written notice, cure period, then the state-specific remedy. Example: a Minnesota tenant files rent escrow after the 14-day cure.",
        "medium"),
    "habitability": ("act",
        "What 'fit and habitable' legally means — heat, water, plumbing, codes; source: state habitability statutes.",
        "How a habitability claim works — document the condition, written notice, the remedy the state provides. Example: no heat in January in MN.",
        "medium"),
    "deposit": ("know",
        "Security-deposit rules by state — caps, return deadlines, itemization; source: verified 50-state dataset.",
        "How to get a deposit back — move-out condition photos, forwarding address, the return deadline. Example: MN's 21-day rule.",
        "low"),
    "rent": ("act",
        "Rent-payment records, late fees, and the escrow-vs-withholding difference; source: state statutes.",
        "How to keep clean payment records and what to do when rent becomes disputed. Example: escrow deposit with the court.",
        "medium"),
    "lease": ("know",
        "What lease terms actually bind a tenant and which clauses are unenforceable; source: state landlord-tenant acts.",
        "How to read a lease — the clauses that matter (term, notice, fees, entry) and the ones a court may not enforce. Example: an illegal no-guest clause.",
        "low"),
    "evidence": ("record",
        "What makes a record useful in a housing dispute — dated, contemporaneous, source-attached; source: legal-aid guidance.",
        "How to build a usable record — photos with dates, saved texts, logged calls. Example: timestamped photos of a leak.",
        "low"),
    "court_prep": ("act",
        "What happens at a housing-court hearing and how self-represented tenants fare; source: court self-help materials.",
        "How to prepare for a hearing — the packet, the order of events, what to bring. Example: an answer filed, documents organized, hearing day checklist.",
        "high"),
    "retaliation": ("govern",
        "What retaliation protections exist — the presumption windows after a tenant complains; source: state retaliation statutes.",
        "How retaliation protections work — reporting a code violation then a rent raise or eviction attempt shortly after. Example: MN's presumption period.",
        "high"),
    "discrimination": ("govern",
        "Fair-housing enforcement — protected classes, complaint volumes, where to file; source: HUD/FHAP data.",
        "What housing discrimination looks like and where a complaint goes — HUD, state agencies. Example: different terms offered to a family with kids.",
        "high"),
    "safety": ("record",
        "Housing safety conditions and the inspection/complaint systems that address them; source: code-enforcement data.",
        "What to do about unsafe conditions — document, report to the right agency, track the complaint. Example: broken lock → inspector → follow-up.",
        "medium"),
    "timeline": ("record",
        "Why chronology decides housing disputes — notice dates, cure windows, deadlines; source: practice guides.",
        "How the timeline builds itself from the tenant's documents and why it matters. Example: proving a repair request came before the eviction notice.",
        "low"),
    "small_claims": ("act",
        "Small-claims limits and what housing disputes fit (deposit recovery is the classic); source: state court rules.",
        "How small-claims court works for a tenant — the filing fee, the limit, what to bring. Example: suing for an unreturned deposit.",
        "medium"),
    "landing": ("know",
        "What Semptify is and isn't — a public utility for tenants, not a law firm; source: project docs.",
        "How to start — set up the vault, upload a first document, see the organized record. Example: first visit walkthrough.",
        "low"),
    "tenant_rights": ("know",
        "The baseline rights every US tenant has — habitability, notice, due process — and where they vary; source: state-law dataset.",
        "An overview of the rights a tenant holds and how to find their state's specifics. Example: entry-notice rules differ by state.",
        "low"),
    "journal": ("record",
        "Why contemporaneous notes carry weight in disputes; source: record-keeping guidance.",
        "How to use the journal — log conversations and incidents as they happen. Example: logging a landlord call right after it ends.",
        "low"),
    "law_library": ("know",
        "What a jurisdiction-aware official-source library covers; source: library scope.",
        "How to use the Law Library — pick a state, read the statute with its source link. Example: the MN escrow statute.",
        "low"),
}


def request_for(key: str, display: str, pillar: str, stats_brief: str,
                about_brief: str, upl: str, is_subject: bool = False) -> dict:
    base = {
        "module" if not is_subject else "subject": key,
        "display_name": display,
        "pillar": pillar,
        "requested_at": TODAY,
        "status": "requested",
        "articles": [
            {
                "id": "stats",
                "kind": "statistical",
                "title": f"{display}: the numbers behind it",
                "brief": stats_brief,
                "upl_risk_tier": upl,
                "status": "requested",
            },
            {
                "id": "about",
                "kind": "usage",
                "title": f"{display}: what it does and how to use it",
                "brief": about_brief,
                "upl_risk_tier": upl,
                "status": "requested",
            },
        ],
    }
    return base


def main() -> None:
    written = []
    for mod, (disp, pillar, sb, ab) in sorted(MODULES.items()):
        upl = MODULE_UPL.get(mod, "low")
        d = MODULES_DIR / mod
        if not d.is_dir():
            print(f"  !! skipping {mod} — no module dir")
            continue
        req = request_for(mod, disp, pillar, sb, ab, upl)
        out = d / "content_request.json"
        out.write_text(json.dumps(req, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(out.relative_to(ROOT)))

    SUBJECTS_DIR.mkdir(parents=True, exist_ok=True)
    for subj, (pillar, sb, ab, upl) in sorted(SUBJECTS.items()):
        sdir = SUBJECTS_DIR / subj
        sdir.mkdir(exist_ok=True)
        req = request_for(subj, subj.replace("_", " ").title(), pillar, sb, ab, upl, is_subject=True)
        out = sdir / "content_request.json"
        out.write_text(json.dumps(req, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(out.relative_to(ROOT)))

    print(f"wrote {len(written)} request files")


if __name__ == "__main__":
    main()
