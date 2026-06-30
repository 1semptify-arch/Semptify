# 🤖 Auto Mode - Fully Automated Case Analysis System

## Overview

The Auto Mode system provides **fully automated analysis** of every document uploaded to Semptify. When a user uploads a document, the system automatically:

1. ✅ **Extracts timeline** - Dates, events, deadlines
2. ✅ **Generates calendar** - Events with reminders  
3. ✅ **Identifies complaints** - Regulatory agencies to contact
4. ✅ **Assesses rights** - Tenant protections & strengths
5. ✅ **Detects missteps** - Legal procedural violations
6. ✅ **Suggests tactics** - Proactive defense strategies
7. ✅ **Generates summary** - Progress report with actionable recommendations

---

## System Architecture

### Core Components

#### 1. **AutoModeOrchestrator** (`app/services/auto_mode_orchestrator.py`)
Central orchestrator that coordinates all automated analyses.

**Method:** `run_full_auto_analysis()`
- Triggers all analysis engines sequentially
- Collects results into unified structure
- Generates comprehensive summary
- Publishes results via event bus

```python
results = await orchestrator.run_full_auto_analysis(
    doc_id="doc_123",
    user_id="user_456",
    document_content="...eviction notice text...",
    filename="Eviction_Notice.pdf"
)
```

#### 2. **AutoModeSummaryService** (`app/services/auto_mode_summary_service.py`)
Generates comprehensive summaries and actionable recommendations.

**Key Outputs:**
- Timeline summary with event counts
- Calendar event summary with upcoming dates
- Complaint filing opportunities
- Rights assessment (strengths/weaknesses)
- Detected legal missteps
- Recommended defense tactics
- **Recommended Actions** - Prioritized action items
- **Urgent Actions** - Time-sensitive critical items
- **Next Steps** - Guided workflow
- **Progress & Confidence** - Metrics about analysis quality

#### 3. **Analysis Engines** (Already Exist)
- **TimelineBuilder** - Extracts dates and events
- **CalendarService** - Creates calendar events
- **LegalAnalysisEngine** - Assesses rights and missteps
- **ComplaintWizard** - Identifies complaint opportunities
- **ProactiveTacticsEngine** - Recommends defense strategies

#### 4. **Auto Mode Router** (`app/routers/auto_mode.py`)
REST API endpoints for:
- Enable/disable auto mode
- Configure analysis settings
- Trigger manual analysis
- Get analysis results

---

## Workflow

### User Uploads Document

```
User uploads eviction notice
    ↓
Intake Router receives file
    ↓
AUTO MODE TRIGGERED (if enabled)
    ↓
AutoModeOrchestrator.run_full_auto_analysis()
    ├─ TimelineBuilder extracts timeline
    ├─ CalendarService generates calendar
    ├─ LegalAnalysisEngine assesses case
    ├─ ComplaintWizard identifies agencies
    ├─ ProactiveTacticsEngine suggests tactics
    └─ AutoModeSummaryService creates summary
    ↓
Summary Generated with:
    • Analysis results
    • Progress (0-100%)
    • Confidence score
    • Recommended actions
    • Urgent alerts
    • Next steps
    ↓
Results Published via Event Bus
    ↓
UI Updates in Real-Time
    ├─ Progress bar updates
    ├─ Urgent warnings displayed
    ├─ Action cards shown
    └─ Next steps outlined
```

---

## Analysis Summary Structure

### Full JSON Response

