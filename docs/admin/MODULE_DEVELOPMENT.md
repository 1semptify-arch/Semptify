# Semptify Module Development Guide

## 🧠 The Positronic Mesh

Semptify uses a **Positronic Mesh** (Workflow Orchestration Engine) to coordinate all modules. This allows:

- **Bidirectional Communication** - Modules can send and receive data from each other
- **Workflow Orchestration** - Multi-step processes spanning multiple modules
- **Event-Driven Architecture** - Modules react to system events
- **Centralized State** - Shared context across all modules

---

## 📦 Quick Start: Creating a New Module

### Step 1: Create Your Module File

Create a new file in `app/modules/your_module_name.py`:

```python
from app.sdk import (
    ModuleSDK,
    ModuleDefinition,
    ModuleCategory,
    DocumentType,
    PackType,
)

# Define your module
module_definition = ModuleDefinition(
    name="your_module_name",
    display_name="Your Module Name",
    description="What your module does",
    version="1.0.0",
    category=ModuleCategory.UTILITY,
)

# Create SDK instance
sdk = ModuleSDK(module_definition)

# Register actions
@sdk.action("your_action", produces=["result"])
async def your_action(user_id, params, context):
    return {"result": "done"}

# Initialize function
def initialize():
    sdk.initialize()
```

### Step 2: Register in main.py

Add to the startup sequence in `app/main.py`:

```python
from app.modules.your_module_name import initialize as init_your_module
init_your_module()
```

That's it! Your module is now part of the Positronic Mesh.

---

## 📋 Module Definition Options

```python
ModuleDefinition(
    # Required
    name="unique_snake_case_name",      # Unique identifier
    display_name="Human Readable Name",  # UI display name
    description="What this module does", # Description
    
    # Optional
    version="1.0.0",                     # Semantic version
    category=ModuleCategory.UTILITY,     # Organization category
    
    # Document handling
    handles_documents=[                   # Document types this can process
        DocumentType.LEASE,
        DocumentType.EVICTION_NOTICE,
    ],
    
    # Inter-module communication
    accepts_packs=[                       # Info packs this can receive
        PackType.EVICTION_DATA,
    ],
    produces_packs=[                      # Info packs this creates
        PackType.ANALYSIS_RESULT,
    ],
    
    # Dependencies
    depends_on=["documents", "calendar"], # Required modules
    
    # Capabilities
    has_ui=False,                         # Has frontend component
    has_background_tasks=False,           # Runs background jobs
    requires_auth=True,                   # Needs user authentication
)
```

---

## ⚡ Registering Actions

Actions are functions your module exposes to the mesh:

```python
@sdk.action(
    "action_name",                        # Unique action identifier
    description="What this action does",  # Human-readable description
    required_params=["param1", "param2"], # Required parameters
    optional_params=["param3"],           # Optional parameters
    produces=["output_key"],              # Context keys this produces
    requires_context=["needed_key"],      # Context keys this needs
    timeout_seconds=30,                   # Max execution time
)
async def action_name(
    user_id: str,                         # User making the request
    params: Dict[str, Any],               # Action parameters
    context: Dict[str, Any],              # Workflow context
) -> Dict[str, Any]:                      # Must return a dict
    # Your logic here
    return {"output_key": "result"}
```

### Action Handler Signature

All action handlers receive three arguments:

| Argument | Type | Description |
|----------|------|-------------|
| `user_id` | `str` | The user's unique identifier |
| `params` | `Dict[str, Any]` | Parameters passed to this action |
| `context` | `Dict[str, Any]` | Shared workflow context (accumulated from previous steps) |

### Return Value

Actions must return a `Dict[str, Any]`. The keys should match what you declared in `produces`.

---

## 📤 Sending Data to Other Modules

### Create Info Packs

```python
# Send data to a specific module
sdk.create_pack(
    pack_type=PackType.EVICTION_DATA,
    user_id=user_id,
    data={"key": "value"},
    target_module="eviction_defense",  # None = broadcast to all
    priority=5,  # 1-10, higher = more urgent
)
```

### Request Data from Modules

```python
# Request specific data from another module
data = await sdk.request_data(
    from_module="documents",
    data_keys=["recent_uploads", "document_count"],
    user_id=user_id,
)
```

### Invoke Actions Directly

```python
# Call an action on another module
result = await sdk.invoke_action(
    module="calendar",
    action="calculate_deadlines",
    user_id=user_id,
    params={"start_date": "2024-01-01"},
)
```

---

## 🔄 Triggering Workflows

Modules can trigger multi-step workflows:

```python
# Trigger a predefined workflow
workflow = await sdk.trigger_workflow(
    workflow_type="eviction_defense",
    user_id=user_id,
    initial_context={"document": uploaded_doc},
)
```

### Available Workflow Types

| Type | Description | Modules Involved |
|------|-------------|------------------|
| `eviction_defense` | Full eviction defense process | documents → calendar → eviction → forms → copilot |
| `lease_analysis` | Analyze a lease document | documents → law_library → timeline → calendar |
| `court_prep` | Prepare for court hearing | eviction → documents → timeline → forms → zoom_court |
| `full_sync` | Sync all module states | all modules → context → ui |
| `deadline_alert` | Handle urgent deadline | calendar → copilot → ui |

