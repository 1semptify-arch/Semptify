# Semptify Context Systems Overview
## How Context is Handled Across the Platform

**Date:** June 14, 2026  
**Purpose:** Document all context engines and their integration points

---

## 🧠 Core Context Architecture

Semptify has **multiple context engines** that work together to provide a comprehensive understanding of user state, document context, and system awareness.

### **Primary Context Systems:**

1. **Context Loop** (`app/services/context_loop.py`) - The Brain
2. **User Context** (`app/core/user_context.py`) - Identity & Permissions
3. **Tenant Briefcase** (`app/core/tenant_briefcase.py`) - User Data Summary
4. **Positronic Brain** (`app/services/positronic_brain.py`) - Module Mesh Network

---

## 🔄 Context Loop - The Central Processing Engine

**Location:** `app/services/context_loop.py`

**Purpose:** The BRAIN of Semptify - everything flows through here

### **Core Loop Process:**
```
INPUT → PROCESS → INTENSITY → OUTPUT → LEARN
```

### **Key Components:**

#### **1. Event Types**
```python
class EventType(str, Enum):
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_ANALYZED = "document_analyzed"
    DEADLINE_APPROACHING = "deadline_approaching"
    DEADLINE_PASSED = "deadline_passed"
    ISSUE_DETECTED = "issue_detected"
    ACTION_TAKEN = "action_taken"
    PHASE_CHANGED = "phase_changed"
    LAW_MATCHED = "law_matched"
    USER_DISMISSED = "user_dismissed"
    PREDICTION_MADE = "prediction_made"
    INTENSITY_SPIKE = "intensity_spike"
```

#### **2. Context Events**
```python
@dataclass
class ContextEvent:
    id: str
    type: EventType
    timestamp: datetime
    user_id: str
    data: dict
    intensity: float = 0.0  # 0-100 scale
    severity: Severity = Severity.INFO
    source: str = ""
    processed: bool = False
```

#### **3. User Context**
```python
@dataclass
class UserContext:
    user_id: str
    phase: str = "active"
    intensity_score: float = 0.0
    
    # Documents and evidence
    documents: list = field(default_factory=list)
    document_types: set = field(default_factory=set)
    
    # Issues and deadlines
    active_issues: list = field(default_factory=list)
    deadlines: list = field(default_factory=list)
    
    # Laws and rights
    applicable_laws: list = field(default_factory=list)
    rights_at_risk: list = field(default_factory=list)
    
    # History and predictions
    events: list = field(default_factory=list)
    actions_taken: list = field(default_factory=list)
    predicted_needs: list = field(default_factory=list)
    risk_factors: list = field(default_factory=list)
```

#### **4. Intensity Engine**
- **0-20:** Low priority, informational
- **21-40:** Medium priority, should address soon
- **41-60:** High priority, needs attention
- **61-80:** Urgent, act now
- **81-100:** Critical, emergency situation

### **Integration Points:**
- **Document Upload** → Triggers analysis and law matching
- **Deadline Detection** → Calculates urgency and triggers alerts
- **Issue Detection** → Updates risk factors and suggested actions
- **User Actions** → Learns patterns and improves predictions

---

## 👤 User Context - Identity & Permissions

**Location:** `app/core/user_context.py`

**Purpose:** Handles role, storage provider, and permissions for each user session

### **Core Components:**

#### **1. User Roles**
```python
class UserRole(str, Enum):
    ADMIN = "admin"            # System admin: full access
    MANAGER = "manager"        # Case manager: multi-client coordination
    TENANT = "tenant"          # Tenant: standard housing case user
    USER = "user"              # Legacy alias for tenant (deprecated)
    ADVOCATE = "advocate"      # Tenant advocate: help multiple users
    LEGAL = "legal"            # Legal role: attorneys, clerks, court staff
    JUDGE = "judge"            # Judge: judicial officer overseeing cases
```

#### **2. Storage Providers**
```python
class StorageProvider(str, Enum):
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"
    LOCAL = "local"  # For admin/system users
```

