#!/bin/bash
# Quick fix script for TailSentry not displaying real Tailscale data
# Run this script on your Debian system with sudo

set -e  # Exit on any error

# ANSI colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root${NC}"
  echo "Use: sudo $0"
  exit 1
fi

# Locate the Tailscale binary
TAILSCALE_PATH=$(which tailscale)
if [ -z "$TAILSCALE_PATH" ]; then
    echo -e "${RED}Tailscale binary not found in PATH. Is Tailscale installed?${NC}"
    exit 1
fi

echo -e "${BLUE}Found Tailscale at: ${GREEN}$TAILSCALE_PATH${NC}"

# Ensure proper permissions on the Tailscale binary
echo -e "${BLUE}Setting permissions on Tailscale binary...${NC}"
chmod 755 "$TAILSCALE_PATH"

# Check Tailscale status
echo -e "${BLUE}Checking Tailscale status...${NC}"
if ! $TAILSCALE_PATH status &> /dev/null; then
    echo -e "${RED}Tailscale is not running or authenticated.${NC}"
    echo -e "${YELLOW}Please run 'sudo tailscale up' first.${NC}"
    exit 1
fi

# Update the .env file
INSTALL_DIR="/opt/tailsentry"
ENV_FILE="$INSTALL_DIR/.env"

echo -e "${BLUE}Updating .env file...${NC}"
if [ -f "$ENV_FILE" ]; then
    # Backup the original .env file
    cp "$ENV_FILE" "$ENV_FILE.bak"
    echo "Created backup: $ENV_FILE.bak"
    
    # Check if TAILSCALE_PATH is already set
    if grep -q "^TAILSCALE_PATH=" "$ENV_FILE"; then
        # Update the existing setting
        sed -i "s|^TAILSCALE_PATH=.*|TAILSCALE_PATH=$TAILSCALE_PATH|" "$ENV_FILE"
    else
        # Add the setting if it doesn't exist
        echo "TAILSCALE_PATH=$TAILSCALE_PATH" >> "$ENV_FILE"
    fi

    # Set USE_MOCK_DATA to false
    if grep -q "^USE_MOCK_DATA=" "$ENV_FILE"; then
        sed -i "s|^USE_MOCK_DATA=.*|USE_MOCK_DATA=false|" "$ENV_FILE"
    else
        echo "USE_MOCK_DATA=false" >> "$ENV_FILE"
    fi

    # Ensure DEVELOPMENT=false to avoid using mock data
    if grep -q "^DEVELOPMENT=" "$ENV_FILE"; then
        sed -i "s|^DEVELOPMENT=.*|DEVELOPMENT=false|" "$ENV_FILE"
    else
        echo "DEVELOPMENT=false" >> "$ENV_FILE"
    fi

    echo -e "${GREEN}Updated .env file with correct settings.${NC}"
else
    echo -e "${RED}.env file not found at $ENV_FILE${NC}"
    exit 1
fi

# Update the systemd service file
SERVICE_FILE="/etc/systemd/system/tailsentry.service"

echo -e "${BLUE}Updating service file...${NC}"
if [ -f "$SERVICE_FILE" ]; then
    # Backup the original service file
    cp "$SERVICE_FILE" "$SERVICE_FILE.bak"
    echo "Created backup: $SERVICE_FILE.bak"
    
    # Create a new service file with the correct environment variables
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=TailSentry - Tailscale Management Dashboard
After=network.target tailscaled.service
Requires=tailscaled.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10
Environment=PATH=/usr/sbin:/usr/bin:/sbin:/bin:$INSTALL_DIR/venv/bin
Environment=PYTHONPATH=$INSTALL_DIR
Environment=TAILSCALE_PATH=$TAILSCALE_PATH
Environment=USE_MOCK_DATA=false
Environment=DEVELOPMENT=false

[Install]
WantedBy=multi-user.target
EOF
    echo -e "${GREEN}Updated service file with correct environment variables.${NC}"
else
    echo -e "${RED}Service file not found at $SERVICE_FILE${NC}"
    exit 1
fi

# Clear the cache files
echo -e "${BLUE}Clearing cache files...${NC}"
CACHE_FILE="$INSTALL_DIR/data/tailscale_status_cache.json"
if [ -f "$CACHE_FILE" ]; then
    rm "$CACHE_FILE"
    echo "Removed cache file: $CACHE_FILE"
fi

# Reload systemd and restart the service
echo -e "${BLUE}Reloading systemd and restarting service...${NC}"
systemctl daemon-reload
systemctl restart tailsentry.service

# Check service status
echo -e "${BLUE}Checking service status...${NC}"
systemctl status tailsentry.service --no-pager

