"""Nonprofit Office — sourced rules for forming and running a Minnesota 501(c)(3).

Every rule here carries the source it came from and the date it was checked.
Items marked ``verified=False`` are well-known practice that was not re-checked
against the source on the stated date — confirm on the source before relying.

This is organizational guidance for Semptify's own entity, not legal advice.
Fees and thresholds change; re-check the source at the moment of filing.
"""

from __future__ import annotations

VERIFIED_ON = "2026-11-08"
FEES_VERIFIED_ON = "2026-11-05"

SOURCES: dict[str, dict[str, str]] = {
    "mn_317a_111": {
        "label": "Minn. Stat. § 317A.111 — required contents of articles",
        "url": "https://www.revisor.mn.gov/statutes/cite/317A.111",
    },
    "mn_317a_203": {
        "label": "Minn. Stat. § 317A.203 — board of three or more individuals",
        "url": "https://www.revisor.mn.gov/statutes/cite/317A.203",
    },
    "mn_317a_231": {
        "label": "Minn. Stat. § 317A.231 — board meetings: at least yearly, remote allowed, 5 days' notice",
        "url": "https://www.revisor.mn.gov/statutes/cite/317A.231",
    },
    "mn_317a_235": {
        "label": "Minn. Stat. § 317A.235 — quorum is a majority unless bylaws set otherwise (never under one-third)",
        "url": "https://www.revisor.mn.gov/statutes/cite/317A.235",
    },
    "mn_317a_237": {
        "label": "Minn. Stat. § 317A.237 — act of the board: majority of directors present and entitled to vote; no proxy voting",
        "url": "https://www.revisor.mn.gov/statutes/cite/317A.237",
    },
    "mn_317a_239": {
        "label": "Minn. Stat. § 317A.239 — action without a meeting: written action signed by all directors",
        "url": "https://www.revisor.mn.gov/statutes/cite/317A.239",
    },
    "mn_317a_255": {
        "label": "Minn. Stat. § 317A.255 — director conflicts of interest: disclose, interested director does not count",
        "url": "https://www.revisor.mn.gov/statutes/cite/317A.255",
    },
    "mn_317a_305": {
        "label": "Minn. Stat. § 317A.305 — duties of the president and treasurer",
        "url": "https://www.revisor.mn.gov/statutes/cite/317A.305",
    },
    "mn_317a_811": {
        "label": "Minn. Stat. § 317A.811 — notice to the Attorney General before dissolving or moving substantially all assets",
        "url": "https://www.revisor.mn.gov/statutes/cite/317A.811",
    },
    "mn_sos_fees": {
        "label": "MN Secretary of State — business filing fee schedule (nonprofit articles $70 mail / $90 expedited)",
        "url": "https://www.sos.state.mn.us/business-liens/business-filing-and-certification-fee-schedule/",
    },
    "mn_sos_articles_form": {
        "label": "MN Secretary of State — nonprofit articles form (says 501(c)(3) filers need IRS language, not this form)",
        "url": "https://www.sos.mn.gov/media/6178/nonprofitarticlesofincorporation.pdf",
    },
    "mn_sos_renewal": {
        "label": "MN Secretary of State — nonprofit annual renewal: due December 31, no fee, dissolution if missed (§ 317A.823)",
        "url": "https://www.sos.mn.gov/media/1534/nonprofitrenewal.pdf",
    },
    "mn_309_52": {
        "label": "Minn. Stat. § 309.52 — register with the Attorney General within 30 days of passing $25,000 in contributions; $25 fee",
        "url": "https://www.revisor.mn.gov/statutes/cite/309.52",
    },
    "mn_309_53": {
        "label": "Minn. Stat. § 309.53 — Attorney General annual report: 15th day of the 7th month after year end; $50 late fee; audit over $750,000 revenue",
        "url": "https://www.revisor.mn.gov/statutes/cite/309.53",
    },
    "mn_ag_due_dates": {
        "label": "MN Attorney General — charity annual report due-date table",
        "url": "https://www.ag.state.mn.us/Charity/PDF/CharOrgDueDates.pdf",
    },
    "mn_st16": {
        "label": "MN Department of Revenue — Form ST16, nonprofit sales tax exemption (separate from federal exemption; about 60 days)",
        "url": "https://www.revenue.state.mn.us/application-nonprofit-exempt-status",
    },
    "mcn_start": {
        "label": "Minnesota Council of Nonprofits — forms, fees, sample articles",
        "url": "https://minnesotanonprofits.org/resources-tools/starting-a-nonprofit/forms-fees-publications",
    },
    "mcn_alternatives": {
        "label": "Minnesota Council of Nonprofits — alternatives to starting a nonprofit (fiscal sponsorship, fee around 10%)",
        "url": "https://minnesotanonprofits.org/resources-tools/starting-a-nonprofit/alternatives-to-starting-a-nonprofit",
    },
    "propel_fiscal": {
        "label": "Propel Nonprofits — board's guide to fiscal sponsorship (fee usually 5–10%)",
        "url": "https://propelnonprofits.org/wp-content/uploads/2024/02/Fiscal-Sponsorship-Guide-for-Hosts-FINAL.pdf",
    },
    "irs_pub557_language": {
        "label": "IRS — suggested articles language (Publication 557)",
        "url": "https://www.irs.gov/charities-non-profits/suggested-language-for-corporations-and-associations-per-publication-557",
    },
    "irs_ein": {
        "label": "IRS — apply for an Employer Identification Number (no cost)",
        "url": "https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online",
    },
    "irs_1023ez_fee": {
        "label": "IRS — user fee: Form 1023-EZ $275, Form 1023 $600",
        "url": "https://www.irs.gov/charities-non-profits/form-1023-and-1023-ez-amount-of-user-fee",
    },
    "irs_1023ez_instr": {
        "label": "IRS — Form 1023-EZ instructions: eligibility worksheet; file within 27 months for exemption back to formation",
        "url": "https://www.irs.gov/instructions/i1023ez",
    },
    "irs_990_which": {
        "label": "IRS — which 990 form: 990-N ≤ $50,000 normal receipts; 990-EZ < $200,000 receipts and < $500,000 assets; else 990",
        "url": "https://www.irs.gov/charities-non-profits/form-990-series-which-forms-do-exempt-organizations-file-filing-phase-in",
    },
    "irs_990_due": {
        "label": "IRS — 990 due the 15th day of the 5th month after year end (Form 8868 extends 990/990-EZ 6 months; 990-N cannot be extended)",
        "url": "https://www.irs.gov/charities-non-profits/annual-exempt-organization-return-due-date",
    },
    "irs_revocation": {
        "label": "IRS — automatic revocation after 3 consecutive years without a 990 filing",
        "url": "https://www.irs.gov/charities-non-profits/automatic-revocation-of-exemption",
    },
    "irs_990t": {
        "label": "IRS — Form 990-T required at $1,000+ gross unrelated business income",
        "url": "https://www.irs.gov/charities-non-profits/unrelated-business-income-tax",
    },
    "irs_ack": {
        "label": "IRS — written acknowledgment for any single gift of $250 or more; what it must say",
        "url": "https://www.irs.gov/charities-non-profits/charitable-organizations/charitable-contributions-written-acknowledgments",
    },
    "irs_quid": {
        "label": "IRS — disclosure required for a payment over $75 that is partly a gift and partly goods/services",
        "url": "https://www.irs.gov/charities-non-profits/charitable-organizations/charitable-contributions-quid-pro-quo-contributions",
    },
    "irs_public_support": {
        "label": "IRS — public support test: one-third of support from the general public, measured over 5 years",
        "url": "https://www.irs.gov/charities-non-profits/exempt-organizations-annual-reporting-requirements-form-990-schedules-a-and-b-public-charity-support-test",
    },
    "irs_990_instr": {
        "label": "IRS — Form 990 instructions (Part VI governance questions; Part IX functional expenses)",
        "url": "https://www.irs.gov/instructions/i990",
    },
    "irs_employment": {
        "label": "IRS — employment taxes for exempt organizations (Form 941 quarterly, W-2 by January 31)",
        "url": "https://www.irs.gov/charities-non-profits/employment-taxes-for-exempt-organizations",
    },
    "irs_teos": {
        "label": "IRS — Tax Exempt Organization Search (confirm determination is listed)",
        "url": "https://apps.irs.gov/app/eos/",
    },
    "repo_articles_draft": {
        "label": "Repo draft — MN articles with IRS 501(c)(3) clauses (docs/org/MN_ARTICLES_OF_INCORPORATION_501c3_DRAFT.md)",
        "url": "",
    },
}

