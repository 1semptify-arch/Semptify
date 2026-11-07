"""Tests for the /bill/live clean-statute view derivation.

The /bill/live page shows two views of one file: a clean statute reading
copy (derived by bill_statute_view at render time) and the verbatim
working file for drafting notes. These tests pin the transform rules
against both a synthetic sample and the real published partial, so a
format change in the case-side publish pipeline fails loudly here.
"""

from pathlib import Path

from app.modules.portal.service import bill_statute_view

DRAFT = (
    Path(__file__).resolve().parent.parent
    / "app" / "templates" / "public" / "bill_draft.html"
)

SAMPLE = """<h3>BILL — LIVE DRAFT (titled) · the working statute text</h3>
<p>*The one live document. No versions — this file IS the bill, always.*</p>
<h3>MINNESOTA RENT ASSURANCE &amp; DEPOSIT PROTECTION ACT</h3>
<h3>TITLE I — DEPOSIT PROTECTION</h3>
<p>*The proven, self-funding core. Amends Minn. Stat. §504B.178. Precedent:</p>
<p>UK Tenancy Deposit Protection (custodial schemes).*</p>
<p>**I-1. Custodial escrow.** Every residential security deposit is paid</p>
<p>into bonded program escrow at lease signing and held there **for the</p>
<p>tenancy**. The landlord never holds, itemizes, or returns the deposit.</p>
<p>*(Locked: DECISIONS 10/23 — UK custodial shape, supersedes clean-year</p>
<p>refund.)*</p>
<p>**III-1.** Contents coverage rides the same pool.</p>
<p>---</p>
<h3>Locked clauses — what&#x27;s non-negotiable (per DECISIONS.md)</h3>
<p>1. No subrogation — a paid claim ends the matter</p>
"""


def test_real_draft_derivation_markers():
    """The published partial must contain the markers the split needs —
    if the case-side publish format changes, this fails loudly instead of
    silently falling back to the raw view on the statute tab."""
    out = bill_statute_view(DRAFT.read_text(encoding="utf-8"))
    assert out is not None, "bill_statute_view returned None — publish format changed?"
    assert "MINNESOTA RENT ASSURANCE" in out
    assert "TITLE IV" in out


def test_real_draft_strips_shorthand():
    out = bill_statute_view(DRAFT.read_text(encoding="utf-8"))
    for shorthand in ("Locked:", "NEEDS BRAD", "REMEDIATION", "Open drafting Q"):
        assert shorthand not in out
    # No leftover markdown or drafting separators.
    assert "*" not in out
    assert "<p>---</p>" not in out
    assert "<p></p>" not in out
    # The notes tail stays on the notes tab.
    assert "Locked clauses" not in out
    assert "Open drafting questions" not in out


def test_clean_view_structure():
    out = bill_statute_view(SAMPLE)
    assert '<h4 class="clause-head">I-1. Custodial escrow.</h4>' in out
    assert '<h4 class="clause-head">III-1.</h4>' in out
    # Bold spanning a published paragraph break merges and becomes strong.
    assert "<strong>for the tenancy</strong>" in out
    # Italic title note spanning a paragraph break merges into one em.
    assert "<em>The proven, self-funding core. Amends Minn. Stat. §504B.178. Precedent: UK Tenancy Deposit Protection (custodial schemes).</em>" in out
    # Drafting separators become rules, annotations vanish.
    assert '<hr class="bill-rule">' in out
    assert "supersedes clean-year" not in out
    assert "Locked clauses" not in out


def test_missing_markers_return_none():
    assert bill_statute_view("<p>unrelated html</p>") is None
    assert bill_statute_view("") is None
