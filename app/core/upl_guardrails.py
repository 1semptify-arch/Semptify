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


__all__ = ["UPLRiskTier"]
