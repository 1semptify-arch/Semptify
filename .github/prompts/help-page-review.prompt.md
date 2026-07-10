---
mode: agent
description: Weekly review of help page resources to keep crisis hotlines, legal aid, and county contacts up to date
---

<!-- Mirrors .devin/workflows/help-page-review.md — keep both in sync when editing. -->

# Weekly Help Page Resource Review

**Run every week** (Mondays or start of work session) to verify help page info is current.

## Pages to Review

1. `static/help.html` — main help page
2. `static/tenant/help.html` — tenant-specific help
3. `staticbac/tenant/help.html` — backup reference (do not edit, just compare)

## What to Check

### Phone Numbers & Hotlines
- [ ] 988 Suicide & Crisis Lifeline — verify `tel:988` still correct
- [ ] National Domestic Violence Hotline — verify `1-800-799-7233`
- [ ] HOME Line MN — verify `612-728-5767` (or `1-800-745-6686`)
- [ ] Legal Aid MN — verify `1-888-543-5110` (or `1-888-354-5522`)
- [ ] 211 United Way — verify `tel:211`
- [ ] County numbers: Hennepin, Ramsey, Dakota, Anoka, Washington, St. Louis

### Websites
- [ ] https://www.211.org — still live
- [ ] https://www.housinglink.org — still live
- [ ] https://www.hud.gov/topics/rental_assistance — still live
- [ ] https://www.lawhelpmn.org — still live
- [ ] https://homelinemn.org — still live
- [ ] https://www.mncourts.gov/Help-Topics/Eviction-Landlord-and-Tenant-Cases.aspx — still live
- [ ] https://www.ag.state.mn.us/Consumer/Handbooks/LT/default.asp — still live
- [ ] https://www.revisor.mn.gov/statutes/cite/504B — still live
- [ ] https://www.hud.gov/states/minnesota/renting — still live

### Legal Aid Directory (in static/help.html)
- [ ] Verify each legal aid org in the state-select directory still exists
- [ ] Check URLs resolve (lafla.org, baylegal.org, legalservicesnyc.org, etc.)
- [ ] Add any new states/orgs if found

### FAQ Content
- [ ] Verify MN eviction response deadline still 7 days
- [ ] Verify MN Statute 504B reference still valid
- [ ] Check for any law changes that affect FAQ answers

## Verification Method

For each URL: fetch it or search the web to confirm the site is live and the info matches.

For phone numbers: search the web for the org name + "phone number" to confirm current number.

## If Changes Needed

1. Edit `static/help.html` first (main page)
2. Mirror changes to `static/tenant/help.html` for consistency
3. Do NOT edit `staticbac/tenant/help.html` — it's the backup reference
4. Run `python -m py_compile` on any Python files if routes changed (none expected for HTML-only edits)

## Completion

- [ ] Update `BUILD_STATE.md` with date of last help page review
- [ ] Note any broken links or outdated info found and fixed
