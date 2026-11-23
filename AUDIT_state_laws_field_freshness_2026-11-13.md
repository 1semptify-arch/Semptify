# State-Laws Field Freshness Audit — 2026-11-13

**Task:** `task-f3b5ce6c` (master queue, 4 folded intake items: `intake-00f8a1db`,
`intake-bceb08ad`, `intake-7956a7c0`, `intake-c3cc3a3e`)
**Agent:** swe-2 (dispatched)
**Subject file:** `static/data/state-laws.json` (canonical — only copy in tree;
`app/modules/state_laws/router.py` `DATA_PATH` resolves here)
**Driver:** `LEARNING_PLATFORM_DESIGN_2026-11-06.md` gap #3 — lessons must not
cite this file as authoritative until a freshness pass lands.

---

## 1. What the intake claimed vs. what the file actually said

The intake note (written 2026-11-06, mid-refactor) was directionally right but
stale in three particulars. Verified against the file itself 2026-11-13:

| Intake claim | Actual state (verified) |
|---|---|
| "all 50 states now carry status 'complete'" | 44 carry `complete`, 6 carry `partial` (IA IN MO ND SD WI) — honesty fix `0a02eebd` landed same day |
| "no file-level last_updated" | `metadata.last_updated` exists (was 2026-11-06) — the field was present |
| "MN has only 3 housing_laws entries" | `housing_laws` is a fixed 3-key dict (`landlord_tenant_act`, `statute_url`, `summary`) for **every** substantial/full state — that is the schema, not MN thinness |
| "6 states have none [housing_laws]" | True — the 6 `partial` states lack `housing_laws` and `rent_control` by crisis-tier design |
| "12 complete / 38 stub audit count no longer matches" | True — the 2026 Know-Your-Rights audit count was stale; replaced by the three-tier model below |

## 2. Depth tiers (per `docs/blueprints/content_review_next_states_blueprint.md`)

Every state record now carries `data_depth` + `last_verified` (added this pass):

| `data_depth` | Count | States | Contents |
|---|---|---|---|
| `full` | 11 | CA FL GA IL MI MN NC NY OH PA TX | All law sections + `forms_templates` + `special_programs` |
| `substantial` | 33 | all other `status: complete` states | All law-bearing sections (housing_laws, notice, deposit, rent_control, repairs, entry, eviction, discrimination, legal_aid, gov resources, sources); missing `forms_templates`/`special_programs` enrichment |
| `crisis-tier` | 6 | IA IN MO ND SD WI (`status: partial`) | Verified crisis fields only: notice, deposit, entry, eviction, repairs, sources, legal-aid `stub_url` |

`status` now means "row schema filled" (complete/partial); `data_depth` means
"how much law the row answers." Both are exposed on `GET /api/states` (list
items + `depth_counts`) and `GET /api/states/{code}` via additive
`StateDetails` fields — no contract change.

## 3. Per-field freshness — provenance and verdict

| Tier | Last verbatim primary-source pass | Evidence |
|---|---|---|
| full (11) | 2026-09-21 | `explanation-corpus-vetting-2026-09-19` — all 11 states' `tenant_remedies` + corrections; commits `5b8301bd`, `06533e15` |
| substantial (33) | 2026-09-21 | 39-entry verbatim vetting (`handoffs/explanation-corpus-vetting-report-2026-09-21.md`) — claim classes: act cite, nonpayment notice, deposit limit/deadline, habitability cite, remedy flags, entry notice, eviction protections. 7 material + 12 minor errors found and fixed in `06533e15` |
| crisis-tier (6) | 2026-09-21 | Same 39-entry vetting (IA MO ND SD WI IN pass clean per report line 71); fields originally verified 2026-09-07 (`93c1b071`, per their `notes`) |

**Verdict:** every populated field in all 50 states was last checked against
primary sources **2026-09-21** — ~7.5 weeks stale as of this audit. No
post-9/21 statutory changes were checked in this pass (none found by
inspection of the file; a drift sweep is future work, not assumed clean).
`last_verified` records *when populated fields were checked* — it is not a
completeness claim and not proof of current-law accuracy today.

## 4. Folded-item dispositions

- **`intake-bceb08ad` (status=complete overstates depth + stale preflight
  doc):** `data_depth` now distinguishes the 33 substantial rows from the 11
  full rows; `.devin/skills/preflight/SKILL.md` and its
  `.github/prompts/preflight.prompt.md` mirror updated — the "12 complete /
  38 stub" description removed, replaced with the tier model.
- **`intake-7956a7c0` (`stub_count` misleads):** not renamed — contract
  change, out of content scope per its own triage note. Mitigated instead:
  list items now carry `data_depth`/`last_verified` and the response carries
  `depth_counts`, so consumers have the honest signal without touching
  `stub_count`.
- **`intake-c3cc3a3e` (stub_url residue on 9 substantial states):** kept —
  the values are lawhelp/legal-aid referral links (e.g. AZ→azlawhelp.org,
  MD→peoples-law.org), consistent with the field's purpose on partial rows;
  `StateDetails` already exposes it. Harmless residue, not an honesty defect.
  If Brad wants it renamed `referral_url`, that's a one-line schema pass.

## 5. Open flags for the next pass

- **MO legal aid:** `MO.notes` itself flags `stub_url` (mobar.org attorney
  search) is a referral, not legal aid — replace with a real MO legal-aid
  link on next content pass.
- **`/law-library` badge:** `LAST_VERIFIED_DATE = "2025-01-01"` hardcoded in
  the law_library router (per the design doc) — separate file, separate fix.
- **Drift sweep:** no scheduled re-verification exists. ADR-0009
  (ContextFact freshness) is the natural home; `last_verified` is the field
  it should drive.
- **`review_status` per state:** deliberately NOT added — the blueprint
  reserves the VETTED/BETA authority decision for Brad. `last_verified`
  added here is a factual date only.

## 6. Guidance for learning content (the consumer that flagged this)

- `full` + `substantial` rows: populated fields are citable with a
  `last_verified` badge; recheck against the row's `sources`/`statute_url`
  if >90 days old at publish time.
- `crisis-tier` rows: cite only the populated crisis fields; the absence of
  `housing_laws`/`rent_control` means "not yet written," not "no such law."
- Never cite `metadata.last_updated` alone as field freshness — it moves
  with any file edit; `last_verified` is the honest per-state signal.