PHASES: list[dict[str, str]] = [
    {"id": "prepare", "title": "Get ready", "summary": "People, name, and address — decisions only you can make."},
    {"id": "mn_formation", "title": "Form the Minnesota corporation", "summary": "File the articles, hold the first board meeting, get the EIN."},
    {"id": "federal", "title": "Federal tax exemption", "summary": "Apply to the IRS for 501(c)(3) recognition."},
    {"id": "mn_after", "title": "Minnesota after exemption", "summary": "Charity registration, sales tax exemption, yearly renewal."},
]

FORMATION_STEPS: list[dict] = [
    {
        "id": "board_three",
        "phase": "prepare",
        "title": "Line up three directors",
        "why": "Minnesota requires a board of three or more people. The articles, the first meeting, and the IRS form all need them.",
        "how": "You plus two others who agree to serve. Record them on the Board tab.",
        "cost_cents": 0,
        "source_ids": ["mn_317a_203"],
        "verified": True,
    },
    {
        "id": "name_check",
        "phase": "prepare",
        "title": "Check the corporate name is available",
        "why": "The Secretary of State rejects names already in use.",
        "how": "Search the name on the Secretary of State business search. Reserving it is optional ($35 mail / $55 online) and only worth it if filing is delayed.",
        "cost_cents": 0,
        "source_ids": ["mn_sos_fees"],
        "verified": True,
    },
    {
        "id": "registered_office",
        "phase": "prepare",
        "title": "Choose the registered office address",
        "why": "The articles need a Minnesota street address (a P.O. box alone is not accepted). It becomes permanent public record.",
        "how": "Decide between a home address, a trusted partner's office, or a paid registered-agent address. An agent name is optional; the address is not.",
        "cost_cents": 0,
        "source_ids": ["mn_317a_111", "mn_sos_renewal"],
        "verified": True,
    },
    {
        "id": "counsel_check",
        "phase": "prepare",
        "title": "Get a no-cost legal check of the draft articles",
        "why": "An amendment after filing costs $35–$55 and a delay. A check before filing avoids it.",
        "how": "Bring the repo draft articles to a Minnesota nonprofit legal clinic (the Minnesota Council of Nonprofits lists options). Ask about purpose wording, the address, and naming directors in the articles.",
        "cost_cents": 0,
        "source_ids": ["repo_articles_draft", "mcn_start"],
        "verified": True,
    },
    {
        "id": "mn_articles",
        "phase": "mn_formation",
        "title": "File the articles of incorporation with the Secretary of State",
        "why": "This creates the Minnesota nonprofit corporation (Chapter 317A). The standard state form is not enough for 501(c)(3); the articles must carry the IRS purpose, non-inurement, and dissolution clauses.",
        "how": "Use the repo draft articles (IRS language included). Mail = $70, slower. Online or in person = $90, expedited. Keep the filed copy — every later step needs it.",
        "cost_cents": 7000,
        "source_ids": ["mn_sos_fees", "mn_sos_articles_form", "irs_pub557_language", "repo_articles_draft"],
        "verified": True,
        "fee_verified_on": FEES_VERIFIED_ON,
    },
    {
        "id": "org_meeting",
        "phase": "mn_formation",
        "title": "Hold the organizational board meeting",
        "why": "The board adopts the rules the IRS and funders ask about, and names the officers Minnesota expects (president and treasurer).",
        "how": "Use the Meetings tab, kind 'organizational'. Adopt bylaws and a conflict-of-interest policy, elect president and treasurer, set the fiscal year, authorize the EIN, bank account, and IRS application.",
        "cost_cents": 0,
        "source_ids": ["mn_317a_305", "mn_317a_231", "irs_990_instr"],
        "verified": True,
    },
    {
        "id": "ein",
        "phase": "mn_formation",
        "title": "Get the EIN from the IRS",
        "why": "The organization's federal ID. Needed for the bank, the IRS application, and every funder's W-9.",
        "how": "Apply online at IRS.gov after the articles come back filed. No cost; issued the same day.",
        "cost_cents": 0,
        "source_ids": ["irs_ein"],
        "verified": True,
    },
    {
        "id": "bank_account",
        "phase": "mn_formation",
        "title": "Open a bank account in the organization's name",
        "why": "Organization money must stay separate from personal money. Funders send grants to the organization's account only.",
        "how": "Bring the filed articles, the EIN letter, and the board resolution authorizing the account. Record the opening on the Books tab.",
        "cost_cents": 0,
        "source_ids": ["mn_317a_305"],
        "verified": False,
    },
    {
        "id": "ez_eligibility",
        "phase": "federal",
        "title": "Confirm Form 1023-EZ eligibility",
        "why": "The short form costs $275 instead of $600. It requires gross receipts of $50,000 or less in each of the past 3 and next 3 years, and total assets of $250,000 or less.",
        "how": "Complete the eligibility worksheet in the 1023-EZ instructions. The Books tab shows actual receipts and assets.",
        "cost_cents": 0,
        "source_ids": ["irs_1023ez_instr"],
        "verified": True,
    },
    {
        "id": "form_1023ez",
        "phase": "federal",
        "title": "File Form 1023-EZ",
        "why": "This is the IRS request to recognize Semptify as a 501(c)(3) public charity. Filed within 27 months of formation, exemption reaches back to the formation date.",
        "how": "File online through Pay.gov with the $275 user fee. The calendar shows the 27-month date.",
        "cost_cents": 27500,
        "source_ids": ["irs_1023ez_fee", "irs_1023ez_instr"],
        "verified": True,
        "fee_verified_on": FEES_VERIFIED_ON,
    },
    {
        "id": "determination_letter",
        "phase": "federal",
        "title": "Receive and file the IRS determination letter",
        "why": "This is what funders ask for. Until it arrives, say plainly that tax-deductibility is pending.",
        "how": "Save the letter and record the date on the Profile. Confirm the organization appears in the IRS Tax Exempt Organization Search.",
        "cost_cents": 0,
        "source_ids": ["irs_teos"],
        "verified": True,
    },
    {
        "id": "ag_registration",
        "phase": "mn_after",
        "title": "Register with the Minnesota Attorney General (when required)",
        "why": "Required within 30 days after contributions pass $25,000 in a year, or sooner if paid fundraisers are used. Fee $25.",
        "how": "File the Charitable Organization Registration Statement. The Books tab warns before the $25,000 line is crossed.",
        "cost_cents": 2500,
        "source_ids": ["mn_309_52"],
        "verified": True,
    },
    {
        "id": "st16",
        "phase": "mn_after",
        "title": "Apply for Minnesota sales tax exemption (Form ST16)",
        "why": "Federal exemption does not cover Minnesota sales tax. Approval lets the organization buy supplies and equipment tax-free.",
        "how": "Send Form ST16 with the articles and IRS letter to the Department of Revenue. No fee; about 60 days.",
        "cost_cents": 0,
        "source_ids": ["mn_st16"],
        "verified": True,
    },
    {
        "id": "first_renewal",
        "phase": "mn_after",
        "title": "File the first Minnesota annual renewal",
        "why": "Due by December 31 every year starting the calendar year after filing. Missing it dissolves the corporation.",
        "how": "File online with the Secretary of State. No fee. The calendar tracks it every year.",
        "cost_cents": 0,
        "source_ids": ["mn_sos_renewal"],
        "verified": True,
    },
]

