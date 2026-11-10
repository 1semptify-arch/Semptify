# Voice Board — Moderation Standard

The public version of this standard is published on `/your-voice` ("The
review standard"). This file is the working rubric for whoever moderates —
Brad, an agent, or a future community moderator. If the public text and this
rubric ever disagree, the public text wins; fix this file.

A sibling copy of this rubric lives in `semptify-bill-mirror/MODERATION.md`
(the repo that serves semptify.org). Keep the decision table identical in
both — the ops sections differ per repo.

## The line (Brad, 2026-11-10)

Moderation protects people. It never protects the bill from criticism.
Constructive criticism — including harsh criticism of the bill, the math,
the politics, or the people writing it — is the point of the board. We
cannot grow if we are unwilling to hear every viewpoint.

Hate, bigotry, racism, antisemitism — there is no place for that. That is
fear coming out sideways, not a viewpoint. It gets removed, always.

**When in doubt: publish and answer. The bias is toward hearing it, not
hiding it.**

## Decision table

| Post contains | Action |
|---|---|
| Names, addresses, case details, identifying info | Strip the details, publish the rest (Polis-style redaction — sentiment survives) |
| Threats, harassment, doxxing | Decline |
| Hate/bigotry targeting a group (racism, antisemitism, etc.) | Decline |
| Spam, ads, repeated junk, gibberish | Decline |
| Illegal content | Decline |
| Impersonation (claims to be a named person/org untruthfully) | Decline |
| Opinion on the bill — support, criticism, hostile tone but about the issue | **Publish.** Answer in the open if we can |
| Question | Publish; answer when possible, labeled by role |
| False or misleading claim about the bill/facts | Publish; correct it publicly in the answer — do not delete for being wrong |

Notes:

- Posts are anonymous by design, so "personal attack" almost always means
  an attack on a group or an identifiable public figure — the hate row
  governs. Criticism of the bill's *authors* as public actors is opinion;
  slurs and dehumanizing language are hate.
- Harsh tone alone is not a decline reason. A post that says "this bill is
  a scam and here's why" stays up. A post that says "kill all landlords"
  does not.
- Unverifiable claims get answered with the public record (the draft text,
  the research page), not silently removed — corrections are posted in the
  open, same as everything else on this site.

## How moderation runs today

- Intended path: `/admin/public-voice` review lane
  (`app/templates/pages/admin_public_voice.html`) → publish / answer /
  decline / unpublish via `POST /admin/api/public-forms/voice-posts/{id}`
  (`app/modules/admin_api/router.py`, elevation-gated). Posts land in the
  `voice_posts` table (`app/models/models.py::VoicePost`); the public API
  `GET /api/voice-posts` serves only `is_published = True`.
- Admin lane is currently excluded from the `render_mvp` production build —
  see the mirror repo's OPERATIONS_LOG.
- Interim path until the admin lane ships: direct `voice_posts` update in
  the Neon `semptifty_db` database — `status` + `is_published` per the
  decision table. `awaiting_review` counts unpublished rows including
  declined ones (known cosmetic bug — logged to intake).
- Voice posts cannot be edited before publish today — there is no
  "publish the rest" button for the strip-PII row. Until an edit field
  exists, a post containing personal details should be handled in the
  interim DB path or declined. (Stories already support edit-before-publish
  via the same lane.)
- Every moderation action should be deliberate and logged — no silent
  deletes.

## Toward public-driven review

The published standard is only half of "driven by the public." The full
version adds a **flag/report** control on each board post so readers
surface problems themselves, feeding the same review queue.

**Shipped 2026-11-10 (app side):** every published board post carries a
quiet "Report a problem" control. Reports are anonymous — a reason code
only, no names, no free text — via `POST /api/voice-posts/{id}/flag`.
Reasons mirror the decline rows of the decision table. A flagged post
**stays up** while flagged (the bias is toward hearing it) and lands in
the same `/admin/public-voice` review queue, sorted flag-first, with its
count and reasons shown. The reviewer can keep it ("clear flag"),
unpublish, decline, or answer — any review action resolves the flag.
The mirror repo's static copy of the page needs a matching control;
tracked separately.
