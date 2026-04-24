#!/bin/bash
# Semptify GUI Test Runner (Unix/Mac)
# This script runs the Playwright GUI test bot

echo "============================================"
echo "Semptify GUI Test Bot"
echo "============================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Check if virtual environment exists and activate it
if [ -d "../.venv" ]; then
    echo "Activating virtual environment..."
    source "../.venv/bin/activate"
elif [ -d "../venv311" ]; then
    echo "Activating virtual environment (venv311)..."
    source "../venv311/bin/activate"
fi

# Check if playwright is installed
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "Installing Playwright..."
    pip install playwright
    playwright install chromium
fi

# Default arguments
HEADED=""
SLOW=""
ROLE="all"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --headed)
            HEADED="--headed"
            shift
            ;;
        --slow)
            SLOW="--slow 500"
            shift
            ;;
        --role)
            ROLE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo ""
echo "Running GUI tests with role: $ROLE"
if [ -n "$HEADED" ]; then echo "Mode: HEADED (visible browser)"; fi
if [ -n "$SLOW" ]; then echo "Slow motion: 500ms"; fi

python3 "$(dirname "$0")/gui_test_bot.py" $HEADED $SLOW --role "$ROLE"

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "============================================"
    echo "Tests completed with failures"
    echo "============================================"
    exit 1
else
    echo ""
    echo "============================================"
    echo "All tests passed!"
    echo "============================================"
fi
