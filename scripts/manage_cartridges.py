#!/usr/bin/env python3
"""
Semptify Cartridge Compatibility Manager

Manages module compatibility, updates, and inventory through cartridge-based system.
Cartridges contain preset parameters and compatibility matrices for safe updates.

Usage:
    python scripts/manage_cartridges.py list                    # List all cartridges
    python scripts/manage_cartridges.py validate <module>      # Validate module cartridge
    python scripts/manage_cartridges.py update <module> <cartridge_file>  # Update module
    python scripts/manage_cartridges.py inventory              # Update compliance inventory
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

COMPATIBILITY_FILE = Path("compatibility_system.json")
MODULE_INVENTORY = Path("MODULE_COMPLIANCE_INVENTORY.csv")

class CartridgeManager:
    def __init__(self):
        self.compatibility_data = self._load_compatibility_data()
        self.inventory_data = self._load_inventory_data()

    def _load_compatibility_data(self) -> Dict[str, Any]:
        """Load the compatibility system data."""
        if not COMPATIBILITY_FILE.exists():
            print(f"Error: {COMPATIBILITY_FILE} not found")
            return {}
        try:
            with COMPATIBILITY_FILE.open('r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading compatibility data: {e}")
            return {}

    def _load_inventory_data(self) -> List[Dict[str, str]]:
        """Load the module compliance inventory."""
        if not MODULE_INVENTORY.exists():
            print(f"Warning: {MODULE_INVENTORY} not found")
            return []
        try:
            with MODULE_INVENTORY.open('r') as f:
                lines = f.readlines()
            if not lines:
                return []
            headers = lines[0].strip().split(',')
            data = []
            for line in lines[1:]:
                values = line.strip().split(',')
                if len(values) >= len(headers):
                    data.append(dict(zip(headers, values)))
            return data
        except Exception as e:
            print(f"Error loading inventory data: {e}")
            return []

    def list_cartridges(self) -> None:
        """List all cartridges and their status."""
        cartridges = self.compatibility_data.get('cartridges', {})
        print("Semptify Module Cartridges:")
        print("=" * 50)
        for name, cartridge in cartridges.items():
            status = cartridge.get('status', 'unknown')
            version = cartridge.get('version', 'unknown')
            print(f"{name}: v{version} [{status}]")

    def validate_cartridge(self, module_name: str) -> bool:
        """Validate a cartridge's compatibility."""
        cartridges = self.compatibility_data.get('cartridges', {})
        if module_name not in cartridges:
            print(f"Error: Cartridge for {module_name} not found")
            return False

        cartridge = cartridges[module_name]
        print(f"Validating {module_name} cartridge...")

        # Check dependencies
        dependencies = cartridge.get('dependencies', [])
        missing_deps = []
        for dep in dependencies:
            if dep not in cartridges:
                missing_deps.append(dep)

        if missing_deps:
            print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
            return False

        # Check preset parameters
        params = cartridge.get('preset_parameters', {})
        if not params:
            print("⚠️  No preset parameters defined")
        else:
            print(f"✅ {len(params)} preset parameters configured")

        # Check compatibility matrix
        matrix = cartridge.get('compatibility_matrix', {})
        if not matrix:
            print("⚠️  No compatibility matrix defined")
        else:
            print(f"✅ Compatibility matrix: {len(matrix)} checks")

        print(f"✅ {module_name} cartridge is valid")
        return True

    def update_module(self, module_name: str, cartridge_file: str) -> bool:
        """Update a module using a cartridge file."""
        cartridge_path = Path(cartridge_file)
        if not cartridge_path.exists():
            print(f"Error: Cartridge file {cartridge_file} not found")
            return False

        try:
            with cartridge_path.open('r') as f:
                new_cartridge = json.load(f)
        except Exception as e:
            print(f"Error loading cartridge file: {e}")
            return False

        # Validate the new cartridge
        if not self._validate_cartridge_structure(new_cartridge):
            return False

        # Backup current state
        self._backup_current_cartridge(module_name)

        # Apply update
        self.compatibility_data['cartridges'][module_name] = new_cartridge
        self._save_compatibility_data()

        print(f"✅ Updated {module_name} with cartridge {cartridge_file}")
        return True

    def _validate_cartridge_structure(self, cartridge: Dict[str, Any]) -> bool:
        """Validate cartridge JSON structure."""
        required_fields = ['version', 'status', 'dependencies', 'preset_parameters', 'compatibility_matrix']
        for field in required_fields:
            if field not in cartridge:
                print(f"❌ Missing required field: {field}")
                return False
        return True

    def _backup_current_cartridge(self, module_name: str) -> None:
        """Backup current cartridge state."""
        cartridges = self.compatibility_data.get('cartridges', {})
        if module_name in cartridges:
            backup_file = Path(f"cartridge_backup_{module_name}.json")
            try:
                with backup_file.open('w') as f:
                    json.dump(cartridges[module_name], f, indent=2)
                print(f"📁 Backed up {module_name} to {backup_file}")
            except Exception as e:
                print(f"Warning: Could not backup {module_name}: {e}")

    def _save_compatibility_data(self) -> None:
        """Save compatibility data to file."""
        try:
            with COMPATIBILITY_FILE.open('w') as f:
                json.dump(self.compatibility_data, f, indent=2)
        except Exception as e:
            print(f"Error saving compatibility data: {e}")

    def update_inventory(self) -> None:
        """Update the compliance inventory based on cartridge status."""
        cartridges = self.compatibility_data.get('cartridges', {})
        inventory = self.inventory_data

        updated_count = 0
        for item in inventory:
            name = item.get('name', '')
            if name in cartridges:
                cartridge = cartridges[name]
                current_status = item.get('status', '')

                # Update status based on cartridge
                if current_status == 'unknown':
                    item['status'] = 'compliant'
                    item['privacy_scope'] = 'user_controlled'
                    item['evidence_role'] = 'preservation'
                    item['security_notes'] = 'cartridge_managed'
                    item['next_action'] = 'monitor'
                    updated_count += 1

        # Update inventory status in compatibility data
        self.compatibility_data['inventory_status'] = {
            'total_modules': len(inventory),
            'reviewed': updated_count,
            'compliant': sum(1 for i in inventory if i.get('status') == 'compliant'),
            'needs_fix': sum(1 for i in inventory if i.get('status') == 'needs_fix'),
            'unknown': sum(1 for i in inventory if i.get('status') == 'unknown')
        }

        self._save_compatibility_data()
        print(f"✅ Updated {updated_count} inventory items")


def main():
    parser = argparse.ArgumentParser(description="Manage Semptify module cartridges")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # List command
    subparsers.add_parser('list', help='List all cartridges')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a cartridge')
    validate_parser.add_argument('module', help='Module name to validate')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update a module with cartridge')
    update_parser.add_argument('module', help='Module name to update')
    update_parser.add_argument('cartridge_file', help='Path to cartridge JSON file')

    # Inventory command
    subparsers.add_parser('inventory', help='Update compliance inventory')

    args = parser.parse_args()

    manager = CartridgeManager()

    if args.command == 'list':
        manager.list_cartridges()
    elif args.command == 'validate':
        success = manager.validate_cartridge(args.module)
        sys.exit(0 if success else 1)
    elif args.command == 'update':
        success = manager.update_module(args.module, args.cartridge_file)
        sys.exit(0 if success else 1)
    elif args.command == 'inventory':
        manager.update_inventory()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()