COST_PATHS: list[dict] = [
    {
        "id": "diy_mail",
        "title": "Do it yourself, file articles by mail",
        "total_cents": 34500,
        "lines": [("Minnesota articles (mail)", 7000), ("EIN", 0), ("Form 1023-EZ", 27500)],
        "tradeoff": "Lowest cost. Mail is slower (weeks). The drafted articles and this module cover the paperwork.",
        "recommended": True,
        "source_ids": ["mn_sos_fees", "irs_1023ez_fee"],
    },
    {
        "id": "diy_online",
        "title": "Do it yourself, file articles online",
        "total_cents": 36500,
        "lines": [("Minnesota articles (online, expedited)", 9000), ("EIN", 0), ("Form 1023-EZ", 27500)],
        "tradeoff": "$20 more for a 2–5 business day turnaround on the articles.",
        "recommended": False,
        "source_ids": ["mn_sos_fees", "irs_1023ez_fee"],
    },
    {
        "id": "full_1023",
        "title": "Full Form 1023 (only if not eligible for the short form)",
        "total_cents": 67000,
        "lines": [("Minnesota articles (mail)", 7000), ("EIN", 0), ("Form 1023", 60000)],
        "tradeoff": "Needed only if projected receipts exceed $50,000 a year or assets exceed $250,000. Much longer application.",
        "recommended": False,
        "source_ids": ["irs_1023ez_fee", "irs_1023ez_instr"],
    },
    {
        "id": "paid_service",
        "title": "Paid filing service or attorney",
        "total_cents": None,
        "lines": [("Same government fees as above", 34500), ("Service or attorney fee", None)],
        "tradeoff": "Government fees do not go down — the service fee is added on top. You still recruit the board and adopt the bylaws. Check the provider's own price page; a no-cost legal clinic check of the drafted articles covers most of the value.",
        "recommended": False,
        "source_ids": ["mcn_start"],
    },
    {
        "id": "fiscal_sponsor",
        "title": "Fiscal sponsorship (accept grants before the IRS letter)",
        "total_cents": None,
        "lines": [("Sponsor's fee on money received", None)],
        "tradeoff": "An existing 501(c)(3) receives tax-deductible gifts and grants for the project and keeps control of the funds. Fee usually 5–10% of money received. Useful as a bridge while the IRS application is pending; needs a written agreement.",
        "recommended": False,
        "source_ids": ["mcn_alternatives", "propel_fiscal"],
    },
]

