#!/bin/bash
# Pre-commit hook to enforce utc_now() usage

echo "🔍 Checking datetime consistency..."

# Count violations
violations=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' | xargs grep -l "datetime\.now(timezone\.utc)" 2>/dev/null | wc -l)

if [ $violations -gt 0 ]; then
    echo "❌ Found datetime.now(timezone.utc) in staged files"
    echo "Use utc_now() from app.core.utc instead"
    echo ""
    echo "Violating files:"
    git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' | xargs grep -l "datetime\.now(timezone.utc)" 2>/dev/null
    echo ""
    echo "Run: python scripts/fix_datetime_consistency.py"
    exit 1
else
    echo "✅ Datetime usage is consistent"
fi
