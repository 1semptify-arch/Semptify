# Data Storage Assessment & Interactive Timeline Design

**Date:** 2025-04-22  
**Scope:** PostgreSQL, User Cloud Storage (Google Drive/Dropbox/OneDrive), Timeline/Vault Data

---

## 1. Current Storage Architecture

### 1.1 PostgreSQL (Primary Metadata Store)

**Strengths:**
- ✅ Proper timezone handling (`DateTime(timezone=True)` with UTC)
- ✅ Indexed foreign keys (`user_id` on all tables)
- ✅ JSONB support for flexible metadata
- ✅ Relationship cascading (`delete-orphan`)

**Tables with Timeline-Relevant Data:**

| Table | Purpose | Key Date Columns | Indexed |
|-------|---------|------------------|---------|
| `users` | User accounts | `created_at`, `updated_at`, `last_login` | ✅ |
| `documents` | Document metadata | `uploaded_at` | ✅ (user_id) |
| `timeline_events` | Manual events | `event_date`, `created_at` | ✅ (user_id, event_date) |
| `calendar_events` | Deadlines/hearings | `start_datetime`, `created_at` | ✅ (user_id) |
| `vault_items` | Evidence vault | `event_time`, `record_time`, `semptify_entry_time` | ✅ (all 3) |
| `rent_payments` | Payment records | `payment_date`, `due_date` | ✅ (user_id) |
| `complaints` | Agency complaints | `created_at`, `updated_at` | ✅ (user_id) |
| `certified_mail` | Mail tracking | `sent_date`, `delivered_date` | ✅ (user_id) |

### 1.2 User Cloud Storage (Primary Document Store)

**SSOT Paths:** (`app/core/vault_paths.py`)
```
Semptify5.0/Vault/
├── documents/              # Raw uploaded files
├── certificates/           # Document certifications
├── timeline/
│   └── events.json         # Auto-extracted timeline events (SSOT)
└── overlays/
    ├── registry.json       # Overlay manifest
    ├── documents/          # Per-document overlays
    ├── queries/            # Query overlays
    └── forms/              # Form-fill overlays
```

**Three-Timestamp Model** (vault_items table):
| Timestamp | Meaning | Source |
|-----------|---------|--------|
| `event_time` | When the event actually occurred | Document content/EXIF/extraction |
| `record_time` | When the document was created | File system/EXIF DateTimeOriginal |
| `semptify_entry_time` | When uploaded to Semptify | System generated |

---

## 2. Data Storage Assessment

### 2.1 What's Working Well

| Aspect | Status | Notes |
|--------|--------|-------|
| Timezone handling | ✅ | All `DateTime(timezone=True)` with UTC |
| Foreign key integrity | ✅ | Proper FK constraints with indexes |
| Cloud-first documents | ✅ | Documents live in user cloud, metadata in PG |
| Extracted timeline events | ✅ | `events.json` in cloud is SSOT |
| Three-timestamp model | ✅ | `vault_items` has proper provenance tracking |
| JSONB metadata | ✅ | Deep searchable JSON for EXIF, headers, etc. |

### 2.2 Areas for Improvement

| Issue | Impact | Solution |
|-------|--------|----------|
| **Document ID mismatch** | Medium | `documents` table uses `String(36)` but `vault_items` uses integer `item_id`. Hard to correlate. |
| **Timeline events in two places** | High | DB `timeline_events` and cloud `events.json` can diverge. Need merge strategy. |
| **No unified date index** | High | Can't query across documents/calendar/events by date range efficiently. |
| **Calendar not linked to timeline** | Medium | Court dates in `calendar_events` aren't automatically in timeline view. |
| **Rent payments isolated** | Low | Payment records not surfaced in timeline view. |
| **Missing GIN indexes on JSONB** | Medium | `vault_items.item_metadata` and `tags` not GIN-indexed for search. |

### 2.3 Recommendations (Priority Order)

#### Priority 1: Unified Timeline View Query
Create a materialized view or service that aggregates all time-based data:

```sql
-- Concept: Unified chronology view
CREATE VIEW unified_chronology AS
-- Documents (upload date)
SELECT 
    'document' as item_type,
    d.id,
    d.user_id,
    d.uploaded_at as sort_date,
    d.document_type,
    d.filename as title,
    NULL as description
FROM documents d

UNION ALL

-- Timeline events (event date)
SELECT 
    'timeline_event' as item_type,
    te.id,
    te.user_id,
    te.event_date as sort_date,
    te.event_type,
    te.title,
    te.description
FROM timeline_events te

UNION ALL

-- Calendar events (start date)
SELECT 
    'calendar_event' as item_type,
    ce.id,
    ce.user_id,
    ce.start_datetime as sort_date,
    ce.event_type,
    ce.title,
    ce.description
FROM calendar_events ce

UNION ALL

-- Vault items (event time)
SELECT 
    'vault_item' as item_type,
    vi.item_id::text,
    vi.user_id,
    vi.event_time as sort_date,
    vi.item_type,
    vi.title,
    vi.summary as description
FROM vault_items vi;
```