# Create a test script to verify integration
echo -e "${BLUE}Creating verification script...${NC}"
TEST_SCRIPT="$INSTALL_DIR/tailsentry_verification.py"
cat > "$TEST_SCRIPT" << EOF
#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import time

# Add TailSentry path to system path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("===== TailSentry Tailscale Integration Verification =====")

# Try to import TailscaleClient
try:
    from tailscale_client import TailscaleClient
    print("✅ Successfully imported TailscaleClient")
except ImportError as e:
    print(f"❌ Failed to import TailscaleClient: {e}")
    sys.exit(1)

# Check for environment variables
print("\nChecking environment variables:")
tailscale_path_env = os.environ.get('TAILSCALE_PATH')
use_mock_data_env = os.environ.get('USE_MOCK_DATA')
development_env = os.environ.get('DEVELOPMENT')

print(f"TAILSCALE_PATH = {tailscale_path_env or 'Not set'}")
print(f"USE_MOCK_DATA = {use_mock_data_env or 'Not set'}")
print(f"DEVELOPMENT = {development_env or 'Not set'}")

# Try to get Tailscale path
try:
    tailscale_path = TailscaleClient.get_tailscale_path()
    print(f"\n✅ Found Tailscale at: {tailscale_path}")
    
    # Check if it matches environment variable
    if tailscale_path_env and tailscale_path != tailscale_path_env:
        print(f"⚠️ Warning: Path from code ({tailscale_path}) doesn't match environment variable ({tailscale_path_env})")
except Exception as e:
    print(f"\n❌ Failed to get Tailscale path: {e}")
    sys.exit(1)

# Try to get real Tailscale status directly
print("\nTesting direct Tailscale command:")
try:
    result = subprocess.run([tailscale_path, "status", "--json"], 
                            capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        print("✅ Tailscale command executed successfully")
        
        if "Self" in data:
            print(f"  Device name: {data['Self'].get('HostName', 'unknown')}")
            print(f"  Tailscale IPs: {', '.join(data['Self'].get('TailscaleIPs', ['none']))}")
            peer_count = len(data.get("Peer", {}))
            print(f"  Connected peers: {peer_count}")
        else:
            print("⚠️ No 'Self' data found in Tailscale status")
    else:
        print(f"⚠️ Tailscale command failed with code {result.returncode}")
        print(f"  Error: {result.stderr}")
except Exception as e:
    print(f"❌ Error executing Tailscale command: {e}")

# Try through TailscaleClient
print("\nTesting TailscaleClient.status_json() method:")
try:
    status = TailscaleClient.status_json()
    if isinstance(status, dict):
        if "Self" in status:
            print("✅ TailscaleClient successfully retrieved real data")
            print(f"  Device name: {status['Self'].get('HostName', 'unknown')}")
            print(f"  Tailscale IPs: {', '.join(status['Self'].get('TailscaleIPs', ['none']))}")
            peer_count = len(status.get("Peer", {}))
            print(f"  Connected peers: {peer_count}")
            
            # Check if this is real or mock data
            if status['Self'].get('HostName') == "tailscale-server" and peer_count == 3:
                print("❌ WARNING: This looks like mock data! Not real Tailscale data.")
            else:
                print("✅ This appears to be real Tailscale data")
        else:
            print("⚠️ Data retrieved but missing 'Self' information")
            print(f"  Available keys: {', '.join(status.keys())}")
    else:
        print(f"⚠️ Unexpected data type: {type(status)}")
except Exception as e:
    print(f"❌ Error in TailscaleClient.status_json(): {e}")

print("\n===== Verification complete =====")

# Force status cache refresh
print("\nTesting cache refresh:")
try:
    # Clear the _status_json_cached cache
    print("Waiting 5 seconds to ensure cache expiration...")
    time.sleep(5)
    
    # Call it again to force refresh
    status = TailscaleClient.status_json()
    if isinstance(status, dict) and "Self" in status:
        print("✅ Cache refreshed successfully")
    else:
        print("❌ Cache refresh issue")
except Exception as e:
    print(f"❌ Error testing cache: {e}")
EOF

# Make it executable
chmod +x "$TEST_SCRIPT"

# Run the verification script
echo -e "${BLUE}Running verification script...${NC}"
cd "$INSTALL_DIR"
python3 "$TEST_SCRIPT"

echo -e "${GREEN}Fix script completed!${NC}"
echo ""
echo "If you're still not seeing real Tailscale data:"
echo "1. Check the TailSentry logs: sudo tail -f $INSTALL_DIR/logs/tailsentry.log"
echo "2. Make sure your browser is not caching old data (try Ctrl+F5 or incognito mode)"
echo "3. Verify that your Tailscale PAT is configured correctly if you're using API features"
echo ""
echo "Access TailSentry at: http://localhost:8080 or http://$(hostname -I | awk '{print $1}'):8080"
