# Semptify Role GUI Base Function Framework

## Goal
Create a stable product structure where:
- each role has one canonical GUI home
- all core abilities are organized into a small, natural set of function groups
- user input is simple and natural (type, upload, speak, click)
- behavior is predictable and testable

## Product Principles
1. One role, one home: every role enters through exactly one canonical route.
2. One mental model: all users follow the same workflow shape, with role-specific depth.
3. Easy input first: the UI starts with plain language and document upload, not forms.
4. Progressive complexity: show simple actions first, reveal advanced tools only when needed.
5. No dead ends: every page has a clear next action and safe fallback route.

## Canonical Role Homes
- Tenant: /tenant
- Advocate: /advocate
- Legal: /legal
- Admin: /admin

Each role home is the only official entry point for that role UI.
Legacy routes are compatibility aliases that redirect to canonical routes.

## Base Function Groups (Universal)
All role GUIs are built from the same six base function groups.

### 1) Capture
Purpose: get information into the system.
- Upload documents
- Add notes/events
- Voice-to-text intake
- Quick case facts (date, issue, parties)

### 2) Understand
Purpose: turn raw input into meaning.
- Timeline extraction
- Calendar extraction
- Rights and risk detection
- Complaint opportunity detection

### 3) Plan
Purpose: produce a clear path.
- Prioritized action list
- Urgent deadlines
- Defense tactic suggestions
- Next-step recommendations

### 4) Act
Purpose: execute outputs.
- Generate forms/motions
- File complaint workflows
- Assemble evidence packets
- Export/share legal packet

### 5) Track
Purpose: maintain state and progress.
- Case status progression
- Task completion
- Hearing/deadline progress
- Activity and chain-of-custody audit

### 6) Collaborate
Purpose: connect people safely.
- Tenant-to-advocate handoff
- Advocate-to-legal escalation
- Privileged legal notes separation
- Admin oversight and system alerts

## Role-by-Role UI Scope

### Tenant UI (/tenant)
Primary focus: Capture -> Understand -> Plan.
- Must show: My Case, Documents, Timeline, Help, AI assistant
- Hide legal/admin complexity by default
- Prominent emergency and deadline actions

### Advocate UI (/advocate)
Primary focus: Capture -> Plan -> Track across multiple clients.
- Must show: Clients, Queue, Intake, Documents, Timeline
- Multi-case triage and assignment
- Non-privileged coordination notes

### Legal UI (/legal)
Primary focus: Plan -> Act with privileged workflows.
- Must show: Case Files, Filings, Privileged Notes, Conflicts, Law Library
- Clear privilege boundaries
- Court-ready document generation entry points

### Admin UI (/admin)
Primary focus: Track -> Collaborate -> Configure.
- Must show: Mission Control, GUI Hub, Mode Selector, Docs Hub
- System health, rollout controls, audit views
- Feature flags and compatibility routing visibility

## Natural Input Framework (Easy Input)
Every role home starts with one unified intake surface.

### Unified Intake Surface
- Text box: "Tell Semptify what happened"
- Upload zone: drag/drop documents
- Voice button: speak your issue
- Quick chips: "Missed rent", "Notice received", "Court date", "Repair issue"

### Input Pipeline
1. Capture input (text/upload/voice/chip)
2. Normalize into one IntakeEvent object
3. Route through auto analysis
4. Produce immediate output:
   - What we found
   - What is urgent
   - What to do next

### IntakeEvent Contract
- actor_role
- source_type (text|file|voice|chip)
- raw_content
- case_context_id
- timestamp
- confidence

## Shared App Shell Standard
All role pages use the same shell structure:
- Header: role badge, case context, quick emergency action
- Left nav: role-scoped menu only
- Main workspace: current function group panel
- Right rail (optional): urgent actions + next steps
- Footer: sync status + user/session status

## Route and Alias Policy
1. Canonical routes are role homes and approved subroutes only.
2. Legacy static URLs must redirect to canonical path or mapped alias.
3. New feature pages are never linked directly from role nav until they are mapped into a function group.

## Migration Plan

### Phase A: Stabilize routing
- Keep canonical homes as single source of truth.
- Add explicit alias mapping tables for tenant/advocate/legal/admin subpages.
- Reject unsafe path traversal.

### Phase B: Unify shell
- Move role homes to shared template shell blocks.
- Ensure each role home has the same layout system.

### Phase C: Function-group navigation
- Replace page-by-page nav with function-group nav labels.
- Keep page internals role-specific.

### Phase D: Easy input everywhere
- Add unified intake surface to all role homes.
- Connect to common IntakeEvent pipeline.

### Phase E: Guardrails and tests
- Add route tests for canonical and alias paths.
- Add smoke tests for role menu links.
- Add regression tests for urgent action rendering.

## Definition of Done
1. Every role has one canonical home that loads reliably.
2. Every role nav item resolves to an existing, working route.
3. Every role home includes the same unified intake surface.
4. Every intake path (text/upload/voice/chip) produces an action plan.
5. Legacy links redirect cleanly to canonical structure.
6. Route, alias, and menu tests pass.

## Immediate Execution Backlog
1. Build shared role shell template and apply to tenant/advocate/legal/admin templates.
2. Add role route tests for:
   - /tenant, /advocate, /legal, /admin
   - mapped aliases for each role
3. Add one reusable "easy input" component and mount it in all role homes.
4. Refactor role navigation labels to function-group language.
5. Add a compatibility report endpoint listing alias coverage and broken links.
