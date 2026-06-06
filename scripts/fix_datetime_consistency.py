#!/usr/bin/env python
"""
Fix datetime.now(timezone.utc) inconsistencies across the codebase.

This script replaces all instances of datetime.now(timezone.utc) with utc_now()
to ensure consistent timezone handling throughout Semptify.
"""

import os
import re
import sys
from pathlib import Path

def fix_datetime_in_file(file_path: Path) -> int:
    """Fix datetime inconsistencies in a single file.
    
    Returns:
        Number of fixes made.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0
    
    # Check if utc_now is already imported
    needs_import = 'from app.core.utc import utc_now' not in content
    
    # Pattern to match datetime.now(timezone.utc)
    pattern = r'datetime\.now\(timezone\.utc\)'
    replacements = re.findall(pattern, content)
    
    if not replacements:
        return 0
    
    # Replace with utc_now()
    content = re.sub(pattern, 'utc_now()', content)
    
    # Add import if needed
    if needs_import:
        # Find the last import statement
        import_pattern = r'(from\s+app\.\w+\s+import\s+.+|import\s+.+)'
        imports = re.findall(import_pattern, content)
        
        if imports:
            last_import = imports[-1]
            # Insert utc_now import after the last import
            content = content.replace(
                last_import,
                f"{last_import}\nfrom app.core.utc import utc_now"
            )
    
    # Write back
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return 0
    
    return len(replacements)

def main():
    """Main entry point."""
    app_dir = Path("app")
    
    if not app_dir.exists():
        print("Error: app/ directory not found")
        sys.exit(1)
    
    total_fixes = 0
    files_fixed = 0
    
    # Find all Python files
    for py_file in app_dir.rglob("*.py"):
        fixes = fix_datetime_in_file(py_file)
        if fixes > 0:
            print(f"Fixed {fixes} instances in {py_file}")
            total_fixes += fixes
            files_fixed += 1
    
    print(f"\n✅ Fixed {total_fixes} instances across {files_fixed} files")
    print(f"🔧 All datetime.now(timezone.utc) replaced with utc_now()")

if __name__ == "__main__":
    main()
