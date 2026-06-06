#!/usr/bin/env python
"""
Semptify Folder Structure Verifier
Run this to check your vault structure completeness
"""

import os
from pathlib import Path

def check_vault_structure(base_path="G:\\My Drive"):
    """Verify Semptify vault structure completeness."""
    
    print("🔍 SEMPTIFY VAULT STRUCTURE VERIFIER")
    print("=" * 50)
    print(f"Checking: {base_path}")
    print()
    
    # Expected structure
    expected = {
        "Semptify5.0": {
            "README.txt": "Installation summary",
            ".Semptify5.0": {
                "auth": {
                    "token.enc": "Encrypted OAuth token",
                    "token.enc.backup": "Token backup", 
                    "device_keys.json": "Device registration",
                    "provisioning.json": "Installation state",
                    "rehome.json": "Reconnection script"
                },
                "vault": {
                    "README.md": "Vault information",
                    "manifest.json": "Vault metadata"
                }
            },
            "Vault": {
                "documents": "Your uploaded documents",
                "certificates": "Official certificates",
                "timeline": {
                    "events.json": "Timeline events data"
                },
                "overlays": {
                    "registry.json": "Overlay index",
                    "documents": "Document overlays",
                    "queries": "Query results", 
                    "forms": "Form-fill overlays",
                    "redactions": "Redaction overlays",
                    "evidence": "Evidence overlays",
                    "legal": "Legal overlays",
                    "timeline": "Timeline overlays"
                }
            }
        }
    }
    
    results = {
        "found": [],
        "missing": [],
        "errors": []
    }
    
    def check_structure(structure, current_path, prefix=""):
        """Recursively check expected structure."""
        for name, content in structure.items():
            full_path = Path(current_path) / name
            display_name = f"{prefix}{name}"
            
            try:
                if full_path.exists():
                    if isinstance(content, dict):
                        # It's a folder, check inside
                        if full_path.is_dir():
                            results["found"].append(f"📁 {display_name}/")
                            check_structure(content, full_path, f"{prefix}  ")
                        else:
                            results["errors"].append(f"❌ {display_name} (should be folder, is file)")
                    else:
                        # It's a file
                        if full_path.is_file():
                            size = full_path.stat().st_size
                            if size > 0:
                                results["found"].append(f"📄 {display_name} ({size} bytes)")
                            else:
                                results["errors"].append(f"⚠️  {display_name} (empty file)")
                        else:
                            results["missing"].append(f"❌ {display_name} (missing file)")
                else:
                    if isinstance(content, dict):
                        results["missing"].append(f"❌ {display_name}/ (missing folder)")
                    else:
                        results["missing"].append(f"❌ {display_name} (missing file)")
                        
            except Exception as e:
                results["errors"].append(f"❌ {display_name} (error: {e})")
    
    # Start checking
    check_structure(expected, base_path)
    
    # Print results
    print("✅ FOUND ITEMS:")
    for item in results["found"]:
        print(f"  {item}")
    
    print(f"\n❌ MISSING ITEMS ({len(results['missing'])}):")
    for item in results["missing"]:
        print(f"  {item}")
    
    print(f"\n⚠️  ERRORS ({len(results['errors'])}):")
    for item in results["errors"]:
        print(f"  {item}")
    
    # Summary
    total_expected = len(results["found"]) + len(results["missing"])
    completion = (len(results["found"]) / total_expected * 100) if total_expected > 0 else 0
    
    print(f"\n📊 COMPLETION: {completion:.1f}%")
    print(f"   Found: {len(results['found'])}")
    print(f"   Missing: {len(results['missing'])}")
    print(f"   Errors: {len(results['errors'])}")
    
    # Diagnosis
    if completion == 100:
        print("\n🎉 VAULT STRUCTURE IS COMPLETE!")
    elif completion >= 80:
        print("\n⚠️  VAULT MOSTLY COMPLETE - Check missing items")
    elif completion >= 50:
        print("\n🔧 VAULT PARTIALLY COMPLETE - May need repair")
    else:
        print("\n❌ VAULT INCOMPLETE - Re-run vault creation")
    
    return results

if __name__ == "__main__":
    check_vault_structure()
