#!/bin/bash
# Fix TailSentry Real Tailscale Data Integration for Debian
# This script addresses issues with TailSentry not displaying real Tailscale data

set -e  # Exit on any error

# ANSI colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== TailSentry Tailscale Integration Repair Tool ===${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}This script needs to be run as root.${NC}"
  echo "Please run with: sudo $0"
  exit 1
fi

# Check for Tailscale
echo -e "${BLUE}[1/6] Checking Tailscale installation...${NC}"
if ! command -v tailscale &> /dev/null; then
    echo -e "${RED}Tailscale is not installed.${NC}"
    echo "Would you like to install Tailscale now? [y/N]"
    read -r install_tailscale
    if [[ "$install_tailscale" =~ ^[Yy]$ ]]; then
        echo "Installing Tailscale..."
        curl -fsSL https://tailscale.com/install.sh | sh
    else
        echo -e "${RED}Cannot continue without Tailscale.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Tailscale is installed.${NC}"
fi

# Check Tailscale status
echo ""
echo -e "${BLUE}[2/6] Checking Tailscale status...${NC}"
if ! tailscale status &> /dev/null; then
    echo -e "${RED}Tailscale is not authenticated or not running.${NC}"
    echo "Would you like to authenticate Tailscale now? [y/N]"
    read -r auth_tailscale
    if [[ "$auth_tailscale" =~ ^[Yy]$ ]]; then
        echo "Running tailscale up..."
        tailscale up
    else
        echo -e "${YELLOW}Continuing without authentication, but TailSentry may not work correctly.${NC}"
    fi
else
    echo -e "${GREEN}Tailscale is running and authenticated.${NC}"
fi

# Find TailSentry installation
echo ""
echo -e "${BLUE}[3/6] Locating TailSentry installation...${NC}"
TAILSENTRY_PATHS=("/opt/tailsentry" "/usr/local/tailsentry" "$(pwd)")
TAILSENTRY_PATH=""

for path in "${TAILSENTRY_PATHS[@]}"; do
    if [ -f "$path/main.py" ] && [ -f "$path/tailscale_client.py" ]; then
        TAILSENTRY_PATH="$path"
        echo -e "${GREEN}Found TailSentry at: $TAILSENTRY_PATH${NC}"
        break
    fi
done

if [ -z "$TAILSENTRY_PATH" ]; then
    echo -e "${YELLOW}Could not find TailSentry installation.${NC}"
    echo "Please enter the path to your TailSentry installation:"
    read -r TAILSENTRY_PATH
    
    if [ ! -f "$TAILSENTRY_PATH/main.py" ] || [ ! -f "$TAILSENTRY_PATH/tailscale_client.py" ]; then
        echo -e "${RED}Invalid TailSentry path.${NC}"
        exit 1
    fi
fi

# Fix permissions
echo ""
echo -e "${BLUE}[4/6] Setting correct permissions...${NC}"
TAILSCALE_PATH=$(which tailscale)
echo "Tailscale binary is at: $TAILSCALE_PATH"

# Make sure TailSentry can access tailscale
chmod 755 "$TAILSCALE_PATH"
echo -e "${GREEN}Set executable permissions on Tailscale binary.${NC}"

# Make sure the service runs as root
if [ -f "/etc/systemd/system/tailsentry.service" ]; then
    echo "Found TailSentry service."
    if ! grep -q "User=root" "/etc/systemd/system/tailsentry.service"; then
        echo "Setting service to run as root..."
        # Use sed to replace or add the User directive
        if grep -q "User=" "/etc/systemd/system/tailsentry.service"; then
            sed -i 's/User=.*/User=root/' "/etc/systemd/system/tailsentry.service"
        else
            sed -i '/\[Service\]/a User=root' "/etc/systemd/system/tailsentry.service"
        fi
        
        # Make sure PATH includes tailscale location
        if ! grep -q "Environment=\"PATH=" "/etc/systemd/system/tailsentry.service"; then
            sed -i '/\[Service\]/a Environment="PATH=/usr/sbin:/usr/bin:/sbin:/bin"' "/etc/systemd/system/tailsentry.service"
        fi
        
        systemctl daemon-reload
        echo -e "${GREEN}Service updated to run as root with correct PATH.${NC}"
    else
        echo -e "${GREEN}Service is already configured to run as root.${NC}"
    fi
