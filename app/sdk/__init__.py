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

from app.sdk.module_sdk import (
    # Main SDK class
    ModuleSDK,

    # Definition classes
    ModuleDefinition,
    ActionDefinition,
    InfoPack,
    ModuleRequest,

    # Enums
    ModuleCategory,
    DocumentType,
    PackType,

    # Base class (alternative to SDK)
    BaseModule,

    # Helper functions
    create_module,
    generate_module_template,
)

from app.core.module_sdk import (
    # Core module SDK (product manifest integration)
    ModuleCapability,
    ModuleManifest,
    InstalledModule,
    ModuleRegistry,
    module_registry,
    register_module,
    register_tier_modules,
    get_module_status,
)
from app.core.product_manifest import ProductTier

from app.sdk.flask_converter import (
    FlaskConverter,
    FlaskAnalyzer,
    FlaskAnalysis,
)

from app.sdk.plugin_manager import (
    PluginManager,
    Plugin,
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
