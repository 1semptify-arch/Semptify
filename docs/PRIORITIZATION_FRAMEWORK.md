# Semptify Prioritization Framework

**Purpose**: How we decide what to work on and what to defer.

---

## Priority Levels

### 🔴 P0 - CRITICAL (Work on now)
**Criteria**:
- Blocks all other work
- Production is broken
- Legal/compliance risk
- Security vulnerability

**Examples**:
- Core mechanics stabilization
- Single source of truth implementation
- Security patches

### 🟠 P1 - HIGH (Next in queue)
**Criteria**:
- Required for core functionality
- Has active dependencies waiting
- User-facing bug affecting workflows

**Examples**:
- Document upload/timeline alignment
- Workflow routing completion

### 🟡 P2 - MEDIUM (Plan for soon)
**Criteria**:
- Improves user experience
- Reduces technical debt
- Enables future features

**Examples**:
- Performance optimizations
- UI polish
- Additional integrations

### 🟢 P3 - LOW (Backlog)
**Criteria**:
- Nice to have
- No active dependencies
- Can wait indefinitely

**Examples**:
- Analytics
- Nice-to-have features

### 🅿️ PARKED (Design only)
**Criteria**:
- Design is complete
- Implementation would create tech debt now
- Blocked by prerequisite work
- Would conflict with active work

**Process**:
1. Create design document
2. Add to `docs/BUILD_OUT_STATUS.md` as PARKED
3. Add to `ACTIVE_CONTEXT.md`
4. Set "Resume When" criteria
5. Do NOT create implementation files

---

## Prioritization Decision Tree

```
Is there a production issue?
├── YES → P0 (Fix immediately)
└── NO → Is it core mechanics?
    ├── YES → Is it blocking other work?
    │   ├── YES → P0
    │   └── NO → P1
    └── NO → Is there a design doc?
        ├── YES → PARK (don't implement yet)
        └── NO → Does it reduce tech debt?
            ├── YES → P2
            └── NO → P3
```

---

## Current Priorities (As of 2026-04-20)

### P0 - Active Now
| Task | Why P0 |
|------|--------|
| Stateless routing (`route_user()`) | Foundation for everything else |
| Cloud storage patterns | Must be stable before overlay work |

### P1 - Next
| Task | Blocked By |
|------|------------|
| Document mechanics alignment | Routing stable |
| Overlay system integration (current 3) | Cloud patterns stable |

### 🅿️ PARKED
| Project | Design Doc | Resume When |
|---------|------------|-------------|
| Unified Overlay System | `docs/OVERLAY_SYSTEM_DESIGN.md` | Core mechanics stable |

---

## Anti-Patterns (Don't Do These)

### ❌ Starting multiple big projects
**Why**: Context switching kills velocity. Finish core mechanics before starting overlays.

### ❌ Implementing without design
**Why**: You'll end up with 3 separate overlay systems (current state).

### ❌ "Quick fixes" that add tech debt
**Why**: They compound. The local `document_overlay_service.py` was a "quick fix."

### ❌ Working on parked items
**Why**: You'll create conflicts with prerequisite work.

---

## How to Park Something

1. **Create design document**: `docs/{PROJECT}_DESIGN.md`
2. **Add to BUILD_OUT_STATUS.md**: Under "### Parked" section
3. **Add to BLUEPRINT.md**: Mark with 🅿️ PARKED
4. **Update ACTIVE_CONTEXT.md**: List in PARKED section
5. **Set resume criteria**: Specific conditions for when to resume

**Do NOT**:
- Create implementation files
- Add to main codebase
- Start parallel work on it

---

## How to Unpark Something

1. Check "Resume When" criteria - ALL must be met
2. Review design document for currency
3. Update priority to P1 or P0
4. Remove from PARKED sections
5. Create implementation plan

---

## Weekly Review Checklist

- [ ] Review ACTIVE_CONTEXT.md - still accurate?
- [ ] Check PARKED items - any unblocked?
- [ ] Verify P0 items - making progress?
- [ ] Reassess priorities based on new information

---

## Files That Track Priority

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `ACTIVE_CONTEXT.md` | What's being worked on NOW | Daily |
| `docs/BUILD_OUT_STATUS.md` | Build status + parked items | Weekly |
| `BLUEPRINT.md` | System inventory | When adding major components |
| `docs/*_DESIGN.md` | Parked project designs | When design changes |

---

## Principles

1. **Finish before starting**: Complete core mechanics before overlays
2. **Design before building**: No more 3 separate systems
3. **Park, don't delete**: Preserve work without creating conflicts
4. **Resume with criteria**: Clear conditions for when to unpark
5. **One source of truth**: `ACTIVE_CONTEXT.md` is current priority

---

*This framework applies to all Semptify development work.*