POLICIES: list[dict] = [
    {
        "id": "bylaws",
        "title": "Bylaws",
        "why": "The board's operating rules: number of directors, terms, officers, meetings, quorum, notice, fiscal year, amendments.",
        "required_by": "Expected by the IRS application and every funder.",
        "outline": [
            "Purpose (matches the articles)",
            "Directors: number (three or more), terms, how elected, removal, vacancies",
            "Officers: president and treasurer (plus secretary if wanted), duties, terms",
            "Meetings: at least one per year, regular schedule, special meetings, 5 days' notice unless set in advance, remote participation",
            "Quorum (majority unless set otherwise, never under one-third) and voting",
            "Action without a meeting by written action of all directors",
            "Conflicts of interest (points to the policy)",
            "Fiscal year, signing authority, books and records",
            "No members (board-run)",
            "Amending the bylaws",
        ],
        "source_ids": ["mn_317a_203", "mn_317a_231", "mn_317a_235", "mn_317a_239", "mn_317a_305"],
    },
    {
        "id": "conflict_of_interest",
        "title": "Conflict-of-interest policy",
        "why": "Form 990 asks whether one exists and is monitored. Minnesota law sets the disclosure-and-recusal procedure.",
        "required_by": "Form 990 Part VI; Minn. Stat. § 317A.255.",
        "outline": [
            "What counts as a conflict (director, family, related organization, financial interest)",
            "Duty to disclose before the board acts",
            "Interested director leaves the vote and does not count toward approval",
            "Board confirms the deal is fair and reasonable",
            "Minutes record the disclosure and the vote",
            "Each director signs a yearly disclosure statement",
        ],
        "source_ids": ["mn_317a_255", "irs_990_instr"],
    },
    {
        "id": "whistleblower",
        "title": "Whistleblower policy",
        "why": "Form 990 asks whether one exists. Protects anyone who reports a concern in good faith.",
        "required_by": "Form 990 Part VI.",
        "outline": ["How to report a concern", "Who receives reports (a director other than the subject)", "No retaliation", "Confidentiality", "How reports are investigated and recorded"],
        "source_ids": ["irs_990_instr"],
    },
    {
        "id": "document_retention",
        "title": "Document retention and destruction policy",
        "why": "Form 990 asks whether one exists. Keeps the records the law and funders expect.",
        "required_by": "Form 990 Part VI.",
        "outline": [
            "Keep permanently: articles, bylaws, amendments, minutes, IRS letter, annual filings",
            "Keep at least 7 years: financial records, bank statements, receipts, payroll",
            "Grant records: as long as the grant agreement requires",
            "Stop destruction when any legal matter or audit is pending",
            "Who is responsible",
        ],
        "source_ids": ["irs_990_instr"],
    },
    {
        "id": "gift_acceptance",
        "title": "Gift acceptance policy",
        "why": "Decides ahead of time which gifts the organization will and will not take, and how gifts are acknowledged.",
        "required_by": "Good practice; supports the IRS acknowledgment rules.",
        "outline": [
            "Gifts that fit the mission are accepted; gifts with conditions that conflict with the mission are declined",
            "Written acknowledgment for any single gift of $250 or more",
            "Disclosure for payments over $75 that include goods or services",
            "Restricted gifts are tracked in their own fund and used only as the donor specified",
            "No gifts that buy influence over Semptify's content or tenants' information",
        ],
        "source_ids": ["irs_ack", "irs_quid"],
    },
    {
        "id": "financial_controls",
        "title": "Financial controls policy",
        "why": "The treasurer keeps accurate records and pays only as the board orders. A written policy makes that routine.",
        "required_by": "Minn. Stat. § 317A.305 (treasurer duties); funders' due-diligence questions.",
        "outline": [
            "Board approves a yearly budget",
            "Spending limit above which board approval is required",
            "Two people see every bank statement",
            "Receipts kept for every expense",
            "Treasurer's report at every board meeting",
            "Expense reimbursement with receipts only",
        ],
        "source_ids": ["mn_317a_305"],
    },
]

