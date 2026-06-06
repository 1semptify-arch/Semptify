#!/usr/bin/env python
"""
Fix all naive datetime.now() calls in the app/ directory.
Replaces datetime.now() with utc_now() from app.core.utc.
Skips _migrated/ and templates/ directories.
"""

import re
from pathlib import Path

BASE = Path('app')
FIXED = 0
SKIPPED = 0

def fix_file(path: Path) -> bool:
    global FIXED
    try:
        content = path.read_text(encoding='utf-8')
    except Exception:
        return False

    lines = content.split('\n')
    changes = []
    import_idx = None
    has_utc_import = 'from app.core.utc import' in content or 'utc_now' in content

    for i, line in enumerate(lines):
        if re.search(r'\bdatetime\.now\(\s*\)', line) and 'timezone' not in line:
            changes.append(i)
        # Find a good place to insert the import
        if line.startswith('from ') or line.startswith('import '):
            import_idx = i

    if not changes:
        return False

    print(f"\n{'='*60}")
    print(f"FILE: {path}")
    print(f"  Found {len(changes)} naive datetime.now() call(s)")

    for i in changes:
        old = lines[i]
        new = old.replace('datetime.now()', 'utc_now()')
        lines[i] = new
        print(f"  Line {i+1}: {old.strip()[:80]}...")
        print(f"           -> {new.strip()[:80]}...")

    if not has_utc_import and import_idx is not None:
        lines.insert(import_idx + 1, 'from app.core.utc import utc_now')
        print(f"  Added: from app.core.utc import utc_now")

    path.write_text('\n'.join(lines), encoding='utf-8')
    FIXED += len(changes)
    print(f"  FIXED ✓")
    return True

print("Scanning app/ for naive datetime.now() calls...")
print(f"{'='*60}")

for root, dirs, files in BASE.walk():
    if '_migrated' in str(root) or 'templates' in str(root):
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        fix_file(root / f)

print(f"\n{'='*60}")
print(f"TOTAL: Fixed {FIXED} naive datetime.now() call(s)")
