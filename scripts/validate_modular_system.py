#!/usr/bin/env python3
"""
Modular Component System Validation Script
========================================

Comprehensive validation of the modular component system including:
- Component file structure validation
- CSS integration validation
- HTML template validation
- API endpoint validation
- Event system validation
- Role-specific functionality validation
- Performance validation

Usage: python scripts/validate_modular_system.py
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
from urllib.parse import urljoin

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ModularSystemValidator:
    """Validates the complete modular component system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {
            "file_structure": {"passed": 0, "failed": 0, "issues": []},
            "css_integration": {"passed": 0, "failed": 0, "issues": []},
            "html_templates": {"passed": 0, "failed": 0, "issues": []},
            "api_endpoints": {"passed": 0, "failed": 0, "issues": []},
            "event_system": {"passed": 0, "failed": 0, "issues": []},
            "role_functionality": {"passed": 0, "failed": 0, "issues": []},
            "performance": {"passed": 0, "failed": 0, "issues": []}
        }
    
    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks"""
        print("Starting Modular Component System Validation...")
        print("=" * 60)
        
        # Run all validation methods
        self.validate_file_structure()
        self.validate_css_integration()
        self.validate_html_templates()
        self.validate_api_endpoints()
        self.validate_event_system()
        self.validate_role_functionality()
        self.validate_performance()
        
        # Generate summary
        self.generate_summary()
        
        return self.results
    
    def validate_file_structure(self) -> None:
        """Validate that all required component files exist"""
        print("\n1. Validating File Structure...")
        
        required_files = [
            # Design system
            "design-system/index.css",
            "design-system/index.js",
            
            # Function group components
            "design-system/components/function-groups/capture/upload-zone.html",
            "design-system/components/function-groups/capture/upload-zone.css",
            "design-system/components/function-groups/capture/quick-input.html",
            "design-system/components/function-groups/capture/quick-input.css",
            "design-system/components/function-groups/capture/voice-intake.html",
            "design-system/components/function-groups/capture/voice-intake.css",
            "design-system/components/function-groups/capture/index.css",
            
            "design-system/components/function-groups/understand/timeline-view.html",
            "design-system/components/function-groups/understand/timeline-view.css",
            "design-system/components/function-groups/understand/rights-analysis.html",
            "design-system/components/function-groups/understand/rights-analysis.css",
            "design-system/components/function-groups/understand/risk-detection.html",
            "design-system/components/function-groups/understand/risk-detection.css",
            "design-system/components/function-groups/understand/index.css",
            
            "design-system/components/function-groups/plan/action-list.html",
            "design-system/components/function-groups/plan/action-list.css",
            "design-system/components/function-groups/plan/deadline-tracker.html",
            "design-system/components/function-groups/plan/deadline-tracker.css",
            "design-system/components/function-groups/plan/next-step-card.html",
            "design-system/components/function-groups/plan/next-step-card.css",
            "design-system/components/function-groups/plan/index.css",
            
            # Role-specific components
            "design-system/components/function-groups/role-specific/tenant/dashboard.html",
            "design-system/components/function-groups/role-specific/tenant/case-summary.html",
            "design-system/components/function-groups/role-specific/tenant/emergency-actions.html",
            "design-system/components/function-groups/role-specific/tenant/index.css",
            
            "design-system/components/function-groups/role-specific/advocate/dashboard.html",
            "design-system/components/function-groups/role-specific/advocate/client-management.html",
            "design-system/components/function-groups/role-specific/advocate/index.css",
            
            "design-system/components/function-groups/role-specific/legal/dashboard.html",
            "design-system/components/function-groups/role-specific/legal/index.css",
            
            "design-system/components/function-groups/role-specific/admin/dashboard.html",
            "design-system/components/function-groups/role-specific/admin/index.css",
            
            # Onboarding components
            "design-system/components/function-groups/onboarding/welcome.html",
            "design-system/components/function-groups/onboarding/demo.html",
            "design-system/components/function-groups/onboarding/onboarding-tracker.html",
            
            # Backend integration
            "app/routers/components.py",
            
            # Role pages
            "app/templates/pages/tenant_dashboard.html",
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            if full_path.exists():
                self.results["file_structure"]["passed"] += 1
                print(f"  + {file_path}")
            else:
                self.results["file_structure"]["failed"] += 1
                self.results["file_structure"]["issues"].append(f"Missing file: {file_path}")
                print(f"  - {file_path} (MISSING)")
    
    def validate_css_integration(self) -> None:
        """Validate CSS integration and imports"""
        print("\n2. Validating CSS Integration...")
        
        # Check main design system CSS
        main_css_path = project_root / "design-system/components/index.css"
        if main_css_path.exists():
            with open(main_css_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            # Check for required imports
            required_imports = [
                "function-groups/capture/index.css",
                "function-groups/understand/index.css",
                "function-groups/plan/index.css",
                "function-groups/role-specific/tenant/index.css",
                "function-groups/role-specific/advocate/index.css",
                "function-groups/role-specific/legal/index.css",
                "function-groups/role-specific/admin/index.css"
            ]
            
            for import_path in required_imports:
                if import_path in css_content:
                    self.results["css_integration"]["passed"] += 1
                    print(f"  + {import_path}")
                else:
                    self.results["css_integration"]["failed"] += 1
                    self.results["css_integration"]["issues"].append(f"Missing CSS import: {import_path}")
                    print(f"  - {import_path} (MISSING)")
            
            # Check for CSS variables
            required_variables = [
                "--color-tenant-primary",
                "--color-advocate-primary",
                "--color-legal-primary",
                "--color-admin-primary"
            ]
            
            for variable in required_variables:
                if variable in css_content:
                    self.results["css_integration"]["passed"] += 1
                    print(f"  + {variable}")
                else:
                    self.results["css_integration"]["failed"] += 1
                    self.results["css_integration"]["issues"].append(f"Missing CSS variable: {variable}")
                    print(f"  - {variable} (MISSING)")
        else:
            self.results["css_integration"]["failed"] += 1
            self.results["css_integration"]["issues"].append("Main CSS file not found")
            print("  - design-system/components/index.css (MISSING)")
    
    def validate_html_templates(self) -> None:
        """Validate HTML template structure and includes"""
        print("\n3. Validating HTML Templates...")
        
        # Check tenant dashboard template
        tenant_dashboard_path = project_root / "app/templates/pages/tenant_dashboard.html"
        if tenant_dashboard_path.exists():
            with open(tenant_dashboard_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Check for required includes
            required_includes = [
                "design-system/index.css",
                "workspace-stage-model.js",
                "role-specific/tenant/dashboard.html",
                "role-specific/tenant/emergency-actions.html",
                "role-specific/tenant/case-summary.html"
            ]
            
            for include in required_includes:
                if include in html_content:
                    self.results["html_templates"]["passed"] += 1
                    print(f"  + {include}")
                else:
                    self.results["html_templates"]["failed"] += 1
                    self.results["html_templates"]["issues"].append(f"Missing include: {include}")
                    print(f"  - {include} (MISSING)")
            
            # Check for required elements
            required_elements = [
                "class=\"tenant-dashboard-page\"",
                "class=\"workspace-stage-panel\"",
                "class=\"emergency-actions\"",
                "class=\"dashboard-main\"",
                "class=\"dashboard-sidebar\""
            ]
            
            for element in required_elements:
                if element in html_content:
                    self.results["html_templates"]["passed"] += 1
                    print(f"  + {element}")
                else:
                    self.results["html_templates"]["failed"] += 1
                    self.results["html_templates"]["issues"].append(f"Missing element: {element}")
                    print(f"  - {element} (MISSING)")
        else:
            self.results["html_templates"]["failed"] += 1
            self.results["html_templates"]["issues"].append("Tenant dashboard template not found")
            print("  - app/templates/pages/tenant_dashboard.html (MISSING)")
    
    def validate_api_endpoints(self) -> None:
        """Validate API endpoints are accessible"""
        print("\n4. Validating API Endpoints...")
        
        endpoints = [
            "/api/components/config/tenant",
            "/api/components/config/advocate",
            "/api/components/config/legal",
            "/api/components/config/admin",
            "/api/components/workspace-stage",
            "/api/components/next-step"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    self.results["api_endpoints"]["passed"] += 1
                    print(f"  + {endpoint} ({response.status_code})")
                else:
                    self.results["api_endpoints"]["failed"] += 1
                    self.results["api_endpoints"]["issues"].append(f"Endpoint error: {endpoint} ({response.status_code})")
                    print(f"  - {endpoint} ({response.status_code})")
            except requests.exceptions.RequestException as e:
                self.results["api_endpoints"]["failed"] += 1
                self.results["api_endpoints"]["issues"].append(f"Endpoint unreachable: {endpoint} ({str(e)})")
                print(f"  - {endpoint} (UNREACHABLE)")
    
    def validate_event_system(self) -> None:
        """Validate event system functionality"""
        print("\n5. Validating Event System...")
        
        # Test component event endpoints
        event_endpoints = [
            ("/api/components/capture/upload", {
                "component_id": "test_upload",
                "role": "tenant",
                "timestamp": "2026-04-16T20:00:00Z",
                "event_type": "capture-upload",
                "files": [{"name": "test.pdf", "size": 1024}],
                "total_size": 1024
            }),
            ("/api/components/understand/timeline", {
                "component_id": "test_timeline",
                "role": "tenant",
                "timestamp": "2026-04-16T20:00:00Z",
                "event_type": "understand-timeline-select",
                "event_id": "timeline_123",
                "event_data": {"date": "2026-04-15"}
            }),
            ("/api/components/plan/action", {
                "component_id": "test_action",
                "role": "tenant",
                "timestamp": "2026-04-16T20:00:00Z",
                "event_type": "plan-action-select",
                "action_id": "action_123",
                "action_data": {"action": "file_response"}
            })
        ]
        
        for endpoint, payload in event_endpoints:
            try:
                response = requests.post(f"{self.base_url}{endpoint}", json=payload, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if "success" in data and data["success"]:
                        self.results["event_system"]["passed"] += 1
                        print(f"  + {endpoint} (SUCCESS)")
                    else:
                        self.results["event_system"]["failed"] += 1
                        self.results["event_system"]["issues"].append(f"Event failed: {endpoint}")
                        print(f"  - {endpoint} (FAILED)")
                else:
                    self.results["event_system"]["failed"] += 1
                    self.results["event_system"]["issues"].append(f"Event error: {endpoint} ({response.status_code})")
                    print(f"  - {endpoint} ({response.status_code})")
            except requests.exceptions.RequestException as e:
                self.results["event_system"]["failed"] += 1
                self.results["event_system"]["issues"].append(f"Event unreachable: {endpoint} ({str(e)})")
                print(f"  - {endpoint} (UNREACHABLE)")
    
    def validate_role_functionality(self) -> None:
        """Validate role-specific functionality"""
        print("\n6. Validating Role Functionality...")
        
        # Test role-specific endpoints
        role_endpoints = [
            ("/api/components/tenant/emergency-action", {
                "component_id": "test_emergency",
                "emergency_id": "emergency_123",
                "action": "call_hotline"
            }),
            ("/api/components/advocate/handoff-client", {
                "component_id": "test_handoff",
                "client_id": "client_123",
                "target_role": "legal"
            }),
            ("/api/components/legal/start-review", {
                "component_id": "test_review",
                "case_id": "case_123",
                "review_type": "document_analysis"
            }),
            ("/api/components/admin/system-maintenance", {
                "component_id": "test_maintenance",
                "maintenance_type": "database_backup"
            })
        ]
        
        for endpoint, params in role_endpoints:
            try:
                response = requests.post(f"{self.base_url}{endpoint}", params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if "success" in data and data["success"]:
                        self.results["role_functionality"]["passed"] += 1
                        print(f"  + {endpoint} (SUCCESS)")
                    else:
                        self.results["role_functionality"]["failed"] += 1
                        self.results["role_functionality"]["issues"].append(f"Role action failed: {endpoint}")
                        print(f"  - {endpoint} (FAILED)")
                else:
                    self.results["role_functionality"]["failed"] += 1
                    self.results["role_functionality"]["issues"].append(f"Role action error: {endpoint} ({response.status_code})")
                    print(f"  - {endpoint} ({response.status_code})")
            except requests.exceptions.RequestException as e:
                self.results["role_functionality"]["failed"] += 1
                self.results["role_functionality"]["issues"].append(f"Role action unreachable: {endpoint} ({str(e)})")
                print(f"  - {endpoint} (UNREACHABLE)")
    
    def validate_performance(self) -> None:
        """Validate system performance"""
        print("\n7. Validating Performance...")
        
        # Test response times
        endpoints_to_test = [
            "/api/components/config/tenant",
            "/api/components/workspace-stage",
            "/api/components/next-step"
        ]
        
        total_time = 0
        for endpoint in endpoints_to_test:
            try:
                start_time = time.time()
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                end_time = time.time()
                response_time = end_time - start_time
                total_time += response_time
                
                if response.status_code == 200 and response_time < 2.0:  # 2 second threshold
                    self.results["performance"]["passed"] += 1
                    print(f"  + {endpoint} ({response_time:.2f}s)")
                else:
                    self.results["performance"]["failed"] += 1
                    self.results["performance"]["issues"].append(f"Slow response: {endpoint} ({response_time:.2f}s)")
                    print(f"  - {endpoint} ({response_time:.2f}s - SLOW)")
            except requests.exceptions.RequestException as e:
                self.results["performance"]["failed"] += 1
                self.results["performance"]["issues"].append(f"Performance test failed: {endpoint} ({str(e)})")
                print(f"  - {endpoint} (FAILED)")
        
        # Calculate average response time
        if endpoints_to_test:
            avg_time = total_time / len(endpoints_to_test)
            print(f"  Average response time: {avg_time:.2f}s")
            
            if avg_time < 1.0:
                self.results["performance"]["passed"] += 1
                print(f"  + Average response time acceptable")
            else:
                self.results["performance"]["failed"] += 1
                self.results["performance"]["issues"].append(f"Average response time too slow: {avg_time:.2f}s")
                print(f"  - Average response time too slow: {avg_time:.2f}s")
    
    def generate_summary(self) -> None:
        """Generate validation summary"""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed
            
            print(f"\n{category.upper()}:")
            print(f"  Passed: {passed}")
            print(f"  Failed: {failed}")
            
            if results["issues"]:
                print("  Issues:")
                for issue in results["issues"][:3]:  # Show first 3 issues
                    print(f"    - {issue}")
                if len(results["issues"]) > 3:
                    print(f"    ... and {len(results['issues']) - 3} more issues")
        
        print(f"\nOVERALL:")
        print(f"  Total Passed: {total_passed}")
        print(f"  Total Failed: {total_failed}")
        
        if total_failed == 0:
            print("  Status: ALL TESTS PASSED")
            print("\n  Modular Component System is ready for production!")
        else:
            print("  Status: SOME TESTS FAILED")
            print(f"\n  Please address {total_failed} issues before deployment.")
        
        # Save results to file
        results_file = project_root / "validation_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: {results_file}")


def main():
    """Main validation function"""
    # Check if server is running
    base_url = "http://localhost:8000"
    
    try:
        response = requests.get(f"{base_url}/api/version", timeout=5)
        if response.status_code == 200:
            print(f"Server is running at {base_url}")
        else:
            print(f"Server responded with status {response.status_code}")
    except requests.exceptions.RequestException:
        print(f"Server is not running at {base_url}")
        print("Please start the server with: python -m uvicorn app.main:fastapi_app --reload")
        return
    
    # Run validation
    validator = ModularSystemValidator(base_url)
    results = validator.validate_all()
    
    # Exit with appropriate code
    total_failed = sum(category["failed"] for category in results.values())
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