GRANT_READINESS: list[dict] = [
    {"id": "entity", "title": "Minnesota corporation filed", "why": "Funders give to an organization, not a person.", "source_ids": ["mn_317a_111"]},
    {"id": "ein", "title": "EIN", "why": "Goes on the W-9 every funder asks for.", "source_ids": ["irs_ein"]},
    {"id": "exemption", "title": "IRS determination letter — or a fiscal sponsor", "why": "Most foundations grant only to 501(c)(3) public charities or through a fiscal sponsor.", "source_ids": ["irs_teos", "mcn_alternatives"]},
    {"id": "board", "title": "Board of three or more", "why": "Funders ask for the board list.", "source_ids": ["mn_317a_203"]},
    {"id": "bylaws", "title": "Bylaws adopted", "why": "Standard attachment to applications.", "source_ids": ["mn_317a_203"]},
    {"id": "coi", "title": "Conflict-of-interest policy adopted", "why": "Due-diligence question on most applications and on Form 990.", "source_ids": ["mn_317a_255"]},
    {"id": "bank", "title": "Bank account in the organization's name", "why": "Grants are paid to the organization's account.", "source_ids": ["mn_317a_305"]},
    {"id": "budget", "title": "This year's budget approved by the board", "why": "Every application asks for an organizational budget.", "source_ids": []},
    {"id": "books", "title": "Books kept for the current year", "why": "Funders ask for financial statements; the Books tab produces them.", "source_ids": ["irs_990_instr"]},
    {"id": "ag", "title": "Attorney General registration (if required)", "why": "Required after $25,000 in contributions; funders check.", "source_ids": ["mn_309_52"]},
    {"id": "mission", "title": "Mission and program description written", "why": "The first section of every application.", "source_ids": []},
]