```json
{
  "status": "complete",
  "doc_id": "doc_123",
  "filename": "Eviction_Notice.pdf",
  "analysis_timestamp": "2024-03-23T10:30:00Z",
  
  "summary": {
    "overall_progress": 85,
    "analysis_confidence": 0.92,
    
    "timeline_events": 12,
    "calendar_events": 5,
    "complaints": 2,
    "rights": 8,
    "missteps": 3,
    "tactics": 4,
    
    "summaries": {
      "timeline": "Extracted 12 timeline events...",
      "calendar": "Generated 5 calendar events...",
      "complaints": "Identified 2 complaints...",
      "rights": "Your Strengths (3)... Areas to Address (2)...",
      "missteps": "3 potential legal missteps detected...",
      "tactics": "Recommended 4 defense tactics..."
    },
    
    "recommended_actions": [
      {
        "action_id": "review_timeline",
        "title": "Review Extracted Timeline",
        "description": "12 events extracted - verify accuracy",
        "priority": "high",
        "estimated_time": "5-10 minutes",
        "link": "/timeline?doc_id=doc_123"
      },
      {
        "action_id": "file_complaints",
        "title": "File 2 Complaint(s)",
        "description": "Regulatory agencies identified",
        "priority": "high",
        "estimated_time": "20-30 min/complaint",
        "link": "/complaints?doc_id=doc_123"
      },
      {
        "action_id": "address_missteps",
        "title": "Address 3 Legal Misstep(s)",
        "description": "Procedural violations detected",
        "priority": "critical",
        "estimated_time": "15-30 minutes",
        "link": "/legal-missteps?doc_id=doc_123"
      },
      {
        "action_id": "implement_tactics",
        "title": "Consider 4 Defense Tactic(s)",
        "description": "Proactive strategies identified",
        "priority": "medium",
        "estimated_time": "15-20 minutes",
        "link": "/tactics?doc_id=doc_123"
      }
    ],
    
    "urgent_actions": [
      {
        "action": "address_missteps",
        "message": "⚠️ 3 legal procedural violations detected",
        "severity": "critical",
        "deadline": "Immediate"
      },
      {
        "action": "file_complaints",
        "message": "📋 2 complaints ready to file",
        "severity": "high",
        "deadline": "Within 3 days"
      }
    ],
    
    "next_steps": [
      "1. Review extracted timeline and calendar for accuracy",
      "2. ⚠️ ADDRESS MISSTEPS IMMEDIATELY",
      "3. Consider filing complaints",
      "4. Evaluate defense tactics",
      "5. Gather supporting documentation",
      "6. Upload more documents",
      "7. Share with legal counsel"
    ]
  }
}
```

---

## UI Components

### Auto Analysis Summary Dashboard (`static/auto_analysis_summary.html`)

**Features:**
- Progress bar (0-100%)
- Confidence score display
- Urgent actions alerts (with color coding)
- 6 Summary cards (Timeline, Calendar, Complaints, Rights, Missteps, Tactics)
- Recommended actions (clickable cards)
- Next steps (ordered workflow)
- Responsive design (mobile-friendly)

**Color Coding:**
- 🔴 **Critical Priority** - Red (missteps, violations)
- 🟠 **High Priority** - Orange (complaints, deadlines)
- 🔵 **Medium Priority** - Blue (review actions)
- ✅ **Completed** - Green

---

## API Endpoints

### 1. **Get Auto Mode Status**
```
GET /api/auto-mode/status
```
Returns current auto mode configuration and status.

### 2. **Toggle Auto Mode**
```
POST /api/auto-mode/toggle
{
  "enabled": true
}
```

### 3. **Update Configuration**
```
POST /api/auto-mode/config
{
  "auto_generate_timeline": true,
  "auto_generate_calendar": true,
  "auto_identify_complaints": true,
  "auto_assess_rights": true,
  "auto_detect_missteps": true,
  "auto_suggest_tactics": true
}
```

### 4. **Get Analysis Results**
```
GET /api/auto-mode/analysis/{doc_id}
```

### 5. **Run Manual Analysis**
```
POST /api/auto-mode/run-analysis/{doc_id}
{
  "document_content": "...",
  "filename": "document.pdf"
}
```

### 6. **Get Available Features**
```
GET /api/auto-mode/features
```

---

## Recommended Actions Explained

### 1. **Review Extracted Timeline** (HIGH)
- **What:** Verify dates and events extracted from documents
- **Why:** Accuracy is critical for your legal case
- **Time:** 5-10 minutes
- **Link:** `/timeline?doc_id={doc_id}`

