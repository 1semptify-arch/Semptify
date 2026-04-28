---
description: SSOT Architecture Analysis - Trace data flow through Semptify systems
---

# SSOT Analysis Workflow

Use this when analyzing data flows, document paths, or system interactions in Semptify.

## Purpose

Trace how information moves through the system from entry to storage to retrieval, identifying:
- Where data is stored (primary, backup, cache)
- Transformation steps and their weights (CPU, I/O, network)
- SSOT compliance (single source of truth violations)
- Integration points between services

## Steps

### 1. Identify Entry Point

Find where the data/action originates:
```
- HTTP endpoint? → routers/*.py
- Internal service? → services/*.py
- Background job? → core/jobs.py or worker files
- User action? → static/*.html + router
```

### 2. Trace the Path

Follow the data through each system:
```
Step N: [System/Service Name]
├─ What happens here? (transform, store, validate)
├─ WEIGHT: [High/Medium/Low] + reason (I/O, CPU, network)
├─ BALANCE: What trade-off does this step make?
└─ OUTPUT: What format/structure emerges?
```

### 3. Map Storage Locations

Create table of where data lives:

| Data Type | Primary | Backup | Cache | Access Pattern |
|-----------|---------|--------|-------|----------------|
| Original | Path A | Path B | Path C | Read/Write freq |

### 4. Identify SSOT Issues

Check for violations:
- [ ] Multiple sources of same data?
- [ ] Race conditions between writes?
- [ ] Orphaned data in one system but not another?
- [ ] Uncertified/unverified data flowing downstream?

### 5. Document Flow Diagram

```
[Entry] → [Step 1] → [Step 2] → ... → [Final Storage]
            ↓           ↓
        [Side Effect] [Event Trigger]
```

### 6. Certification States (for documents)

Define valid states for tracked entities:

| State | Field A | Field B | Status | Meaning |
|-------|---------|---------|--------|---------|
| Valid | ✅ | ✅ | `True` | Ready for use |
| Partial | ✅ | ❌ | `False` | Needs completion |
| Invalid | ❌ | - | `False` | Failed/rejected |

### 7. Propose Unification

If multiple steps call same service separately → UNIFY:

**OLD (Distributed):**
```
Service A → calls Registry
Service B → calls Registry (redundant)
Router   → calls Registry (redundant)
```

**NEW (Unified):**
```
Service A → Auto-registers → returns certified object
Service B → Uses certified object
Router   → Enriches only (no separate call)
```

### 8. Update SSOT Documentation

Add to `docs/SSOT_EXPORT.md`:
- New unified flow diagram
- Certification states table
- SSOT rule (one-sentence principle)
- Code pattern (old vs new)

## Template Output

```markdown
## [Feature] Flow Analysis

### Path (N Steps)
```
Step 0: [Entry]
...
```

### Storage Locations
| Type | Primary | Backup | Cache |
|------|---------|--------|-------|
| ... | ... | ... | ... |

### SSOT Rule
> "[One-sentence principle]"

### Certification States
| State | ... | is_valid | Meaning |
|-------|-----|----------|---------|
| ... | ... | ... | ... |

### Code Pattern
```python
# OLD: [problem]
...

# NEW: [solution]
...
```
```

## Example: Document Upload Flow

See `docs/SSOT_EXPORT.md` section 1.1 for completed example.

Key insight: Every vault document auto-registers - router only enriches.