#### **3. Role-Based Permissions**
- **TENANT:** Vault, timeline, calendar, copilot, complaints, ledger, eviction defense
- **ADVOCATE:** Multi-client access, case management, legal research
- **LEGAL:** Court forms, legal analysis, case management
- **ADMIN:** Full system access, user management, configuration

### **Integration Points:**
- **Authentication** → Sets user role and storage provider
- **UI Rendering** → Determines what features to show
- **API Access** → Controls what endpoints are available
- **Data Access** → Manages permissions for user data

---

## 📋 Tenant Briefcase - User Data Summary

**Location:** `app/core/tenant_briefcase.py`

**Purpose:** Unified, lightweight data object available on every tenant page

### **Design Principles:**
- **Fast load** (~100ms)
- **~10KB memory footprint**
- **Lazy-load details on demand**
- **Template-friendly properties**

### **Core Components:**

#### **1. Data Summaries**
```python
@dataclass
class VaultSummary:
    total_documents: int = 0
    recent_documents: int = 0
    has_documents: bool = False
    by_type: Dict[str, int] = field(default_factory=dict)
    documents: List[Dict[str, Any]] = field(default_factory=list)
    storage_used_mb: float = 0.0

@dataclass
class TimelineSummary:
    total_events: int = 0
    recent_events: int = 0
    has_events: bool = False
    events: List[Dict[str, Any]] = field(default_factory=list)
    next_hearing: Optional[Dict[str, Any]] = None

@dataclass
class DeadlineSummary:
    total_deadlines: int = 0
    upcoming_deadlines: int = 0
    has_deadlines: bool = False
    deadlines: List[Dict[str, Any]] = field(default_factory=list)
    next_deadline: Optional[Dict[str, Any]] = None
```

#### **2. Main Briefcase**
```python
@dataclass
class TenantBriefcase:
    user_id: str
    vault: VaultSummary
    timeline: TimelineSummary
    deadlines: DeadlineSummary
    
    # Quick access properties
    @property
    def needs_attention(self) -> bool
    @property
    def has_urgent_items(self) -> bool
    @property
    def next_deadline(self) -> Optional[Dict[str, Any]]
```

### **Integration Points:**
- **Template Rendering** → Provides quick access to user data
- **Dashboard Display** → Shows summary information
- **Navigation** → Highlights urgent items
- **Performance** → Reduces database queries

---

## 🧬 Positronic Brain - Module Mesh Network

**Location:** `app/services/positronic_brain.py`

**Purpose:** Neural core that connects ALL Semptify modules together

### **Capabilities:**
- **Real-time communication** between modules
- **Automatic state sharing**
- **Cross-module workflow triggers**
- **Full system awareness**

### **Module Types:**
```python
class ModuleType(str, Enum):
    DOCUMENTS = "documents"
    TIMELINE = "timeline"
    CALENDAR = "calendar"
    EVICTION = "eviction"
    COPILOT = "copilot"
    VAULT = "vault"
    AUTH = "auth"
    CONTEXT = "context"
    UI = "ui"
    FORMS = "forms"
    LAW_LIBRARY = "law_library"
    ZOOM_COURT = "zoom_court"
    NOTIFICATIONS = "notifications"
    LOCATION = "location"
    LEGAL_ANALYSIS = "legal_analysis"
    TENANCY_HUB = "tenancy_hub"
    LEGAL_TRAILS = "legal_trails"
    COURT_FORMS = "court_forms"
    ZOOM_COURT_PREP = "zoom_court_prep"
    DOCUMENT_FLOW = "document_flow"
    OCR_SERVICE = "ocr_service"
```

### **Integration Points:**
- **Module Registration** → Connects new modules to the mesh
- **Event Broadcasting** → Shares events across modules
- **State Synchronization** → Keeps modules in sync
- **Workflow Orchestration** → Coordinates complex operations

---

## 🔗 Context Integration with Data Freshness

### **How Context Systems Use Fresh Data:**