---

## 🎯 Event Handling

React to system events:

```python
@sdk.on_event("workflow_started")
async def on_workflow_started(event_type: str, data: Dict[str, Any]):
    workflow_id = data.get("workflow_id")
    workflow_type = data.get("type")
    # React to workflow starting

@sdk.on_event("workflow_completed")
async def on_workflow_completed(event_type: str, data: Dict[str, Any]):
    # React to workflow completing

@sdk.on_event("document_uploaded")
async def on_document_uploaded(event_type: str, data: Dict[str, Any]):
    # React to new document
```

### Available Events

| Event | Data | Description |
|-------|------|-------------|
| `workflow_started` | `workflow_id`, `type`, `user_id` | A workflow began |
| `workflow_completed` | `workflow_id`, `type`, `context_keys` | A workflow finished |
| `workflow_failed` | `workflow_id`, `step_id`, `error` | A workflow errored |
| `workflow_waiting_input` | `workflow_id`, `step_id`, `prompt` | Workflow needs user input |
| `workflow_step_completed` | `workflow_id`, `step_id`, `module`, `action` | A step finished |
| `module_invoked` | `module`, `action`, `user_id` | Direct action invocation |

---

## 📁 Module Categories

```python
class ModuleCategory(str, Enum):
    DOCUMENT = "document"          # Document processing
    LEGAL = "legal"                # Legal analysis/forms
    CALENDAR = "calendar"          # Scheduling/deadlines
    COMMUNICATION = "communication"  # User communication
    ANALYSIS = "analysis"          # Data analysis
    STORAGE = "storage"            # File/data storage
    UI = "ui"                      # User interface
    UTILITY = "utility"            # General utilities
    AI = "ai"                      # AI/ML features
    INTEGRATION = "integration"    # External integrations
```

---

## 📄 Document Types

```python
class DocumentType(str, Enum):
    EVICTION_NOTICE = "eviction_notice"
    LEASE = "lease"
    COURT_FILING = "court_filing"
    PAYMENT_RECORD = "payment_record"
    COMMUNICATION = "communication"
    PHOTO = "photo"
    LEGAL_FORM = "legal_form"
    ID_DOCUMENT = "id_document"
    UNKNOWN = "unknown"
```

---

## 📦 Info Pack Types

```python
class PackType(str, Enum):
    EVICTION_DATA = "eviction_data"
    LEASE_DATA = "lease_data"
    DEADLINE_DATA = "deadline_data"
    CASE_DATA = "case_data"
    USER_DATA = "user_data"
    FORM_DATA = "form_data"
    ANALYSIS_RESULT = "analysis_result"
    CUSTOM = "custom"
```

---

## 🔧 Adding API Endpoints

If your module needs REST API endpoints:

```python
from fastapi import APIRouter, Cookie
from typing import Optional

router = APIRouter()

@router.get("/your-endpoint")
async def your_endpoint(
    semptify_uid: Optional[str] = Cookie(default=None),
):
    user_id = semptify_uid or "anonymous"
    # Your logic
    return {"result": "data"}
```

Then in `main.py`:
```python
from app.modules.your_module import router as your_router
app.include_router(your_router, prefix="/api/your-module", tags=["Your Module"])
```

---

## ✅ Complete Example

See `app/modules/example_payment_tracking.py` for a complete working example.

---

## 🧪 Testing Your Module

```python
# test_your_module.py
import pytest
from app.modules.your_module import sdk, your_action

@pytest.mark.asyncio
async def test_your_action():
    result = await your_action(
        user_id="test_user",
        params={"input": "test"},
        context={},
    )
    assert "result" in result
    assert result["result"] == "expected_value"
```

---

## 📊 Module Status

Check your module's status:

```python
status = sdk.get_status()
# Returns:
# {
#     "name": "your_module",
#     "display_name": "Your Module",
#     "version": "1.0.0",
#     "initialized": True,
#     "actions": ["action1", "action2"],
#     "event_handlers": ["workflow_started"],
#     "connected_to_mesh": True,
#     "connected_to_hub": True,
# }
```

---

## 🚀 Best Practices

1. **Always return a dict** from action handlers
2. **Declare what you produce** in the `produces` parameter
3. **Handle errors gracefully** - wrap risky code in try/except
4. **Log meaningful messages** using the logger
5. **Keep actions focused** - one action, one purpose
6. **Use context** for workflow data, params for direct calls
7. **Test independently** before integrating

---

## 🔗 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     POSITRONIC MESH                          │
│                 (Workflow Orchestration)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Module A │  │ Module B │  │ Module C │  │ Module D │   │
│  │  (SDK)   │  │  (SDK)   │  │  (SDK)   │  │  (SDK)   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│       └─────────────┴──────┬──────┴─────────────┘          │
│                            │                                │
│                    ┌───────▼───────┐                       │
│                    │  MODULE HUB   │                       │
│                    │ (Info Packs)  │                       │
│                    └───────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## ❓ Need Help?

- Check `app/modules/example_payment_tracking.py` for a complete example
- Review `app/sdk/module_sdk.py` for full API documentation
- Look at existing modules in `app/services/` for patterns
