"""FCA/Qui Tam case readiness — issue-spotting and evidence organization.

This module is a tenant-facing organizer. It does not determine that a claim
exists, does not give legal advice, and does not file anything. It surfaces
federal and state legal frameworks as questions and checklists for an attorney.
"""

from pydantic import BaseModel, Field


class FcaReadinessItem(BaseModel):
    """One item in the federal case readiness checklist."""

    id: str
    framework: str  # false_claims_act | fair_housing | mn_anti_retaliation
    category: str
    label: str
    required: bool = True
    completed: bool = False
    notes: str = ""
    document_ids: list[str] = Field(default_factory=list)
    hint: str = ""


class FcaReadinessUpdate(BaseModel):
    """Request body to save the FCA readiness checklist for a case."""

    readiness_checklist: list[FcaReadinessItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Starter referral resources — user can share these with an attorney.
# Semptify does not endorse any firm. Contact info must be verified by counsel.
# ---------------------------------------------------------------------------

FCA_REFERRAL_RESOURCES: list[dict] = [
    {
        "name": "HOME Line — Minnesota Tenant Hotline",
        "phone": "612-728-5767",
        "url": "https://homelinemn.org/",
        "description": "Free counseling and rental help for tenants statewide.",
    },
    {
        "name": "Legal Aid Minnesota",
        "phone": "1-888-743-5327",
        "url": "https://www.mylegalaid.org/",
        "description": "Free legal services for low-income Minnesotans.",
    },
    {
        "name": "National Housing Law Project",
        "url": "https://www.nhlp.org/",
        "description": "National housing rights legal resource and referrals.",
    },
    {
        "name": "Minnesota Disability Law Center",
        "phone": "1-800-292-4150",
        "url": "https://www.mndlc.org/",
        "description": "Disability rights legal services in Minnesota.",
    },
    {
        "name": "Taxpayers Against Fraud Education Fund",
        "url": "https://taf.org/",
        "description": "Public information about the False Claims Act and qui tam process.",
    },
]


# ---------------------------------------------------------------------------
# Default readiness checklist — issue-spotting only, no legal conclusions.
# ---------------------------------------------------------------------------

def _item(framework: str, category: str, label: str, hint: str, required: bool = True) -> dict:
    counter = _item.counter
    _item.counter += 1
    return {
        "id": f"{framework}_{category}_{counter:03d}",
        "framework": framework,
        "category": category,
        "label": label,
        "required": required,
        "completed": False,
        "notes": "",
        "document_ids": [],
        "hint": hint,
    }


_item.counter = 0


def build_default_checklist(frameworks: list[str] | None = None) -> list[dict]:
    """Return a default FCA/federal case readiness checklist."""
    _item.counter = 0
    all_items = [
        # False Claims Act / Qui Tam
        _item(
            "false_claims_act",
            "claim_identification",
            "Identify the specific request, invoice, certification, or statement that may be false",
            "A qui tam case needs the exact claim and the government program it was submitted to.",
        ),
        _item(
            "false_claims_act",
            "program",
            "Identify the federal, state, or local housing program involved",
            "HUD, Section 8, Housing Choice Voucher, LIHTC, rural housing, or other assisted-housing program.",
        ),
        _item(
            "false_claims_act",
            "factual_baseline",
            "Document what actually happened versus what was reported or claimed",
            "Keep the chronology separate from any legal conclusions.",
        ),
        _item(
            "false_claims_act",
            "knowledge",
            "Describe who knew what, and when, based on documents and events",
            "This is for an attorney to evaluate scienter, materiality, and causation.",
        ),
        _item(
            "false_claims_act",
            "damages",
            "List the amounts, overcharges, or withheld funds at issue",
            "Include lease charges, fees, program payments, or damages the attorney can review.",
        ),
        _item(
            "false_claims_act",
            "evidence",
            "Collect documents that show the claim and the truth side by side",
            "Lease, notices, invoices, vouchers, emails, inspection reports, photos, audio, and correspondence.",
        ),
        _item(
            "false_claims_act",
            "disclosure_bar",
            "Note whether the same information has already been publicly disclosed or reported",
            "The public-disclosure bar can be a major issue in qui tam cases — attorney must evaluate.",
        ),
        # Fair Housing Act
        _item(
            "fair_housing",
            "protected_class",
            "Describe any protected-class factors that may relate to the events",
            "Disability, race, color, religion, sex, familial status, national origin, or other protected basis.",
        ),
        _item(
            "fair_housing",
            "treatment_comparison",
            "Note how similarly situated tenants were treated, if known",
            "Selective enforcement, different notices, or different fees can be evidence for counsel to review.",
        ),
        _item(
            "fair_housing",
            "accommodation",
            "Document any disability-related accommodation request and response",
            "Service animal, reasonable modification, or other accommodation — request and denial in writing if possible.",
        ),
        _item(
            "fair_housing",
            "pattern",
            "Record whether this appears isolated or part of a broader pattern",
            "Other tenants, repeated conduct, or property-wide practices are questions for counsel.",
        ),
        # Minnesota anti-retaliation
        _item(
            "mn_anti_retaliation",
            "protected_activity",
            "Document the protected activity: complaint, repair request, inspection report, or exercise of rights",
            "Minn. Stat. § 504B.441 protects tenants who exercise lawful rights.",
        ),
        _item(
            "mn_anti_retaliation",
            "causation_timeline",
            "Create a timeline showing the protected activity and any action taken afterward",
            "Timing, threats, notices, or eviction filings after the protected activity are key facts for counsel.",
        ),
        _item(
            "mn_anti_retaliation",
            "adverse_action",
            "List the adverse actions: eviction, rent increase, notice, fee, or other penalty",
            "Keep the list factual and include dates and document references.",
        ),
        _item(
            "mn_anti_retaliation",
            "exhaustion",
            "Note any administrative complaints, agency contacts, or required notices already made",
            "HUD, local housing inspector, Minnesota Attorney General, or other agency — share with attorney.",
        ),
        # Cross-cutting
        _item(
            "cross_cutting",
            "chronology",
            "Ensure every checklist item is tied to a dated timeline entry and a document",
            "A complete packet should let an attorney follow the story in order.",
        ),
        _item(
            "cross_cutting",
            "witnesses",
            "List witnesses and other tenants who may have relevant information",
            "Do not contact them through Semptify — give the list to your attorney.",
        ),
        _item(
            "cross_cutting",
            "attorney",
            "Prepare a one-page summary and a chronological packet for attorney review",
            "This tool can help assemble it; only a qualified attorney can decide what claims may apply.",
        ),
    ]

    if not frameworks:
        return all_items

    return [i for i in all_items if i["framework"] in frameworks or i["framework"] == "cross_cutting"]


def calculate_readiness_score(checklist: list[dict]) -> int:
    """Return percent of required checklist items that are marked complete."""
    if not checklist:
        return 0
    required = [i for i in checklist if i.get("required", True)]
    if not required:
        return 0
    completed = sum(1 for i in required if i.get("completed"))
    return int((completed / len(required)) * 100)


def get_referral_resources() -> list[dict]:
    """Return referral resources for the FCA readiness packet."""
    return list(FCA_REFERRAL_RESOURCES)


def build_readiness_summary(checklist: list[dict], narrative: str = "") -> dict:
    """Return a factual summary of readiness state for the UI/packet."""
    frameworks = {"false_claims_act", "fair_housing", "mn_anti_retaliation", "cross_cutting"}
    by_framework = {
        fw: [i for i in checklist if i.get("framework") == fw]
        for fw in frameworks
    }
    missing = [i for i in checklist if i.get("required") and not i.get("completed")]

    return {
        "score": calculate_readiness_score(checklist),
        "total_items": len(checklist),
        "completed_items": sum(1 for i in checklist if i.get("completed")),
        "missing_required_count": len(missing),
        "missing_required_ids": [i.get("id") for i in missing],
        "by_framework": {
            fw: {
                "total": len(items),
                "completed": sum(1 for i in items if i.get("completed")),
                "score": calculate_readiness_score(items),
            }
            for fw, items in by_framework.items()
        },
        "narrative_present": bool(narrative and str(narrative).strip()),
    }
