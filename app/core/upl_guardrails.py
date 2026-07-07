"""
UPL Guardrails — Legal-Risk-Tier Enforcement
============================================

Shared module for classifying Semptify features and outputs by risk of
Unauthorized Practice of Law (UPL).

Semptify is a public-service housing-rights tool, NOT a law firm. Every
feature that touches legal-adjacent territory must be classified against
this tier system before being built, and the classification must be
enforced at the boundary where the feature produces user-facing output.

North star: Semptify gives people facts and helps them organize — it does
NOT give legal advice. Get legal advice from a qualified attorney.

Tier semantics
--------------
- LOW               — Pure facts, statutes, public records, neutral listings.
                      No characterization, no application to a user's situation.
- LOW_MEDIUM        — Factual explanations of legal concepts in plain language
                      with an explicit "this is not legal advice" pointer.
                      No advice tailored to the user's specific case.
- MEDIUM            — Guided organization of the user's own facts (timeline,
                      journal, evidence index, packet assembly). No interpretation,
                      no recommendations, no "next steps" advice.
- MEDIUM_HIGH       — Surfaces legal options or statutes that *may* apply to a
                      user's described situation, with mandatory disclaimer and
                      a hard redirect to "get a qualified attorney". No prediction
                      of outcome, no recommendation to act.
- HIGH              — Generates tailored legal arguments, fills court forms with
                      legal reasoning, or drafts documents intended to be filed.
                      Requires attorney review gate before output. Never auto-filed.
- VERY_HIGH_DO_NOT_BUILD — Anything that constitutes the practice of law:
                      personalized legal advice, case-specific outcome predictions,
                      representation of the user, attorney-client relationship
                      creation, or automated filing without attorney review.
                      These features MUST NOT be built. No override, no bypass.

Enforcement rule
----------------
Any feature classified at or above MEDIUM_HIGH MUST:
  1. Display the canonical "We do not give legal advice. Get legal advice
     from a qualified attorney." notice on the same screen as the output.
  2. Provide a visible path to real outside legal help on the same screen.
  3. For HIGH tier, require an explicit attorney-review gate before the
     user can receive the output.

VERY_HIGH_DO_NOT_BUILD is a hard stop. If a proposed feature lands here,
do not build it. Flag it to the project owner and stop.

This module is the single source of truth for UPL risk classification.
Other modules import the enum from here — they MUST NOT redefine it.
"""

from enum import Enum


class UPLRiskTier(str, Enum):
    """
    Risk tier for Unauthorized Practice of Law (UPL) enforcement.

    Inherit from `str` so the tier serializes cleanly to JSON and is
    comparable as a string in logs, overlays, and API responses.

    Ordering is intentional and monotonic — higher index = higher risk.
    Use `tier.value` for stable serialization; use `tier.name` for logs.
    Never compare tiers by name string — compare by the enum member or
    by its position in `UPLRiskTier.__members__.values()`.
    """

    LOW = "low"
    """Pure facts, statutes, public records, neutral listings. No characterization
    of the user's situation. Example: a state statute quoted verbatim with citation."""

    LOW_MEDIUM = "low_medium"
    """Factual explanation of a legal concept in plain language, with an explicit
    'this is not legal advice' pointer. Not tailored to the user's case. Example:
    a plain-English glossary entry for 'retaliatory eviction'."""

    MEDIUM = "medium"
    """Guided organization of the user's own facts — timeline, journal, evidence
    index, packet assembly. No interpretation, no recommendations, no 'next steps'
    advice. Example: the attorney intake packet export (chronological facts only)."""

    MEDIUM_HIGH = "medium_high"
    """Surfaces legal options or statutes that *may* apply to a user's described
    situation. Mandatory disclaimer + hard redirect to 'get a qualified attorney'.
    No outcome prediction, no recommendation to act. Example: 'these statutes may
    apply to your situation — talk to an attorney to confirm'."""

    HIGH = "high"
    """Generates tailored legal arguments, fills court forms with legal reasoning,
    or drafts documents intended to be filed. Requires an attorney-review gate
    before output is released to the user. Never auto-filed. Example: a drafted
    answer to an eviction complaint that must be reviewed by an attorney before
    the user can download it."""

    VERY_HIGH_DO_NOT_BUILD = "very_high_do_not_build"
    """Hard stop. Constitutes the practice of law: personalized legal advice,
    case-specific outcome predictions, representation of the user, creation of
    an attorney-client relationship, or automated filing without attorney review.
    These features MUST NOT be built. No override, no bypass. If a proposed
    feature lands here, flag it to the project owner and stop."""


