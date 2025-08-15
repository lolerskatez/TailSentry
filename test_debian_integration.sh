#!/bin/bash
# TailSentry Integration Test for Debian
# This script tests the TailSentry integration with Tailscale

# Set colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo "=== TailSentry Integration Test ==="
echo ""

# Check if Tailscale is installed
echo -n "Checking if Tailscale is installed... "
if command -v tailscale &> /dev/null; then
    echo -e "${GREEN}FOUND${NC}"
    TAILSCALE_PATH=$(which tailscale)
    echo "  Path: $TAILSCALE_PATH"
else
    echo -e "${RED}NOT FOUND${NC}"
    echo "  Please install Tailscale first"
    exit 1
fi

# Check if Tailscale is running
echo -n "Checking if Tailscale daemon is running... "
if systemctl is-active --quiet tailscaled; then
    echo -e "${GREEN}RUNNING${NC}"
else
    echo -e "${RED}NOT RUNNING${NC}"
    echo "  Please start Tailscale daemon with: sudo systemctl start tailscaled"
    exit 1
fi

# Check if Tailscale is authenticated
echo -n "Checking if Tailscale is authenticated... "
if tailscale status --self=false | grep -q "authenticated"; then
    echo -e "${GREEN}AUTHENTICATED${NC}"
else
    echo -e "${YELLOW}NOT AUTHENTICATED${NC}"
    echo "  Please authenticate with: sudo tailscale up"
    echo "  Continuing tests anyway..."
fi

# Check if TailSentry can access Tailscale
echo -n "Testing if TailSentry can access Tailscale... "
cd /opt/tailsentry 2>/dev/null || cd $(dirname "$0")

# Try to run a Python test
python3 -c "
import sys
sys.path.append('.')
try:
    from tailscale_client import TailscaleClient
    path = TailscaleClient.get_tailscale_path()
    status = TailscaleClient.status_json()
    success = bool(status) and not isinstance(status, str)
    print('Path:', path)
    print('Success:', success)
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    print('Error:', str(e))
    sys.exit(1)
" &> /tmp/tailsentry_test.log

if [ $? -eq 0 ]; then
    echo -e "${GREEN}SUCCESS${NC}"
    cat /tmp/tailsentry_test.log
else
    echo -e "${RED}FAILED${NC}"
    cat /tmp/tailsentry_test.log
    echo "  Please check error message above"
fi

echo ""
echo "=== Test Complete ==="
