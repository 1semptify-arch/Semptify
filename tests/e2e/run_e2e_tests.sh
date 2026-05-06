#!/bin/bash
#
# Semptify E2E Test Runner
# ========================
# 
# Usage:
#   ./run_e2e_tests.sh              # Run all tests
#   ./run_e2e_tests.sh --quick      # Run quick smoke test only
#   ./run_e2e_tests.sh --ci          # Run in CI mode (headless)
#   ./run_e2e_tests.sh --flows       # Run user flow continuity tests
#   ./run_e2e_tests.sh --url http://localhost:8000  # Custom URL
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default settings
URL="http://localhost:8000"
MODE="full"
HEADLESS="false"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --quick)
      MODE="quick"
      shift
      ;;
    --ci)
      MODE="ci"
      HEADLESS="true"
      shift
      ;;
    --flows)
      MODE="flows"
      shift
      ;;
    --url)
      URL="$2"
      shift 2
      ;;
    --help)
      echo "Semptify E2E Test Runner"
      echo ""
      echo "Options:"
      echo "  --quick     Run quick smoke test only"
      echo "  --ci        Run in CI mode (headless, no browser window)"
      echo "  --flows     Run user flow continuity tests"
      echo "  --url URL   Set target URL (default: http://localhost:8000)"
      echo "  --help      Show this help"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo -e "${YELLOW}🧪 Semptify E2E Test Runner${NC}"
echo "=========================================="
echo "Target URL: $URL"
echo "Mode: $MODE"
echo "Headless: $HEADLESS"
echo "=========================================="
echo ""

# Check if server is running
echo "Checking if server is running..."
if ! curl -s "$URL/healthz" > /dev/null; then
  echo -e "${RED}❌ Server not responding at $URL${NC}"
  echo "Please start the server first:"
  echo "  python -m app.main"
  exit 1
fi
echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Check if Playwright is installed
if ! command -v npx &> /dev/null; then
  echo -e "${RED}❌ npx not found. Please install Node.js and npm.${NC}"
  exit 1
fi

# Ensure Playwright browsers are installed
echo "Checking Playwright installation..."
npx playwright install chromium 2>/dev/null || true

# Set environment variables
export SEMPTIFY_URL="$URL"

# Run the appropriate test
if [ "$MODE" == "quick" ]; then
  echo -e "${YELLOW}Running quick smoke test...${NC}"
  node tests/e2e/smoke_test.js
elif [ "$MODE" == "ci" ]; then
  echo -e "${YELLOW}Running CI tests (headless)...${NC}"
  export HEADLESS="true"
  node tests/e2e/playwright_full_system_test.js
elif [ "$MODE" == "flows" ]; then
  echo -e "${YELLOW}Running user flow continuity tests...${NC}"
  echo "Browser window will open. Press Ctrl+C to stop."
  echo ""
  node tests/e2e/user_flow_continuity_test.js
else
  echo -e "${YELLOW}Running full system test...${NC}"
  echo "Browser window will open. Press Ctrl+C to stop."
  echo ""
  node tests/e2e/playwright_full_system_test.js
fi

echo ""
echo -e "${GREEN}✅ Test run completed${NC}"
echo "Check /tmp/semptify_e2e_report.json for detailed results"
