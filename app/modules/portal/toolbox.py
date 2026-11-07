"""Toolbox Catalog — SSOT for every service semptify.org mentions.

Every tool, service, or capability promised anywhere on the public site
(service catalog, tools page, donate page, about, privacy, developers,
advocacy, legal research, hello) has exactly one entry here with an honest
build status. Public pages `/toolbox` and `/toolbox/{id}` render from this
list, so a visitor who clicks on something not built yet gets a calm,
truthful page instead of a dead end or a generic redirect.

This is a data registry, not a set of code stubs: unbuilt services are
described, never faked. Building a service means writing its blueprint,
building it in the Forge, and then flipping its status here.

Status meanings (shown to the public):
- live     — works today
- partial  — some of it works today; the rest is being built
- planned  — designed or promised, not built yet
- vision   — long-term goal, needs funding or partners first

Level meanings (see C:/master-repo/SEMPTIFY_WHOLE_PICTURE_MAP.md §2):
- L0 read & learn · L1 my own record · L2 helped (consent-shared)
- L3 self-hosted workshop · L4 civic / aggregate public data only
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import ClassVar

STATUSES = ("live", "partial", "planned", "vision")
LEVELS = ("L0", "L1", "L2", "L3", "L4")
ENGINES = ("content", "record", "action", "help", "civic", "trust", "page")

STATUS_LABELS = {"live": "Works today", "partial": "Partly ready", "planned": "Planned", "vision": "Long-term"}
STATUS_CLASSES = {"live": "badge--success", "partial": "badge--accent", "planned": "badge--secondary", "vision": "badge--secondary"}
LEVEL_LABELS = {
    "L0": "Read and learn — no personal data",
    "L1": "Your own record — kept in your own storage",
    "L2": "Shared with a helper, only with your consent",
    "L3": "Run on your own computer",
    "L4": "Public records and anonymous totals only",
}


@dataclass(frozen=True)
class ToolboxEntry:
    """One service Semptify has promised somewhere on the public site."""

    id: str
    name: str
    purpose: str  # one plain sentence: what it does for a person
    group: str  # key into ToolboxCatalog.GROUPS
    status: str  # one of STATUSES
    level: str  # one of LEVELS
    engine: str  # one of ENGINES — which build engine owns it
    today: str  # what a person can do right now, honestly
    today_path: str = ""  # optional link for `today` (internal path or official site)
    backed_by: tuple[str, ...] = ()  # existing app/modules/* folders behind it
    promised_on: tuple[str, ...] = ()  # public pages that mention it
    note: str = ""  # honesty note — where a page claims more than exists
    queue_ref: str = ""  # orchestrator queue id, when one exists

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ToolboxCatalog:
    """Central registry — the only list of promised services."""

    GROUPS: ClassVar[dict[str, dict[str, str]]] = {
        "start": {"label": "Start here", "description": "For the moment something goes wrong."},
        "record": {"label": "Keep a record", "description": "Your own dated record, kept in your own storage."},
        "know": {"label": "Know your rights", "description": "Verified facts, with official sources shown."},
        "act": {"label": "Take the next step", "description": "Letters, forms, complaints, and court preparation."},
        "together": {"label": "Together", "description": "Tenant groups, public input, and the bill."},
        "helpers": {"label": "For advocates and legal aid", "description": "Helping someone with their consent."},
        "research": {"label": "Research and public data", "description": "Patterns from public records, never personal data."},
        "builders": {"label": "For developers", "description": "Open source, open documentation."},
        "support": {"label": "Support and contact", "description": "How Semptify is funded and how to reach us."},
    }

    ENTRIES: ClassVar[list[ToolboxEntry]] = [
        # ------------------------------------------------------------ START
        ToolboxEntry(
            id="situation_picker", name="What happened?",
            purpose="Pick your situation in plain words and see where to begin.",
            group="start", status="live", level="L0", engine="content",
            today="Open the start page and choose what happened.", today_path="/preamble",
            backed_by=("preamble", "portal"), promised_on=("/", "/portal", "/services"),
        ),
        ToolboxEntry(
            id="situation_guides", name="Do this now guides",
            purpose="Short steps to take tonight, before details are forgotten or lost.",
            group="start", status="live", level="L0", engine="content",
            today="Pick a situation guide from the home page.", today_path="/",
            backed_by=("portal",), promised_on=("/",),
        ),
        ToolboxEntry(
            id="crisis_resources", name="Crisis and emergency lines",
            purpose="Phone numbers for urgent help, listed neutrally.",
            group="start", status="live", level="L0", engine="help",
            today="Call 211 for basic needs or 988 for a mental health crisis.", today_path="/help",
            promised_on=("/help", "/about"),
        ),
        ToolboxEntry(
            id="help_center", name="Help center",
            purpose="Common questions, how storage works, and where real legal help is.",
            group="start", status="live", level="L0", engine="help",
            today="Read the help page.", today_path="/help",
            promised_on=("/help", "/contact"),
        ),
        ToolboxEntry(
            id="credit_report_guide", name="Credit report guide",
            purpose="Teach a person to pull and read their own credit reports. Semptify never sees them.",
            group="start", status="planned", level="L0", engine="content",
            today="The official source for your reports is the U.S. consumer protection agency.",
            today_path="https://www.consumerfinance.gov/",
            queue_ref="plan-20261027-semptify-feature-credit-report-pull-guid-cf67",
        ),
        # ----------------------------------------------------------- RECORD
        ToolboxEntry(
            id="document_vault", name="Document vault",
            purpose="Keep leases, photos, receipts, and notices in your own Google Drive, Dropbox, or OneDrive.",
            group="record", status="partial", level="L1", engine="record",
            today="Connect your own storage from the start page.", today_path="/preamble",
            backed_by=("vault", "storage", "vault_engine", "cloud_sync"),
            promised_on=("/donate", "/privacy", "/portal"),
            note="All three storage providers exist in code. Moving every record type into your own storage is about 40% done.",
        ),
        ToolboxEntry(
            id="timeline", name="Unified timeline",
            purpose="Every event in your tenancy, in order, in one place.",
            group="record", status="live", level="L1", engine="record",
            today="Start from the start page, then open the timeline.", today_path="/preamble",
            backed_by=("timeline",), promised_on=("/donate", "/portal"),
        ),
        ToolboxEntry(
            id="journal", name="Journal",
            purpose="Write down what happened, when it happened.",
            group="record", status="live", level="L1", engine="record",
            today="Start from the start page, then open the journal.", today_path="/preamble",
            backed_by=("journal",), promised_on=("/document-everything",),
        ),
        ToolboxEntry(
            id="calendar", name="Calendar",
            purpose="Court dates, deadlines, and everything in your tenancy on one calendar.",
            group="record", status="live", level="L1", engine="record",
            today="Start from the start page, then open the calendar.", today_path="/preamble",
            backed_by=("calendar",),
        ),
        ToolboxEntry(
            id="contacts_log", name="Contacts and call log",
            purpose="Who you talked to, when, and what was said.",
            group="record", status="live", level="L1", engine="record",
            today="Start from the start page, then open contacts.", today_path="/preamble",
            backed_by=("contacts", "communication"),
        ),
        ToolboxEntry(
            id="rent_ledger", name="Rent ledger",
            purpose="A record of every payment and every charge.",
            group="record", status="live", level="L1", engine="record",
            today="Start from the start page, then open the rent ledger.", today_path="/preamble",
            backed_by=("rent",),
        ),
        ToolboxEntry(
            id="quick_capture", name="Quick capture",
            purpose="Save a photo, file, voice note, or call in a few taps.",
            group="record", status="live", level="L1", engine="record",
            today="Start from the start page.", today_path="/preamble",
            backed_by=("intake", "documents"),
        ),
        ToolboxEntry(
            id="document_center", name="Document center",
            purpose="See and organize everything you have saved.",
            group="record", status="live", level="L1", engine="record",
            today="Start from the start page.", today_path="/preamble",
            backed_by=("document_center", "briefcase"), promised_on=("/donate",),
        ),
        ToolboxEntry(
            id="retaliation_tracker", name="Retaliation tracker",
            purpose="Track what happened after you asserted a right, in order.",
            group="record", status="live", level="L1", engine="record",
            today="Start from the start page.", today_path="/preamble",
            backed_by=("dispute_tracker",), promised_on=("/donate",),
        ),
        ToolboxEntry(
            id="timestamp_seal", name="Dated fingerprint for documents",
            purpose="Create a fingerprint of a file so anyone can check later that it was not changed.",
            group="record", status="partial", level="L1", engine="trust",
            today="Upload a document to your vault — every upload automatically gets a certificate with a fingerprint and an independent timestamp.",
            today_path="/preamble",
            backed_by=("vault", "storage"),
            promised_on=("/privacy",),
            note="Vault uploads already create a certificate: a SHA-256 fingerprint plus an RFC 3161 third-party timestamp (a self-signed fallback is marked when the outside service is unreachable). A stand-alone browser-side fingerprint tool is still planned. The privacy page wrongly said 'blockchain' — corrected 2026-11-06.",
        ),
        ToolboxEntry(
            id="fems", name="Forensic evidence system (FEMS)",
            purpose="Organize case documents with a chain of custody.",
            group="record", status="partial", level="L1", engine="record",
            today="Use the document center for now.", today_path="/preamble",
            backed_by=("fems",), promised_on=("/donate",),
        ),
        # ------------------------------------------------------------- KNOW
        ToolboxEntry(
            id="law_library", name="Know your rights law library",
            purpose="Housing law in plain words, with the official source shown for every fact.",
            group="know", status="partial", level="L0", engine="content",
            today="Open the law library.", today_path="/law-library",
            backed_by=("law_library", "state_laws", "context_engine"),
            promised_on=("/", "/donate", "/hello", "/services"),
            note="Minnesota is the deepest. Other states have entries but uneven depth, and content is still marked BETA. The donate page's present-tense '35 states' claim was corrected 2026-11-06; its remaining 'all 50 states + DC' mentions are Phase 2 / impact-with-funding goals, clearly future.",
        ),
        ToolboxEntry(
            id="situation_research", name="Go deeper on your situation",
            purpose="Find the statutes, cases, and agency rules that fit your exact situation.",
            group="know", status="partial", level="L0", engine="content",
            today="Search the law library by topic.", today_path="/law-library",
            backed_by=("legal_analysis", "context_engine", "law_linker"), promised_on=("/donate",),
        ),
        ToolboxEntry(
            id="read_aloud", name="Read aloud",
            purpose="Have any page read to you instead of reading it.",
            group="know", status="planned", level="L0", engine="page",
            today="Your device's built-in screen reader works on every Semptify page.",
            backed_by=("voice",),
        ),
        ToolboxEntry(
            id="languages", name="Other languages",
            purpose="Semptify in the languages tenants actually speak.",
            group="know", status="planned", level="L0", engine="content",
            today="Pages are in English only for now.",
            promised_on=("/donate",),
            note="12 language files exist as empty placeholders. Real translations are deferred until they can be done properly.",
        ),
        # -------------------------------------------------------------- ACT
        ToolboxEntry(
            id="eviction_defense", name="Eviction defense",
            purpose="Understand an eviction notice and calculate your deadlines.",
            group="act", status="partial", level="L1", engine="action",
            today="Open eviction defense.", today_path="/eviction-defense",
            backed_by=("eviction_defense", "eviction_timeline"), promised_on=("/donate",),
        ),
        ToolboxEntry(
            id="complaint_wizard", name="Complaint wizard",
            purpose="Find the right agency and prepare a housing complaint step by step.",
            group="act", status="partial", level="L1", engine="action",
            today="Read how complaints work.", today_path="/complaints",
            backed_by=("complaints",), promised_on=("/complaints", "/services", "/donate"),
            note="The step-by-step wizard flow works through the API (start, answer, finish — drafts save to the tenant's vault; anonymous visitors get the complaint text plus filing instructions). A click-through page is still being built.",
        ),
        ToolboxEntry(
            id="case_builder", name="Case builder",
            purpose="Pull your records together into one organized case.",
            group="act", status="partial", level="L1", engine="action",
            today="Start from the start page.", today_path="/preamble",
            backed_by=("case_builder",), promised_on=("/donate",),
        ),
        ToolboxEntry(
            id="court_forms", name="Court forms",
            purpose="Find and fill the court forms that fit your situation.",
            group="act", status="partial", level="L1", engine="action",
            today="Your local courthouse self-help center can help with forms.",
            backed_by=("court_forms", "public_forms"), promised_on=("/donate",),
        ),
        ToolboxEntry(
            id="court_packet", name="Court packet builder",
            purpose="Put your records in order, labeled and ready to hand to a court.",
            group="act", status="partial", level="L1", engine="action",
            today="Start from the start page.", today_path="/preamble",
            backed_by=("court_packet", "packet_builder"),
        ),
        ToolboxEntry(
            id="court_prep", name="Court appearance preparation",
            purpose="Know what happens at a hearing and what to say, including online hearings.",
            group="act", status="partial", level="L0", engine="action",
            today="Start from the start page.", today_path="/preamble",
            backed_by=("zoom_court", "zoom_court_prep"),
        ),
        ToolboxEntry(
            id="letters", name="Sample letters",
            purpose="Plain sample letters: repair requests, deposit requests, records-preservation requests.",
            group="act", status="planned", level="L0", engine="action",
            today="Write your request in your own words, date it, and keep a copy.",
            note="Registered as response_letter_generator but not built.",
        ),
        ToolboxEntry(
            id="deadline_engine", name="Deadline calculator for every notice",
            purpose="Turn the date on a notice into the deadlines that follow from it.",
            group="act", status="partial", level="L1", engine="action",
            today="Eviction deadlines can be calculated today in eviction defense.", today_path="/eviction-defense",
            backed_by=("eviction_defense",),
            note="Eviction deadlines work. A general rules engine for other notices is planned (proven first on the case side).",
        ),
        ToolboxEntry(
            id="document_delivery", name="Document delivery",
            purpose="Send a document and keep a record that it was sent.",
            group="act", status="partial", level="L1", engine="action",
            today="Send by a method that gives you a receipt, and save the receipt.",
            backed_by=("document_delivery",), promised_on=("/privacy",),
        ),
        ToolboxEntry(
            id="pdf_tools", name="PDF tools",
            purpose="Merge, split, and convert PDFs without setting anything up.",
            group="act", status="partial", level="L0", engine="action",
            today="The tool exists inside Semptify. A stand-alone version is being built.", today_path="/preamble",
            backed_by=("pdf_tools",), promised_on=("/tools", "/services"),
            note="Pages say no setup is needed, but the button leads to the general start page.",
        ),
        ToolboxEntry(
            id="document_converter", name="Document converter",
            purpose="Change documents between PDF, Word, web page, and text.",
            group="act", status="partial", level="L0", engine="action",
            today="The tool exists inside Semptify. A stand-alone version is being built.", today_path="/preamble",
            backed_by=("document_converter",), promised_on=("/tools", "/services"),
            note="Same as PDF tools: the button leads to the general start page.",
        ),
        ToolboxEntry(
            id="public_forms", name="Public forms library",
            purpose="Housing forms and templates to download or fill.",
            group="act", status="partial", level="L0", engine="action",
            today="The library exists inside Semptify. A browsable public version is being built.", today_path="/preamble",
            backed_by=("public_forms",), promised_on=("/tools", "/services"),
        ),
        ToolboxEntry(
            id="mobile_app", name="Semptify on your phone",
            purpose="A phone version built for one hand and a small screen.",
            group="act", status="partial", level="L1", engine="page",
            today="semptify.org works in your phone's browser.", today_path="/",
            promised_on=("/donate",),
            note="Semptify Go (the phone app) is a separate earlier build. A dedicated phone toolset is deferred.",
        ),
        # --------------------------------------------------------- TOGETHER
        ToolboxEntry(
            id="tenant_union_finder", name="Find a tenant group near you",
            purpose="Find a local tenants union or tenant organization.",
            group="together", status="planned", level="L0", engine="help",
            today="Dial 211 and ask for tenant organizations in your area.", today_path="tel:211",
            backed_by=("campaign",), promised_on=("/donate",),
            note="Every listing must be reviewed and approved before it appears (listing rules).",
        ),
        ToolboxEntry(
            id="start_a_group", name="Start a tenant group",
            purpose="A plain guide to forming a tenant group: structure, outreach, funding, limits.",
            group="together", status="planned", level="L0", engine="content",
            today="Read the outline on the advocacy page.", today_path="/advocacy",
            promised_on=("/advocacy", "/services", "/donate"),
            note="The advocacy page lists the topics. The guide itself is not written yet.",
        ),
        ToolboxEntry(
            id="reach_legislators", name="Reach your legislators",
            purpose="Find who represents you and how to contact them through official channels.",
            group="together", status="live", level="L0", engine="civic",
            today="Open the official lookup links.", today_path="/reach-legislators",
            promised_on=("/donate",),
            note="Links go only to .gov pages run by the legislatures themselves.",
        ),
        ToolboxEntry(
            id="tell_your_story", name="Tell your story",
            purpose="Share what happened, anonymously, to inform public policy.",
            group="together", status="live", level="L4", engine="civic",
            today="Tell your story.", today_path="/tell-your-story",
            backed_by=("public_forms",), promised_on=("/donate",),
            note="Anonymous stories publish after a moderation pass that removes personal details.",
        ),
        ToolboxEntry(
            id="your_voice", name="Your Voice",
            purpose="Read the housing bill as it is written and ask or weigh in anonymously.",
            group="together", status="live", level="L4", engine="civic",
            today="Open Your Voice.", today_path="/your-voice",
            backed_by=("public_forms",), promised_on=("/", "/hello"),
            note="Answers post through the elevation-gated review lane at /admin/public-voice.",
        ),
        ToolboxEntry(
            id="housing_bill", name="The Minnesota housing bill",
            purpose="A rent assurance and deposit protection bill, written in public.",
            group="together", status="live", level="L4", engine="civic",
            today="Read the bill section.", today_path="/bill",
            promised_on=("/",),
        ),
        ToolboxEntry(
            id="tool_requests", name="Ask for a tool",
            purpose="Tell us what you need. Requests and answers are public.",
            group="together", status="live", level="L0", engine="trust",
            today="Send a tool request.", today_path="/tool-requests",
            backed_by=("public_forms",), promised_on=("/", "/hello"),
        ),
        # ---------------------------------------------------------- HELPERS
        ToolboxEntry(
            id="share_with_legal_aid", name="Share my record with legal aid",
            purpose="Let a legal aid office or attorney see your record, with your consent, and take it back any time.",
            group="helpers", status="partial", level="L2", engine="help",
            today="Download your records and bring them to your appointment.",
            backed_by=("legal_share",),
            note="Built on a branch that is waiting for review.",
            queue_ref="feat/legal-share-portal",
        ),
        ToolboxEntry(
            id="advocate_portal", name="Advocate tools",
            purpose="Help tenants with their consent: shared records, referrals, coordination.",
            group="helpers", status="planned", level="L2", engine="help",
            today="Advocates can help a tenant use Semptify side by side.",
            backed_by=("advocate",), promised_on=("/advocacy", "/services"),
            note="Advocate and legal roles were removed from this app on purpose. They will come back as a separate add-on.",
        ),
        ToolboxEntry(
            id="legal_portal", name="Legal professional tools",
            purpose="Matter files, filing preparation, and exhibits for attorneys working with tenants.",
            group="helpers", status="planned", level="L2", engine="help",
            today="Attorneys can receive a tenant's downloaded record directly.",
            backed_by=("legal", "legal_filing"), promised_on=("/legal-research", "/services"),
            note="Same as advocate tools: will return as a separate add-on.",
        ),
        ToolboxEntry(
            id="agency_connect", name="Agencies connect",
            purpose="A way for housing agencies to receive referrals and share public information.",
            group="helpers", status="planned", level="L2", engine="help",
            today="Agencies can write to the partnerships address.", today_path="/contact",
            promised_on=("/services",),
        ),
        ToolboxEntry(
            id="partnerships", name="Advocacy partnerships",
            purpose="Organizations working with Semptify to serve tenants.",
            group="helpers", status="planned", level="L2", engine="help",
            today="Write to the partnerships address.", today_path="/contact",
            promised_on=("/advocacy", "/donate"),
        ),
        # --------------------------------------------------------- RESEARCH
        ToolboxEntry(
            id="landlord_research", name="Research landlords from public records",
            purpose="Court filings and property records about a landlord, from official public sources.",
            group="research", status="partial", level="L4", engine="civic",
            today="Court records are public through the court's own website.",
            backed_by=("legal_intel", "crawler", "external_mappings"),
            promised_on=("/legal-research", "/services"),
            note="Research tools exist for internal use only. A public version must use sanctioned public sources and show patterns, not target people.",
        ),
        ToolboxEntry(
            id="litigation_intelligence", name="Litigation intelligence",
            purpose="Patterns across housing court cases.",
            group="research", status="partial", level="L4", engine="civic",
            today="Not available to the public yet.",
            backed_by=("litigation_intelligence",), promised_on=("/donate", "/legal-research"),
            note="Marked inactive. One part (graph engine) needs to be built or removed.",
        ),
        ToolboxEntry(
            id="housing_accountability", name="Housing accountability",
            purpose="Find repeated patterns in housing conduct, such as repeated charges.",
            group="research", status="partial", level="L4", engine="civic",
            today="Not available to the public yet.",
            backed_by=("housing_accountability", "accountability_ledger"),
        ),
        ToolboxEntry(
            id="fraud_exposure", name="Fraud documentation",
            purpose="Document patterns of housing fraud from records.",
            group="research", status="partial", level="L4", engine="civic",
            today="Not available to the public yet.",
            backed_by=("fraud_exposure",), promised_on=("/donate",),
        ),
        ToolboxEntry(
            id="public_records_suite", name="Public records suite",
            purpose="Organize public-record findings about housing conduct.",
            group="research", status="partial", level="L4", engine="civic",
            today="Not available to the public yet.",
            backed_by=("public_exposure",), promised_on=("/donate",),
            note="Shown on the donate page as Public Exposure Suite. Public copy should use calmer naming.",
        ),
        ToolboxEntry(
            id="researcher_data", name="Research data access",
            purpose="Aggregate, anonymous datasets for researchers. No personal data.",
            group="research", status="vision", level="L4", engine="civic",
            today="Researchers can write to us.", today_path="/contact",
            promised_on=("/services", "/donate"),
        ),
        ToolboxEntry(
            id="policy_reporting", name="Policy impact reporting",
            purpose="Court data across cities, turned into public reports for lawmakers.",
            group="research", status="vision", level="L4", engine="civic",
            today="See the numbers behind the Minnesota bill.", today_path="/bill/research",
            promised_on=("/donate",),
        ),
        ToolboxEntry(
            id="legal_aid_integration", name="Legal aid system connection",
            purpose="Hand a tenant's record to a legal aid office's own case system, with consent.",
            group="research", status="vision", level="L2", engine="help",
            today="Download your records and bring them to legal aid.",
            promised_on=("/donate",),
        ),
        # --------------------------------------------------------- BUILDERS
        ToolboxEntry(
            id="open_source", name="Open source code",
            purpose="All of Semptify's code is public to read, check, and build on.",
            group="builders", status="live", level="L3", engine="trust",
            today="Read the code on GitHub.", today_path="https://github.com/1semptify-arch/Semptify",
            promised_on=("/", "/donate", "/hello", "/developers"),
        ),
        ToolboxEntry(
            id="api_docs", name="API documentation",
            purpose="Public documentation of every Semptify endpoint.",
            group="builders", status="planned", level="L3", engine="trust",
            today="Read the code on GitHub.", today_path="https://github.com/1semptify-arch/Semptify",
            promised_on=("/developers",),
            note="The developers page listed /docs, /redoc, and /openapi.json — all three still return not-found on semptify.org (re-checked 2026-11-06). Page copy corrected on this branch: the spec ships with the code, public docs are a future decision.",
        ),
        ToolboxEntry(
            id="external_sdk", name="Developer kit (SDK)",
            purpose="A kit for building tools that work with Semptify.",
            group="builders", status="partial", level="L3", engine="trust",
            today="The kit lives in the code repository.", today_path="https://github.com/1semptify-arch/Semptify",
            promised_on=("/developers", "/services"),
        ),
        ToolboxEntry(
            id="module_marketplace", name="Module marketplace",
            purpose="A shared place for community-built modules.",
            group="builders", status="vision", level="L3", engine="trust",
            today="Contributions go through GitHub.", today_path="https://github.com/1semptify-arch/Semptify",
            promised_on=("/developers",),
        ),
        ToolboxEntry(
            id="self_host_kit", name="Run it yourself",
            purpose="A packaged version an advocate or tenant can run on their own computer.",
            group="builders", status="vision", level="L3", engine="record",
            today="The code is open to run today, with technical setup.",
            today_path="https://github.com/1semptify-arch/Semptify",
        ),
        # ---------------------------------------------------------- SUPPORT
        ToolboxEntry(
            id="donations", name="Donations",
            purpose="Support the work through GitHub Sponsors, one time or monthly.",
            group="support", status="live", level="L0", engine="trust",
            today="See how funding works.", today_path="/donate",
            promised_on=("/", "/donate", "/hello", "/your-voice"),
        ),
        ToolboxEntry(
            id="volunteer", name="Volunteer and contribute",
            purpose="Ways to give time: code, review, writing, translation.",
            group="support", status="planned", level="L0", engine="trust",
            today="Contributions go through GitHub.", today_path="https://github.com/1semptify-arch/Semptify",
            promised_on=("/donate",),
        ),
        ToolboxEntry(
            id="feedback", name="Feedback",
            purpose="Tell us what works, what doesn't, and what blocks you.",
            group="support", status="live", level="L0", engine="trust",
            today="Send feedback.", today_path="/feedback",
            promised_on=("/contact", "/accessibility"),
        ),
        ToolboxEntry(
            id="contact_mailboxes", name="Contact addresses",
            purpose="Separate addresses for general, technical, legal, privacy, partnership, and press questions.",
            group="support", status="partial", level="L0", engine="trust",
            today="Use the feedback form, which is confirmed working.", today_path="/feedback",
            promised_on=("/contact", "/help", "/privacy", "/terms", "/disclaimer"),
            note="Nine distinct addresses appear across public pages (hello, tech, legal, privacy, partnerships, press, support, brad, admin) — the contact page shows six of them. Whether each is a working mailbox has not been verified.",
        ),
    ]

    @classmethod
    def all(cls) -> list[ToolboxEntry]:
        return list(cls.ENTRIES)

    @classmethod
    def get(cls, entry_id: str) -> ToolboxEntry | None:
        return next((e for e in cls.ENTRIES if e.id == entry_id), None)

    @classmethod
    def grouped(cls) -> list[tuple[str, dict[str, str], list[ToolboxEntry]]]:
        """Entries grouped in GROUPS order — the shape the /toolbox page renders."""
        return [
            (gid, meta, [e for e in cls.ENTRIES if e.group == gid])
            for gid, meta in cls.GROUPS.items()
        ]

    @classmethod
    def counts(cls) -> dict[str, int]:
        return {s: sum(1 for e in cls.ENTRIES if e.status == s) for s in STATUSES}

    @classmethod
    def page_context(cls) -> dict:
        """Template context shared by /toolbox and /toolbox/{id}."""
        return {
            "groups": cls.grouped(),
            "counts": cls.counts(),
            "status_label": STATUS_LABELS,
            "status_class": STATUS_CLASSES,
            "level_label": LEVEL_LABELS,
        }

    @classmethod
    def to_dict(cls) -> dict:
        return {
            "entries": [e.to_dict() for e in cls.ENTRIES],
            "groups": cls.GROUPS,
            "counts": cls.counts(),
            "total": len(cls.ENTRIES),
        }


toolbox = ToolboxCatalog()
