"""Context Engine taxonomy — 13 housing-rights subjects plus landing-page public claims."""

from enum import StrEnum


class Subject(StrEnum):
    """Canonical 13 subjects for Context Engine."""

    EVICTION = "eviction"
    REPAIR = "repair"
    RENT = "rent"
    LEASE = "lease"
    DEPOSIT = "deposit"
    DISCRIMINATION = "discrimination"
    SAFETY = "safety"
    HABITABILITY = "habitability"
    RETALIATION = "retaliation"
    SMALL_CLAIMS = "small_claims"
    COURT_PREP = "court_prep"
    EVIDENCE = "evidence"
    TIMELINE = "timeline"
    LANDING = "landing"


ALL_SUBJECTS = tuple(s.value for s in Subject)
SUBJECT_LABELS = {
    Subject.EVICTION.value: "Eviction Defense",
    Subject.REPAIR.value: "Repair Requests",
    Subject.RENT.value: "Rent & Payments",
    Subject.LEASE.value: "Lease Terms",
    Subject.DEPOSIT.value: "Security Deposits",
    Subject.DISCRIMINATION.value: "Discrimination",
    Subject.SAFETY.value: "Safety & Crime",
    Subject.HABITABILITY.value: "Habitability & Code",
    Subject.RETALIATION.value: "Retaliation",
    Subject.SMALL_CLAIMS.value: "Small Claims",
    Subject.COURT_PREP.value: "Court Preparation",
    Subject.EVIDENCE.value: "Evidence Documentation",
    Subject.TIMELINE.value: "Timeline Building",
    Subject.LANDING.value: "Landing Page",
}

# Map free_api_pack endpoints to subjects for gatherer integration
SUBJECT_TO_FREE_API = {
    Subject.EVICTION.value: "court_listener_search",
    Subject.REPAIR.value: "epa_echo_lookup",
    Subject.HABITABILITY.value: "epa_echo_lookup",
    Subject.SAFETY.value: "epa_echo_lookup",
    Subject.LEASE.value: "mn_statute_search",
    Subject.RENT.value: "mn_statute_search",
    Subject.DEPOSIT.value: "mn_statute_search",
    Subject.RETALIATION.value: "mn_statute_search",
    Subject.DISCRIMINATION.value: "hud_fair_housing",
    Subject.SMALL_CLAIMS.value: "mn_statute_search",
    Subject.COURT_PREP.value: "mncourts_search",
    Subject.EVIDENCE.value: None,  # No external API — guidance only
    Subject.TIMELINE.value: None,  # No external API — guidance only
    Subject.LANDING.value: None,  # Public marketing/landing claims — verified by fact-check/freshness system
}
