"""Document Center module — Feature Module.

The 3-pane document viewer and overlay management UI.
Lifecycle: dev_only — admin-only while under active construction.

Architecture: Feature Module (reads from Pipeline Modules — documents, vault,
intake, unified_overlay_manager — but never calls other Feature Modules).
"""

from app.modules.document_center.router import router

__all__ = ["router"]
