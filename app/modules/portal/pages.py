"""Portal Pages Registry — SSOT for public website sub-pages.

Each entry is a public page on semptify.org. When a new page is added,
it gets registered here and gets a template — no rewriting existing pages.

Design:
- Additive — new pages are added, not inserted into existing pages
- SSOT — this registry is the only place public pages are defined
- SEO-ready — each page has title, description, keywords for meta tags
- Mobile-first — each template extends public_base.html
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PortalPage:
    """A single public page on the guest portal.

    Immutable — SSOT for one public page.
    """

    id: str  # unique identifier (e.g. "about")
    title: str  # page title for <title> tag
    path: str  # URL path (e.g. "/about")
    template: str  # Jinja2 template path (e.g. "public/about.html")
    description: str = ""  # meta description for SEO
    keywords: str = ""  # meta keywords for SEO
    og_title: str = ""  # OpenGraph title
    og_description: str = ""  # OpenGraph description
    in_sitemap: bool = True  # include in sitemap.xml
    in_footer: bool = True  # include in footer links
    footer_label: str = ""  # label for footer link (defaults to title)
    order: int = 100  # sort order in footer
    redirect_to: str = ""  # external URL the path permanently redirects to (page moved off-app)


@dataclass
class PortalPageRegistry:
    """Central registry — THE source of truth for public pages.

    No main.py or router defines its own page list.
    All public pages flow from here.
    """

    PAGES: ClassVar[list[PortalPage]] = [
        PortalPage(
            id="hello",
            title="Hello — Welcome to Semptify",
            path="/hello",
            template="public/hello.html",
            description="What Semptify is becoming, what's in the works — including a housing bill proposal — where the build stands, and our standing commitments: no cost, no advertising, no tracking.",
            keywords="semptify welcome, under construction, housing bill, tenant rights platform, no tracking, donations",
            og_title="Hello — Welcome to Semptify",
            og_description="What Semptify is becoming, what's in the works, and where the build stands.",
            footer_label="Welcome",
            order=3,
        ),
        PortalPage(
            id="your_voice",
            title="Your Voice — the housing bill, in public — Semptify",
            path="/your-voice",
            template="public/your_voice.html",
            description="Watch an idea become a bill and maybe a law — out in the open. Read the live draft, ask a question, or share an opinion. Anonymous, no names, no tracking.",
            keywords="your voice, housing bill, tenant rights bill, public comment, renters, housing legislation, semptify",
            og_title="Your Voice — the housing bill, in public",
            og_description="Watch an idea become a bill and maybe a law. Read the live draft, ask a question, or share an opinion.",
            footer_label="Your Voice",
            order=4,
            redirect_to="https://semptify.org/your-voice",
        ),
        PortalPage(
            id="tell_your_story",
            title="Tell Your Story — Semptify",
            path="/tell-your-story",
            template="public/tell_your_story.html",
            description="Share what happened in your rental, anonymously. Stories are reviewed to remove personal details, then published to inform the housing bill and public policy.",
            keywords="tell your story, tenant story, renter experience, housing bill, public policy, anonymous",
            og_title="Tell Your Story — Semptify",
            og_description="Share what happened, anonymously. Stories inform the housing bill and public policy.",
            footer_label="Tell your story",
            order=97,
        ),
        PortalPage(
            id="reach_legislators",
            title="Reach Your Legislators — Semptify",
            path="/reach-legislators",
            template="public/reach_legislators.html",
            description="Find who represents you and how to contact them through official government channels — the Minnesota Legislature and the U.S. Congress.",
            keywords="contact legislators, who represents me, Minnesota legislature, housing bill, renters",
            og_title="Reach Your Legislators — Semptify",
            og_description="Find who represents you through official government channels.",
            footer_label="Reach legislators",
            order=98,
        ),
        PortalPage(
            id="what_the_bill_changes",
            title="What the Bill Would Change — Semptify Live, Issue 001",
            path="/what-the-bill-changes",
            template="public/what_the_bill_changes.html",
            description="The Issue 001 cover story: nobody sends you a letter when your rights are violated. What the public housing-documentation bill aims to change — and what it honestly isn't yet.",
            keywords="housing bill, tenant documentation, renter rights, what the bill changes, semptify live, cover story",
            og_title="What the Bill Would Change — Semptify Live",
            og_description="Nobody sends you a letter when your rights are violated. What the public housing bill aims to change.",
            footer_label="The bill",
            order=96,
            redirect_to="https://semptify.org/what-the-bill-changes",
        ),
        PortalPage(
            id="bill",
            title="The Minnesota Rent Assurance Bill — Semptify",
            path="/bill",
            template="public/bill_hub.html",
            description="A Minnesota housing bill written in public — the live draft, the numbers behind it, and how to weigh in. For renters, providers, students, and neighbors.",
            keywords="minnesota housing bill, rent assurance, deposit protection, tenant bill, public bill, semptify",
            og_title="The Minnesota Rent Assurance Bill — in public",
            og_description="A Minnesota housing bill written in public — read the live draft and check the numbers.",
            footer_label="The MN Bill",
            order=4,
            redirect_to="https://semptify.org/bill",
        ),
        PortalPage(
            id="bill_live",
            title="The Live Draft — Minnesota Bill — Semptify",
            path="/bill/live",
            template="public/bill_live.html",
            description="The real working draft of the Minnesota rent assurance bill — refreshed daily, every figure triple-checked or honestly marked.",
            keywords="housing bill live draft, rent assurance text, working draft",
            og_title="The Live Draft — Minnesota Bill",
            og_description="The real working text — refreshed daily.",
            in_footer=False,
            redirect_to="https://semptify.org/bill/live",
        ),
        PortalPage(
            id="bill_research",
            title="The Numbers & Sources — Minnesota Bill — Semptify",
            path="/bill/research",
            template="public/bill_research.html",
            description="Every figure behind the Minnesota rent assurance bill, with its source and verification status — published only after triple-check.",
            keywords="housing bill research, rent assurance figures, bill fact check",
            og_title="The Numbers & Sources — Minnesota Bill",
            og_description="Every figure, its source, and its check status.",
            in_footer=False,
            redirect_to="https://semptify.org/bill/research",
        ),
        PortalPage(
            id="tool_requests",
            title="Tool Requests — Semptify",
            path="/tool-requests",
            template="public/tool_requests.html",
            description="Ask for a tool you need. No name, no email required — every request and our response is posted publicly, because Semptify takes no names and tracks no one.",
            keywords="tool request, request a tool, public requests, tenant tools, semptify",
            og_title="Tool Requests — Semptify",
            og_description="Ask for a tool you need. Every request and our response is posted publicly.",
            footer_label="Tool requests",
            order=95,
        ),
        PortalPage(
            id="portal",
            title="Semptify — Tenant Rights, Documented",
            path="/portal",
            template="public/portal.html",
            description="Upload your documents. Track your deadlines. Build your case. All in one place, and your documents stay in your own cloud storage.",
            keywords="tenant rights, tenant organizer, housing, renter rights, landlord tenant, eviction defense, habitability, security deposit, housing advocacy",
            og_title="Semptify — Tenant Rights, Documented",
            og_description="Upload your documents. Track your deadlines. Build your case. All in one place.",
            footer_label="Get started",
            order=5,
        ),
        PortalPage(
            id="document_everything",
            title="Document Everything — Semptify",
            path="/document-everything",
            template="public/document_everything.html",
            description="Semptify runs on one idea: document everything. A clear, dated record keeps the facts straight — whether or not you ever use Semptify.",
            keywords="document everything, tenant records, rental documentation, tenant rights, keep a record",
            og_title="Document Everything — Semptify",
            og_description="A clear, dated record keeps the facts straight — whether or not you ever use Semptify.",
            footer_label="Document everything",
            order=8,
        ),
        PortalPage(
            id="credit_reports",
            title="Pull Your Own Credit Reports — Semptify",
            path="/credit-reports",
            template="public/credit_reports.html",
            description="A six-step guide to pulling all three of your credit reports from the official government-authorized site — at no cost, no sign-up, no paid service. What you need, how to save them, and what to look for.",
            keywords="credit report, annualcreditreport, credit bureaus, collection account, landlord debt collections, tenant credit, pull credit report",
            og_title="Pull Your Own Credit Reports — Semptify",
            og_description="See what's on your credit reports — all three bureaus, at no cost, on the official site.",
            footer_label="Credit reports",
            order=62,
        ),
        PortalPage(
            id="about",
            title="About Semptify — Tenant Rights Organization",
            path="/about",
            template="public/about.html",
            description="Semptify is a tenant rights organization building technology to protect and advance lawful tenant rights through documentation, education, and record keeping.",
            keywords="about semptify, tenant rights organization, housing advocacy, nonprofit",
            og_title="About Semptify — Tenant Rights Organization",
            og_description="A tenant rights organization building technology to protect renters.",
            footer_label="About",
            order=10,
        ),
        PortalPage(
            id="services",
            title="Our Services — Semptify",
            path="/services",
            template="public/services.html",
            description="Semptify offers tools for tenants, advocates, agencies, donors, and developers. Browse our services catalog.",
            keywords="semptify services, tenant tools, housing services",
            og_title="Our Services — Semptify",
            og_description="Tools for tenants, advocates, agencies, donors, and developers.",
            footer_label="Services",
            order=20,
        ),
        PortalPage(
            id="advocacy",
            title="Advocacy — Semptify",
            path="/advocacy",
            template="public/advocacy.html",
            description="Partner with Semptify as an advocacy organization, or learn how to start a tenant advocacy group in your area.",
            keywords="tenant advocacy, advocacy group, housing advocacy, partner with semptify",
            og_title="Advocacy — Semptify",
            og_description="Partner with Semptify or start a tenant advocacy group.",
            footer_label="Advocacy",
            order=40,
        ),
        PortalPage(
            id="legal_research",
            title="Research Tools — Semptify",
            path="/legal-research",
            template="public/legal_research.html",
            description="Statute and public-records research tools — court filings, property records, and housing patterns.",
            keywords="legal research, landlord research, court filings, property records, housing law",
            og_title="Research Tools — Semptify",
            og_description="Statute and public-records research tools.",
            footer_label="Research",
            order=50,
        ),
        PortalPage(
            id="complaints",
            title="Filing a Complaint — Semptify",
            path="/complaints",
            template="public/complaints.html",
            description="Walk through filing a housing complaint step by step. Habitability, discrimination, retaliation, security deposit disputes.",
            keywords="file housing complaint, habitability complaint, discrimination complaint, retaliation complaint, security deposit dispute",
            og_title="Filing a Complaint — Semptify",
            og_description="Walk through filing a housing complaint step by step.",
            footer_label="Complaints",
            order=60,
        ),
        PortalPage(
            id="donate",
            title="Support Semptify — Every Renter Deserves Peace at Home",
            path="/donate",
            template="public/donate.html",
            description="Support Semptify via GitHub Sponsors — see the platform, the privacy architecture, and the grant funding roadmap.",
            keywords="donate tenant rights, github sponsors, housing nonprofit, support tenants",
            og_title="Support Semptify — Every Renter Deserves Peace at Home",
            og_description="Support Semptify via GitHub Sponsors — see the platform, the privacy architecture, and the grant funding roadmap.",
            footer_label="Donate",
            order=70,
        ),
        PortalPage(
            id="developers",
            title="Developer Hub — Semptify",
            path="/developers",
            template="public/developers.html",
            description="Resources for developers: the Semptify codebase, the developer kit, and how to contribute.",
            keywords="semptify sdk, developer tools, open source, contribute",
            og_title="Developer Hub — Semptify",
            og_description="The code, the developer kit, and how to contribute.",
            footer_label="Developers",
            order=80,
        ),
        PortalPage(
            id="volunteer",
            title="Volunteer — Semptify",
            path="/volunteer",
            template="public/volunteer.html",
            description="Ways to give time to Semptify: code, review, testing, and — when it is ready — translation. Everything is public and every change is reviewed by a person.",
            keywords="volunteer semptify, contribute tenant rights, open source housing, give time nonprofit",
            og_title="Volunteer — Semptify",
            og_description="Ways to give time: code, review, testing. Everything is public and reviewed by a person.",
            footer_label="Volunteer",
            order=85,
        ),
        PortalPage(
            id="tools",
            title="Tools — Semptify",
            path="/tools",
            template="public/tools.html",
            description="PDF tools, document converter, and public forms — three tool sets inside Semptify.",
            keywords="pdf tools, document converter, public forms, housing forms, tenant tools",
            og_title="Tools — Semptify",
            og_description="Three tool sets inside Semptify — PDF tools, document converter, and public forms.",
            footer_label="Tools",
            order=90,
        ),
        PortalPage(
            id="contact",
            title="Contact Semptify",
            path="/contact",
            template="public/contact.html",
            description="Contact Semptify for support, partnership, press, or general inquiries.",
            keywords="contact semptify, support, partnership, press, inquiry",
            og_title="Contact Semptify",
            og_description="Contact Semptify for support, partnership, press, or general inquiries.",
            footer_label="Contact",
            order=100,
        ),
        PortalPage(
            id="privacy",
            title="Privacy Policy — Semptify",
            path="/privacy",
            template="public/privacy.html",
            description="Semptify privacy policy. We never store your documents on our servers. Your data stays in your control.",
            keywords="privacy policy, data privacy, tenant data, document storage",
            og_title="Privacy Policy — Semptify",
            og_description="We never store your documents on our servers. Your data stays in your control.",
            footer_label="Privacy",
            order=110,
        ),
        PortalPage(
            id="terms",
            title="Terms of Use — Semptify",
            path="/terms",
            template="public/terms.html",
            description="Semptify terms of use. Semptify is an organizational tool and educational resource — not a law firm.",
            keywords="terms of use, terms of service, legal terms, semptify terms",
            og_title="Terms of Use — Semptify",
            og_description="Semptify is an organizational tool and educational resource — not a law firm.",
            footer_label="Terms",
            order=120,
        ),
        PortalPage(
            id="help",
            title="Help & Support — Semptify",
            path="/help",
            template="public/help.html",
            description="Help and support for Semptify users. Find answers, contact support, and access emergency resources.",
            keywords="help, support, semptify help, tenant support, emergency resources",
            og_title="Help & Support — Semptify",
            og_description="Help and support for Semptify users.",
            footer_label="Help",
            order=130,
        ),
        PortalPage(
            id="disclaimer",
            title="Legal Disclaimer — Semptify",
            path="/disclaimer",
            template="public/disclaimer.html",
            description="Semptify is an organizational tool and educational resource — not a law firm. We do not provide legal advice.",
            keywords="legal disclaimer, not legal advice, tenant rights, housing law",
            og_title="Legal Disclaimer — Semptify",
            og_description="Semptify is not a law firm and does not provide legal advice.",
            footer_label="Disclaimer",
            order=140,
        ),
        PortalPage(
            id="accessibility",
            title="Accessibility Statement — Semptify",
            path="/accessibility",
            template="public/accessibility.html",
            description="Semptify accessibility statement. We aim for WCAG 2.1 AA across the site and application.",
            keywords="accessibility, WCAG, screen reader, keyboard navigation, accessible design",
            og_title="Accessibility Statement — Semptify",
            og_description="Our accessibility commitment and known limitations.",
            footer_label="Accessibility",
            order=150,
        ),
        PortalPage(
            id="feedback",
            title="Feedback — Semptify",
            path="/feedback",
            template="public/feedback.html",
            description="Share feedback about Semptify. Every message is read.",
            keywords="feedback, contact semptify, report a problem, suggestion",
            og_title="Feedback — Semptify",
            og_description="Share feedback about Semptify.",
            footer_label="Feedback",
            order=160,
        ),
        PortalPage(
            id="credits",
            title="Open Source Credits — Semptify",
            path="/credits",
            template="public/credits.html",
            description="Semptify is built on excellent open source software. Licenses and credits for every dependency.",
            keywords="open source, credits, licenses, semptify dependencies",
            og_title="Open Source Credits — Semptify",
            og_description="Licenses and credits for the software Semptify is built on.",
            footer_label="Credits",
            order=170,
        ),
        PortalPage(
            id="toolbox",
            title="The Toolbox — what works today, what is coming — Semptify",
            path="/toolbox",
            template="public/toolbox.html",
            description="Every tool and service Semptify has mentioned, with an honest status and what you can do right now.",
            keywords="semptify tools, tenant tools, what works today, roadmap, honest status",
            og_title="The Toolbox — Semptify",
            og_description="Every tool Semptify has mentioned, and where each one honestly stands.",
            footer_label="The Toolbox",
            order=6,
        ),
        # ---------------------------------------------------------------
        # The six pillar front pages — the doors onto the path
        # (SEMPTIFY_ORG_ARCHITECTURE_DRAFT.md §2, §4.2). One shared template;
        # per-pillar content comes from app/modules/portal/pillars.py.
        # in_footer=False: the six doors belong on the front door and the
        # toolbox, not repeated in the universal footer.
        # ---------------------------------------------------------------
        PortalPage(
            id="information",
            title="Information — know your rights — Semptify",
            path="/path/information",
            template="public/pillar_front.html",
            description="Know your rights before the dispute starts. Plain-language, sourced answers about tenant rights: the law library, situation guides, state pages, and a glossary.",
            keywords="tenant rights, know your rights, renter rights information, housing law library",
            og_title="Information — know your rights — Semptify",
            og_description="Plain-language, sourced answers about tenant rights and process.",
            in_footer=False,
        ),
        PortalPage(
            id="research",
            title="Research — what applies to my situation — Semptify",
            path="/path/research",
            template="public/pillar_front.html",
            description="Go deeper than the general rules: situation research, a case law reader, and a credit report guide — checked against the facts of your own situation.",
            keywords="tenant research, housing law research, case law, credit report guide",
            og_title="Research — Semptify",
            og_description="Go deeper than the general rules: statutes, records, and patterns for your situation.",
            in_footer=False,
        ),
        PortalPage(
            id="documentation",
            title="Documentation — a paper trail you can trust — Semptify",
            path="/path/documentation",
            template="public/pillar_front.html",
            description="A dated record of every notice, payment, repair request, and conversation — kept in your own storage. Journal, calendar, contacts, rent ledger, quick capture, vault, and checklists.",
            keywords="document everything, tenant records, rental documentation, paper trail, rent ledger",
            og_title="Documentation — Semptify",
            og_description="A dated record of every notice, payment, repair request, and conversation.",
            in_footer=False,
        ),
        PortalPage(
            id="organize",
            title="Organize — one record a stranger can follow — Semptify",
            path="/path/organize",
            template="public/pillar_front.html",
            description="Turn scattered photos, texts, and papers into one coherent record: timeline, document center, case builder, exports, and stand-alone PDF and conversion tools.",
            keywords="organize documents, tenant timeline, case builder, pdf tools, document converter",
            og_title="Organize — Semptify",
            og_description="Turn scattered photos, texts, and papers into one coherent record.",
            in_footer=False,
        ),
        PortalPage(
            id="collaborate",
            title="Collaborate — find who else is in this — Semptify",
            path="/path/collaborate",
            template="public/pillar_front.html",
            description="Find a tenants association or advocate near you, or learn how to start one: group finder, a start-a-group field guide, and a group toolkit.",
            keywords="tenant association, tenant group, tenants union, housing advocacy, organize neighbors",
            og_title="Collaborate — Semptify",
            og_description="Find a tenants association or advocate, or start one.",
            in_footer=False,
        ),
        PortalPage(
            id="be_heard",
            title="Be heard — make it count — Semptify",
            path="/path/be-heard",
            template="public/pillar_front.html",
            description="Put it on the record where it counts: complaint wizard, eviction defense, court forms and prep, sample letters, reaching your legislators, and telling your story.",
            keywords="file housing complaint, eviction defense, court forms, reach legislators, tell your story",
            og_title="Be heard — Semptify",
            og_description="File a legitimate complaint and pass your story to whoever will listen.",
            in_footer=False,
        ),
    ]

    @classmethod
    def get_page(cls, page_id: str) -> PortalPage | None:
        """Get a single page by ID."""
        for p in cls.PAGES:
            if p.id == page_id:
                return p
        return None

    @classmethod
    def get_page_by_path(cls, path: str) -> PortalPage | None:
        """Get a single page by URL path."""
        for p in cls.PAGES:
            if p.path == path:
                return p
        return None

    @classmethod
    def get_footer_pages(cls) -> list[PortalPage]:
        """Return pages that should appear in the footer, sorted by order."""
        return sorted([p for p in cls.PAGES if p.in_footer], key=lambda p: p.order)

    @classmethod
    def get_sitemap_pages(cls) -> list[PortalPage]:
        """Return pages that should appear in the sitemap, sorted by path."""
        return sorted([p for p in cls.PAGES if p.in_sitemap], key=lambda p: p.path)

    @classmethod
    def to_dict(cls) -> dict:
        """Export complete page registry for API consumption."""
        return {
            "pages": [
                {
                    "id": p.id,
                    "title": p.title,
                    "path": p.path,
                    "template": p.template,
                    "description": p.description,
                    "in_sitemap": p.in_sitemap,
                    "in_footer": p.in_footer,
                    "footer_label": p.footer_label,
                    "order": p.order,
                }
                for p in cls.PAGES
            ],
            "total_pages": len(cls.PAGES),
        }


# Global instance — import this
portal_pages = PortalPageRegistry()