#### Priority 2: Add GIN Index on JSONB
```sql
-- For deep metadata search
CREATE INDEX idx_vault_items_metadata ON vault_items USING GIN (item_metadata);
CREATE INDEX idx_vault_items_tags ON vault_items USING GIN (tags);
```

#### Priority 3: Link Document IDs
Add `document_registry_id` to `vault_items` table to link cloud documents with vault items.

#### Priority 4: Calendar → Timeline Sync
Auto-create timeline events when calendar events are added (especially court dates).

---

## 3. Interactive Timeline View Design

### 3.1 User Requirements

From your request:
> "I want an interactive timeline view of all things in the vault. On-the-fly ability to change the displayed data in different ranges. Display documents according to date-recorded and then maybe the event time."

**Key Features:**
1. **Multi-source aggregation** — Documents, timeline events, calendar, vault items
2. **Dynamic date axis** — Switch between: `event_time`, `record_time`, `semptify_entry_time`, `uploaded_at`
3. **Range filtering** — Date range slider/wheel (day/week/month/year views)
4. **Real-time updates** — As new docs upload, timeline updates
5. **Evidence highlighting** — Court-relevant items stand out

### 3.2 Proposed API Design

```python
# GET /api/timeline/unified
class TimelineViewRequest(BaseModel):
    date_axis: str = "event_time"  # event_time | record_time | entry_time | uploaded_at
    start_date: Optional[str] = None  # ISO date or "-30d", "-6m", "-1y"
    end_date: Optional[str] = None
    item_types: List[str] = ["document", "vault_item", "timeline_event", "calendar_event"]
    evidence_only: bool = False
    
class TimelineItem(BaseModel):
    id: str
    item_type: str  # document | vault_item | timeline_event | calendar_event | payment
    title: str
    description: Optional[str]
    date_display: str  # The date shown (based on date_axis)
    event_date: Optional[str]  # When it happened
    record_date: Optional[str]  # When created
    entry_date: str  # When added to Semptify
    is_evidence: bool
    urgency: Optional[str]  # critical | high | normal
    icon: str  # FontAwesome/Lucide icon name
    color: str  # Tailwind color class
    source: str  # upload | extraction | manual | calendar
    document_id: Optional[str]  # Link to document
    thumbnail_url: Optional[str]

class TimelineViewResponse(BaseModel):
    items: List[TimelineItem]
    total: int
    date_range: Dict[str, str]  # {start, end}
    group_by: str  # day | week | month | year
    facets: Dict[str, int]  # {document: 42, timeline_event: 15, ...}
```

### 3.3 Frontend Component Structure

```html
<!-- Timeline Container -->
<div class="timeline-interactive">
  
  <!-- Controls -->
  <div class="timeline-controls">
    <!-- Date Axis Selector -->
    <select id="date-axis">
      <option value="event_time">Event Date (when it happened)</option>
      <option value="record_time">Record Date (when created)</option>
      <option value="entry_time">Upload Date (when added to Semptify)</option>
    </select>
    
    <!-- Range Slider -->
    <input type="range" id="range-slider" min="0" max="100" value="50">
    
    <!-- View Mode -->
    <button-group>
      <button data-view="list">List</button>
      <button data-view="timeline">Timeline</button>
      <button data-view="calendar">Calendar</button>
    </button-group>
    
    <!-- Filters -->
    <filter-chips>
      <chip data-type="document">Documents</chip>
      <chip data-type="event">Events</chip>
      <chip data-type="court">Court Dates</chip>
      <chip data-type="evidence" data-highlight>Evidence Only</chip>
    </filter-chips>
  </div>
  
  <!-- Timeline Visualization -->
  <div class="timeline-visualization">
    <!-- Year/Month Headers -->
    <div class="timeline-groups">
      <div class="group" data-year="2025">
        <div class="group-header">2025</div>
        <div class="group-items">
          <!-- Items rendered here -->
        </div>
      </div>
    </div>
  </div>
  
  <!-- Detail Panel (slide-out) -->
  <div class="timeline-detail" id="detail-panel">
    <!-- Document/Event details -->
  </div>
</div>
```

### 3.4 Implementation Plan

#### Phase 1: Backend API (2-3 hours)
1. Create `GET /api/timeline/unified` endpoint
2. Implement `TimelineAggregationService`:
   - Query cloud `events.json` (primary)
   - Query DB `timeline_events` (fallback/merge)
   - Query `documents` for upload dates
   - Query `calendar_events` for court dates
   - Query `vault_items` for evidence items
