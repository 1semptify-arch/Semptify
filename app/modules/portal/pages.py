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
    id: str                          # unique identifier (e.g. "about")
    title: str                       # page title for <title> tag
    path: str                        # URL path (e.g. "/about")
    template: str                    # Jinja2 template path (e.g. "public/about.html")
    description: str = ""            # meta description for SEO
    keywords: str = ""               # meta keywords for SEO
    og_title: str = ""               # OpenGraph title
    og_description: str = ""         # OpenGraph description
    in_sitemap: bool = True          # include in sitemap.xml
    in_footer: bool = True           # include in footer links
    footer_label: str = ""           # label for footer link (defaults to title)
    order: int = 100                 # sort order in footer


@dataclass
class PortalPageRegistry:
    """Central registry — THE source of truth for public pages.

    No main.py or router defines its own page list.
    All public pages flow from here.
    """

    PAGES: ClassVar[list[PortalPage]] = [
        PortalPage(
            id="portal",
            title="Semptify — Tenant Rights, Documented",
            path="/portal",
            template="public/portal.html",
            description="Upload your documents. Track your deadlines. Build your case. All in one place, no cost, and your documents stay in your own cloud storage.",
            keywords="tenant rights, tenant organizer, housing, renter rights, landlord tenant, eviction defense, habitability, security deposit, housing advocacy",
            og_title="Semptify — Tenant Rights, Documented",
            og_description="Upload your documents. Track your deadlines. Build your case. All in one place.",
            footer_label="Get started",
            order=5,
        ),
        PortalPage(
            id="about",
            title="About Semptify — Tenant Rights Organization",
            path="/about",
            template="public/about.html",
            description="Semptify is a tenant rights organization building technology to protect and advance lawful tenant rights through documentation, education, and evidence preservation.",
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
            description="Semptify offers free tools for tenants, advocates, legal professionals, agencies, donors, researchers, and developers. Browse our services catalog.",
            keywords="semptify services, tenant tools, free tenant tools, housing services",
            og_title="Our Services — Semptify",
            og_description="Free tools for tenants, advocates, legal professionals, and more.",
            footer_label="Services",
            order=20,
        ),
        PortalPage(
            id="renters_guide",
            title="Renter's Guide — Know Your Rights — Semptify",
            path="/renters-guide",
            template="public/renters_guide.html",
            description="A plain-language guide to tenant rights and responsibilities. Understand what your landlord must do, and what you must do. Facts only, no opinions.",
            keywords="renters guide, tenant rights, tenant responsibilities, landlord tenant law, housing rights",
            og_title="Renter's Guide — Know Your Rights — Semptify",
            og_description="A plain-language guide to tenant rights and responsibilities.",
            footer_label="Renter's Guide",
            order=30,
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
            title="Legal Research — Semptify",
            path="/legal-research",
            template="public/legal_research.html",
            description="Legal research tools for attorneys, paralegals, and researchers. Research landlords, court filings, and property history.",
            keywords="legal research, landlord research, court filings, litigation intelligence, housing law",
            og_title="Legal Research — Semptify",
            og_description="Legal research tools for attorneys and researchers.",
            footer_label="Legal Research",
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
            title="Donate — Support Tenant Rights — Semptify",
            path="/donate",
            template="public/donate.html",
            description="Semptify is free for tenants, forever. Donations keep it that way. Donate anonymously — no account required.",
            keywords="donate tenant rights, anonymous donation, housing nonprofit, support tenants",
            og_title="Donate — Support Tenant Rights — Semptify",
            og_description="Semptify is free for tenants, forever. Donations keep it that way.",
            footer_label="Donate",
            order=70,
        ),
        PortalPage(
            id="developers",
            title="Developer Hub — Semptify",
            path="/developers",
            template="public/developers.html",
            description="Resources for developers: external SDK, Forge module marketplace, API documentation, and contribution guidelines.",
            keywords="semptify sdk, developer tools, api documentation, open source, contribute",
            og_title="Developer Hub — Semptify",
            og_description="SDK, module marketplace, API docs, and contribution guidelines.",
            footer_label="Developers",
            order=80,
        ),
        PortalPage(
            id="tools",
            title="Standalone Tools — Semptify",
            path="/tools",
            template="public/tools.html",
            description="Free standalone tools: PDF tools, document converter, public forms. No account required.",
            keywords="free pdf tools, document converter, public forms, housing forms, no account required",
            og_title="Standalone Tools — Semptify",
            og_description="Free standalone tools. No account required.",
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
