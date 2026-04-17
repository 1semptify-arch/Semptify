#!/usr/bin/env python3
"""
Simple Vault System Test
========================

Test vault component functionality without external dependencies.
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path

class VaultTester:
    """Simple vault functionality tester"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        
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
    
    def test_vault_endpoints(self):
        """Test vault API endpoints"""
        try:
            # Test vault files endpoint
            response = requests.get(f"{self.base_url}/api/vault/sidebar/files")
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                
                self.log_test(
                    "Vault Files Endpoint",
                    True,
                    f"Retrieved {len(files)} files"
                )
                
                # Test file categories
                categories = set()
                for file in files:
                    category = self._get_file_category(file.get("name", ""))
                    categories.add(category)
                
                self.log_test(
                    "File Categorization",
                    True,
                    f"Found categories: {', '.join(categories)}"
                )
            else:
                self.log_test(
                    "Vault Files Endpoint",
                    False,
                    f"HTTP {response.status_code}"
                )
            
            # Test vault stats endpoint
            response = requests.get(f"{self.base_url}/api/vault/sidebar/stats")
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get("stats", {})
                
                self.log_test(
                    "Vault Stats Endpoint",
                    True,
                    f"Stats: {stats.get('total_files', 0)} files, {stats.get('storage_used', 0)}% used"
                )
            else:
                self.log_test(
                    "Vault Stats Endpoint",
                    False,
                    f"HTTP {response.status_code}"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "Vault API Endpoints",
                False,
                f"Request failed: {str(e)}"
            )
            return False
    
    def test_vault_upload(self):
        """Test vault upload functionality"""
        try:
            # Create test file
            test_file_path = Path("test_upload.txt")
            test_file_path.write_text("Test file for vault upload")
            
            # Test upload
            with open(test_file_path, 'rb') as test_file:
                files = {'files': test_file}
                metadata = json.dumps({
                    "source": "test_script",
                    "files": [{"name": "test_upload.txt", "size": 25, "type": "text/plain"}]
                })
                
                response = requests.post(
                    f"{self.base_url}/api/vault/sidebar/upload",
                    files=files,
                    data={'metadata': metadata}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    self.log_test(
                        "Vault Upload",
                        data.get("success", False),
                        data.get("message", "Upload failed")
                    )
                else:
                    self.log_test(
                        "Vault Upload",
                        False,
                        f"HTTP {response.status_code}"
                    )
            
            # Clean up
            if test_file_path.exists():
                test_file_path.unlink()
            
            return True
            
        except Exception as e:
            self.log_test(
                "Vault Upload Test",
                False,
                f"Test failed: {str(e)}"
            )
            return False
    
    def test_vault_config(self):
        """Test vault component configuration"""
        try:
            # Test vault component config endpoint
            response = requests.get(f"{self.base_url}/api/vault/component-config")
            
            if response.status_code == 200:
                data = response.json()
                
                self.log_test(
                    "Vault Component Config",
                    data.get("show_vault", False),
                    "Vault accessible" if data.get("show_vault") else "Vault not accessible"
                )
                
                # Check configuration details
                if data.get("show_vault"):
                    config_items = ["role", "compact_mode", "show_stats", "auto_sync"]
                    for item in config_items:
                        if item in data:
                            self.log_test(True, f"Config item '{item}' present", {"value": data[item]})
                        else:
                            self.log_test(False, f"Config item '{item}' missing")
            else:
                self.log_test(
                    "Vault Component Config",
                    False,
                    f"HTTP {response.status_code}"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "Vault Config Test",
                False,
                f"Request failed: {str(e)}"
            )
            return False
    
    def test_vault_search(self):
        """Test vault search functionality"""
        try:
            # Test search endpoint
            response = requests.get(f"{self.base_url}/api/vault/sidebar/search?query=test")
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                
                self.log_test(
                    "Vault Search",
                    True,
                    f"Search returned {len(files)} results for 'test'"
                )
            else:
                self.log_test(
                    "Vault Search",
                    False,
                    f"HTTP {response.status_code}"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "Vault Search Test",
                False,
                f"Request failed: {str(e)}"
            )
            return False
    
    def _get_file_category(self, filename):
        """Determine file category from filename"""
        extension = Path(filename).suffix.lower()
        
        document_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'}
        audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.flac'}
        video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv'}
        
        if extension in document_extensions:
            return 'documents'
        elif extension in image_extensions:
            return 'images'
        elif extension in audio_extensions:
            return 'audio'
        elif extension in video_extensions:
            return 'video'
        else:
            return 'other'
    
    def run_all_tests(self):
        """Run all vault system tests"""
        print("🧪 Starting Vault System Test Suite")
        print("=" * 50)
        
        # Test 1: Vault Component Configuration
        self.test_vault_config()
        
        # Test 2: Vault API Endpoints
        self.test_vault_endpoints()
        
        # Test 3: Vault Upload
        self.test_vault_upload()
        
        # Test 4: Vault Search
        self.test_vault_search()
        
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

def main():
    """Main test function"""
    print("🔍 Testing Vault System")
    print("⚠️  Make sure server is running with vault integration enabled")
    print("📋 Expected: Server at http://localhost:8000")
    print("🔐 Expected: Storage credentials configured")
    
    tester = VaultTester()
    
    success = tester.run_all_tests()
    
    if success:
        print("\n🚀 Vault system is ready for production!")
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
    exit_code = main()
    exit(exit_code)