MEETING_KINDS = ("organizational", "regular", "annual", "special")

AGENDA_TEMPLATE: list[str] = [
    "Call to order; who is present; quorum confirmed",
    "Conflict-of-interest disclosures for anything on this agenda",
    "Approve minutes of the last meeting",
    "Treasurer's report (from the Books tab)",
    "Compliance calendar: what is due before the next meeting",
    "Old business",
    "New business and motions",
    "Set the next meeting date (announcing it here removes the need for separate notice)",
    "Adjourn",
]

ORGANIZATIONAL_AGENDA: list[str] = [
    "Call to order; directors present; quorum confirmed",
    "Accept the filed articles of incorporation",
    "Adopt the bylaws",
    "Adopt the conflict-of-interest policy; each director signs a disclosure",
    "Elect officers: president and treasurer (and secretary, if used)",
    "Set the fiscal year",
    "Authorize the EIN application",
    "Authorize opening a bank account and name who may sign",
    "Authorize filing Form 1023-EZ and paying the $275 fee",
    "Adopt the whistleblower, document retention, gift acceptance, and financial controls policies",
    "Set the regular meeting schedule",
    "Adjourn",
]

INCOME_CATEGORIES: dict[str, str] = {
    "contribution": "Contributions and gifts",
    "grant": "Grants",
    "program_service": "Program service revenue",
    "investment": "Interest and investment income",
    "unrelated_business": "Unrelated business income",
    "other": "Other revenue",
}

