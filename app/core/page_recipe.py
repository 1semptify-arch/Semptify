"""
Page Recipe System
==================
Template for defining page purpose, required components, and assembly steps.

Work backwards: Start with the goal, define what functions/routes are needed
to fulfill that purpose, then implement.

Usage:
    from app.core.page_recipe import PageRecipe, PageComponent
    
    recipe = PageRecipe(
        page_id="document_intake",
        purpose="Allow tenants to upload and organize case documents",
        user_intent="I need to get my documents into the system safely",
        success_criteria=["Files uploaded to vault", "Documents categorized", "User sees confirmation"],
        trigger_routes=["/documents/upload", "/vault/add"],
        required_functions=["file_validation", "virus_scan", "vault_store", "category_detect"],
        data_inputs=["files", "document_type", "case_id"],
        data_outputs=["vault_document_id", "upload_manifest"],
        api_endpoints=["POST /api/vault/upload", "GET /api/vault/status/{id}"],
        ui_components=["drop_zone", "progress_bar", "category_selector", "success_modal"],
        error_states=["file_too_large", "unsupported_format", "upload_failed", "scan_failed"],
        completion_redirect="/vault",
        telemetry_events=["upload_started", "upload_complete", "category_selected"]
    )
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class PageIntent(str, Enum):
    """Classification of page purpose/intent."""
    COLLECT = "collect"           # Gather information/documents from user
    PRESENT = "present"           # Show information to user
    PROCESS = "process"           # Transform data (upload, analyze, etc.)
    NAVIGATE = "navigate"         # Route user to next step
    COMMUNICATE = "communicate"   # Enable messaging/collaboration
    CONFIGURE = "configure"       # Settings and preferences
    VERIFY = "verify"           # Confirm identity, facts, or actions
    OUTPUT = "output"           # Generate deliverables (forms, packets)


class ComponentType(str, Enum):
    """Types of page components."""
    API_ENDPOINT = "api_endpoint"
    UI_COMPONENT = "ui_component"
    DATA_MODEL = "data_model"
    ROUTE_GUARD = "route_guard"
    SERVICE_FUNCTION = "service_function"
    TEMPLATE_PARTIAL = "template_partial"
    STATIC_ASSET = "static_asset"
    TELEMETRY_HOOK = "telemetry_hook"


@dataclass
class PageComponent:
    """
    Single component required for a page.
    
    Examples:
        - API endpoint that serves data
        - UI component that renders something
        - Service function that processes data
        - Route guard that checks permissions
    """
    component_type: ComponentType
    name: str                      # e.g., "upload_endpoint", "drop_zone"
    description: str               # What it does
    required: bool = True          # Can page work without this?
    implemented: bool = False      # Status
    file_path: Optional[str] = None  # Where it lives
    depends_on: List[str] = field(default_factory=list)  # Other components this needs


@dataclass
class PageStep:
    """
    A step in the user journey to complete the page's task.
    
    Work backwards from completion:
    1. Final state (success)
    2. What must happen just before?
    3. What must happen before that?
    ... until start state
    """
    order: int                     # Step number (reverse: highest = final)
    description: str               # What user does or system does
    actor: str                     # "user" or "system"
    triggers: List[str] = field(default_factory=list)      # What triggers this step
    requires: List[str] = field(default_factory=list)      # Components needed
    outputs: List[str] = field(default_factory=list)       # Data produced
    error_states: List[str] = field(default_factory=list) # What can go wrong
    next_step: Optional[int] = None  # Next in sequence


@dataclass
class PageRecipe:
    """
    Complete recipe for building a page.
    
    This is the master template that answers:
    - WHY does this page exist? (purpose, user_intent)
    - WHAT must it accomplish? (success_criteria)
    - HOW does it get there? (steps, components)
    - WHAT can go wrong? (error_states)
    """
    
    # Identity
    page_id: str                   # Unique identifier
    page_title: str                # Human name
    intent: PageIntent             # Classification
    
    # Purpose
    purpose: str                   # One sentence: what this page achieves
    user_intent: str               # What the user wants when they arrive
    success_criteria: List[str] = field(default_factory=list)  # How we know it worked
    
    # Triggers - How users get here
    trigger_routes: List[str] = field(default_factory=list)      # URLs that lead here
    entry_conditions: List[str] = field(default_factory=list)      # What must be true
    
    # Components - What must exist
    components: List[PageComponent] = field(default_factory=list)
    
    # Steps - The journey
    steps: List[PageStep] = field(default_factory=list)
    
    # Data flow
    data_inputs: List[str] = field(default_factory=list)   # What comes in
    data_outputs: List[str] = field(default_factory=list) # What goes out
    
    # Completion
    completion_redirect: Optional[str] = None  # Where to go when done
    completion_actions: List[str] = field(default_factory=list)  # Side effects
    
    # Failure handling
    error_states: List[str] = field(default_factory=list)      # Known error cases
    recovery_paths: Dict[str, str] = field(default_factory=dict)  # error -> recovery route
    
    # Observability
    telemetry_events: List[str] = field(default_factory=list)
    
    def validate(self) -> Dict[str, Any]:
        """Check recipe completeness and return status."""
        missing = []
        if not self.purpose:
            missing.append("purpose")
        if not self.user_intent:
            missing.append("user_intent")
        if not self.success_criteria:
            missing.append("success_criteria")
        if not self.steps:
            missing.append("steps")
        
        unimplemented = [c for c in self.components if c.required and not c.implemented]
        
        return {
            "complete": len(missing) == 0 and len(unimplemented) == 0,
            "missing_fields": missing,
            "unimplemented_components": [c.name for c in unimplemented],
            "total_components": len(self.components),
            "implemented_count": len([c for c in self.components if c.implemented])
        }
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph of components."""
        graph = {}
        for component in self.components:
            graph[component.name] = component.depends_on
        return graph
    
    def to_dict(self) -> dict:
        """Export recipe as dictionary."""
        return {
            "page_id": self.page_id,
            "page_title": self.page_title,
            "intent": self.intent.value,
            "purpose": self.purpose,
            "user_intent": self.user_intent,
            "success_criteria": self.success_criteria,
            "validation": self.validate(),
            "components": [
                {
                    "type": c.component_type.value,
                    "name": c.name,
                    "description": c.description,
                    "required": c.required,
                    "implemented": c.implemented,
                    "file_path": c.file_path,
                    "depends_on": c.depends_on
                }
                for c in self.components
            ],
            "steps": [
                {
                    "order": s.order,
                    "description": s.description,
                    "actor": s.actor,
                    "triggers": s.triggers,
                    "requires": s.requires,
                    "outputs": s.outputs
                }
                for s in sorted(self.steps, key=lambda x: x.order)
            ],
            "data_flow": {
                "inputs": self.data_inputs,
                "outputs": self.data_outputs
            },
            "error_handling": {
                "error_states": self.error_states,
                "recovery_paths": self.recovery_paths
            }
        }


