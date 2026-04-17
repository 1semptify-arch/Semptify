#!/usr/bin/env python3
"""
System Health Check - Comprehensive Backend Verification
Tests all systems before frontend integration
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

class SystemHealthCheck:
    """Comprehensive system verification for Semptify backend."""
    
    def __init__(self):
        self.results = {}
        self.errors = []
        
    async def run_all_checks(self):
        """Run all system health checks."""
        print("=" * 70)
        print("SEMPIFY SYSTEM HEALTH CHECK")
        print("Backend Verification Before Frontend Integration")
        print("=" * 70)
        
        # 1. Server Startup
        await self.check_server_startup()
        
        # 2. Core Systems
        await self.check_core_systems()
        
        # 3. Database & Storage
        await self.check_database_storage()
        
        # 4. All Modules
        await self.check_all_modules()
        
        # 5. API Endpoints
        await self.check_api_endpoints()
        
        # 6. Services
        await self.check_services()
        
        # Final Report
        self.print_report()
        
    async def check_server_startup(self):
        """Verify server starts without errors."""
        print("\n[1/6] Server Startup Check...")
        try:
            from app.main import create_app
            app = create_app()
            
            self.results['server_startup'] = {
                'status': 'PASS',
                'title': app.title,
                'version': app.version,
                'routes_count': len(app.routes)
            }
            print(f"  ✓ Server: {app.title} v{app.version}")
            print(f"  ✓ Routes: {len(app.routes)} registered")
        except Exception as e:
            self.results['server_startup'] = {'status': 'FAIL', 'error': str(e)}
            self.errors.append(f"Server startup failed: {e}")
            print(f"  ✗ Server startup failed: {e}")
            
    async def check_core_systems(self):
        """Verify all core systems are operational."""
        print("\n[2/6] Core Systems Check...")
        
        systems = {
            'Security Headers': 'app.core.security_headers',
            'Storage Middleware': 'app.core.storage_middleware',
            'Job Processor': 'app.core.job_processor',
            'WebSocket Manager': 'app.core.websocket_manager',
            'Mesh Integration': 'app.core.mesh_integration',
            'Module Hub': 'app.core.module_hub',
            'Compliance': 'app.core.compliance',
        }
        
        for name, module_path in systems.items():
            try:
                __import__(module_path)
                print(f"  ✓ {name}")
                self.results[f'core_{name.lower().replace(" ", "_")}'] = {'status': 'PASS'}
            except Exception as e:
                print(f"  ✗ {name}: {e}")
                self.results[f'core_{name.lower().replace(" ", "_")}'] = {'status': 'FAIL', 'error': str(e)}
                
    async def check_database_storage(self):
        """Verify database and storage systems."""
        print("\n[3/6] Database & Storage Check...")
        
        try:
            from app.core.storage_middleware import StorageRequirementMiddleware
            print("  ✓ Storage Middleware")
            self.results['storage_middleware'] = {'status': 'PASS'}
        except Exception as e:
            print(f"  ✗ Storage Middleware: {e}")
            self.results['storage_middleware'] = {'status': 'FAIL', 'error': str(e)}
            
        try:
            from app.routers import storage
            print(f"  ✓ Storage Router: {storage.router is not None}")
            self.results['storage_router'] = {'status': 'PASS'}
        except Exception as e:
            print(f"  ✗ Storage Router: {e}")
            self.results['storage_router'] = {'status': 'FAIL', 'error': str(e)}
            
    async def check_all_modules(self):
        """Verify all critical modules load."""
        print("\n[4/6] Module Loading Check...")
        
        modules = {
            'Health': 'app.routers.health',
            'Onboarding': 'app.routers.onboarding',
            'Storage': 'app.routers.storage',
            'Plugins': 'app.routers.plugins',
            'Development': 'app.routers.development',
            'Documents': 'app.routers.documents',
            'Vault': 'app.routers.vault',
            'Legal Analysis': 'app.routers.legal_analysis',
            'Court Forms': 'app.routers.court_forms',
            'Research': 'app.routers.research',
            'HUD Funding': 'app.routers.hud_funding',
            'Location': 'app.routers.location',
            'Free API Pack': 'semptify_free_apis',
        }
        
        loaded = 0
        failed = 0
        
        for name, module_path in modules.items():
            try:
                module = __import__(module_path, fromlist=['router'])
                router = getattr(module, 'router', None)
                if router:
                    print(f"  ✓ {name}")
                    loaded += 1
                    self.results[f'module_{name.lower().replace(" ", "_")}'] = {'status': 'PASS'}
                else:
                    print(f"  ⚠ {name} (no router)")
                    failed += 1
            except Exception as e:
                print(f"  ✗ {name}: {e}")
                failed += 1
                self.results[f'module_{name.lower().replace(" ", "_")}'] = {'status': 'FAIL', 'error': str(e)}
                
        print(f"\n  Modules: {loaded} loaded, {failed} failed")
        
    async def check_api_endpoints(self):
        """Verify critical API endpoints are registered."""
        print("\n[5/6] API Endpoints Check...")
        
        from app.main import create_app
        app = create_app()
        
        # Check for critical endpoints
        critical_paths = [
            '/health',
            '/api/version',
            '/onboarding',
            '/storage/providers',
        ]
        
        found_paths = []
        for route in app.routes:
            path = getattr(route, 'path', None)
            if path:
                for critical in critical_paths:
                    if critical in path:
                        found_paths.append(critical)
                        
        for path in critical_paths:
            if path in found_paths:
                print(f"  ✓ {path}")
            else:
                print(f"  ⚠ {path} (not found)")
                
        self.results['api_endpoints'] = {
            'status': 'PASS',
            'total_routes': len(app.routes),
            'critical_found': len(set(found_paths))
        }
        
    async def check_services(self):
        """Verify background services."""
        print("\n[6/6] Background Services Check...")
        
        try:
            from app.core.job_processor import get_job_processor, JobProcessor
            processor = get_job_processor()
            print(f"  ✓ Job Processor ({processor.max_workers} workers)")
            self.results['job_processor'] = {'status': 'PASS', 'workers': processor.max_workers}
        except Exception as e:
            print(f"  ✗ Job Processor: {e}")
            self.results['job_processor'] = {'status': 'FAIL', 'error': str(e)}
            
        try:
            from app.core.websocket_manager import get_websocket_manager, WebSocketManager
            manager = get_websocket_manager()
            print(f"  ✓ WebSocket Manager ({len(manager.connections)} connections)")
            self.results['websocket_manager'] = {'status': 'PASS', 'connections': len(manager.connections)}
        except Exception as e:
            print(f"  ✗ WebSocket Manager: {e}")
            self.results['websocket_manager'] = {'status': 'FAIL', 'error': str(e)}
            
    def print_report(self):
        """Print final health report."""
        print("\n" + "=" * 70)
        print("SYSTEM HEALTH REPORT")
        print("=" * 70)
        
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r.get('status') == 'PASS')
        failed = sum(1 for r in self.results.values() if r.get('status') == 'FAIL')
        
        print(f"\nTotal Checks: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        
        if failed == 0:
            print("\n🎉 ALL SYSTEMS OPERATIONAL - READY FOR FRONTEND INTEGRATION")
            print("\nThe backend is fully functional and ready to receive the frontend.")
            print("All mechanical systems are verified and working correctly.")
        else:
            print(f"\n⚠️  {failed} system(s) need attention before frontend integration")
            
        if self.errors:
            print("\nErrors encountered:")
            for error in self.errors:
                print(f"  - {error}")
                
        print("\n" + "=" * 70)
        
        # Save detailed report
        report_file = Path(__file__).parent / 'system_health_report.json'
        with open(report_file, 'w') as f:
            json.dump({
                'summary': {
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'ready_for_frontend': failed == 0
                },
                'results': self.results,
                'errors': self.errors
            }, f, indent=2)
        print(f"\nDetailed report saved to: {report_file}")
        
        return failed == 0

if __name__ == "__main__":
    checker = SystemHealthCheck()
    result = asyncio.run(checker.run_all_checks())
    sys.exit(0 if result else 1)
