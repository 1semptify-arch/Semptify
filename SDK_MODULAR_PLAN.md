# SDK Modular Integration Plan

## Problem Statement
The current SDK is designed as a unified client (`SemptifyClient`) that imports all modules. For individual module extraction and use in other repositories, we need a modular design where each module can stand alone.

## Current Structure Issues
```python
# Current: Everything coupled through SemptifyClient
from sdk import SemptifyClient
client = SemptifyClient()
client.documents.upload()  # Requires all modules
```

## Target Modular Structure
```python
# Target: Individual modules can be used alone
from sdk.documents import DocumentClient
from sdk.auth import AuthClient

# Standalone document module
docs = DocumentClient(base_url="http://api.example.com", token="jwt_token")
docs.upload("lease.pdf")

# Standalone auth module
auth = AuthClient(base_url="http://api.example.com")
auth.login("google", code)
```

## Implementation Plan

### 1. Module Self-Containment (Priority: HIGH)

**Each module must:**
- Have its own `__init__.py` that exports only its classes
- Import `BaseClient` from `sdk.base` (shared dependency)
- Define its own data models and exceptions
- Work independently without requiring other modules

**Files to modify:**
```
sdk/
├── auth/
│   ├── __init__.py      # Export AuthClient, UserInfo
│   ├── client.py        # AuthClient implementation
│   └── models.py        # UserInfo, OAuthState
├── documents/
│   ├── __init__.py      # Export DocumentClient, Document
│   ├── client.py        # DocumentClient implementation
│   └── models.py        # Document, IntakeDocument
├── timeline/
│   ├── __init__.py
│   ├── client.py
│   └── models.py
├── copilot/
│   ├── __init__.py
│   ├── client.py
│   └── models.py
├── complaints/
│   ├── __init__.py
│   ├── client.py
│   └── models.py
├── briefcase/
│   ├── __init__.py
│   ├── client.py
│   └── models.py
└── vault/
    ├── __init__.py
    ├── client.py
    └── models.py
```

### 2. Authentication Flexibility (Priority: HIGH)

**Problem:** Current modules assume cookie-based auth through shared client.

**Solution:** Each module accepts multiple auth methods:
```python
# Option 1: Direct token
client = DocumentClient(
    base_url="http://api.example.com",
    auth_token="jwt_token_here"
)

# Option 2: API Key
client = DocumentClient(
    base_url="http://api.example.com",
    api_key="api_key_here"
)

# Option 3: OAuth flow (auth module integration)
auth = AuthClient(base_url="http://api.example.com")
user = auth.login("google", code)
docs = DocumentClient(base_url="http://api.example.com", auth_token=user.token)
```

### 3. Minimal Dependencies (Priority: MEDIUM)

**Shared dependencies only:**
- `sdk.base` - BaseClient with HTTP handling
- `sdk.exceptions` - Common exception hierarchy
- `pydantic` - Data models (if used)

**No cross-module imports:**
- `documents` must not import `auth`
- `timeline` must not import `documents`
- Each module stands alone

### 4. Unified Client as Facade (Priority: LOW)

**Keep `SemptifyClient` as convenience wrapper:**
```python
# sdk/client.py (facade pattern)
class SemptifyClient:
    def __init__(self, base_url, ...):
        # Initialize all modules for convenience
        self.auth = AuthClient(base_url, ...)
        self.documents = DocumentClient(base_url, auth=self.auth)
        # etc.
```

### 5. Package Structure for Distribution

**Option A: Single Package with Submodules**
```python
# pip install semptify-sdk
from semptify_sdk import DocumentClient
from semptify_sdk.auth import AuthClient
```

**Option B: Individual Packages**
```python
# pip install semptify-documents
# pip install semptify-auth
from semptify_documents import DocumentClient
from semptify_auth import AuthClient
```

**Recommendation:** Start with Option A, easier to evolve to Option B later.

## Implementation Steps

### Phase 1: Module Extraction (Week 1)
1. Create module directories
2. Move existing code to module files
3. Update imports to be self-contained
4. Test each module independently

### Phase 2: Auth Flexibility (Week 1)
1. Modify BaseClient to accept auth tokens directly
2. Update each module to support token auth
3. Add API key support
4. Test with different auth methods

### Phase 3: Documentation & Examples (Week 2)
1. Write individual module READMEs
2. Create standalone usage examples
3. Update main SDK documentation
4. Add integration tests

### Phase 4: Packaging (Week 2)
1. Update setup.py/pyproject.toml
2. Test package installation
3. Publish to PyPI (if desired)
4. Create migration guide

## Benefits

1. **Microservice Architecture:** Teams can use only needed modules
2. **Reduced Bundle Size:** Smaller dependencies for individual use cases
3. **Independent Versioning:** Modules can evolve separately
4. **Testing:** Each module can be unit tested in isolation
5. **Reusability:** Modules can be used in non-Semptify projects

## Migration Path

**For existing users:**
```python
# Before (still works)
from sdk import SemptifyClient
client = SemptifyClient()
client.documents.upload()

# After (new options)
from sdk import SemptifyClient  # Still available
from sdk.documents import DocumentClient  # New standalone
docs = DocumentClient()
docs.upload()
```

**For new projects:**
```python
# Use only what's needed
from sdk.documents import DocumentClient
docs = DocumentClient(base_url="https://api.semptify.com", token="...")
```

## Success Metrics

1. Each module can be imported and used independently
2. No circular dependencies between modules
3. Standalone module tests pass
4. Documentation examples work without full SDK
5. Package size reduced for individual module use
