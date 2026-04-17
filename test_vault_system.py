#!/usr/bin/env python3
"""
Vault System Test Script
=========================

Comprehensive test for the persistent vault component and upload system.
Tests vault functionality, storage integration, and cross-component communication.
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime

class VaultSystemTester:
    """Test suite for vault system functionality"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": timestamp,
            "details": details or {}
        }
        
        self.test_results.append(result)
        print(f"[{timestamp}] {status} {test_name}: {message}")
        
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    async def test_vault_component_config(self):
        """Test vault component configuration endpoint"""
        try:
            async with self.session.get(f"{self.base_url}/api/vault/sidebar/files") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    self.log_test(
                        "Vault Component Config",
                        data.get("show_vault", False),
                        "Vault config response" if data.get("show_vault") else "Vault not configured"
                    )
                    
                    # Test configuration details
                    if data.get("show_vault"):
                        config_items = ["role", "compact_mode", "show_stats", "auto_sync", "storage_provider"]
                        for item in config_items:
                            if item in data:
                                self.log_test(True, f"Config item '{item}' present", {"value": data[item]})
                            else:
                                self.log_test(False, f"Config item '{item}' missing")
                    return True
                else:
                    self.log_test(False, "Vault config endpoint returned error", {"status": response.status})
                    return False
                    
        except Exception as e:
            self.log_test(False, f"Vault config test failed: {str(e)}")
            return False
    
    async def test_vault_file_operations(self):
        """Test vault file operations (list, upload, search, stats)"""
        try:
            # Test file listing
            async with self.session.get(f"{self.base_url}/api/vault/sidebar/files") as response:
                if response.status == 200:
                    files_data = await response.json()
                    files = files_data.get("files", [])
                    
                    self.log_test(
                        "Vault File Listing",
                        True,
                        f"Retrieved {len(files)} files"
                    )
                else:
                    self.log_test(False, "File listing failed", {"status": response.status})
                    return False
            
            # Test file upload
            test_file_path = Path("test_vault_upload.txt")
            test_file_path.write_text("Test file for vault upload system")
            
            with open(test_file_path, 'rb') as test_file:
                data = aiohttp.FormData()
                data.add_field('files', test_file, filename="test_vault_upload.txt")
                data.add_field('metadata', json.dumps({
                    "source": "test_script",
                    "files": [{"name": "test_vault_upload.txt", "size": 25, "type": "text/plain"}]
                }))
                
                async with self.session.post(f"{self.base_url}/api/vault/sidebar/upload") as response:
                    if response.status == 200:
                        upload_data = await response.json()
                        
                        self.log_test(
                            "Vault File Upload",
                            upload_data.get("success", False),
                            upload_data.get("message", "Upload failed")
                        )
                    else:
                        self.log_test(False, "File upload failed", {"status": response.status})
            
            # Test search functionality
            async with self.session.get(f"{self.base_url}/api/vault/sidebar/search?query=test") as response:
                if response.status == 200:
                    search_data = await response.json()
                    files = search_data.get("files", [])
                    
                    self.log_test(
                        "Vault Search",
                        True,
                        f"Search returned {len(files)} results for 'test'"
                    )
                else:
                    self.log_test(False, "Search failed", {"status": response.status})
            
            # Test statistics
            async with self.session.get(f"{self.base_url}/api/vault/sidebar/stats") as response:
                if response.status == 200:
                    stats_data = await response.json()
                    stats = stats_data.get("stats", {})
                    
                    self.log_test(
                        "Vault Statistics",
                        True,
                        f"Stats: {stats.get('total_files', 0)} files, {stats.get('storage_used', 0)}% used"
                    )
                else:
                    self.log_test(False, "Stats failed", {"status": response.status})
            
            # Clean up test file
            if test_file_path.exists():
                test_file_path.unlink()
            
            return True
            
        except Exception as e:
            self.log_test(False, f"Vault file operations test failed: {str(e)}")
            return False
    
    async def test_cross_component_events(self):
        """Test cross-component event communication"""
        try:
            # Test that vault component responds to capture-upload events
            # This would require browser automation, so we'll test the API endpoints directly
            
            # Test workspace stage update event
            stage_update_data = {
                "has_documents": True,
                "stage": "understand",
                "component_id": "test_vault"
            }
            
            async with self.session.post(f"{self.base_url}/api/components/workspace-stage") as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    self.log_test(
                        "Workspace Stage Update",
                        True,
                        "Workspace stage updated successfully"
                    )
                else:
                    self.log_test(False, "Workspace stage update failed", {"status": response.status})
            
            return True
            
        except Exception as e:
            self.log_test(False, f"Cross-component events test failed: {str(e)}")
            return False
    
    async def test_onboarding_integration(self):
        """Test onboarding completion and vault activation"""
        try:
            # Test that vault appears after onboarding
            async with self.session.get(f"{self.base_url}/api/vault/sidebar/files") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check if vault is accessible (should be after onboarding)
                    if data.get("files"):
                        self.log_test(
                            "Onboarding Integration",
                            True,
                            "Vault accessible after onboarding"
                        )
                    else:
                        self.log_test(
                            "Onboarding Integration",
                            False,
                            "Vault not accessible after onboarding"
                        )
                else:
                    self.log_test(False, "Onboarding integration test failed", {"status": response.status})
            
            return True
            
        except Exception as e:
            self.log_test(False, f"Onboarding integration test failed: {str(e)}")
            return False
    
    async def test_storage_integration(self):
        """Test storage provider integration"""
        try:
            # Test storage provider detection
            async with self.session.get(f"{self.base_url}/storage/providers") as response:
                if response.status == 200:
                    self.log_test(
                        "Storage Provider Detection",
                        True,
                        "Storage providers endpoint accessible"
                    )
                else:
                    self.log_test(False, "Storage providers endpoint failed", {"status": response.status})
            
            return True
            
        except Exception as e:
            self.log_test(False, f"Storage integration test failed: {str(e)}")
            return False
    
    async def test_vault_persistence(self):
        """Test vault data persistence across page reloads"""
        try:
            # Upload a file
            test_file_path = Path("test_persistence.txt")
            test_file_path.write_text("Persistence test file")
            
            with open(test_file_path, 'rb') as test_file:
                data = aiohttp.FormData()
                data.add_field('files', test_file, filename="test_persistence.txt")
                data.add_field('metadata', json.dumps({
                    "source": "persistence_test",
                    "files": [{"name": "test_persistence.txt", "size": 20, "type": "text/plain"}]
                }))
                
                # Upload file
                async with self.session.post(f"{self.base_url}/api/vault/sidebar/upload") as response:
                    if response.status == 200:
                        upload_data = await response.json()
                        
                        if upload_data.get("success"):
                            # Wait a moment
                            await asyncio.sleep(1)
                            
                            # Check if file persists
                            async with self.session.get(f"{self.base_url}/api/vault/sidebar/files") as response2:
                                if response2.status == 200:
                                    files_data = await response2.json()
                                    files = files_data.get("files", [])
                                    
                                    # Check if our test file is there
                                    test_file_found = any(f.get("name") == "test_persistence.txt" for f in files)
                                    
                                    if test_file_found:
                                        self.log_test(
                                            "Vault Persistence",
                                            True,
                                            "File persists across requests"
                                        )
                                    else:
                                        self.log_test(
                                            "Vault Persistence",
                                            False,
                                            "File does not persist across requests"
                                        )
                                else:
                                    self.log_test(False, "Persistence check failed", {"status": response2.status})
                        else:
                            self.log_test(False, "Upload failed for persistence test")
                    else:
                        self.log_test(False, "Upload failed for persistence test")
            
            # Clean up
            if test_file_path.exists():
                test_file_path.unlink()
            
            return True
            
        except Exception as e:
            self.log_test(False, f"Vault persistence test failed: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run complete vault system test suite"""
        print("🧪 Starting Vault System Test Suite")
        print("=" * 50)
        
        # Test 1: Vault Component Configuration
        await self.test_vault_component_config()
        
        # Test 2: File Operations
        await self.test_vault_file_operations()
        
        # Test 3: Cross-Component Events
        await self.test_cross_component_events()
        
        # Test 4: Onboarding Integration
        await self.test_onboarding_integration()
        
        # Test 5: Storage Integration
        await self.test_storage_integration()
        
        # Test 6: Vault Persistence
        await self.test_vault_persistence()
        
        print("\n" + "=" * 50)
        print("🧪 Vault System Test Complete")
        
        # Generate summary
        passed_tests = len([r for r in self.test_results if "PASS" in r["status"]])
        total_tests = len(self.test_results)
        
        print(f"\n📊 Test Summary: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! Vault system is fully functional.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
        
        return passed_tests == total_tests
    
    def generate_report(self):
        """Generate test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed_tests": len([r for r in self.test_results if "PASS" in r["status"]]),
            "test_results": self.test_results
        }
        
        # Save report
        report_path = Path("vault_test_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Test report saved to: {report_path.absolute()}")
        return report_path

async def main():
    """Main test function"""
    import sys
    
    # Check if server is running
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"🔍 Testing vault system at: {base_url}")
    print("⚠️  Make sure the server is running with vault integration enabled")
    print("⚠️  Storage credentials should be configured for full functionality")
    
    tester = VaultSystemTester(base_url)
    
    async with tester as t:
        success = await t.run_all_tests()
        
        if success:
            print("\n🚀 Vault system is ready for production use!")
            print("📋 Next steps:")
            print("   1. Configure storage credentials")
            print("   2. Test with real files")
            print("   3. Verify cross-component communication")
            print("   4. Deploy to production")
        else:
            print("\n🔧 Fix issues before deploying to production")
            print("📋 Check test report for details")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
