"""
Semptify Module SDK
===================

Import everything you need from here to integrate a new module.

Quick Start:
    from app.sdk import ModuleSDK, ModuleDefinition
import logging
logger = logging.getLogger(__name__)
    
    module = ModuleDefinition(name="my_module", ...)
    sdk = ModuleSDK(module)
    
    @sdk.action("my_action")
    async def my_action(user_id, params, context):
        return {"result": "done"}
    
    sdk.initialize()

Convert Flask:
    from app.sdk import FlaskConverter
    converter = FlaskConverter()
    converter.convert_file("flask_app.py", "new_module")

Plugins:
    from app.sdk import plugin_manager
    plugin_manager.discover_plugins()
    plugin_manager.load_all()
"""

from app.core.module_sdk import (
    InstalledModule,
    # Core module SDK (product manifest integration)
    ModuleCapability,
    ModuleManifest,
    ModuleRegistry,
    get_module_status,
    module_registry,
    register_module,
    register_tier_modules,
)
from app.core.product_manifest import ProductTier
from app.sdk.auth import (
    CookieAuth,
    UserIdComponents,
    UserRole,
    generate_token,
    get_permissions,
    hash_token,
    make_user_id,
    parse_user_id,
    set_auth_cookie,
    verify_auth_cookie,
)
from app.sdk.flask_converter import (
    FlaskAnalysis,
    FlaskAnalyzer,
    FlaskConverter,
)
from app.sdk.module_sdk import (
    ActionDefinition,
    # Base class (alternative to SDK)
    BaseModule,
    DocumentType,
    InfoPack,
    # Enums
    ModuleCategory,
    # Definition classes
    ModuleDefinition,
    ModuleRequest,
    # Main SDK class
    ModuleSDK,
    PackType,
    # Helper functions
    create_module,
    generate_module_template,
)
from app.sdk.navigation import (
    get_next_path,
    get_onboarding_start,
    get_path,
    get_reconnect_path,
    get_stage,
    is_canonical_path,
)
from app.sdk.plugin_manager import (
    Plugin,
    PluginManager,
    PluginMetadata,
    PluginStatus,
    plugin_manager,
)

__all__ = [
    # Core SDK
    "ModuleSDK",
    "ModuleDefinition",
    "ActionDefinition",
    "InfoPack",
    "ModuleRequest",
    "ModuleCategory",
    "DocumentType",
    "PackType",
    "BaseModule",
    "create_module",
    "generate_module_template",

    # Module SDK (product manifest integration)
    "ModuleCapability",
    "ModuleManifest",
    "InstalledModule",
    "ModuleRegistry",
    "module_registry",
    "register_module",
    "register_tier_modules",
    "get_module_status",
    "ProductTier",

    # Flask Converter
    "FlaskConverter",
    "FlaskAnalyzer",
    "FlaskAnalysis",

    # Plugin System
    "PluginManager",
    "Plugin",
    "PluginMetadata",
    "PluginStatus",
    "plugin_manager",
]