# ---------------------------------------------------------------------------
# Standard disclaimer text — single source of truth
# ---------------------------------------------------------------------------
# Every module that outputs MEDIUM_HIGH or HIGH content MUST display one of
# these disclaimers on the same screen as the output. Use UPL_DISCLAIMER for
# compact UI surfaces (buttons, badges, inline notices); use
# UPL_DISCLAIMER_LONG for page-level banners and footers. Both are canonical —
# do not reword, paraphrase, or invent new variants in other modules.

UPL_DISCLAIMER: str = (
    "We do not give legal advice. Get legal advice from a qualified attorney."
)
"""Short canonical notice. Displayed inline with MEDIUM_HIGH+ output."""

UPL_DISCLAIMER_LONG: str = (
    "Semptify is an organizational tool and educational resource — not a law firm. "
    "We can't give legal advice. For legal advice, contact a licensed attorney "
    "or your local legal aid society."
)
"""Long canonical notice. Used in page banners, footers, and about/help pages.
Matches the wording already shipped in public_base.html, about.html, complaints.html."""


# ---------------------------------------------------------------------------
# Standard referral block — legal aid and crisis contacts
# ---------------------------------------------------------------------------
# Every module that outputs MEDIUM_HIGH or HIGH content MUST display a visible
# path to real outside legal help on the same screen (per the enforcement rule
# in the module docstring). This is that path. One shared block — do not
# duplicate or reword in other modules.
#
# Contacts sourced from the canonical 911 help page (static/911/) and
# location_service.py. "Free" appears in external resource descriptions as a
# factual statement about THEIR services (per the 2026-06-30 word rule —
# external factual descriptions are permitted; Semptify self-description is not).

UPL_REFERRAL_CONTACTS: dict = {
    "crisis_line": {
        "name": "988 Suicide & Crisis Lifeline",
        "phone": "988",
        "description": "Mental health crisis, emotional distress, suicide prevention.",
        "hours": "24/7 · Free · Confidential · English/Español",
    },
    "housing_help": {
        "name": "211 United Way",
        "phone": "211",
        "description": "Emergency rental assistance, food, shelter, crisis referrals statewide.",
        "hours": "24/7 · Toll-free 1-800-543-7709 · Text your zip to 898-211",
    },
    "home_line_mn": {
        "name": "HOME Line — Minnesota Tenant Hotline",
        "phone": "612-728-5767",
        "url": "https://homelinemn.org/",
        "description": "Free legal advice, counseling, and rental help for tenants statewide.",
        "hours": "Mon–Thu 9am–6pm · Fri 9am–3pm · Toll-free 1-866-866-3546",
    },
    "legal_aid_mn": {
        "name": "Legal Aid Minnesota",
        "phone": "1-888-743-5327",
        "url": "https://www.mylegalaid.org/",
        "description": "Free legal services for low-income Minnesotans.",
        "hours": "Statewide intake line",
    },
}
"""Canonical referral contacts. Render in UI or return from API endpoints.
Keys are stable identifiers — do not rename. Values may be updated when
contact info changes (update here, not in copies elsewhere)."""

UPL_REFERRAL_BLOCK_TEXT: str = "\n".join(
    f"{c['name']}\n  Call: {c['phone']}"
    + (f"  ·  Web: {c['url']}" if c.get("url") else "")
    + f"\n  {c['description']}\n  {c['hours']}"
    for c in UPL_REFERRAL_CONTACTS.values()
)
"""Plain-text rendering of UPL_REFERRAL_CONTACTS for logs, API responses,
SMS gateways, and any surface that needs a flat string instead of structured
data. Generated from the dict so it never drifts."""


__all__ = [
    "UPLRiskTier",
    "UPL_DISCLAIMER",
    "UPL_DISCLAIMER_LONG",
    "UPL_REFERRAL_CONTACTS",
    "UPL_REFERRAL_BLOCK_TEXT",
]
