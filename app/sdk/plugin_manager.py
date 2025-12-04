"""
Semptify Plugin Manager
=======================

Manages add-on/plugin modules that can be dynamically loaded
and integrated with the Positronic Mesh.

Features:
- Discover plugins from directory
- Load/unload plugins at runtime
- Plugin dependencies resolution
- Plugin versioning and updates
- Plugin marketplace (future)

Usage:
    from app.sdk.plugin_manager import plugin_manager
    
    # Load all plugins
    plugin_manager.discover_plugins()
    plugin_manager.load_all()
    
    # Load specific plugin
    plugin_manager.load_plugin("my_plugin")
    
    # Check plugin status
    status = plugin_manager.get_plugin_status("my_plugin")
"""

import importlib
import importlib.util
import logging
import os
import sys
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import traceback

logger = logging.getLogger(__name__)


# =============================================================================
# PLUGIN STATUS
# =============================================================================

class PluginStatus(str, Enum):
    """Status of a plugin"""
    DISCOVERED = "discovered"    # Found but not loaded
    LOADING = "loading"          # Currently loading
    ACTIVE = "active"            # Loaded and running
    DISABLED = "disabled"        # Manually disabled
    ERROR = "error"              # Failed to load
    INCOMPATIBLE = "incompatible"  # Version/dependency issue
    UPDATING = "updating"        # Being updated


# =============================================================================
# PLUGIN METADATA
# =============================================================================

@dataclass
class PluginMetadata:
    """Metadata about a plugin"""
    name: str
    display_name: str
    description: str
    version: str
    author: str = ""
    website: str = ""
    license: str = "MIT"
    
    # Requirements
    min_semptify_version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)  # Other plugins required
    python_packages: List[str] = field(default_factory=list)  # pip packages
    
    # Categorization
    category: str = "utility"
    tags: List[str] = field(default_factory=list)
    
    # Entry points
    main_module: str = "main"  # Main module file (without .py)
    init_function: str = "initialize"  # Function to call on load
    
    # Optional
    icon: str = ""
    screenshots: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        return cls(
            name=data.get("name", "unknown"),
            display_name=data.get("display_name", data.get("name", "Unknown")),
            description=data.get("description", ""),
            version=data.get("version", "0.0.1"),
            author=data.get("author", ""),
            website=data.get("website", ""),
            license=data.get("license", "MIT"),
            min_semptify_version=data.get("min_semptify_version", "1.0.0"),
            dependencies=data.get("dependencies", []),
            python_packages=data.get("python_packages", []),
            category=data.get("category", "utility"),
            tags=data.get("tags", []),
            main_module=data.get("main_module", "main"),
            init_function=data.get("init_function", "initialize"),
            icon=data.get("icon", ""),
            screenshots=data.get("screenshots", []),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "website": self.website,
            "license": self.license,
            "min_semptify_version": self.min_semptify_version,
            "dependencies": self.dependencies,
            "python_packages": self.python_packages,
            "category": self.category,
            "tags": self.tags,
            "main_module": self.main_module,
            "init_function": self.init_function,
        }


# =============================================================================
# PLUGIN INSTANCE
# =============================================================================

@dataclass
class Plugin:
    """Represents a loaded plugin"""
    metadata: PluginMetadata
    path: Path
    status: PluginStatus = PluginStatus.DISCOVERED
    module: Any = None  # The loaded Python module
    sdk: Any = None  # The plugin's SDK instance
    error: Optional[str] = None
    loaded_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.metadata.name,
            "display_name": self.metadata.display_name,
            "version": self.metadata.version,
            "status": self.status.value,
            "path": str(self.path),
            "error": self.error,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "metadata": self.metadata.to_dict(),
        }


# =============================================================================
# PLUGIN MANAGER
# =============================================================================

