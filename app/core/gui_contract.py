"""
GUI Requirements Contract - Standardized UI Component Specification
====================================================================

Purpose: Define a universal contract for all Semptify modules to specify their GUI requirements.
This ensures consistency across the application and makes it easy to understand what each module needs.

Usage: Each module creates a GUI_REQUIREMENTS dict following this contract.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class InputType(StrEnum):
    """Types of input fields."""

    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    PASSWORD = "password"  # pragma: allowlist secret
    FILE = "file"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    SELECT = "select"
    MULTISELECT = "multiselect"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"
    SEARCH = "search"
    SLIDER = "slider"
    TOGGLE = "toggle"


class OutputType(StrEnum):
    """Types of output displays."""

    TEXT = "text"
    NUMBER = "number"
    TABLE = "table"
    LIST = "list"
    GRID = "grid"
    CARD = "card"
    CHART = "chart"
    PROGRESS = "progress"
    STATUS = "status"
    ALERT = "alert"
    MODAL = "modal"
    POPOUT = "popout"
    TOOLTIP = "tooltip"
    BADGE = "badge"


class ActionType(StrEnum):
    """Types of actions/buttons."""

    SUBMIT = "submit"
    CANCEL = "cancel"
    SAVE = "save"
    DELETE = "delete"
    EDIT = "edit"
    VIEW = "view"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    PROCESS = "process"
    REFRESH = "refresh"
    SEARCH = "search"
    FILTER = "filter"
    SORT = "sort"
    EXPORT = "export"
    IMPORT = "import"
    CUSTOM = "custom"


class IndicatorType(StrEnum):
    """Types of indicators."""

    PROGRESS = "progress"
    SPINNER = "spinner"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    STATUS = "status"
    BADGE = "badge"
    COUNTER = "counter"
    TIMER = "timer"


class PopOutType(StrEnum):
    """Types of pop-outs/modals."""

    MODAL = "modal"
    DRAWER = "drawer"
    TOOLTIP = "tooltip"
    POPOVER = "popover"
    DROPDOWN = "dropdown"
    CONTEXT_MENU = "context_menu"
    NOTIFICATION = "notification"
    CONFIRMATION = "confirmation"
    ALERT = "alert"


class InputField(BaseModel):
    """Specification for an input field."""

    name: str
    label: str
    type: InputType
    required: bool = False
    default: Any = None
    placeholder: str | None = None
    options: list[dict[str, Any]] | None = None  # For select/multiselect
    validation: dict[str, Any] | None = None  # Validation rules
    help_text: str | None = None
    disabled: bool = False
    hidden: bool = False


class OutputDisplay(BaseModel):
    """Specification for an output display."""

    name: str
    label: str
    type: OutputType
    data_source: str  # API endpoint or data key
    refresh_interval: int | None = None  # Seconds
    columns: list[dict[str, Any]] | None = None  # For tables
    actions: list[dict[str, Any]] | None = None  # Row actions


class ActionButton(BaseModel):
    """Specification for an action button."""

    name: str
    label: str
    type: ActionType
    endpoint: str | None = None  # API endpoint
    method: str = "POST"  # HTTP method
    confirm: str | None = None  # Confirmation message
    disabled: bool = False
    icon: str | None = None
    style: str | None = None  # CSS class/style
    loading_state: str | None = None  # What to show while loading


class Indicator(BaseModel):
    """Specification for an indicator."""

    name: str
    type: IndicatorType
    data_source: str  # API endpoint or data key
    position: str = "top-right"  # Position on screen
    auto_hide: bool = False
    timeout: int | None = None  # Auto-hide after seconds


class PopOut(BaseModel):
    """Specification for a pop-out/modal."""

    name: str
    type: PopOutType
    trigger: str  # What triggers it (click, hover, auto)
    title: str | None = None
    content: str  # URL or content template
    size: str | None = None  # small, medium, large, full
    dismissible: bool = True


class SpecialRequirement(BaseModel):
    """Special GUI requirements."""

    name: str
    description: str
    type: str  # accessibility, security, performance, etc.
    implementation: str  # How to implement


class GUIRequirements(BaseModel):
    """Complete GUI requirements contract for a module."""

    module_name: str
    version: str = "1.0"

    # Page Layout
    layout: str = "default"  # default, wide, narrow, custom
    sections: list[str] = Field(default_factory=list)  # Page sections

    # Input Fields
    inputs: list[InputField] = Field(default_factory=list)

    # Output Displays
    outputs: list[OutputDisplay] = Field(default_factory=list)

    # Action Buttons
    actions: list[ActionButton] = Field(default_factory=list)

    # Indicators
    indicators: list[Indicator] = Field(default_factory=list)

    # Pop-outs/Modals
    popouts: list[PopOut] = Field(default_factory=list)

    # Special Requirements
    special_requirements: list[SpecialRequirement] = Field(default_factory=list)

    # Navigation
    navigation: dict[str, str] = Field(default_factory=dict)  # name -> url

    # Permissions
    required_permissions: list[str] = Field(default_factory=list)

    # Dependencies
    css_files: list[str] = Field(default_factory=list)
    js_files: list[str] = Field(default_factory=list)

    # API Endpoints
    api_endpoints: list[str] = Field(default_factory=list)


# =============================================================================
# Helper Functions
# =============================================================================


def create_input_field(name: str, label: str, type: InputType, **kwargs) -> InputField:
    """Helper to create an input field."""
    return InputField(name=name, label=label, type=type, **kwargs)


def create_output_display(name: str, label: str, type: OutputType, data_source: str, **kwargs) -> OutputDisplay:
    """Helper to create an output display."""
    return OutputDisplay(name=name, label=label, type=type, data_source=data_source, **kwargs)


def create_action_button(name: str, label: str, type: ActionType, **kwargs) -> ActionButton:
    """Helper to create an action button."""
    return ActionButton(name=name, label=label, type=type, **kwargs)


def create_indicator(name: str, type: IndicatorType, data_source: str, **kwargs) -> Indicator:
    """Helper to create an indicator."""
    return Indicator(name=name, type=type, data_source=data_source, **kwargs)


def create_popout(name: str, type: PopOutType, trigger: str, **kwargs) -> PopOut:
    """Helper to create a pop-out."""
    return PopOut(name=name, type=type, trigger=trigger, **kwargs)


# =============================================================================
# Example Usage
# =============================================================================

EXAMPLE_GUI_REQUIREMENTS = GUIRequirements(
    module_name="example_module",
    layout="default",
    sections=["header", "main", "sidebar", "footer"],
    inputs=[
        create_input_field("search", "Search", InputType.SEARCH, placeholder="Search documents..."),
        create_input_field(
            "category",
            "Category",
            InputType.SELECT,
            options=[
                {"value": "all", "label": "All"},
                {"value": "pdf", "label": "PDF"},
                {"value": "word", "label": "Word"},
            ],
        ),
    ],
    outputs=[
        create_output_display("results", "Results", OutputType.GRID, data_source="/api/results"),
    ],
    actions=[
        create_action_button("process", "Process All", ActionType.PROCESS, endpoint="/api/process"),
    ],
    indicators=[
        create_indicator("status", IndicatorType.STATUS, data_source="/api/status"),
    ],
    popouts=[
        create_popout("help", PopOutType.TOOLTIP, trigger="hover", content="Help text"),
    ],
    navigation={
        "Home": "/",
        "Settings": "/settings",
    },
    api_endpoints=["/api/results", "/api/process", "/api/status"],
)
