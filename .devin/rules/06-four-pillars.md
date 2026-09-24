---
description: Four-pillar module map and assignment rules
---

# Four Pillars

Every module must be assigned to exactly one pillar before it is built.

| Pillar | Audience | Examples |
|---|---|---|
| **RECORD** | Tenant primary (core) | Document Center, Vault, Timeline, Journal, Calendar, Capture, Rent Ledger, Comms Log, PDF Tools, FEMS |
| **KNOW** | Everyone | Law Library, State Laws, Context Engine, RISC, Free API Pack, Court Case Lookup, Housing Accountability, Location/Jurisdiction, Search |
| **ACT** | Tenant (+ share-granted helpers) | Case Builder, Eviction Defense, Court Forms, Court Packet, Legal Filing, Complaint Wizard, Guided Intake, Plan Maker, MNDES, Legal Trails |
| **GOVERN** | Ops only (dormant) | Admin Console, Module Flags, Semptify Forge, Capability System, Onboarding, Auth/Storage, Role UI, Workflow Engine, Audit Logs, Dev Tools |

## Assignment rules

- **RECORD** = tenant primary. The two core tenant pillars are RECORD + KNOW.
- **KNOW** = everyone can access verified facts; facts only, no opinions.
- **ACT** = guided lawful action; authenticated tenant. Share-granted helpers (advocate/legal tooling) are tenant-authorized via sharing, not roles — no pro roles exist in this repo (PR #317).
- **GOVERN** = platform integrity; never tenant-facing. There is no admin role — GOVERN surfaces are dormant, reachable only via Brad's env-credentialed ops elevation.
