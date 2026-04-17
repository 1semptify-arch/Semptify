#!/usr/bin/env python3
"""
Vault System Validation Script
============================

Comprehensive validation of vault component implementation.
Tests file structure, integration, and configuration without requiring server.
"""

import os
import json
from pathlib import Path
from datetime import datetime

class VaultSystemValidator:
    """Validate vault system implementation"""
    
    def __init__(self):
        self.validation_results = []
        
    def log_validation(self, test_name, success, message, details=None):
        """Log validation result"""
        status = "✅ PASS" if success else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": timestamp,
            "details": details or {}
        }
        
        self.validation_results.append(result)
        print(f"[{timestamp}] {status} {test_name}: {message}")
        
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    def validate_vault_component_structure(self):
        """Validate vault component file structure"""
        try:
            vault_component_path = Path("design-system/components/function-groups/vault/vault-sidebar-clean.html")
            
            if not vault_component_path.exists():
                self.log_validation(
                    "Vault Component Structure",
                    False,
                    "Vault component file not found"
                )
                return False
            
            # Read component content
            with open(vault_component_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required elements
            required_elements = [
                'class="vault-sidebar"',
                'id="{{ component_id }}"',
                'data-role="{{ role }}"',
                'onclick="handleVaultUpload(event)"',
                'onclick="filterByCategory',
                'onclick="searchVault(event)"',
                'id="vault_files_container"'
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in content:
                    missing_elements.append(element)
            
            if missing_elements:
                self.log_validation(
                    "Vault Component Structure",
                    False,
                    f"Missing required elements: {', '.join(missing_elements)}"
                )
            else:
                self.log_validation(
                    "Vault Component Structure",
                    True,
                    "All required elements present"
                )
            
            # Check for CSS syntax issues
            css_issues = self._check_css_syntax(content)
            if css_issues:
                self.log_validation(
                    "Vault Component CSS",
                    False,
                    f"CSS syntax issues found: {', '.join(css_issues)}"
                )
            else:
                self.log_validation(
                    "Vault Component CSS",
                    True,
                    "CSS syntax is valid"
                )
            
            # Check for JavaScript functions
            js_functions = [
                'function initializeVault',
                'function handleVaultUpload',
                'function searchVault',
                'function filterByCategory',
                'function updateVaultUI',
                'function setupVaultEventListeners'
            ]
            
            missing_functions = []
            for func in js_functions:
                if func not in content:
                    missing_functions.append(func)
            
            if missing_functions:
                self.log_validation(
                    "Vault Component JavaScript",
                    False,
                    f"Missing JavaScript functions: {', '.join(missing_functions)}"
                )
            else:
                self.log_validation(
                    "Vault Component JavaScript",
                    True,
                    "All required JavaScript functions present"
                )
            
            return len(missing_elements) == 0 and len(missing_functions) == 0 and len(css_issues) == 0
            
        except Exception as e:
            self.log_validation(
                "Vault Component Structure",
                False,
                f"Validation failed: {str(e)}"
            )
            return False
    
    def validate_backend_integration(self):
        """Validate backend vault router integration"""
        try:
            vault_router_path = Path("app/routers/vault.py")
            
            if not vault_router_path.exists():
                self.log_validation(
                    "Vault Backend Integration",
                    False,
                    "Vault router file not found"
                )
                return False
            
            # Read router content
            with open(vault_router_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required endpoints
            required_endpoints = [
                '@router.get("/sidebar/files")',
                '@router.post("/sidebar/upload")',
                '@router.get("/sidebar/stats")',
                '@router.get("/sidebar/search")'
            ]
            
            missing_endpoints = []
            for endpoint in required_endpoints:
                if endpoint not in content:
                    missing_endpoints.append(endpoint)
            
            if missing_endpoints:
                self.log_validation(
                    "Vault Backend Integration",
                    False,
                    f"Missing required endpoints: {', '.join(missing_endpoints)}"
                )
            else:
                self.log_validation(
                    "Vault Backend Integration",
                    True,
                    "All required endpoints present"
                )
            
            # Check for proper imports
            required_imports = [
                'from fastapi import APIRouter',
                'from fastapi import UploadFile, File, Form',
                'from pydantic import BaseModel'
            ]
            
            missing_imports = []
            for import_stmt in required_imports:
                if import_stmt not in content:
                    missing_imports.append(import_stmt)
            
            if missing_imports:
                self.log_validation(
                    "Vault Backend Imports",
                    False,
                    f"Missing required imports: {', '.join(missing_imports)}"
                )
            else:
                self.log_validation(
                    "Vault Backend Imports",
                    True,
                    "All required imports present"
                )
            
            return len(missing_endpoints) == 0 and len(missing_imports) == 0
            
        except Exception as e:
            self.log_validation(
                "Vault Backend Integration",
                False,
                    f"Validation failed: {str(e)}"
            )
            return False
    
    def validate_page_integration(self):
        """Validate vault component integration in pages"""
        try:
            tenant_dashboard_path = Path("app/templates/pages/tenant_dashboard.html")
            
            if not tenant_dashboard_path.exists():
                self.log_validation(
                    "Page Integration",
                    False,
                    "Tenant dashboard not found"
                )
                return False
            
            # Read dashboard content
            with open(tenant_dashboard_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for vault component inclusion
            if 'vault-sidebar-clean.html' not in content:
                self.log_validation(
                    "Page Integration",
                    False,
                    "Vault component not included in tenant dashboard"
                )
            else:
                self.log_validation(
                    "Page Integration",
                    True,
                    "Vault component included in tenant dashboard"
                )
            
            # Check for responsive layout adjustments
            required_css = [
                'margin-right: 320px',
                '.vault-sidebar {',
                '.dashboard-content {'
            ]
            
            missing_css = []
            for css in required_css:
                if css not in content:
                    missing_css.append(css)
            
            if missing_css:
                self.log_validation(
                    "Page Responsive Layout",
                    False,
                    f"Missing responsive CSS: {', '.join(missing_css)}"
                )
            else:
                self.log_validation(
                    "Page Responsive Layout",
                    True,
                    "Responsive layout adjustments present"
                )
            
            return 'vault-sidebar-clean.html' in content and len(missing_css) == 0
            
        except Exception as e:
            self.log_validation(
                "Page Integration",
                False,
                f"Validation failed: {str(e)}"
            )
            return False
    
    def validate_main_app_integration(self):
        """Validate vault router integration in main app"""
        try:
            main_app_path = Path("app/main.py")
            
            if not main_app_path.exists():
                self.log_validation(
                    "Main App Integration",
                    False,
                    "Main app file not found"
                )
                return False
            
            # Read main app content
            with open(main_app_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for vault router inclusion
            if 'from app.routers import vault' not in content:
                self.log_validation(
                    "Main App Integration",
                    False,
                    "Vault router not imported in main app"
                )
            else:
                self.log_validation(
                    "Main App Integration",
                    True,
                    "Vault router imported in main app"
                )
            
            # Check for vault router inclusion
            if 'fastapi_app.include_router(vault.router' not in content:
                self.log_validation(
                    "Main App Integration",
                    False,
                    "Vault router not included in main app"
                )
            else:
                self.log_validation(
                    "Main App Integration",
                    True,
                    "Vault router included in main app"
                )
            
            return 'from app.routers import vault' in content and 'fastapi_app.include_router(vault.router' in content
            
        except Exception as e:
            self.log_validation(
                "Main App Integration",
                False,
                f"Validation failed: {str(e)}"
            )
            return False
    
    def validate_oauth_storage_integration(self):
        """Validate OAuth storage integration"""
        try:
            # Check for storage router
            storage_router_path = Path("app/routers/storage.py")
            
            if not storage_router_path.exists():
                self.log_validation(
                    "OAuth Storage Integration",
                    False,
                    "Storage router not found"
                )
                return False
            
            # Check for vault service
            vault_service_path = Path("app/services/vault_upload_service.py")
            
            if not vault_service_path.exists():
                self.log_validation(
                    "OAuth Storage Integration",
                    False,
                    "Vault service not found"
                )
            else:
                self.log_validation(
                    "OAuth Storage Integration",
                    True,
                    "Vault service found"
                )
            
            # Read storage router content
            with open(storage_router_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for OAuth providers
            oauth_providers = ['google_drive', 'dropbox', 'onedrive']
            found_providers = []
            
            for provider in oauth_providers:
                if provider in content:
                    found_providers.append(provider)
            
            if len(found_providers) == 0:
                self.log_validation(
                    "OAuth Storage Integration",
                    False,
                    "No OAuth providers found in storage router"
                )
            else:
                self.log_validation(
                    "OAuth Storage Integration",
                    True,
                    f"OAuth providers found: {', '.join(found_providers)}"
                )
            
            return len(found_providers) > 0 and vault_service_path.exists()
            
        except Exception as e:
            self.log_validation(
                "OAuth Storage Integration",
                False,
                f"Validation failed: {str(e)}"
            )
            return False
    
    def validate_credentials_workbook(self):
        """Validate credentials workbook is available"""
        try:
            workbook_path = Path("CREDENTIALS_SETUP_WORKBOOK_REVEALED.html")
            
            if not workbook_path.exists():
                self.log_validation(
                    "Credentials Workbook",
                    False,
                    "Revealed credentials workbook not found"
                )
                return False
            
            # Read workbook content
            with open(workbook_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for credential fields
            credential_fields = [
                'GOOGLE_DRIVE_CLIENT_ID',
                'GOOGLE_DRIVE_CLIENT_SECRET',
                'DROPBOX_APP_KEY',
                'DROPBOX_APP_SECRET',
                'ONEDRIVE_CLIENT_ID',
                'ONEDRIVE_CLIENT_SECRET',
                'R2_ACCOUNT_ID',
                'R2_ACCESS_KEY_ID',
                'R2_SECRET_ACCESS_KEY',
                'R2_BUCKET_NAME'
            ]
            
            found_fields = []
            for field in credential_fields:
                if field in content:
                    found_fields.append(field)
            
            if len(found_fields) == 0:
                self.log_validation(
                    "Credentials Workbook",
                    False,
                    "No credential fields found in workbook"
                )
            else:
                self.log_validation(
                    "Credentials Workbook",
                    True,
                    f"Found {len(found_fields)} credential fields"
                )
            
            # Check if fields are revealed (not password type)
            if 'type="password"' in content:
                self.log_validation(
                    "Credentials Workbook",
                    False,
                    "Password fields still present (not revealed)"
                )
            else:
                self.log_validation(
                    "Credentials Workbook",
                    True,
                    "All credential fields revealed"
                )
            
            return len(found_fields) > 0 and 'type="password"' not in content
            
        except Exception as e:
            self.log_validation(
                "Credentials Workbook",
                False,
                f"Validation failed: {str(e)}"
            )
            return False
    
    def _check_css_syntax(self, content):
        """Check for common CSS syntax issues"""
        css_issues = []
        
        # Check for invalid CSS selectors
        if 'var(--primary-tenant' in content and 'var(--primary-advocate' not in content:
            css_issues.append("Missing role-specific CSS variables")
        
        # Check for unclosed CSS rules
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            css_issues.append(f"Unmatched CSS braces: {open_braces} open, {close_braces} close")
        
        # Check for invalid at-rules
        if '@media (max-width:768px)' in content:
            css_issues.append("Invalid media query syntax")
        
        return css_issues
    
    def run_all_validations(self):
        """Run complete vault system validation"""
        print("🧪 Starting Vault System Validation")
        print("=" * 50)
        
        # Validation 1: Vault Component Structure
        self.validate_vault_component_structure()
        
        # Validation 2: Backend Integration
        self.validate_backend_integration()
        
        # Validation 3: Page Integration
        self.validate_page_integration()
        
        # Validation 4: Main App Integration
        self.validate_main_app_integration()
        
        # Validation 5: OAuth Storage Integration
        self.validate_oauth_storage_integration()
        
        # Validation 6: Credentials Workbook
        self.validate_credentials_workbook()
        
        print("\n" + "=" * 50)
        print("🧪 Vault System Validation Complete")
        
        # Generate summary
        passed_validations = len([r for r in self.validation_results if "PASS" in r["status"]])
        total_validations = len(self.validation_results)
        
        print(f"\n📊 Validation Summary: {passed_validations}/{total_validations} validations passed")
        
        if passed_validations == total_validations:
            print("🎉 All validations passed! Vault system is properly implemented.")
        else:
            print("⚠️  Some validations failed. Check details above.")
        
        return passed_validations == total_validations
    
    def generate_report(self):
        """Generate validation report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_validations": len(self.validation_results),
            "passed_validations": len([r for r in self.validation_results if "PASS" in r["status"]]),
            "validation_results": self.validation_results
        }
        
        # Save report
        report_path = Path("vault_validation_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Validation report saved to: {report_path.absolute()}")
        return report_path

def main():
    """Main validation function"""
    print("🔍 Validating Vault System Implementation")
    print("📋 This validates the vault system without requiring server to be running")
    
    validator = VaultSystemValidator()
    
    success = validator.run_all_validations()
    
    if success:
        print("\n🚀 Vault system is properly implemented and ready for testing!")
        print("📋 Next steps:")
        print("   1. Configure storage credentials")
        print("   2. Start the server")
        print("   3. Test with real files")
        print("   4. Deploy to production")
    else:
        print("\n🔧 Fix implementation issues before testing")
        print("📋 Check validation report for details")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