class PluginManager:
    """
    Central plugin manager for Semptify.
    
    Handles discovery, loading, and lifecycle of plugins.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Plugin storage
        self.plugins: Dict[str, Plugin] = {}
        
        # Plugin directories
        self.plugin_dirs: List[Path] = [
            Path("app/plugins"),      # Built-in plugins
            Path("plugins"),          # User plugins
            Path.home() / ".semptify" / "plugins",  # User home plugins
        ]
        
        # Callbacks
        self.on_plugin_loaded: List[Callable] = []
        self.on_plugin_unloaded: List[Callable] = []
        self.on_plugin_error: List[Callable] = []
        
        # Semptify version (for compatibility checks)
        self.semptify_version = "1.0.0"
        
        logger.info("🔌 Plugin Manager initialized")
    
    def add_plugin_dir(self, path: str):
        """Add a directory to search for plugins"""
        self.plugin_dirs.append(Path(path))
    
    # =========================================================================
    # DISCOVERY
    # =========================================================================
    
    def discover_plugins(self) -> List[Plugin]:
        """Discover all plugins in plugin directories"""
        discovered = []
        
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            # Each subdirectory is a potential plugin
            for item in plugin_dir.iterdir():
                if item.is_dir() and not item.name.startswith(('_', '.')):
                    plugin = self._discover_plugin(item)
                    if plugin:
                        discovered.append(plugin)
        
        logger.info(f"🔍 Discovered {len(discovered)} plugins")
        return discovered
    
    def _discover_plugin(self, path: Path) -> Optional[Plugin]:
        """Discover a single plugin from a directory"""
        # Look for plugin.json or setup.py
        metadata_file = path / "plugin.json"
        
        if not metadata_file.exists():
            # Try to infer from __init__.py
            init_file = path / "__init__.py"
            if init_file.exists():
                metadata = PluginMetadata(
                    name=path.name,
                    display_name=path.name.replace('_', ' ').title(),
                    description=f"Plugin: {path.name}",
                    version="0.0.1",
                )
            else:
                return None
        else:
            # Load from plugin.json
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                metadata = PluginMetadata.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load plugin.json from {path}: {e}")
                return None
        
        # Create plugin instance
        plugin = Plugin(
            metadata=metadata,
            path=path,
            status=PluginStatus.DISCOVERED,
        )
        
        # Store in registry
        self.plugins[metadata.name] = plugin
        
        logger.debug(f"   📦 Found plugin: {metadata.name} v{metadata.version}")
        
        return plugin
    
    # =========================================================================
    # LOADING
    # =========================================================================
    
    def load_all(self) -> Dict[str, bool]:
        """Load all discovered plugins"""
        results = {}
        
        # Sort by dependencies
        load_order = self._resolve_load_order()
        
        for plugin_name in load_order:
            success = self.load_plugin(plugin_name)
            results[plugin_name] = success
        
        loaded_count = sum(1 for v in results.values() if v)
        logger.info(f"✅ Loaded {loaded_count}/{len(results)} plugins")
        
        return results
    
    def load_plugin(self, name: str) -> bool:
        """Load a specific plugin"""
        if name not in self.plugins:
            logger.error(f"Plugin not found: {name}")
            return False
        
        plugin = self.plugins[name]
        
        if plugin.status == PluginStatus.ACTIVE:
            logger.warning(f"Plugin already loaded: {name}")
            return True
        
        plugin.status = PluginStatus.LOADING
        
        try:
            # Check dependencies
            if not self._check_dependencies(plugin):
                plugin.status = PluginStatus.INCOMPATIBLE
                return False
            
            # Check Python packages
            if not self._check_python_packages(plugin):
                plugin.status = PluginStatus.INCOMPATIBLE
                return False
            
            # Load the module
            module = self._load_module(plugin)
            if not module:
                plugin.status = PluginStatus.ERROR
                return False
            
            plugin.module = module
            
            # Get SDK instance if available
            if hasattr(module, 'sdk'):
                plugin.sdk = module.sdk
            
            # Call init function
            init_func = getattr(module, plugin.metadata.init_function, None)
            if init_func:
                init_func()
            
            plugin.status = PluginStatus.ACTIVE
            plugin.loaded_at = datetime.utcnow()
            
            logger.info(f"✅ Loaded plugin: {name} v{plugin.metadata.version}")
            
            # Notify callbacks
            for callback in self.on_plugin_loaded:
                try:
                    callback(plugin)
                except Exception as e:
                    logger.error(f"Plugin loaded callback error: {e}")
            
            return True
            
        except Exception as e:
            plugin.status = PluginStatus.ERROR
            plugin.error = str(e)
            logger.error(f"Failed to load plugin {name}: {e}")
            logger.debug(traceback.format_exc())
            
            # Notify error callbacks
            for callback in self.on_plugin_error:
                try:
                    callback(plugin, e)
                except:
                    pass
            
            return False
    
    def _load_module(self, plugin: Plugin) -> Optional[Any]:
        """Load the plugin's Python module"""
        main_module = plugin.metadata.main_module
        module_path = plugin.path / f"{main_module}.py"
        
        if not module_path.exists():
            # Try __init__.py
            module_path = plugin.path / "__init__.py"
            if not module_path.exists():
                plugin.error = f"Module not found: {main_module}.py or __init__.py"
                return None
        
        # Add plugin path to sys.path temporarily
        plugin_parent = str(plugin.path.parent)
        if plugin_parent not in sys.path:
            sys.path.insert(0, plugin_parent)
        
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                f"semptify_plugin_{plugin.metadata.name}",
                module_path
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            return module
            
        except Exception as e:
            plugin.error = f"Import error: {e}"
            logger.error(f"Failed to import plugin module: {e}")
            return None
    
    def _check_dependencies(self, plugin: Plugin) -> bool:
        """Check if plugin dependencies are met"""
        for dep in plugin.metadata.dependencies:
            if dep not in self.plugins:
                plugin.error = f"Missing dependency: {dep}"
                logger.error(f"Plugin {plugin.metadata.name} missing dependency: {dep}")
                return False
            
            dep_plugin = self.plugins[dep]
            if dep_plugin.status != PluginStatus.ACTIVE:
                plugin.error = f"Dependency not active: {dep}"
                logger.error(f"Plugin {plugin.metadata.name} dependency not active: {dep}")
                return False
        
        return True
    
    def _check_python_packages(self, plugin: Plugin) -> bool:
        """Check if required Python packages are installed"""
        for package in plugin.metadata.python_packages:
            try:
                importlib.import_module(package.split('[')[0])  # Handle package[extra]
            except ImportError:
                plugin.error = f"Missing Python package: {package}"
                logger.error(f"Plugin {plugin.metadata.name} missing package: {package}")
                return False
        
        return True
    
    def _resolve_load_order(self) -> List[str]:
        """Resolve plugin load order based on dependencies"""
        # Simple topological sort
        order = []
        visited = set()
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            
            plugin = self.plugins.get(name)
            if plugin:
                for dep in plugin.metadata.dependencies:
                    visit(dep)
                order.append(name)
        
        for name in self.plugins:
            visit(name)
        
        return order
    
    # =========================================================================
    # UNLOADING
    # =========================================================================
    
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin"""
        if name not in self.plugins:
            return False
        
        plugin = self.plugins[name]
        
        if plugin.status != PluginStatus.ACTIVE:
            return True
        
        try:
            # Call cleanup if available
            if plugin.module and hasattr(plugin.module, 'cleanup'):
                plugin.module.cleanup()
            
            # Remove from sys.modules
            module_name = f"semptify_plugin_{name}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            plugin.status = PluginStatus.DISABLED
            plugin.module = None
            plugin.sdk = None
            
            logger.info(f"🔌 Unloaded plugin: {name}")
            
            # Notify callbacks
            for callback in self.on_plugin_unloaded:
                try:
                    callback(plugin)
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {name}: {e}")
            return False
    
    def reload_plugin(self, name: str) -> bool:
        """Reload a plugin"""
        self.unload_plugin(name)
        return self.load_plugin(name)
    
    # =========================================================================
    # STATUS & INFO
    # =========================================================================
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name"""
        return self.plugins.get(name)
    
    def get_plugin_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get plugin status"""
        plugin = self.plugins.get(name)
        if not plugin:
            return None
        return plugin.to_dict()
    
    def get_all_plugins(self) -> List[Dict[str, Any]]:
        """Get all plugins info"""
        return [p.to_dict() for p in self.plugins.values()]
    
    def get_active_plugins(self) -> List[Plugin]:
        """Get all active plugins"""
        return [p for p in self.plugins.values() if p.status == PluginStatus.ACTIVE]
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of plugin system status"""
        by_status = {}
        for plugin in self.plugins.values():
            status = plugin.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_plugins": len(self.plugins),
            "active_plugins": len(self.get_active_plugins()),
            "by_status": by_status,
            "plugin_dirs": [str(d) for d in self.plugin_dirs],
        }
    
    # =========================================================================
    # PLUGIN CREATION HELPERS
    # =========================================================================
    
    def create_plugin_template(
        self,
        name: str,
        display_name: str,
        description: str,
        output_dir: str = None,
    ) -> Path:
        """Create a new plugin from template"""
        output_dir = Path(output_dir or "plugins")
        plugin_dir = output_dir / name
        plugin_dir.mkdir(parents=True, exist_ok=True)
        
        # Create plugin.json
        metadata = {
            "name": name,
            "display_name": display_name,
            "description": description,
            "version": "1.0.0",
            "author": "",
            "website": "",
            "license": "MIT",
            "min_semptify_version": "1.0.0",
            "dependencies": [],
            "python_packages": [],
            "category": "utility",
            "tags": [],
            "main_module": "main",
            "init_function": "initialize",
        }
        
        with open(plugin_dir / "plugin.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create main.py
        main_code = f'''"""
{display_name} Plugin
{"=" * (len(display_name) + 7)}

{description}
"""

import logging
from typing import Any, Dict

from app.sdk import (
    ModuleSDK,
    ModuleDefinition,
    ModuleCategory,
)

logger = logging.getLogger(__name__)


# Module definition
module_definition = ModuleDefinition(
    name="{name}",
    display_name="{display_name}",
    description="{description}",
    version="1.0.0",
    category=ModuleCategory.UTILITY,
)

# SDK instance
sdk = ModuleSDK(module_definition)


# Actions
@sdk.action("hello", produces=["message"])
async def hello(user_id: str, params: Dict[str, Any], context: Dict[str, Any]):
    """Say hello"""
    return {{"message": f"Hello from {display_name}!"}}


@sdk.action("get_state", produces=["{name}_state"])
async def get_state(user_id: str, params: Dict[str, Any], context: Dict[str, Any]):
    """Get plugin state"""
    return {{"{name}_state": {{"active": True}}}}


# Initialize
def initialize():
    """Initialize the plugin"""
    sdk.initialize()
    logger.info("✅ {display_name} plugin loaded")


def cleanup():
    """Cleanup when plugin is unloaded"""
    logger.info("🔌 {display_name} plugin unloaded")


__all__ = ["sdk", "module_definition", "initialize", "cleanup"]
'''
        
        with open(plugin_dir / "main.py", 'w') as f:
            f.write(main_code)
        
        # Create __init__.py
        with open(plugin_dir / "__init__.py", 'w') as f:
            f.write(f'"""Plugin: {display_name}"""\n')
            f.write('from .main import *\n')
        
        # Create README
        readme = f'''# {display_name}

{description}

## Installation

Copy this folder to your Semptify `plugins` directory.

## Usage

The plugin will be automatically discovered and loaded.

## Configuration

Edit `plugin.json` to configure the plugin.

## API

### Actions

- `hello` - Say hello
- `get_state` - Get plugin state

## License

MIT
'''
        
        with open(plugin_dir / "README.md", 'w') as f:
            f.write(readme)
        
        logger.info(f"✅ Created plugin template: {plugin_dir}")
        
        return plugin_dir


# Global plugin manager instance
plugin_manager = PluginManager()


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Semptify Plugin Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List plugins
    list_parser = subparsers.add_parser("list", help="List all plugins")
    
    # Create plugin
    create_parser = subparsers.add_parser("create", help="Create new plugin")
    create_parser.add_argument("name", help="Plugin name")
    create_parser.add_argument("display_name", help="Display name")
    create_parser.add_argument("description", help="Description")
    create_parser.add_argument("--output", "-o", default="plugins", help="Output directory")
    
    # Load plugin
    load_parser = subparsers.add_parser("load", help="Load a plugin")
    load_parser.add_argument("name", help="Plugin name")
    
    # Unload plugin
    unload_parser = subparsers.add_parser("unload", help="Unload a plugin")
    unload_parser.add_argument("name", help="Plugin name")
    
    # Status
    status_parser = subparsers.add_parser("status", help="Show plugin status")
    status_parser.add_argument("name", nargs="?", help="Plugin name (optional)")
    
    args = parser.parse_args()
    
    if args.command == "list":
        plugin_manager.discover_plugins()
        print("\nDiscovered Plugins:")
        print("-" * 60)
        for plugin in plugin_manager.plugins.values():
            status_icon = "✅" if plugin.status == PluginStatus.ACTIVE else "⚪"
            print(f"{status_icon} {plugin.metadata.name:<20} v{plugin.metadata.version:<10} [{plugin.status.value}]")
            print(f"   {plugin.metadata.description[:50]}")
    
    elif args.command == "create":
        plugin_manager.create_plugin_template(
            args.name,
            args.display_name,
            args.description,
            args.output,
        )
        print(f"\n✅ Created plugin: {args.name}")
        print(f"   Location: {args.output}/{args.name}")
    
    elif args.command == "load":
        plugin_manager.discover_plugins()
        success = plugin_manager.load_plugin(args.name)
        if success:
            print(f"✅ Loaded: {args.name}")
        else:
            print(f"❌ Failed to load: {args.name}")
    
    elif args.command == "unload":
        success = plugin_manager.unload_plugin(args.name)
        if success:
            print(f"✅ Unloaded: {args.name}")
        else:
            print(f"❌ Failed to unload: {args.name}")
    
    elif args.command == "status":
        if args.name:
            status = plugin_manager.get_plugin_status(args.name)
            if status:
                print(json.dumps(status, indent=2))
            else:
                print(f"Plugin not found: {args.name}")
        else:
            summary = plugin_manager.get_status_summary()
            print(json.dumps(summary, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