### 2. **File Complaints** (HIGH)
- **What:** File regulatory complaints with identified agencies
- **Why:** Multiple complaint channels strengthen your position
- **Time:** 20-30 minutes per complaint
- **Link:** `/complaints?doc_id={doc_id}`

### 3. **Review Legal Rights** (HIGH)
- **What:** Understand your tenant rights and protections
- **Why:** Know your legal position and defenses available
- **Time:** 10-15 minutes
- **Link:** `/legal-analysis?doc_id={doc_id}`

### 4. **Address Legal Missteps** (CRITICAL)
- **What:** Review procedural violations by landlord/court
- **Why:** Could result in case dismissal or favorable ruling
- **Time:** 15-30 minutes
- **Link:** `/legal-missteps?doc_id={doc_id}`

### 5. **Implement Defense Tactics** (MEDIUM)
- **What:** Review and plan proactive defense strategies
- **Why:** Strengthen your case before trial
- **Time:** 15-20 minutes
- **Link:** `/tactics?doc_id={doc_id}`

---

## Progress Calculation

Progress is calculated based on completed analyses:
- Timeline extraction: **15%**
- Calendar generation: **10%**
- Complaint identification: **15%**
- Rights assessment: **15%**
- Missteps detection: **15%**
- Tactics recommendation: **15%**
- Document processed: **5%**

**Total: 85% = document fully analyzed**

---

## Confidence Scoring

Confidence (0.0-1.0) is calculated based on:
- **Baseline:** 0.5
- **Timeline quality:** +0.0-0.2 (based on events found)
- **Legal analysis:** +0.15 (if missteps detected)
- **Analysis diversity:** +0.15 (multiple engines used)

**Example:** 0.5 + 0.15 + 0.15 + 0.15 = **0.95 confidence**

---

## Integration Points

### Document Upload Flow
```
1. User uploads document
   ↓
2. Intake Router processes
   ↓
3. IF auto_mode enabled:
   - Trigger AutoModeOrchestrator
   - Generate full summary
   - Publish to event bus
   ↓
4. UI receives results
   ↓
5. Display summary dashboard
   ↓
6. Show recommended actions
```

### Event Bus Integration
```python
# Published event
BusEventType.AUTO_ANALYSIS_COMPLETE
{
    'doc_id': 'doc_123',
    'user_id': 'user_456',
    'results': {...},
    'summary': {...}
}
```

---

## Feature Toggle

Users can enable/disable auto mode in settings:

```python
# Settings page provides toggle
Auto Mode: [ON/OFF]

Individual features can be toggled:
☑ Auto Timeline Extraction
☑ Auto Calendar Generation
☑ Auto Complaint Identification
☑ Auto Rights Assessment
☑ Auto Misstep Detection
☑ Auto Tactics Suggestion
```

---

## Future Enhancements

1. **Persistence** - Store summaries in database
2. **Webhooks** - Notify external systems when analysis completes
3. **AI Refinement** - Use feedback to improve analysis accuracy
4. **Export** - Generate PDF reports of summaries
5. **Sharing** - Share analysis with legal counsel
6. **Notifications** - Email/SMS alerts for urgent actions
7. **Batch Processing** - Upload multiple files at once
8. **Custom Rules** - Allow users to define analysis rules

---

## Error Handling

If analysis fails:
```json
{
  "status": "error",
  "error": "Failed to extract timeline",
  "doc_id": "doc_123",
  "fallback": "Manual review recommended"
}
```

All analysis stages have try-catch to ensure partial results are returned.

---

## Configuration Files

Key files:
- `app/services/auto_mode_orchestrator.py` - Main orchestrator
- `app/services/auto_mode_summary_service.py` - Summary generation
- `app/routers/auto_mode.py` - API endpoints
- `static/auto_analysis_summary.html` - UI dashboard
- `app/main.py` - Router registration