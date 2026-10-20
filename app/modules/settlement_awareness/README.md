# Settlement Awareness

Verified public housing outcomes surfaced alongside matching legal citations
in the Law Linker pop-out.

## What it does

When a tenant opens a citation pop-out (e.g. Minn. Stat. § 504B.178), the
page quietly asks this module whether any **verified** public records —
settlements, judgments, consent decrees, enforcement actions — cite the
same law or match the same subject tag. If yes, they render as small cards
with the official source link. If no records qualify, nothing renders at
all — no placeholder, no stale fallback.

## What it never does

- No AI-authored summaries or interpretations — records are pointers to
  real public sources only.
- No predictions ("you will win"). The disclaimer on every record says so.
- No standalone page — it lives inside the Law Linker pop-out only.
- No stale data — records unverified for >90 days or failing recheck
  auto-hide.

## The gate (Part 3B, enforced at write AND read)

A record surfaces only when ALL of these hold:

- `resolution_status == "Resolved"`
- `source_url` populated
- `fabrication_check == True`
- `ai_generated == False`
- `attested_by` names a human
- `is_verified == True` and `last_verified_date` within 90 days
- `news_*` source authorities also require `primary_source_url`

Intake always lands `Unresolved`; `resolve` refuses on any unmet gate;
`recheck` with a dead source flips `is_verified` off and the record
disappears from every consumer surface.

## API

| Route | Purpose |
|---|---|
| `GET /api/settlement-awareness/related?citation=&subject=` | Consumer surface — verified records only |
| `GET /api/settlement-awareness/recheck` | Weekly worklist of records due for recheck |
| `POST /api/settlement-awareness/records` | Intake — always lands Unresolved |
| `POST /api/settlement-awareness/resolve/{record_id}` | Operator resolve after manual verification |
| `POST /api/settlement-awareness/recheck/{record_id}` | Record a recheck result |

## Files

- `models.py` — `settlement_or_case_records` table (Part 3B field shape)
- `service.py` — gates, matching, recheck worklist
- `router.py` — FastAPI routes
- `register.py` — FunctionGroupContracts (SSOT)
- `tests/` — 12 tests proving the gate, auto-hide, and refusal paths

Lifecycle: `experimental` (promoted 2026-10-20). Blueprint:
`docs/blueprints/settlement_awareness_blueprint.md`.
