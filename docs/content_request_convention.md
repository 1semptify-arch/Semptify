# Content Request Convention — per-module "words needed" files

Every tenant-facing module declares the tenant-facing text it needs in a
`content_request.json` file inside its own directory:

```
app/modules/<name>/content_request.json   # what words this module needs
app/modules/<name>/articles.json          # the fulfilled articles (once written)
```

Composer-subject content (not tied to one module) uses the same pair under:

```
app/data/articles/<subject>/content_request.json
app/data/articles/<subject>/articles.json
```

## content_request.json schema

```json
{
  "module": "vault",
  "display_name": "Vault",
  "pillar": "record",
  "requested_at": "2026-09-19",
  "status": "requested",
  "articles": [
    {
      "id": "stats",
      "kind": "statistical",
      "title": "…",
      "brief": "what the article must establish; which sourced numbers to use",
      "sources_hint": ["…"],
      "upl_risk_tier": "low",
      "status": "requested"
    },
    {
      "id": "about",
      "kind": "usage",
      "title": "…",
      "brief": "what the module does + concrete usage examples",
      "upl_risk_tier": "low",
      "status": "requested"
    }
  ]
}
```

`status` flows `requested → drafted → in_review → vetted` (matching the
`context_explanation_entries` review_status gate: only VETTED may render as a
settled answer).

## articles.json schema

```json
{
  "module": "vault",
  "articles": [
    {
      "id": "stats",
      "kind": "statistical",
      "title": "…",
      "body": "plain-language article text",
      "sources": [{"label": "…", "url": "…"}],
      "voice_gate": "passed",
      "review_status": "BETA"
    }
  ]
}
```

## Standing rules for every article

- **Fact before fiction.** Every factual/statistical claim carries a visible
  source in `sources`. No invented numbers.
- **Voice:** calm, plain, non-adversarial. No "evidence"/"proof" for pre-court
  tenant records (per semptify-voice). No fear or urgency tactics.
- **Legal information, not advice.** UPL tier on the request sets how careful
  the drafting must be; high-tier articles end with a legal-aid pointer.
- **AI disclosure** footer applies wherever articles render (canonical text in
  `SEMPTIFY_REFERENCE_LIBRARY.md` §14).
- **Jurisdiction:** legal claims cite the state statute; generic process
  guidance may be jurisdiction-neutral but says so.

## Generation

`tools/generate_content_requests.py` writes the request files. Editing the
request file is the way a module owner asks for new/changed copy — the file is
the contract between the module and the content pipeline.
