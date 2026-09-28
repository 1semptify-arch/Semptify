"""Interactive call scripts — the "what to say" layer.

Each script is a checklist that runs top to bottom during the call. Items
with a ``capture`` label turn into key_facts on the call log — the tenant
taps/short-types the answer and it is remembered as a named fact (person
spoken to, callback date, quoted fee, reference number) instead of a
typed paragraph.

Copy is plain-spoken. Scripts are data, not legal advice — they help the
tenant say what happened and remember what was said back.
"""

SCRIPTS: dict[str, dict] = {
    "attorney_intake": {
        "key": "attorney_intake",
        "title": "Attorney intake call",
        "purpose": "First call to a lawyer you might hire. Goal: tell the story in two minutes, answer their screening questions, leave with a next step.",
        "sections": [
            {
                "name": "Before you dial",
                "items": [
                    {"label": "Packet link copied and ready to paste", "capture": None},
                    {"label": "Pen and this screen open — every checked answer gets saved", "capture": None},
                    {"label": "Quiet room, ten minutes clear", "capture": None},
                ],
            },
            {
                "name": "Opening — say it close to this",
                "say": "Hi, my name is Brad Crowe. I'm looking for representation in a housing case in Dakota County. I was in LIHTC tax-credit housing, there's an executed settlement, a superseded draft the landlord enforced anyway, and a trial de novo coming up. I have the full document packet organized and ready to share. Is this something your office could look at?",
            },
            {
                "name": "They will probably ask — tap when answered",
                "items": [
                    {"label": "Who is on the other side? (Velair Property Management / Lexington Flats; their attorney is Douglass Turner, Hanbery & Turner)", "capture": "opposing_side_confirmed"},
                    {"label": "Key dates: hearing 12/23/2025, moved out 2/28/2026, trial de novo 11/16/2026", "capture": "dates_given"},
                    {"label": "What do you want out of this? (damages, record corrected, accountability)", "capture": "goal_stated"},
                    {"label": "Have you had a lawyer before? (legal aid — settlement only, broader claims unpursued)", "capture": "prior_counsel_explained"},
                    {"label": "Their fee / cost questions answered", "capture": "fees_discussed"},
                ],
            },
            {
                "name": "You ask them — write the answer next to it",
                "items": [
                    {"label": "Have you handled eviction/retaliation or LIHTC cases before?", "capture": "their_experience"},
                    {"label": "Do you see an affirmative case here, not just defense?", "capture": "their_read"},
                    {"label": "Fee structure — contingency, hourly, fee-shifting statutes?", "capture": "fee_terms"},
                    {"label": "Who actually works the case — you or staff?", "capture": "who_works_it"},
                    {"label": "What happens next and by when?", "capture": "next_step"},
                ],
            },
            {
                "name": "If they say no — still get something",
                "say": "I understand. Two quick things before I let you go: is there a reason it's not a fit — deadline, case type, capacity? And is there anyone you'd point me to?",
                "items": [
                    {"label": "Reason they declined", "capture": "decline_reason"},
                    {"label": "Referral they gave (name + phone)", "capture": "referral"},
                ],
            },
            {
                "name": "Closing",
                "say": "Thank you. I'll send the packet link by email today — it's under Crowe_Sazama_Case_Packet. Can I confirm the best email for you?",
                "items": [
                    {"label": "Person you actually spoke with", "capture": "spoke_with"},
                    {"label": "Their direct email / extension", "capture": "their_email"},
                    {"label": "They promised a reply by", "capture": "reply_by"},
                ],
            },
        ],
    },
    "agency_call": {
        "key": "agency_call",
        "title": "Agency / legal aid call",
        "purpose": "Calls to HOME Line, legal aid, OLPR, MN Housing, and similar offices. Goal: get the right department, a reference number, and a next step.",
        "sections": [
            {
                "name": "Opening",
                "say": "Hi, my name is Brad Crowe. I'm a tenant in Dakota County dealing with an eviction settlement dispute involving LIHTC housing. I need to find out which desk handles this, and I have documentation ready.",
            },
            {
                "name": "Get these every time",
                "items": [
                    {"label": "Name of the person you're talking to", "capture": "spoke_with"},
                    {"label": "Reference / intake / ticket number", "capture": "reference_number"},
                    {"label": "The right department or person for this", "capture": "right_contact"},
                    {"label": "What they need from you (form, packet, deadline)", "capture": "they_need"},
                    {"label": "When you'll hear back", "capture": "reply_by"},
                ],
            },
            {
                "name": "Closing",
                "say": "Let me read that back to be sure I have it right — your name is ___, the reference is ___, and I should expect ___ by ___. Did I get that?",
            },
        ],
    },
    "court_clerk": {
        "key": "court_clerk",
        "title": "Court clerk / records call",
        "purpose": "Dakota County court calls — docket status, filing confirmation, hearing logistics.",
        "sections": [
            {
                "name": "Have ready before dialing",
                "items": [
                    {"label": "Case number 19AV-CV-25-3477 (eviction) and 19HA-CV-26-3761 (conciliation/judgment)", "capture": None},
                    {"label": "Today's question written in one line", "capture": "question"},
                ],
            },
            {
                "name": "Ask",
                "items": [
                    {"label": "Status of the filing / what the docket shows", "capture": "docket_status"},
                    {"label": "Next scheduled date and whether remote appearance is allowed", "capture": "next_date"},
                    {"label": "Anything the court still needs from you", "capture": "court_needs"},
                ],
            },
            {
                "name": "Closing",
                "items": [
                    {"label": "Clerk's name", "capture": "spoke_with"},
                    {"label": "Best number to call back", "capture": "callback_number"},
                ],
            },
        ],
    },
    "follow_up": {
        "key": "follow_up",
        "title": "Follow-up / warm callback",
        "purpose": "Calling back someone you've already spoken with. Goal: reference the last call, move the next step forward, reset the clock on silence.",
        "sections": [
            {
                "name": "Opening",
                "say": "Hi, this is Brad Crowe — I spoke with ___ on ___. They said to expect ___ / to call back today. I'm following up.",
                "items": [
                    {"label": "Same person or someone new?", "capture": "spoke_with"},
                    {"label": "Status they gave", "capture": "status"},
                    {"label": "New commitment + date", "capture": "new_commitment"},
                ],
            },
        ],
    },
}