3. Add date axis switching logic
4. Add range filtering

#### Phase 2: Frontend Component (3-4 hours)
1. Create `InteractiveTimeline` web component
2. Date axis selector dropdown
3. Range slider with zoom (day/week/month/year)
4. Virtual scrolling for performance (1000+ items)
5. Item cards with icons/colors by type

#### Phase 3: Integration (1 hour)
1. Add to `/vault` page as main view
2. Real-time updates via WebSocket or polling
3. Mobile responsive layout

### 3.5 Data Flow

```
User opens Vault Timeline
    ↓
Frontend: GET /api/timeline/unified?date_axis=event_time&range=-1y
    ↓
Backend:
  1. Load cloud events.json (Semptify5.0/Vault/timeline/events.json)
  2. Query DB for manual timeline_events (merge with cloud)
  3. Query documents table (for upload metadata)
  4. Query calendar_events (for court dates)
  5. Merge & sort by selected date_axis
    ↓
Response: TimelineViewResponse
    ↓
Frontend: Render with virtualization
```

### 3.6 SQL Schema Enhancements

```sql
-- Add view for unified timeline (read-only)
CREATE OR REPLACE VIEW unified_timeline AS
WITH all_items AS (
    -- Documents
    SELECT 
        d.id,
        d.user_id,
        'document'::text as item_type,
        d.filename as title,
        d.document_type,
        d.uploaded_at as semptify_entry_time,
        d.uploaded_at as record_time,
        NULL::timestamp as event_time,
        FALSE as is_evidence,
        'normal'::text as urgency
    FROM documents d
    
    UNION ALL
    
    -- Timeline events
    SELECT 
        te.id,
        te.user_id,
        'timeline_event'::text as item_type,
        te.title,
        te.event_type as document_type,
        te.created_at as semptify_entry_time,
        te.event_date as record_time,
        te.event_date as event_time,
        te.is_evidence,
        CASE 
            WHEN te.urgency IS NOT NULL THEN te.urgency
            WHEN te.is_deadline THEN 'critical'
            ELSE 'normal'
        END as urgency
    FROM timeline_events te
    
    UNION ALL
    
    -- Calendar events
    SELECT 
        ce.id,
        ce.user_id,
        'calendar_event'::text as item_type,
        ce.title,
        ce.event_type as document_type,
        ce.created_at as semptify_entry_time,
        ce.start_datetime as record_time,
        ce.start_datetime as event_time,
        ce.is_critical as is_evidence,
        CASE WHEN ce.is_critical THEN 'critical' ELSE 'normal' END as urgency
    FROM calendar_events ce
    
    UNION ALL
    
    -- Vault items
    SELECT 
        vi.item_id::text,
        vi.user_id,
        'vault_item'::text as item_type,
        COALESCE(vi.title, vi.item_type) as title,
        vi.item_type as document_type,
        vi.semptify_entry_time,
        vi.record_time,
        vi.event_time,
        FALSE as is_evidence,
        COALESCE(vi.severity, 'normal') as urgency
    FROM vault_items vi
)
SELECT * FROM all_items;

-- GIN indexes for JSONB search
CREATE INDEX idx_vault_items_metadata_gin ON vault_items USING GIN (item_metadata jsonb_path_ops);
CREATE INDEX idx_vault_items_tags_gin ON vault_items USING GIN (tags);

-- Composite index for timeline queries
CREATE INDEX idx_documents_user_uploaded ON documents(user_id, uploaded_at DESC);
CREATE INDEX idx_timeline_events_user_date ON timeline_events(user_id, event_date DESC);
```

---

## 4. Quick Wins (Can Implement Now)

### 4.1 Add Date Axis to Existing Timeline Endpoint
Modify `GET /api/timeline/` to accept `?sort_by=event_time|record_time|uploaded_at`

### 4.2 Add Range Filter to Existing Endpoint
Add `?start_date=2025-01-01&end_date=2025-03-31` to existing timeline endpoint.

### 4.3 Create Simple Unified View
Create the SQL view above (no code changes needed, just SQL).

---

## 5. Summary

| Question | Answer |
|----------|--------|
| **Is data stored properly?** | Yes. Three-timestamp model is correct. JSONB for metadata is good. |
| **Is data stored efficiently?** | Mostly. Missing GIN indexes on JSONB. Missing unified date index. |
| **Is data stored consistently?** | Yes. All datetime columns are timezone-aware UTC. |
| **Where can we improve?** | 1) Unified timeline view 2) GIN indexes 3) Document-vault item linking 4) Calendar→timeline sync |

**Recommendation:** Start with the SQL view (5 min), then build the interactive timeline API/frontend.