# =============================================================================
# Recipe Registry - Store all page recipes
# =============================================================================

class RecipeRegistry:
    """Central registry of all page recipes."""
    
    _recipes: Dict[str, PageRecipe] = {}
    
    @classmethod
    def register(cls, recipe: PageRecipe) -> None:
        """Add a recipe to the registry."""
        cls._recipes[recipe.page_id] = recipe
    
    @classmethod
    def get(cls, page_id: str) -> Optional[PageRecipe]:
        """Retrieve a recipe by page_id."""
        return cls._recipes.get(page_id)
    
    @classmethod
    def all_recipes(cls) -> Dict[str, PageRecipe]:
        """Get all registered recipes."""
        return cls._recipes.copy()
    
    @classmethod
    def by_intent(cls, intent: PageIntent) -> List[PageRecipe]:
        """Get all recipes of a specific intent type."""
        return [r for r in cls._recipes.values() if r.intent == intent]
    
    @classmethod
    def incomplete(cls) -> List[PageRecipe]:
        """Get all recipes that aren't fully implemented."""
        return [r for r in cls._recipes.values() if not r.validate()["complete"]]


# =============================================================================
# Example Recipe - Document Intake Page
# =============================================================================

def create_document_intake_recipe() -> PageRecipe:
    """
    Example: Document Intake Page Recipe
    
    Shows how to define a page working backwards from the goal.
    """
    return PageRecipe(
        page_id="document_intake",
        page_title="Document Upload",
        intent=PageIntent.COLLECT,
        
        # Purpose
        purpose="Allow tenants to upload case documents to their vault with automatic categorization",
        user_intent="I need to get my eviction notice and lease into the system so my advocate can see them",
        success_criteria=[
            "Files uploaded to user's vault",
            "Documents categorized by type (lease, notice, correspondence)",
            "User sees upload confirmation",
            "Documents appear in timeline",
            "Processing status visible"
        ],
        
        # Triggers
        trigger_routes=["/documents/upload", "/vault/add", "/intake/documents"],
        entry_conditions=["User authenticated", "Storage connected", "Vault initialized"],
        
        # Components (work backwards from success criteria)
        components=[
            # UI Components
            PageComponent(
                component_type=ComponentType.UI_COMPONENT,
                name="drop_zone",
                description="Drag-and-drop file upload area with visual feedback",
                file_path="app/templates/components/upload_zone.html",
                depends_on=[]
            ),
            PageComponent(
                component_type=ComponentType.UI_COMPONENT,
                name="progress_bar",
                description="Shows upload progress and processing status",
                file_path="app/templates/components/progress.html",
                depends_on=["upload_endpoint"]
            ),
            PageComponent(
                component_type=ComponentType.UI_COMPONENT,
                name="category_selector",
                description="Dropdown to manually select document category",
                file_path="app/templates/components/category_select.html",
                depends_on=["auto_categorize_service"]
            ),
            PageComponent(
                component_type=ComponentType.UI_COMPONENT,
                name="success_modal",
                description="Confirmation with next steps",
                file_path="app/templates/components/success_modal.html",
                depends_on=["upload_endpoint"]
            ),
            
            # API Endpoints
            PageComponent(
                component_type=ComponentType.API_ENDPOINT,
                name="upload_endpoint",
                description="POST endpoint that receives files and stores to vault",
                file_path="app/routers/vault.py",
                depends_on=["vault_store_service", "scan_service"]
            ),
            PageComponent(
                component_type=ComponentType.API_ENDPOINT,
                name="status_endpoint",
                description="GET endpoint for checking processing status",
                file_path="app/routers/vault.py",
                depends_on=["upload_endpoint"]
            ),
            
            # Services
            PageComponent(
                component_type=ComponentType.SERVICE_FUNCTION,
                name="vault_store_service",
                description="Stores file to cloud storage with metadata",
                file_path="app/services/vault_service.py",
                depends_on=[]
            ),
            PageComponent(
                component_type=ComponentType.SERVICE_FUNCTION,
                name="scan_service",
                description="Virus scan and security validation",
                file_path="app/services/security_scanner.py",
                depends_on=[]
            ),
            PageComponent(
                component_type=ComponentType.SERVICE_FUNCTION,
                name="auto_categorize_service",
                description="AI classification of document type",
                file_path="app/services/document_classifier.py",
                depends_on=["vault_store_service"]
            ),
            PageComponent(
                component_type=ComponentType.SERVICE_FUNCTION,
                name="timeline_integration",
                description="Extracts dates and adds to case timeline",
                file_path="app/services/timeline_extractor.py",
                depends_on=["auto_categorize_service"]
            ),
            
            # Guards
            PageComponent(
                component_type=ComponentType.ROUTE_GUARD,
                name="auth_guard",
                description="Ensures user is authenticated",
                file_path="app/core/security.py",
                depends_on=[]
            ),
            PageComponent(
                component_type=ComponentType.ROUTE_GUARD,
                name="storage_guard",
                description="Ensures user has storage connected",
                file_path="app/routers/role_ui.py",
                depends_on=["auth_guard"]
            ),
            
            # Telemetry
            PageComponent(
                component_type=ComponentType.TELEMETRY_HOOK,
                name="upload_telemetry",
                description="Emits events for analytics",
                file_path="app/core/telemetry.py",
                depends_on=[]
            )
        ],
        
        # Steps (work backwards from completion)
        steps=[
            # Final step
            PageStep(
                order=6,
                description="User sees success confirmation and next steps",
                actor="system",
                triggers=["processing_complete"],
                requires=["success_modal", "timeline_integration"],
                outputs=["confirmation_displayed"]
            ),
            # Before that
            PageStep(
                order=5,
                description="Timeline updated with document dates",
                actor="system",
                triggers=["categorization_complete"],
                requires=["timeline_integration"],
                outputs=["timeline_events"]
            ),
            PageStep(
                order=4,
                description="Document categorized (auto or manual)",
                actor="system",
                triggers=["scan_passed"],
                requires=["auto_categorize_service", "category_selector"],
                outputs=["document_category"],
                error_states=["categorization_failed"]
            ),
            PageStep(
                order=3,
                description="Security scan completes",
                actor="system",
                triggers=["upload_complete"],
                requires=["scan_service"],
                outputs=["scan_result"],
                error_states=["scan_failed", "virus_detected"]
            ),
            PageStep(
                order=2,
                description="File uploaded to vault",
                actor="system",
                triggers=["user_submits"],
                requires=["upload_endpoint", "vault_store_service"],
                outputs=["vault_document_id"],
                error_states=["upload_failed", "storage_full"]
            ),
            # First step
            PageStep(
                order=1,
                description="User selects or drops files",
                actor="user",
                triggers=["page_load", "drag_drop"],
                requires=["drop_zone", "auth_guard", "storage_guard"],
                outputs=["file_selection"]
            )
        ],
        
        # Data
        data_inputs=["files", "document_type_hint", "case_id", "user_id"],
        data_outputs=["vault_document_id", "upload_manifest", "category", "timeline_events"],
        
        # Completion
        completion_redirect="/vault",
        completion_actions=["timeline_updated", "notification_sent"],
        
        # Errors
        error_states=[
            "file_too_large",
            "unsupported_format", 
            "upload_failed",
            "scan_failed",
            "virus_detected",
            "storage_full",
            "categorization_failed",
            "unauthorized"
        ],
        recovery_paths={
            "file_too_large": "/help/file-size",
            "storage_full": "/storage/upgrade",
            "upload_failed": "/documents/upload?retry=1",
            "unauthorized": "/storage/providers"
        },
        
        # Telemetry
        telemetry_events=[
            "upload_started",
            "upload_complete",
            "scan_complete",
            "categorization_complete",
            "timeline_updated"
        ]
    )


# Register example
RecipeRegistry.register(create_document_intake_recipe())
