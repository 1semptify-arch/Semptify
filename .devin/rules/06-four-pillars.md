---
description: Four-pillar module map and assignment rules
---

# Four Pillars

Every module must be assigned to exactly one pillar before it is built.

| Pillar | Audience | Examples |
|---|---|---|
| **RECORD** | Tenant primary (core) | Document Center, Vault, Timeline, Journal, Calendar, Capture, Rent Ledger, Comms Log, PDF Tools, FEMS |
| **KNOW** | All roles | Law Library, State Laws, Context Engine, RISC, Free API Pack, Court Case Lookup, Housing Accountability, Location/Jurisdiction, Search |
| **ACT** | Tenant + Advocate + Legal | Case Builder, Eviction Defense, Court Forms, Court Packet, Legal Filing, Complaint Wizard, Guided Intake, Plan Maker, MNDES, Legal Trails |
| **GOVERN** | Admin + Dev only | Admin Console, Module Flags, Semptify Forge, Capability System, Onboarding, Auth/Storage, Role UI, Workflow Engine, Audit Logs, Dev Tools |

## Assignment rules

- **RECORD** = tenant primary. The two core tenant pillars are RECORD + KNOW.
- **KNOW** = all roles can access verified facts; facts only, no opinions.
- **ACT** = guided lawful action; requires Tenant, Advocate, or Legal role.
- **GOVERN** = platform integrity; never tenant-facing.
