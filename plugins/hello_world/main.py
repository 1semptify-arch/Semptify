"""
Hello World Plugin
==================

Example plugin demonstrating the Semptify plugin system.
Use this as a template for creating your own plugins!
"""

import logging
from datetime import datetime
from typing import Any, Dict

# Import the SDK
from app.sdk import (
    ModuleSDK,
    ModuleDefinition,
    ModuleCategory,
    PackType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MODULE DEFINITION
# =============================================================================

module_definition = ModuleDefinition(
    name="hello_world",
    display_name="Hello World",
    description="Example plugin demonstrating the plugin system",
    version="1.0.0",
    category=ModuleCategory.UTILITY,
    
    handles_documents=[],
    accepts_packs=[PackType.USER_DATA],
    produces_packs=[PackType.CUSTOM],
    depends_on=[],
    
    has_ui=False,
    has_background_tasks=False,
    requires_auth=False,
)


# =============================================================================
# SDK INSTANCE
# =============================================================================

sdk = ModuleSDK(module_definition)


# =============================================================================
# ACTIONS
# =============================================================================

@sdk.action(
    "greet",
    description="Send a friendly greeting",
    required_params=["name"],
    produces=["greeting"],
)
async def greet(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate a personalized greeting"""
    name = params.get("name", "Friend")
    
    greeting = f"Hello, {name}! Welcome to Semptify! 👋"
    
    logger.info(f"hello_world: Greeted {name}")
    
    return {
        "greeting": greeting,
        "timestamp": datetime.utcnow().isoformat(),
    }


@sdk.action(
    "echo",
    description="Echo back the input message",
    required_params=["message"],
    produces=["echo"],
)
async def echo(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Echo a message back"""
    message = params.get("message", "")
    
    return {
        "echo": message,
        "original_length": len(message),
        "echoed_at": datetime.utcnow().isoformat(),
    }


@sdk.action(
    "get_info",
    description="Get plugin information",
    produces=["info"],
)
async def get_info(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Return information about this plugin"""
    return {
        "info": {
            "name": module_definition.name,
            "display_name": module_definition.display_name,
            "version": module_definition.version,
            "description": module_definition.description,
            "author": "Semptify Team",
            "is_example": True,
        }
    }


@sdk.action(
    "get_state",
    description="Get plugin state",
    produces=["hello_world_state"],
)
async def get_state(
    user_id: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Return plugin state for sync operations"""
    return {
        "hello_world_state": {
            "active": True,
            "user_id": user_id,
            "last_checked": datetime.utcnow().isoformat(),
        }
    }


# =============================================================================
# EVENT HANDLERS
# =============================================================================

@sdk.on_event("workflow_started")
async def on_workflow_started(event_type: str, data: Dict[str, Any]):
    """React to workflow start events"""
    logger.debug(f"hello_world: Noticed workflow started - {data.get('workflow_id')}")


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize():
    """Initialize the plugin - called when plugin is loaded"""
    sdk.initialize()
    logger.info("✅ Hello World plugin loaded! 👋")


def cleanup():
    """Cleanup when plugin is unloaded"""
    logger.info("👋 Hello World plugin unloaded. Goodbye!")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "sdk",
    "module_definition",
    "initialize",
    "cleanup",
    "greet",
    "echo",
    "get_info",
    "get_state",
]
