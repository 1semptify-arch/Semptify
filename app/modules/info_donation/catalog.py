"""Info Donation catalog — the single source of truth for what can be
donated, in what shape, and whether it needs human review before anyone
else ever sees it.

Every item is independently opt-in. Nothing here collects PII: no names,
no street addresses, no landlord names, no case numbers. Free-text items
are stored with ``moderation="pending"`` and are never served to anyone
until a reviewer approves them.

Kinds:
    choice      — one value from ``options``
    multichoice — a list, every element in ``options``
    bool        — true / false
    text        — short free text (always ``needs_review``)
"""

CONSENT_VERSION = "2026-09-21"

# Shown verbatim on the consent screen and versioned — if this text changes,
# bump CONSENT_VERSION so past consents stay honest about what was agreed.
CONSENT_TEXT = (
    "If you share answers here, Semptify stores them on its servers and "
    "combines them with other tenants' answers. What you share is never "
    "shown on its own — only as part of combined totals. Your name, "
    "address, and documents are never included. You can take back anything "
    "you shared at any time, and it will be deleted."
)

DONATION_ITEMS: dict[str, dict] = {
    # --- Outcome data ---
    "outcome": {
        "kind": "choice",
        "label": "How did things turn out?",
        "options": ("resolved", "moved_out", "still_ongoing", "got_legal_help"),
        "needs_review": False,
    },
    "time_to_resolve": {
        "kind": "choice",
        "label": "About how long did it take from start to settled?",
        "options": ("under_a_week", "a_few_weeks", "about_a_month", "a_few_months", "over_a_year"),
        "needs_review": False,
    },
    "stayed_in_home": {
        "kind": "bool",
        "label": "Were you able to stay in your home?",
        "needs_review": False,
    },
    "happened_again": {
        "kind": "bool",
        "label": "Did the same issue come back?",
        "needs_review": False,
    },
    # --- Process data ---
    "tools_that_helped": {
        "kind": "multichoice",
        "label": "Which parts of Semptify helped, if any?",
        "options": (
            "keeping_a_record",
            "documents_and_uploads",
            "timeline",
            "letters_and_notices",
            "know_your_rights",
            "deadline_tools",
            "dispute_tracker",
            "something_else",
        ),
        "needs_review": False,
    },
    "hardest_step": {
        "kind": "choice",
        "label": "Which step took the longest or felt hardest?",
        "options": (
            "knowing_my_rights",
            "the_paperwork",
            "talking_to_the_landlord",
            "waiting_on_official_help",
            "getting_ready_for_court",
            "something_else",
        ),
        "needs_review": False,
    },
    "official_help_responded": {
        "kind": "choice",
        "label": "Did official resources — legal aid, court self-help, hotlines — actually respond?",
        "options": ("answered_quickly", "answered_slowly", "never_answered", "did_not_try"),
        "needs_review": False,
    },
    "letter_response": {
        "kind": "choice",
        "label": "Did the letter or document you sent get a response?",
        "options": ("got_a_response", "no_response", "did_not_send"),
        "needs_review": False,
    },
    # --- Pattern data (aggregate only) ---
    "issue_kinds": {
        "kind": "multichoice",
        "label": "What kinds of issues did you run into?",
        "options": ("repairs", "deposit", "notice", "harassment", "fees_or_charges", "something_else"),
        "needs_review": False,
    },
    "general_area": {
        "kind": "text",
        "label": "General area — city or county only. No street address, no names.",
        "needs_review": True,
    },
    # --- Knowledge donation (human wisdom, reviewed before shown) ---
    "wish_known": {
        "kind": "text",
        "label": "What do you wish you had known earlier?",
        "needs_review": True,
    },
    "resources_that_answered": {
        "kind": "text",
        "label": "Which public resources actually picked up or answered?",
        "needs_review": True,
    },
    # --- Feedback on Semptify itself ---
    "feedback": {
        "kind": "text",
        "label": "Anything in Semptify that was confusing, missing, or wrong?",
        "needs_review": True,
    },
}

MAX_TEXT_LENGTH = 2000


def _humanize(option_value: str) -> str:
    return option_value.replace("_", " ").capitalize()


def public_items() -> list[dict]:
    """Normalized catalog for the page/JS: a list of items with ``key``,
    ``kind``, ``label``, humanized ``options``, and ``needs_review``."""
    items = []
    for key, spec in DONATION_ITEMS.items():
        entry = {
            "key": key,
            "kind": spec["kind"],
            "label": spec["label"],
            "needs_review": spec["needs_review"],
        }
        if "options" in spec:
            entry["options"] = [
                {"value": v, "label": _humanize(v)} for v in spec["options"]
            ]
        items.append(entry)
    return items


def describe_item(item_key: str, value) -> str:
    """Plain-language one-liner describing a stored item — used on the
    review screen and in the tenant's own donation list."""
    item = DONATION_ITEMS.get(item_key)
    if item is None:
        return item_key
    label = item["label"]
    kind = item["kind"]
    if kind == "bool":
        rendered = "Yes" if value else "No"
    elif kind == "multichoice":
        rendered = ", ".join(str(v).replace("_", " ") for v in value) if isinstance(value, list) else str(value)
    else:
        rendered = str(value).replace("_", " ")
    return f"{label} {rendered}"
