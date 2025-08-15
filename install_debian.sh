#!/bin/bash
# Enhanced TailSentry Installation Script for Debian
# Includes integrated diagnostics and fixes for Tailscale integration

set -e  # Exit on any error

# ANSI colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
INSTALL_DIR="/opt/tailsentry"
REPO_URL="https://github.com/lolerskatez/TailSentry.git"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}       TailSentry Installation Script for Debian${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root${NC}"
  echo "Use: sudo $0"
  exit 1
fi

# Step 1: Check for and install Tailscale if needed
echo -e "${BLUE}[1/5] Checking Tailscale installation...${NC}"
TAILSCALE_PATH=""

if ! command -v tailscale &> /dev/null; then
    echo -e "${YELLOW}Tailscale is not installed. Installing now...${NC}"
    
    # Check if we're on Debian/Ubuntu
    if command -v apt &> /dev/null; then
        # Add Tailscale's GPG key and repository
        curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
        curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list
        
        # Update and install
        apt-get update
        apt-get install -y tailscale
    else
        # Generic installer for other distros
        curl -fsSL https://tailscale.com/install.sh | sh
    fi
    
    # Start Tailscale service
    systemctl enable --now tailscaled
    
    if ! command -v tailscale &> /dev/null; then
        echo -e "${RED}Failed to install Tailscale. Cannot continue.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Tailscale installed successfully.${NC}"
else
    echo -e "${GREEN}Tailscale is already installed.${NC}"
fi

# Check Tailscale binary location
TAILSCALE_PATH=$(which tailscale)
echo -e "Tailscale binary found at: ${GREEN}$TAILSCALE_PATH${NC}"

# Step 2: Check Tailscale status and authenticate if needed
echo ""
echo -e "${BLUE}[2/5] Checking Tailscale authentication status...${NC}"

if ! tailscale status &> /dev/null; then
    echo -e "${YELLOW}Tailscale is not authenticated.${NC}"
    echo "Would you like to authenticate Tailscale now? [Y/n]"
    read -r auth_response
    auth_response=${auth_response:-Y}
    
    if [[ ! $auth_response =~ ^[Nn]$ ]]; then
        echo "Running tailscale up..."
        tailscale up
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to authenticate Tailscale.${NC}"
            echo "You can manually authenticate later with: sudo tailscale up"
            echo "Continuing with installation..."
        else
            echo -e "${GREEN}Tailscale authenticated successfully.${NC}"
        fi
    else
        echo "Skipping authentication. You can authenticate later with: sudo tailscale up"
    fi
else
    echo -e "${GREEN}Tailscale is already authenticated.${NC}"
    tailscale ip
fi

# Step 3: Install TailSentry dependencies
echo ""
echo -e "${BLUE}[3/5] Installing system dependencies...${NC}"
if command -v apt &> /dev/null; then
    apt-get update
    apt-get install -y python3 python3-venv python3-pip git
else
    echo -e "${YELLOW}Non-Debian system detected. Installing minimal dependencies...${NC}"
    # For other systems, assume Python is available
    command -v python3 &> /dev/null || { echo -e "${RED}Python 3 required but not found${NC}"; exit 1; }
    command -v pip3 &> /dev/null || { echo -e "${RED}pip3 required but not found${NC}"; exit 1; }
    command -v git &> /dev/null || { echo -e "${RED}git required but not found${NC}"; exit 1; }
fi

# Handle existing installation
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Existing TailSentry installation found.${NC}"
    echo "Would you like to remove it and perform a fresh install? [Y/n]"
    read -r reinstall_response
    reinstall_response=${reinstall_response:-Y}
    
    if [[ ! $reinstall_response =~ ^[Nn]$ ]]; then
        echo "Stopping service..."
        systemctl stop tailsentry.service 2>/dev/null || true
        echo "Removing existing installation..."
        rm -rf "$INSTALL_DIR"
    else
        echo -e "${YELLOW}Aborting installation to preserve existing files.${NC}"
        exit 0
    fi
fi

# Step 4: Install TailSentry
echo ""
echo -e "${BLUE}[4/5] Installing TailSentry...${NC}"

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Clone or copy repository
if [ -d ".git" ]; then
    # We're running from the repo directory, just copy files
    echo "Copying TailSentry files to $INSTALL_DIR..."
    cp -r * "$INSTALL_DIR"
else
    # Download from repository
    echo "Downloading TailSentry..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# Create Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create data directory with proper permissions
mkdir -p "$INSTALL_DIR/data"
chmod 750 "$INSTALL_DIR/data"

# Create logs directory with proper permissions
mkdir -p "$INSTALL_DIR/logs"
chmod 750 "$INSTALL_DIR/logs"

# Setup .env file
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        # Create minimal .env file if example doesn't exist
        cat > .env << EOF
# TailSentry Configuration
SESSION_SECRET=$(openssl rand -hex 32)
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=  # Will be set below
DEVELOPMENT=true
TAILSCALE_PATH=$TAILSCALE_PATH
EOF
    fi
    
    # Prompt for Tailscale PAT
    clear
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🔧 TailSentry Configuration${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "📝 TailSentry requires a Tailscale Personal Access Token (PAT) to manage"
    echo "   your Tailscale network. You can:"
    echo ""
    echo "   • Enter it now for full functionality"
    echo "   • Skip it and configure later in the dashboard"
    echo ""
    echo "🔗 Get your PAT at: https://login.tailscale.com/admin/settings/keys"
    echo ""
    read -s -p "🔑 Enter Tailscale Personal Access Token (or press Enter to skip): " TS_PAT
    echo
    
    # Use Python to update .env file
    TS_PAT="$TS_PAT" python3 << EOF
import secrets
import bcrypt
import os

# Get the Tailscale PAT from environment if provided
ts_pat = os.environ.get('TS_PAT', '')

# Read .env file
try:
    with open('.env', 'r') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading .env file: {e}")
    exit(1)

# Generate default password hash for "admin123"
default_password = "admin123"
password_hash = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt()).decode()

# Replace or set password hash
content = content.replace('ADMIN_PASSWORD_HASH=', f'ADMIN_PASSWORD_HASH={password_hash}')

# Add Tailscale PAT if provided
if ts_pat:
    content = content.replace('TAILSCALE_PAT=', f'TAILSCALE_PAT={ts_pat}')

# Make sure Tailscale path is set
if "TAILSCALE_PATH=" not in content:
    content += f"\nTAILSCALE_PATH={os.environ.get('TAILSCALE_PATH', '/usr/bin/tailscale')}\n"

# Write back to file
try:
    with open('.env', 'w') as f:
        f.write(content)
    print(f"Wrote .env file successfully")
except Exception as e:
    print(f"Error writing .env file: {e}")
    exit(1)

print("Configuration file updated successfully")
print("Default admin credentials set: admin / admin123")
EOF
fi

# Ensure permissions are set correctly for Tailscale access
echo ""
echo -e "${BLUE}Configuring Tailscale access permissions...${NC}"
TAILSCALE_PATH=$(which tailscale)
chmod 755 "$TAILSCALE_PATH"

# Step 5: Install and configure service
echo ""
echo -e "${BLUE}[5/5] Setting up TailSentry service...${NC}"

# Create systemd service file
cat > /etc/systemd/system/tailsentry.service << EOF
[Unit]
Description=TailSentry - Tailscale Management Dashboard
After=network.target tailscaled.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
systemctl daemon-reload
systemctl enable tailsentry.service
systemctl start tailsentry.service

# Configure firewall if needed
if command -v ufw &> /dev/null; then
    echo "Configuring UFW firewall for TailSentry..."
    ufw allow 8000/tcp
    echo "Allowed port 8000 in UFW firewall"
elif command -v firewall-cmd &> /dev/null; then
    echo "Configuring firewalld for TailSentry..."
    firewall-cmd --permanent --add-port=8000/tcp
    firewall-cmd --reload
    echo "Allowed port 8000 in firewalld"
fi

# Final verification test
echo ""
echo -e "${BLUE}Verifying Tailscale integration...${NC}"

# Create a test script to verify integration
TEST_SCRIPT="tailsentry_verification.py"
cat > "$TEST_SCRIPT" << EOF
#!/usr/bin/env python3
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

# Try to get real Tailscale status
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
print("\nTesting TailscaleClient status_json()...")
try:
    status = TailscaleClient.status_json()
    if isinstance(status, dict):
        if "Self" in status:
            print("✅ TailscaleClient successfully retrieved real data")
            print(f"  Device name: {status['Self'].get('HostName', 'unknown')}")
            print(f"  Tailscale IPs: {', '.join(status['Self'].get('TailscaleIPs', ['none']))}")
        else:
            print("⚠️ Data retrieved but missing 'Self' information")
            print(f"  Available keys: {', '.join(status.keys())}")
    else:
        print(f"⚠️ Unexpected data type: {type(status)}")
except Exception as e:
    print(f"❌ Error in TailscaleClient.status_json(): {e}")

print("\nVerification complete!")
EOF

# Run test script
python3 "$TEST_SCRIPT"
rm "$TEST_SCRIPT"  # Clean up after testing

# Clear screen for final summary
clear

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 TailSentry Installation Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📡 TailSentry is now running and managing your Tailscale network!"
echo ""

# Get IP information for access
LOCAL_IP=$(hostname -I | awk '{print $1}')
TAILSCALE_IP=$(tailscale ip 2>/dev/null || echo "Not available")

echo "📍 Local access:     http://localhost:8000"
echo "📍 LAN access:       http://$LOCAL_IP:8000"
if [ "$TAILSCALE_IP" != "Not available" ]; then
    echo "📍 Tailscale access: http://$TAILSCALE_IP:8000"
fi

echo ""
echo "👤 Username:         admin"
echo "🔑 Password:         admin123"
echo "⚠️  IMPORTANT: Change the default password immediately after first login!"
echo ""
echo "🎯 Next Steps:"
echo "   1. Open TailSentry in your browser"
echo "   2. Login with admin / admin123"
echo "   3. Change your password in the settings"
echo "   4. Configure your Tailscale PAT if not set during installation"
echo ""
echo "💡 If you experience any issues with real Tailscale data:"
echo "   - Check TailSentry logs: tail -f $INSTALL_DIR/logs/tailsentry.log"
echo "   - Verify Tailscale status: tailscale status"
echo "   - Restart the service: sudo systemctl restart tailsentry"
echo ""
echo "🔥 TailSentry is now managing your Tailscale network!"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
