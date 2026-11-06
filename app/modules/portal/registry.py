"""Portal Services Registry — SSOT for the semptify.org guest portal.

Each entry is a self-contained service block on the portal page. When Semptify
adds a new service, branch, or connected division, it just gets added here.
No rewriting existing sections. Entries can be toggled off via `visible=False`.

Design principles:
- Additive, not rewrite — new services are added, not inserted into prose
- SSOT — this registry is the only place services are defined
- Toggleable — each entry has a `visible` field (future: tied to module flags)
- Mobile-first — each entry renders as a card that stacks on mobile

Categories group services for the visitor:
- tenant      — services for renters/tenants
- advocate    — services for advocates and advocacy groups
- legal       — services for legal firms and attorneys
- agency      — services for housing agencies and partner orgs
- donor       — services for donors and funders
- researcher  — services for researchers and data analysts
- developer   — services for software developers and contributors
- standalone  — standalone tools (PDF tools, converter, public forms)
- info        — informational pages (about, privacy, terms, help)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PortalService:
    """A single service entry on the guest portal.

    Immutable — SSOT for one service block on the portal page.
    """

    id: str  # unique identifier (e.g. "tenant_organizer")
    name: str  # human-readable name
    short_description: str  # one-line description for the card
    cta_label: str  # call-to-action button text
    cta_path: str  # SSOT navigation path (from navigation.get_stage)
    icon: str = ""  # emoji or icon
    category: str = "tenant"  # grouping category
    order: int = 100  # sort priority within category (lower = first)
    visible: bool = True  # toggle visibility (future: tied to module flags)
    requires_auth: bool = False  # does this service require login?
    description_long: str = ""  # longer description for the service detail page
    pillar: str = "partner"  # one of PortalRegistry.PILLARS keys (the six functions) or "partner"
    audiences: tuple[str, ...] = ()  # CATEGORIES keys this service is for


@dataclass
class PortalRegistry:
    """Central registry — THE source of truth for portal services.

    No page, template, or static file defines its own service list.
    All services flow from here.
    """

    # --- Portal Services (SSOT) ---
    SERVICES: ClassVar[list[PortalService]] = [
        # =====================================================================
        # TENANT SERVICES
        # =====================================================================
        PortalService(
            id="tenant_organizer",
            name="Tenant Document Organizer",
            short_description="Document everything between you and your landlord. Build a timeline of your tenancy.",
            cta_label="Get Started",
            cta_path="/preamble",
            icon="📓",
            category="tenant",
            pillar="documentation",
            audiences=("tenant",),
            order=10,
            requires_auth=False,
            description_long=(
                "Semptify is a document organizer for renters. Keep records of every "
                "interaction with your landlord, build a timeline of your tenancy, and "
                "store documents in your own cloud storage. Private and simple."
            ),
        ),
        PortalService(
            id="tenant_rights_library",
            name="Law Library",
            short_description="Verified statutes, cases, and court rules with official source links. Not legal advice.",
            cta_label="Browse the Library",
            cta_path="/law-library",
            icon="📚",
            category="tenant",
            pillar="information",
            audiences=("tenant", "legal", "researcher",),
            order=20,
            requires_auth=False,
            description_long=(
                "A library of verified facts about tenant rights. Search by state, "
                "topic, or keyword. Every fact includes a source URL — no hallucination, "
                "no opinions, just the law."
            ),
        ),
        PortalService(
            id="tenant_complaint_wizard",
            name="Filing a Complaint",
            short_description="Walk through filing a housing complaint step by step.",
            cta_label="Start a Complaint",
            cta_path="/preamble",
            icon="📝",
            category="tenant",
            pillar="be_heard",
            audiences=("tenant",),
            order=30,
            requires_auth=False,
            description_long=(
                "A guided wizard that helps you draft and file a housing complaint. "
                "Covers habitability, discrimination, retaliation, and security deposit disputes."
            ),
        ),
        # =====================================================================
        # ADVOCATE SERVICES
        # =====================================================================
        PortalService(
            id="advocate_affiliation",
            name="Advocacy Group Affiliations",
            short_description="Partner with Semptify as an advocacy organization.",
            cta_label="Partner With Us",
            cta_path="/advocacy",
            icon="🤝",
            category="advocate",
            pillar="collaborate",
            audiences=("advocate",),
            order=10,
            requires_auth=False,
            description_long=(
                "Housing advocacy groups can partner with Semptify to refer tenants, "
                "share resources, and coordinate support."
            ),
        ),
        PortalService(
            id="advocate_start_group",
            name="Start an Advocacy Group",
            short_description="Resources for forming a new tenant advocacy group in your area.",
            cta_label="Learn How",
            cta_path="/advocacy",
            icon="🌱",
            category="advocate",
            pillar="collaborate",
            audiences=("advocate", "tenant",),
            order=20,
            requires_auth=False,
            description_long=(
                "A guide to forming a tenant advocacy group: legal structure, outreach, "
                "funding, and how Semptify can support your work."
            ),
        ),
        # Advocate Portal — hidden 2026-11-06. The role portals were removed
        # with the tenant-only decision (PR #317); the /advocate page still
        # renders for authenticated users but there is no advocate role to log
        # into. Kept in the registry (visible=False) pending a retire decision.
        PortalService(
            id="advocate_portal",
            name="Advocate Portal",
            short_description="Manage clients, review documents, and coordinate support.",
            cta_label="Advocate Portal",
            cta_path="/advocate",
            icon="🏢",
            category="advocate",
            pillar="collaborate",
            audiences=("advocate",),
            order=30,
            visible=False,
            requires_auth=True,
            description_long=(
                "Tools for advocates: client management, document review, annotations, "
                "invite codes, and case coordination."
            ),
        ),
        # =====================================================================
        # LEGAL SERVICES
        # =====================================================================
        PortalService(
            id="legal_research",
            name="Legal Research on Landlords",
            short_description="Research landlord records, court filings, and property history.",
            cta_label="Research Tools",
            cta_path="/preamble",
            icon="🔍",
            category="legal",
            pillar="research",
            audiences=("legal", "researcher",),
            order=10,
            requires_auth=False,
            description_long=(
                "Tools for researching landlords: court filings, property records, "
                "litigation history, and pattern detection."
            ),
        ),
        # Legal Portal — hidden 2026-11-06, same reason as advocate_portal.
        PortalService(
            id="legal_portal",
            name="Legal Portal",
            short_description="Case management, court filing, discovery, and legal overlays.",
            cta_label="Legal Portal",
            cta_path="/legal",
            icon="⚖️",
            category="legal",
            pillar="organize",
            audiences=("legal",),
            order=20,
            visible=False,
            requires_auth=True,
            description_long=(
                "Tools for attorneys, paralegals, clerks, and judges: matter management, "
                "court filing, discovery prep, exhibits, and legal overlays on tenant documents."
            ),
        ),
        # =====================================================================
        # AGENCY SERVICES
        # =====================================================================
        PortalService(
            id="agency_connect",
            name="Agencies Connect",
            short_description="Housing agencies and partner organizations — connect with Semptify.",
            cta_label="Connect Your Agency",
            cta_path="/contact",
            icon="🏛️",
            category="agency",
            pillar="partner",
            audiences=("agency",),
            order=10,
            requires_auth=False,
            description_long=(
                "Housing agencies, fair housing organizations, and government partners "
                "can connect with Semptify for referrals, data sharing, and coordinated support."
            ),
        ),
        # =====================================================================
        # DONOR SERVICES
        # =====================================================================
        PortalService(
            id="donor_anonymous",
            name="Donors & Supporters",
            short_description="Support tenant rights — see the platform, the privacy model, and the funding roadmap.",
            cta_label="Donate",
            cta_path="/donate",
            icon="💝",
            category="donor",
            pillar="partner",
            audiences=("donor",),
            order=10,
            requires_auth=False,
            description_long=(
                "Semptify costs tenants nothing, ever. Donations keep it that way. "
                "Donate via GitHub Sponsors — one-time or monthly."
            ),
        ),
        # =====================================================================
        # RESEARCHER SERVICES
        # =====================================================================
        # Researcher Tools — hidden 2026-11-06. There is no researcher surface
        # post-#317; the public law library and the bill research pages are open
        # to everyone. Kept dormant pending a retire decision.
        PortalService(
            id="researcher_tools",
            name="Researcher Tools",
            short_description="Advanced research tools and data analysis.",
            cta_label="Researcher Access",
            cta_path="/preamble",
            icon="🔬",
            category="researcher",
            pillar="research",
            audiences=("researcher",),
            order=10,
            visible=False,
            requires_auth=False,
            description_long=(
                "Tools for legal researchers and data analysts: "
                "landlord pattern detection, housing accountability research, and exportable datasets."
            ),
        ),
        # =====================================================================
        # DEVELOPER SERVICES
        # =====================================================================
        PortalService(
            id="developer_sdk",
            name="Software Development",
            short_description="Open source codebase, Forge module pipeline, and API documentation.",
            cta_label="Developer Hub",
            cta_path="/developers",
            icon="💻",
            category="developer",
            pillar="partner",
            audiences=("developer",),
            order=10,
            requires_auth=False,
            description_long=(
                "Resources for developers: the open codebase, the Forge module "
                "lifecycle pipeline, API documentation, and contribution guidelines."
            ),
        ),
        # =====================================================================
        # STANDALONE TOOLS
        # =====================================================================
        PortalService(
            id="standalone_pdf_tools",
            name="PDF Tools",
            short_description="Merge, split, and convert PDFs — inside Semptify.",
            cta_label="Open PDF Tools",
            cta_path="/preamble",
            icon="📄",
            category="standalone",
            pillar="organize",
            audiences=("tenant", "advocate", "legal",),
            order=10,
            requires_auth=False,
            description_long=(
                "PDF tools inside Semptify: merge, split, convert, and sign PDF "
                "documents. Files are processed and returned — nothing is stored."
            ),
        ),
        PortalService(
            id="standalone_document_converter",
            name="Document Converter",
            short_description="Convert documents between formats (PDF, DOCX, HTML, TXT).",
            cta_label="Open Converter",
            cta_path="/preamble",
            icon="🔄",
            category="standalone",
            pillar="organize",
            audiences=("tenant", "advocate", "legal",),
            order=20,
            requires_auth=False,
            description_long=(
                "Convert documents between formats inside Semptify: PDF to DOCX, "
                "DOCX to HTML, HTML to PDF, and more."
            ),
        ),
        PortalService(
            id="standalone_public_forms",
            name="Public Forms",
            short_description="Housing-related forms and templates — inside Semptify.",
            cta_label="Browse Forms",
            cta_path="/preamble",
            icon="📋",
            category="standalone",
            pillar="documentation",
            audiences=("tenant",),
            order=30,
            requires_auth=False,
            description_long=(
                "Public housing forms and templates: lease agreements, notice letters, "
                "complaint forms, and more. Download or fill online."
            ),
        ),
        # =====================================================================
        # ADVANCED SEMPTIFY SYSTEMS
        # =====================================================================
        PortalService(
            id="advanced_systems",
            name="Advanced Semptify Systems",
            short_description="Power-user tools, beta features, and advanced research modules.",
            cta_label="Explore Advanced",
            cta_path="/preamble",
            icon="⚡",
            category="tenant",
            pillar="research",
            audiences=("tenant", "researcher",),
            order=40,
            requires_auth=False,
            description_long=(
                "Advanced tools for power users: records research, housing "
                "accountability, and beta features. Requires opt-in."
            ),
        ),
    ]

    # --- The six core functions (docs/admin/MOTIVATIONS.md §3), in the order a
    # person needs them. "partner" is not a function: it groups the
    # organization-facing doors (agencies, donors, developers).
    PILLARS: ClassVar[dict[str, dict[str, str]]] = {
        "information": {
            "number": "1",
            "label": "Information",
            "question": "What are my rights?",
            "blurb": "Plain-language, sourced answers about tenant rights and process.",
        },
        "research": {
            "number": "2",
            "label": "Research",
            "question": "What applies to my situation?",
            "blurb": "Go deeper than the general rules: statutes, records, and patterns.",
        },
        "documentation": {
            "number": "3",
            "label": "Documentation",
            "question": "What actually happened?",
            "blurb": "A dated record of every notice, payment, repair request, and conversation.",
        },
        "organize": {
            "number": "4",
            "label": "Organize",
            "question": "How do I make it something a person can follow?",
            "blurb": "Turn scattered photos, texts, and papers into one coherent record.",
        },
        "collaborate": {
            "number": "5",
            "label": "Collaborate",
            "question": "Who else is in this with me?",
            "blurb": "Find a tenants association or advocate, or start one.",
        },
        "be_heard": {
            "number": "6",
            "label": "Be Heard",
            "question": "How do I put this on the record?",
            "blurb": "File a legitimate complaint and pass your story to whoever will listen.",
        },
    }
    PARTNER_PILLAR: ClassVar[dict[str, str]] = {
        "number": "",
        "label": "Work with Semptify",
        "question": "Are you an agency, supporter, or developer?",
        "blurb": "Organizations and people who want to partner, fund, or build with us.",
    }

    # --- Category Metadata ---
    CATEGORIES: ClassVar[dict[str, dict[str, str]]] = {
        "tenant": {
            "label": "For Tenants",
            "icon": "🏠",
            "description": "Document your tenancy, know your rights, and protect yourself.",
        },
        "advocate": {
            "label": "For Advocates",
            "icon": "🤝",
            "description": "Partner with Semptify or start an advocacy group.",
        },
        "legal": {
            "label": "For Legal Professionals",
            "icon": "⚖️",
            "description": "Statute and public-records research.",
        },
        "agency": {
            "label": "For Agencies",
            "icon": "🏛️",
            "description": "Housing agencies and partner organizations.",
        },
        "donor": {
            "label": "For Donors",
            "icon": "💝",
            "description": "Support tenant rights through anonymous donation.",
        },
        "researcher": {
            "label": "For Researchers",
            "icon": "🔬",
            "description": "Advanced research tools and data analysis.",
        },
        "developer": {
            "label": "For Developers",
            "icon": "💻",
            "description": "Open source codebase, module pipeline, and contributor resources.",
        },
        "standalone": {
            "label": "Tools",
            "icon": "🛠️",
            "description": "Individual tools inside Semptify.",
        },
    }

    # --- Utility Methods ---
    @classmethod
    def get_visible_services(cls) -> list[PortalService]:
        """Return all visible services, sorted by category order then service order."""
        return sorted(
            [s for s in cls.SERVICES if s.visible],
            key=lambda s: (s.category, s.order),
        )

    @classmethod
    def get_services_by_category(cls, category: str) -> list[PortalService]:
        """Return visible services in a specific category."""
        return sorted(
            [s for s in cls.SERVICES if s.visible and s.category == category],
            key=lambda s: s.order,
        )

    @classmethod
    def get_pillars_with_services(cls) -> list[dict]:
        """Pillars in journey order, each with its visible services (by order).

        Each service dict carries `audience_labels` so a card can say who it is for.
        Pillars with no visible service are omitted; the partner group is last.
        """
        out = []
        for key, meta in [*cls.PILLARS.items(), ("partner", cls.PARTNER_PILLAR)]:
            svcs = sorted(
                (s for s in cls.SERVICES if s.visible and s.pillar == key),
                key=lambda s: s.order,
            )
            if not svcs:
                continue
            out.append(
                {
                    "id": key,
                    **meta,
                    "services": [
                        {
                            "id": s.id,
                            "name": s.name,
                            "short_description": s.short_description,
                            "cta_label": s.cta_label,
                            "cta_path": s.cta_path,
                            "requires_auth": s.requires_auth,
                            "audience_labels": [
                                cls.CATEGORIES[a]["label"].removeprefix("For ")
                                for a in s.audiences
                                if a in cls.CATEGORIES
                            ],
                        }
                        for s in svcs
                    ],
                }
            )
        return out

    @classmethod
    def get_service(cls, service_id: str) -> PortalService | None:
        """Get a single service by ID."""
        for s in cls.SERVICES:
            if s.id == service_id:
                return s
        return None

    @classmethod
    def get_categories_with_services(cls) -> dict[str, dict[str, str]]:
        """Return categories that have at least one visible service."""
        visible = cls.get_visible_services()
        active_categories = {s.category for s in visible}
        return {cat: cls.CATEGORIES[cat] for cat in active_categories if cat in cls.CATEGORIES}

    @classmethod
    def to_dict(cls) -> dict:
        """Export complete portal state for API consumption."""
        visible = cls.get_visible_services()
        return {
            "services": [
                {
                    "id": s.id,
                    "name": s.name,
                    "short_description": s.short_description,
                    "cta_label": s.cta_label,
                    "cta_path": s.cta_path,
                    "icon": s.icon,
                    "category": s.category,
                    "order": s.order,
                    "requires_auth": s.requires_auth,
                    "description_long": s.description_long,
                }
                for s in visible
            ],
            "categories": cls.get_categories_with_services(),
            "total_services": len(visible),
        }


# Global instance — import this
portal = PortalRegistry()