#### **1. Context Loop + Freshness**
```python
# Freshness-aware context events
class FreshContextEvent(ContextEvent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Check data freshness before processing
        self.freshness_status = self.check_freshness()
    
    def check_freshness(self) -> Dict[str, FreshnessStatus]:
        """Check freshness of all referenced data."""
        return {
            "legal_basis": data_freshness_manager.check_freshness(f"legal_{self.data.get('law_id')}"),
            "court_rules": data_freshness_manager.check_freshness(f"court_{self.data.get('court')}"),
            "form_requirements": data_freshness_manager.check_freshness(f"form_{self.data.get('form_type')}")
        }
```

#### **2. User Context + Freshness**
```python
# Freshness-aware user context
class FreshUserContext(UserContext):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data_freshness = self.calculate_context_freshness()
    
    def calculate_context_freshness(self) -> float:
        """Calculate overall freshness score for user context."""
        freshness_scores = []
        
        # Check legal content freshness
        for law in self.applicable_laws:
            freshness = data_freshness_manager.check_freshness(f"statute_{law['id']}")
            freshness_scores.append(100 if freshness == FreshnessStatus.FRESH else 0)
        
        # Check deadline rules freshness
        for deadline in self.deadlines:
            freshness = data_freshness_manager.check_freshness(f"deadline_rules_{deadline['jurisdiction']}")
            freshness_scores.append(100 if freshness == FreshnessStatus.FRESH else 0)
        
        return sum(freshness_scores) / len(freshness_scores) if freshness_scores else 0
```

#### **3. Tenant Briefcase + Freshness**
```python
# Freshness-aware briefcase
class FreshTenantBriefcase(TenantBriefcase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.freshness_indicators = self.get_freshness_indicators()
    
    def get_freshness_indicators(self) -> Dict[str, str]:
        """Get freshness indicators for briefcase data."""
        return {
            "legal_content": "fresh" if data_freshness_manager.check_freshness("legal_content") == FreshnessStatus.FRESH else "stale",
            "court_forms": "fresh" if data_freshness_manager.check_freshness("court_forms") == FreshnessStatus.FRESH else "stale",
            "deadline_rules": "fresh" if data_freshness_manager.check_freshness("deadline_rules") == FreshnessStatus.FRESH else "stale"
        }
```

---

## 🚀 Implementation Roadmap

### **Phase 1: Core Integration (Week 1)**
1. **Fix data freshness manager** circular dependency
2. **Integrate Context Loop** with freshness validation
3. **Add freshness indicators** to user context

### **Phase 2: Briefcase Enhancement (Week 2)**
1. **Add freshness scores** to tenant briefcase
2. **Implement freshness warnings** in UI
3. **Create freshness dashboard** for admins

### **Phase 3: Brain Integration (Week 3)**
1. **Connect Positronic Brain** to freshness events
2. **Implement cross-module** freshness notifications
3. **Add freshness-based** workflow triggers

### **Phase 4: Advanced Features (Week 4)**
1. **Predictive freshness** based on usage patterns
2. **Automatic refresh** scheduling
3. **Freshness analytics** and reporting

---

## 📊 Success Metrics

### **Context Freshness Metrics:**
- Context accuracy: > 95% based on fresh data
- Freshness coverage: 100% of critical context elements
- Update latency: < 5 minutes for critical data
- User confidence: > 90% in context accuracy

### **System Performance Metrics:**
- Briefcase load time: < 100ms
- Context processing time: < 500ms
- Brain mesh latency: < 50ms
- Memory usage: < 10MB per user context

---

## 🎯 Next Steps

1. **Fix unhashable dict error** - Immediate priority
2. **Integrate Context Loop** with data freshness validation
3. **Add freshness indicators** to tenant briefcase
4. **Connect Positronic Brain** to freshness events
5. **Implement freshness-based** UI updates

---

## 📈 Expected Outcomes

- **Real-time context accuracy** based on fresh data
- **Proactive alerts** when context data becomes stale
- **Cross-module awareness** of data freshness status
- **Improved user confidence** in system recommendations
- **Automated context updates** when legal requirements change

This comprehensive context system ensures that Semptify always operates with the most current, accurate, and legally defensible information across all user interactions and system operations.