else
    echo -e "${YELLOW}No tailsentry.service found. Skipping service configuration.${NC}"
fi

# Create debug environment
echo ""
echo -e "${BLUE}[5/6] Setting up debug environment...${NC}"

# Create or update environment file
ENV_FILE="$TAILSENTRY_PATH/.env"
echo "Creating/updating environment file at $ENV_FILE"

cat > "$ENV_FILE" << EOF
# TailSentry Debug Environment
LOG_LEVEL=DEBUG
TAILSCALE_PATH=$TAILSCALE_PATH
DEVELOPMENT=true
EOF

echo -e "${GREEN}Debug environment configured.${NC}"

# Test Tailscale integration
echo ""
echo -e "${BLUE}[6/6] Testing Tailscale integration...${NC}"

# Create a simple test script
TEST_SCRIPT="$TAILSENTRY_PATH/test_integration.py"
cat > "$TEST_SCRIPT" << EOF
#!/usr/bin/env python3
"""Test TailSentry integration with Tailscale"""
import sys
import os
import json
import subprocess

# Add TailSentry path to system path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to import TailscaleClient
try:
    from tailscale_client import TailscaleClient
    print("✅ Successfully imported TailscaleClient")
except ImportError as e:
    print(f"❌ Failed to import TailscaleClient: {e}")
    sys.exit(1)

# Try to get Tailscale path
try:
    tailscale_path = TailscaleClient.get_tailscale_path()
    print(f"✅ Found Tailscale at: {tailscale_path}")
except Exception as e:
    print(f"❌ Failed to get Tailscale path: {e}")
    sys.exit(1)

# Try direct tailscale command
print("\nDirect command test:")
try:
    result = subprocess.run([tailscale_path, "status", "--json"], 
                            capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    print("✅ Direct command successful")
    if "Self" in data:
        print(f"  Hostname: {data['Self'].get('HostName', 'unknown')}")
        print(f"  IPs: {', '.join(data['Self'].get('TailscaleIPs', ['none']))}")
        print(f"  Peers: {len(data.get('Peer', {}))}")
    else:
        print("❌ No 'Self' data in direct output")
except Exception as e:
    print(f"❌ Direct command failed: {e}")

# Try through TailscaleClient
print("\nTailscaleClient test:")
try:
    status = TailscaleClient.status_json()
    print("✅ TailscaleClient.status_json() successful")
    if isinstance(status, dict) and "Self" in status:
        print(f"  Hostname: {status['Self'].get('HostName', 'unknown')}")
        print(f"  IPs: {', '.join(status['Self'].get('TailscaleIPs', ['none']))}")
        print(f"  Peers: {len(status.get('Peer', {}))}")
    else:
        print(f"❌ No proper data from TailscaleClient. Result type: {type(status)}")
        if isinstance(status, dict):
            print(f"  Keys: {', '.join(status.keys())}")
except Exception as e:
    print(f"❌ TailscaleClient test failed: {e}")

print("\nTest complete!")
EOF

chmod +x "$TEST_SCRIPT"
echo "Running test script..."
python3 "$TEST_SCRIPT"

echo ""
echo -e "${BLUE}=== Repair Process Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Restart the TailSentry service: systemctl restart tailsentry"
echo "2. Check the logs: journalctl -u tailsentry -f"
echo "3. Access the dashboard and verify real Tailscale data is displayed"
echo ""
echo -e "${YELLOW}If issues persist, check the detailed logs at: $TAILSENTRY_PATH/logs/tailsentry.log${NC}"
