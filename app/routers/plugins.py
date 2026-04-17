"""
Semptify Plugin Router
======================

Provides API endpoints for managing plugins in the Semptify system.
Integrates with the plugin manager to provide REST API access.

Endpoints:
- GET /api/plugins/ - List all plugins
- GET /api/plugins/{name} - Get plugin details
- POST /api/plugins/{name}/load - Load a plugin
- POST /api/plugins/{name}/unload - Unload a plugin
- POST /api/plugins/{name}/action/{action} - Execute plugin action
- GET /api/plugins/marketplace - Browse plugin marketplace (future)
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import require_user, rate_limit_dependency, StorageUser
from app.sdk.plugin_manager import plugin_manager, PluginStatus

logger = logging.getLogger(__name__)

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class PluginInfo(BaseModel):
    """Plugin information model"""
    name: str = Field(..., description="Plugin name")
    display_name: str = Field(..., description="Plugin display name")
    description: str = Field(..., description="Plugin description")
    version: str = Field(..., description="Plugin version")
    author: str = Field(..., description="Plugin author")
    status: str = Field(..., description="Plugin status")
    category: str = Field(..., description="Plugin category")
    has_ui: bool = Field(..., description="Plugin has UI components")
    loaded_at: Optional[str] = Field(None, description="When plugin was loaded")
    actions: List[str] = Field(default_factory=list, description="Available actions")

class PluginActionRequest(BaseModel):
    """Plugin action request model"""
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    context: Dict[str, Any] = Field(default_factory=dict, description="Action context")

class PluginActionResponse(BaseModel):
    """Plugin action response model"""
    success: bool = Field(..., description="Action success status")
    result: Optional[Dict[str, Any]] = Field(None, description="Action result")
    error: Optional[str] = Field(None, description="Error message if failed")

class PluginListResponse(BaseModel):
    """Plugin list response model"""
    plugins: List[PluginInfo] = Field(..., description="List of plugins")
    total: int = Field(..., description="Total number of plugins")
    loaded: int = Field(..., description="Number of loaded plugins")

# =============================================================================
# ROUTER SETUP
# =============================================================================

router = APIRouter(
    prefix="/api/plugins",
    tags=["plugins"],
    responses={404: {"description": "Plugin not found"}},
)

# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/", response_model=PluginListResponse)
async def list_plugins(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    category_filter: Optional[str] = Query(None, description="Filter by category"),
    current_user: StorageUser = Depends(require_user),
):
    """
    List all available plugins with optional filtering.
    """
    try:
        plugins_data = []
        total = 0
        loaded = 0
        
        for plugin_name, plugin_info in plugin_manager.plugins.items():
            # Apply filters
            if status_filter and plugin_info.status.value != status_filter:
                continue
            if category_filter and plugin_info.definition.category != category_filter:
                continue
            
            total += 1
            if plugin_info.status == PluginStatus.LOADED:
                loaded += 1
            
            # Get available actions
            actions = []
            if plugin_info.sdk:
                actions = list(plugin_info.sdk.actions.keys())
            
            plugin_data = PluginInfo(
                name=plugin_info.definition.name,
                display_name=plugin_info.definition.display_name,
                description=plugin_info.definition.description,
                version=plugin_info.definition.version,
                author=plugin_info.definition.author or "Unknown",
                status=plugin_info.status.value,
                category=plugin_info.definition.category.value,
                has_ui=plugin_info.definition.has_ui,
                loaded_at=plugin_info.loaded_at.isoformat() if plugin_info.loaded_at else None,
                actions=actions,
            )
            plugins_data.append(plugin_data)
        
        return PluginListResponse(
            plugins=plugins_data,
            total=total,
            loaded=loaded,
        )
        
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        raise HTTPException(status_code=500, detail="Failed to list plugins")

@router.get("/{plugin_name}", response_model=PluginInfo)
async def get_plugin(
    plugin_name: str,
    current_user: StorageUser = Depends(require_user),
):
    """
    Get detailed information about a specific plugin.
    """
    try:
        plugin_info = plugin_manager.get_plugin_status(plugin_name)
        if not plugin_info:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
        
        # Get available actions
        actions = []
        if plugin_info.sdk:
            actions = list(plugin_info.sdk.actions.keys())
        
        return PluginInfo(
            name=plugin_info.definition.name,
            display_name=plugin_info.definition.display_name,
            description=plugin_info.definition.description,
            version=plugin_info.definition.version,
            author=plugin_info.definition.author or "Unknown",
            status=plugin_info.status.value,
            category=plugin_info.definition.category.value,
            has_ui=plugin_info.definition.has_ui,
            loaded_at=plugin_info.loaded_at.isoformat() if plugin_info.loaded_at else None,
            actions=actions,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plugin '{plugin_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to get plugin information")

@router.post("/{plugin_name}/load")
async def load_plugin(
    plugin_name: str,
    current_user: StorageUser = Depends(require_user),
):
    """
    Load a specific plugin.
    """
    try:
        success = plugin_manager.load_plugin(plugin_name)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to load plugin '{plugin_name}'")
        
        logger.info(f"Plugin '{plugin_name}' loaded by user {current_user.user_id}")
        
        return {"success": True, "message": f"Plugin '{plugin_name}' loaded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading plugin '{plugin_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to load plugin")

@router.post("/{plugin_name}/unload")
async def unload_plugin(
    plugin_name: str,
    current_user: StorageUser = Depends(require_user),
):
    """
    Unload a specific plugin.
    """
    try:
        success = plugin_manager.unload_plugin(plugin_name)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to unload plugin '{plugin_name}'")
        
        logger.info(f"Plugin '{plugin_name}' unloaded by user {current_user.user_id}")
        
        return {"success": True, "message": f"Plugin '{plugin_name}' unloaded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unloading plugin '{plugin_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to unload plugin")

@router.post("/{plugin_name}/action/{action_name}", response_model=PluginActionResponse)
async def execute_plugin_action(
    plugin_name: str,
    action_name: str,
    request: PluginActionRequest,
    current_user: StorageUser = Depends(require_user),
):
    """
    Execute a specific action on a plugin.
    """
    try:
        plugin_info = plugin_manager.get_plugin_status(plugin_name)
        if not plugin_info:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
        
        if plugin_info.status != PluginStatus.LOADED:
            raise HTTPException(status_code=400, detail=f"Plugin '{plugin_name}' is not loaded")
        
        if not plugin_info.sdk:
            raise HTTPException(status_code=500, detail="Plugin SDK not available")
        
        # Execute action
        result = await plugin_info.sdk.execute_action(
            action_name=action_name,
            user_id=current_user.user_id,
            params=request.params,
            context=request.context,
        )
        
        logger.info(f"Action '{action_name}' executed on plugin '{plugin_name}' by user {current_user.user_id}")
        
        return PluginActionResponse(
            success=True,
            result=result,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing action '{action_name}' on plugin '{plugin_name}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute action: {str(e)}"
        )

@router.get("/marketplace/browse")
async def browse_marketplace(
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    current_user: StorageUser = Depends(require_user),
):
    """
    Browse available plugins in the marketplace (placeholder for future implementation).
    """
    # This is a placeholder for future marketplace implementation
    return {
        "message": "Plugin marketplace coming soon!",
        "available_categories": ["utility", "legal", "housing", "productivity", "integration"],
        "featured_plugins": [
            {
                "name": "hello_world",
                "display_name": "Hello World",
                "description": "Example plugin demonstrating the plugin system",
                "category": "utility",
                "tags": ["example", "demo"],
                "version": "1.0.0",
            }
        ]
    }

@router.get("/health")
async def plugin_system_health():
    """
    Get plugin system health status.
    """
    try:
        stats = plugin_manager.get_system_stats()
        return {
            "status": "healthy",
            "stats": stats,
            "timestamp": plugin_manager._get_current_time().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting plugin system health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": plugin_manager._get_current_time().isoformat(),
        }