FUNCTIONAL_CLASSES: dict[str, str] = {
    "program": "Program services",
    "management_general": "Management and general",
    "fundraising": "Fundraising",
}

EXPENSE_CATEGORIES: dict[str, str] = {
    "hosting_software": "Hosting and software",
    "filing_fees": "Filing and government fees",
    "professional_fees": "Professional fees (legal, accounting)",
    "supplies": "Supplies",
    "printing_postage": "Printing and postage",
    "insurance": "Insurance",
    "travel": "Travel",
    "compensation": "Compensation",
    "grants_paid": "Grants paid to others",
    "other": "Other expenses",
}

HONESTY_NOTES: list[str] = [
    "Gifts to a personal GitHub Sponsors account are personal gifts, not contributions to the organization, and are not tax-deductible. Record them in the books only if they are actually transferred to the organization's account.",
    "Until the IRS determination letter arrives, describe tax-deductibility as pending. If Form 1023-EZ is filed within 27 months of formation and approved, exemption reaches back to the formation date.",
    "No political campaign activity, ever. Lobbying must stay an insubstantial part of activities (the articles say this).",
]


def sources_for(ids: list[str]) -> list[dict[str, str]]:
    return [{"id": i, **SOURCES[i]} for i in ids if i in SOURCES]


def knowledge_bundle() -> dict:
    """Everything static, with sources resolved — served to the page."""

    def with_sources(items: list[dict]) -> list[dict]:
        return [{**item, "sources": sources_for(item.get("source_ids", []))} for item in items]

    return {
        "verified_on": VERIFIED_ON,
        "fees_verified_on": FEES_VERIFIED_ON,
        "phases": PHASES,
        "steps": with_sources(FORMATION_STEPS),
        "cost_paths": [
            {**p, "lines": [{"label": label, "cents": cents} for label, cents in p["lines"]], "sources": sources_for(p["source_ids"])}
            for p in COST_PATHS
        ],
        "policies": with_sources(POLICIES),
        "grant_readiness": with_sources(GRANT_READINESS),
        "agenda_template": AGENDA_TEMPLATE,
        "organizational_agenda": ORGANIZATIONAL_AGENDA,
        "meeting_kinds": list(MEETING_KINDS),
        "income_categories": INCOME_CATEGORIES,
        "functional_classes": FUNCTIONAL_CLASSES,
        "expense_categories": EXPENSE_CATEGORIES,
        "honesty_notes": HONESTY_NOTES,
        "sources": SOURCES,
    }
