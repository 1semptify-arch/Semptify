"""Filedored GUI Requirements - Following the GUI Contract specification."""
from app.core.gui_contract import (
    GUIRequirements,
    InputType,
    OutputType,
    ActionType,
    IndicatorType,
    PopOutType,
    create_input_field,
    create_output_display,
    create_action_button,
    create_indicator,
    create_popout,
)

# =============================================================================
# Filedored GUI Requirements
# =============================================================================

FILEDORED_GUI_REQUIREMENTS = GUIRequirements(
    module_name="filedored",
    version="1.0",
    
    # Page Layout
    layout="wide",
    sections=["header", "controls", "folder-grid", "document-list", "status-bar"],
    
    # Input Fields
    inputs=[
        create_input_field(
            name="search",
            label="Search Documents",
            type=InputType.SEARCH,
            placeholder="Search by filename or content...",
            help_text="Search across all filedored documents",
        ),
        create_input_field(
            name="ai_enabled",
            label="Enable AI Classification",
            type=InputType.TOGGLE,
            default=False,
            help_text="Use AI to classify documents into categories",
        ),
        create_input_field(
            name="process_mode",
            label="Processing Mode",
            type=InputType.SELECT,
            default="all",
            options=[
                {"value": "all", "label": "All Documents"},
                {"value": "unprocessed", "label": "Unprocessed Only"},
                {"value": "selected", "label": "Selected Documents"},
            ],
        ),
    ],
    
    # Output Displays
    outputs=[
        create_output_display(
            name="folder_grid",
            label="Virtual Folders",
            type=OutputType.GRID,
            data_source="/api/filedored/folders",
            refresh_interval=30,
            columns=[
                {"key": "name", "label": "Folder", "sortable": True},
                {"key": "count", "label": "Documents", "sortable": True},
                {"key": "icon", "label": "", "type": "icon"},
            ],
        ),
        create_output_display(
            name="document_list",
            label="Documents",
            type=OutputType.LIST,
            data_source="/api/filedored/browse/{folder}",
            columns=[
                {"key": "filename", "label": "Filename", "sortable": True},
                {"key": "ai_label", "label": "AI Classification", "type": "badge"},
                {"key": "filedored_category", "label": "Category"},
                {"key": "extension", "label": "Type"},
                {"key": "created_at", "label": "Date", "type": "datetime"},
            ],
            actions=[
                {"name": "view", "label": "View", "action": "view_document"},
                {"name": "download", "label": "Download", "action": "download_document"},
                {"name": "move", "label": "Move", "action": "move_document"},
            ],
        ),
        create_output_display(
            name="duplicates",
            label="Duplicate Documents",
            type=OutputType.CARD,
            data_source="/api/filedored/duplicates",
            columns=[
                {"key": "original_filename", "label": "Original"},
                {"key": "duplicate_count", "label": "Duplicates", "type": "badge"},
                {"key": "sha256_hash", "label": "Hash", "type": "monospace"},
            ],
        ),
    ],
    
    # Action Buttons
    actions=[
        create_action_button(
            name="process_all",
            label="Process All Documents",
            type=ActionType.PROCESS,
            endpoint="/api/filedored/process",
            confirm="This will process all documents in your vault. Continue?",
            loading_state="Processing...",
            style="primary",
        ),
        create_action_button(
            name="process_with_ai",
            label="Process with AI",
            type=ActionType.PROCESS,
            endpoint="/api/filedored/process",
            confirm="AI processing may take longer. Continue?",
            loading_state="AI Processing...",
            style="secondary",
        ),
        create_action_button(
            name="check_folders",
            label="Check Folders",
            type=ActionType.REFRESH,
            endpoint="/api/filedored/folders/status",
            loading_state="Checking...",
        ),
        create_action_button(
            name="refresh",
            label="Refresh",
            type=ActionType.REFRESH,
            endpoint="/api/filedored/refresh",
            style="outline",
        ),
        create_action_button(
            name="export_list",
            label="Export List",
            type=ActionType.EXPORT,
            endpoint="/api/filedored/export",
            style="outline",
        ),
    ],
    
    # Indicators
    indicators=[
        create_indicator(
            name="processing_status",
            type=IndicatorType.PROGRESS,
            data_source="/api/filedored/status",
            position="top-right",
        ),
        create_indicator(
            name="folder_status",
            type=IndicatorType.STATUS,
            data_source="/api/filedored/folders/status",
            position="top-left",
        ),
        create_indicator(
            name="duplicate_count",
            type=IndicatorType.BADGE,
            data_source="/api/filedored/duplicates/count",
            position="header",
        ),
    ],
    
    # Pop-outs/Modals
    popouts=[
        create_popout(
            name="help",
            type=PopOutType.TOOLTIP,
            trigger="hover",
            content="Filedored organizes your documents into virtual folders without moving the original files.",
        ),
        create_popout(
            name="processing_details",
            type=PopOutType.MODAL,
            trigger="click",
            title="Processing Details",
            content="/api/filedored/processing/details",
            size="medium",
        ),
        create_popout(
            name="duplicate_details",
            type=PopOutType.DRAWER,
            trigger="click",
            title="Duplicate Documents",
            content="/api/filedored/duplicates/details",
            size="large",
        ),
        create_popout(
            name="ai_settings",
            type=PopOutType.MODAL,
            trigger="click",
            title="AI Classification Settings",
            content="/api/filedored/ai/settings",
            size="small",
        ),
    ],
    
    # Special Requirements
    special_requirements=[
        {
            "name": "accessibility",
            "description": "Screen reader support for folder navigation",
            "type": "accessibility",
            "implementation": "ARIA labels on folder cards, keyboard navigation",
        },
        {
            "name": "bulk_operations",
            "description": "Select and process multiple documents",
            "type": "feature",
            "implementation": "Checkboxes on document list, bulk action toolbar",
        },
        {
            "name": "real_time_updates",
            "description": "Live updates during processing",
            "type": "performance",
            "implementation": "WebSocket connection for processing status",
        },
        {
            "name": "responsive_design",
            "description": "Mobile-friendly interface",
            "type": "design",
            "implementation": "Responsive grid, touch-friendly buttons",
        },
    ],
    
    # Navigation
    navigation={
        "Office": "/office",
        "Tools": "/tools",
        "Documents": "/documents",
        "Vault": "/vault",
    },
    
    # Permissions
    required_permissions=["vault_access", "document_view"],
    
    # Dependencies
    css_files=[
        "/static/css/semptify.css",
        "/static/css/filedored.css",
    ],
    js_files=[
        "/static/js/core/filedored.js",
        "/static/js/core/websocket.js",
    ],
    
    # API Endpoints
    api_endpoints=[
        "/api/filedored/process",
        "/api/filedored/folders",
        "/api/filedored/browse/{folder}",
        "/api/filedored/folders/status",
        "/api/filedored/duplicates",
        "/api/filedored/health",
    ],
)
