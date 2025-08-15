#!/bin/bash
# TailSentry All-in-One Setup Script
# This script handles installation, configuration, testing, and troubleshooting
# for TailSentry on Debian-based systems.

set -e  # Exit on any error

# ANSI colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Config
INSTALL_DIR="/opt/tailsentry"
REPO_URL="https://github.com/lolerskatez/TailSentry.git"
LOG_DIR="/var/log/tailsentry"
DATA_DIR="/var/lib/tailsentry"
SERVICE_PORT=8080
DEFAULT_BRANCH="main"

# Print header banner
print_header() {
    local title="$1"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}       ${BOLD}$title${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Please run as root${NC}"
        echo "Use: sudo $0"
        exit 1
    fi
}

# Command exists function
command_exists() {
    command -v "$1" &> /dev/null
}

# Install Tailscale if needed
install_tailscale() {
    print_header "Tailscale Setup"
    
    if ! command_exists tailscale; then
        echo -e "${YELLOW}Tailscale is not installed. Installing now...${NC}"
        
        # Check if we're on Debian/Ubuntu
        if command_exists apt; then
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
        
        if ! command_exists tailscale; then
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
    
    # Ensure proper permissions
    chmod 755 "$TAILSCALE_PATH"
    
    # Check Tailscale auth status
    echo -e "\n${CYAN}Checking Tailscale authentication status...${NC}"
    if ! tailscale status &> /dev/null; then
        echo -e "${YELLOW}Tailscale is not authenticated.${NC}"
        read -p "Would you like to authenticate Tailscale now? [Y/n] " auth_response
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
        echo -e "Tailscale IP: ${CYAN}$(tailscale ip)${NC}"
    fi
}

# Install system dependencies
install_dependencies() {
    print_header "System Dependencies"
    
    if command_exists apt; then
        apt-get update
        apt-get install -y python3 python3-venv python3-pip git curl jq net-tools lsof
    else
        echo -e "${YELLOW}Non-Debian system detected. Installing minimal dependencies...${NC}"
        # For other systems, assume Python is available
        command_exists python3 || { echo -e "${RED}Python 3 required but not found${NC}"; exit 1; }
        command_exists pip3 || { echo -e "${RED}pip3 required but not found${NC}"; exit 1; }
        command_exists git || { echo -e "${RED}git required but not found${NC}"; exit 1; }
        command_exists curl || { echo -e "${RED}curl required but not found${NC}"; exit 1; }
    fi
    
    echo -e "${GREEN}System dependencies installed successfully.${NC}"
}

# Install TailSentry
install_tailsentry() {
    print_header "TailSentry Installation"
    
    # Handle existing installation
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Existing TailSentry installation found at $INSTALL_DIR${NC}"
        read -p "What would you like to do? [I]nstall fresh, [U]pgrade, [S]kip: " install_option
        install_option=${install_option:-U}
        
        case ${install_option^^} in
            I)
                echo "Stopping service..."
                systemctl stop tailsentry.service 2>/dev/null || true
                echo "Removing existing installation..."
                rm -rf "$INSTALL_DIR"
                ;;
            U)
                echo -e "${CYAN}Upgrading existing installation...${NC}"
                if [ -d "$INSTALL_DIR/.git" ]; then
                    cd "$INSTALL_DIR"
                    # Stash any local changes
                    git stash
                    # Pull the latest changes
                    git pull origin $DEFAULT_BRANCH
                    echo -e "${GREEN}Upgraded TailSentry code.${NC}"
                    
                    # Update dependencies
                    echo -e "${CYAN}Updating Python dependencies...${NC}"
                    source venv/bin/activate
                    pip install -r requirements.txt --upgrade
                    deactivate
                    
                    # Restart service
                    systemctl restart tailsentry.service
                    echo -e "${GREEN}TailSentry service restarted.${NC}"
                    return
                else
                    echo -e "${RED}Cannot upgrade, .git directory not found. Will perform fresh install.${NC}"
                    rm -rf "$INSTALL_DIR"
                fi
                ;;
            S)
                echo -e "${YELLOW}Skipping installation. Using existing installation.${NC}"
                return
                ;;
            *)
                echo -e "${RED}Invalid option. Exiting.${NC}"
                exit 1
                ;;
        esac
    fi
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    
    # Clone or copy repository
    if [ -d ".git" ] && [ "$(pwd)" != "$INSTALL_DIR" ]; then
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
    deactivate
    
    # Set appropriate permissions
    chmod 750 "$LOG_DIR"
    chmod 750 "$DATA_DIR"
    
    # Create symbolic links for data and logs
    if [ ! -L "$INSTALL_DIR/data" ]; then
        rm -rf "$INSTALL_DIR/data"
        ln -s "$DATA_DIR" "$INSTALL_DIR/data"
    fi
    
    if [ ! -L "$INSTALL_DIR/logs" ]; then
        rm -rf "$INSTALL_DIR/logs"
        ln -s "$LOG_DIR" "$INSTALL_DIR/logs"
    fi
    
    echo -e "${GREEN}TailSentry installed successfully.${NC}"
}

# Configure TailSentry
configure_tailsentry() {
    print_header "TailSentry Configuration"
    
    # Tailscale path
    TAILSCALE_PATH=$(which tailscale)
    
    # Setup .env file
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        if [ -f "$INSTALL_DIR/.env.example" ]; then
            cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
        else
            # Create minimal .env file if example doesn't exist
            cat > "$INSTALL_DIR/.env" << EOF
# TailSentry Configuration
SESSION_SECRET=$(openssl rand -hex 32)
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=  # Will be set below
DEVELOPMENT=false
USE_MOCK_DATA=false
TAILSCALE_PATH=$TAILSCALE_PATH
LOG_DIR=$LOG_DIR
DATA_DIR=$DATA_DIR
EOF
        fi
        
        # Prompt for Tailscale PAT
        clear
        print_header "TailSentry Configuration"
        echo -e "📝 TailSentry requires a Tailscale Personal Access Token (PAT) to manage"
        echo -e "   your Tailscale network. You can:"
        echo ""
        echo -e "   • Enter it now for full functionality"
        echo -e "   • Skip it and configure later in the dashboard"
        echo ""
        echo -e "🔗 Get your PAT at: https://login.tailscale.com/admin/settings/keys"
        echo ""
        read -s -p "🔑 Enter Tailscale Personal Access Token (or press Enter to skip): " TS_PAT
        echo
        
        # Use Python to update .env file
        cd "$INSTALL_DIR"
        TS_PAT="$TS_PAT" TAILSCALE_PATH="$TAILSCALE_PATH" python3 << EOF
import secrets
import bcrypt
import os

# Get the Tailscale PAT from environment if provided
ts_pat = os.environ.get('TS_PAT', '')
tailscale_path = os.environ.get('TAILSCALE_PATH', '/usr/bin/tailscale')

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
    if 'TAILSCALE_PAT=' in content:
        content = content.replace('TAILSCALE_PAT=', f'TAILSCALE_PAT={ts_pat}')
    else:
        content += f"\nTAILSCALE_PAT={ts_pat}\n"

# Make sure Tailscale path is set
if "TAILSCALE_PATH=" in content:
    content = content.replace('TAILSCALE_PATH=', f'TAILSCALE_PATH={tailscale_path}')
else:
    content += f"\nTAILSCALE_PATH={tailscale_path}\n"

# Ensure development mode and mock data are disabled
if "DEVELOPMENT=" in content:
    content = content.replace('DEVELOPMENT=true', 'DEVELOPMENT=false')
if "USE_MOCK_DATA=" in content:
    content = content.replace('USE_MOCK_DATA=true', 'USE_MOCK_DATA=false')

# Write back to file
try:
    with open('.env', 'w') as f:
        f.write(content)
    print("Configuration file updated successfully")
except Exception as e:
    print(f"Error writing .env file: {e}")
    exit(1)

print("Default admin credentials set: admin / admin123")
EOF
    else
        echo -e "${CYAN}Updating existing .env file...${NC}"
        # Update critical settings in existing .env file
        cd "$INSTALL_DIR"
        TAILSCALE_PATH="$TAILSCALE_PATH" python3 << EOF
import os

# Get the Tailscale path
tailscale_path = os.environ.get('TAILSCALE_PATH', '/usr/bin/tailscale')

# Read .env file
try:
    with open('.env', 'r') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading .env file: {e}")
    exit(1)

# Make sure Tailscale path is set
if "TAILSCALE_PATH=" in content:
    content = content.replace('TAILSCALE_PATH=', f'TAILSCALE_PATH={tailscale_path}')
else:
    content += f"\nTAILSCALE_PATH={tailscale_path}\n"

# Ensure development mode and mock data are disabled
if "DEVELOPMENT=true" in content:
    content = content.replace('DEVELOPMENT=true', 'DEVELOPMENT=false')
if "USE_MOCK_DATA=true" in content:
    content = content.replace('USE_MOCK_DATA=true', 'USE_MOCK_DATA=false')

# Write back to file
try:
    with open('.env', 'w') as f:
        f.write(content)
    print("Configuration file updated successfully")
except Exception as e:
    print(f"Error writing .env file: {e}")
    exit(1)
EOF
    fi
    
    # Set up systemd service
    echo -e "\n${CYAN}Setting up systemd service...${NC}"
    
    # Create systemd service file
    cat > /etc/systemd/system/tailsentry.service << EOF
[Unit]
Description=TailSentry - Tailscale Management Dashboard
After=network.target tailscaled.service
Requires=tailscaled.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port $SERVICE_PORT
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
    
    # Reload systemd and start service
    systemctl daemon-reload
    systemctl enable tailsentry.service
    systemctl restart tailsentry.service
    
    # Configure firewall if needed
    if command_exists ufw && ufw status | grep -q "Status: active"; then
        echo -e "${CYAN}Configuring UFW firewall for TailSentry...${NC}"
        ufw allow $SERVICE_PORT/tcp
        echo -e "Allowed port $SERVICE_PORT in UFW firewall"
    elif command_exists firewall-cmd && firewall-cmd --state | grep -q "running"; then
        echo -e "${CYAN}Configuring firewalld for TailSentry...${NC}"
        firewall-cmd --permanent --add-port=$SERVICE_PORT/tcp
        firewall-cmd --reload
        echo -e "Allowed port $SERVICE_PORT in firewalld"
    fi
    
    echo -e "${GREEN}TailSentry service configured and started.${NC}"
}

# Run diagnostics
run_diagnostics() {
    print_header "TailSentry Diagnostics"
    
    # Create a comprehensive test script
    DIAG_SCRIPT="$INSTALL_DIR/tailsentry_diagnostics.py"
    
    echo -e "${CYAN}Creating diagnostic script...${NC}"
    cat > "$DIAG_SCRIPT" << 'EOF'
#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import time
import socket
import platform
from pathlib import Path
from datetime import datetime

# Set up basic formatting
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(title):
    """Print a formatted header"""
    print(f"{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}{BOLD} {title}{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}")
    print()

def print_section(title):
    """Print a section title"""
    print(f"\n{BOLD}{title}{RESET}")
    print(f"{'-' * len(title)}")

def print_success(msg):
    """Print a success message"""
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    """Print an error message"""
    print(f"{RED}✗ {msg}{RESET}")

def print_warning(msg):
    """Print a warning message"""
    print(f"{YELLOW}! {msg}{RESET}")

def print_info(msg):
    """Print an info message"""
    print(f"  {msg}")

def run_command(cmd):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

# Start the diagnostics
print_header("TailSentry Diagnostic Tool")

print_info(f"Date and Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print_info(f"Hostname: {socket.gethostname()}")
print_info(f"Platform: {platform.platform()}")
print_info(f"Python Version: {sys.version}")
print_info(f"Working Directory: {os.getcwd()}")

# Add TailSentry path to system path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check for environment variables
print_section("Environment Variables")
env_vars = {
    'TAILSCALE_PATH': os.environ.get('TAILSCALE_PATH'),
    'USE_MOCK_DATA': os.environ.get('USE_MOCK_DATA'),
    'DEVELOPMENT': os.environ.get('DEVELOPMENT'),
    'PYTHONPATH': os.environ.get('PYTHONPATH')
}

for key, value in env_vars.items():
    if value:
        print_success(f"{key} = {value}")
    else:
        print_warning(f"{key} is not set")

# Check for .env file
print_section("Configuration Files")
env_file = Path('.env')
if env_file.exists():
    print_success(".env file exists")
    # Check for critical settings in .env
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            if 'TAILSCALE_PATH=' in content:
                print_success("TAILSCALE_PATH is configured in .env")
            else:
                print_error("TAILSCALE_PATH missing from .env")
                
            if 'DEVELOPMENT=false' in content:
                print_success("DEVELOPMENT mode is disabled")
            elif 'DEVELOPMENT=true' in content:
                print_error("DEVELOPMENT mode is enabled - will use mock data")
                
            if 'USE_MOCK_DATA=false' in content:
                print_success("USE_MOCK_DATA is disabled")
            elif 'USE_MOCK_DATA=true' in content:
                print_error("USE_MOCK_DATA is enabled - will not use real data")
    except Exception as e:
        print_error(f"Failed to read .env file: {e}")
else:
    print_error(".env file is missing")

# Try to import TailscaleClient
print_section("TailscaleClient Module")
try:
    from tailscale_client import TailscaleClient
    print_success("Successfully imported TailscaleClient")
except ImportError as e:
    print_error(f"Failed to import TailscaleClient: {e}")
    sys.exit(1)

# Try to get Tailscale path
try:
    tailscale_path = TailscaleClient.get_tailscale_path()
    print_success(f"Found Tailscale at: {tailscale_path}")
    
    # Check if file exists
    if os.path.exists(tailscale_path):
        print_success(f"Tailscale binary exists at {tailscale_path}")
        # Check permissions
        if os.access(tailscale_path, os.X_OK):
            print_success("Tailscale binary is executable")
        else:
            print_error("Tailscale binary is not executable")
    else:
        print_error(f"Tailscale binary does not exist at {tailscale_path}")
    
    # Check if path matches environment variable
    if env_vars['TAILSCALE_PATH'] and tailscale_path != env_vars['TAILSCALE_PATH']:
        print_warning(f"Path from code ({tailscale_path}) doesn't match environment variable ({env_vars['TAILSCALE_PATH']})")
except Exception as e:
    print_error(f"Failed to get Tailscale path: {e}")
    sys.exit(1)

# Try to get real Tailscale status directly
print_section("Direct Tailscale Command Test")
try:
    returncode, stdout, stderr = run_command([tailscale_path, "status", "--json"])
    
    if returncode == 0:
        print_success("Tailscale command executed successfully")
        try:
            data = json.loads(stdout)
            
            if "Self" in data:
                hostname = data['Self'].get('HostName', 'unknown')
                ips = ', '.join(data['Self'].get('TailscaleIPs', ['none']))
                peer_count = len(data.get("Peer", {}))
                
                print_success(f"Device name: {hostname}")
                print_success(f"Tailscale IPs: {ips}")
                print_success(f"Connected peers: {peer_count}")
                
                # Show first few peers
                if peer_count > 0:
                    print_info("\nSample Peers:")
                    count = 0
                    for id, peer in data.get("Peer", {}).items():
                        if count < 3:  # Show up to 3 peers
                            peer_name = peer.get('HostName', 'unknown')
                            peer_ip = ', '.join(peer.get('TailscaleIPs', ['none']))
                            print_info(f"  - {peer_name}: {peer_ip}")
                            count += 1
                        else:
                            break
            else:
                print_error("No 'Self' data found in Tailscale status")
                print_info(f"Available keys: {', '.join(data.keys())}")
        except json.JSONDecodeError:
            print_error("Failed to parse Tailscale JSON output")
            print_info(f"Raw output: {stdout[:200]}...")
    else:
        print_error(f"Tailscale command failed with code {returncode}")
        print_info(f"Error: {stderr}")
except Exception as e:
    print_error(f"Error executing Tailscale command: {e}")

# Try through TailscaleClient
print_section("TailscaleClient Method Test")
try:
    status = TailscaleClient.status_json()
    if isinstance(status, dict):
        if "Self" in status:
            hostname = status['Self'].get('HostName', 'unknown')
            ips = ', '.join(status['Self'].get('TailscaleIPs', ['none']))
            peer_count = len(status.get("Peer", {}))
            
            print_success("TailscaleClient successfully retrieved data")
            print_success(f"Device name: {hostname}")
            print_success(f"Tailscale IPs: {ips}")
            print_success(f"Connected peers: {peer_count}")
            
            # Check if this is real or mock data
            if hostname == "tailscale-server" and peer_count == 3:
                print_error("WARNING: This looks like mock data! Not real Tailscale data.")
            else:
                print_success("This appears to be real Tailscale data")
        else:
            print_error("Data retrieved but missing 'Self' information")
            print_info(f"Available keys: {', '.join(status.keys())}")
    else:
        print_error(f"Unexpected data type: {type(status)}")
except Exception as e:
    print_error(f"Error in TailscaleClient.status_json(): {e}")

# Check service status
print_section("Service Status")
returncode, stdout, stderr = run_command(["systemctl", "status", "tailsentry.service"])
if returncode == 0:
    print_success("TailSentry service is running")
else:
    print_error("TailSentry service is not running properly")
    print_info(f"Status output: {stdout}")

# Check port binding
print_section("Network Status")
returncode, stdout, stderr = run_command(["netstat", "-tlnp"])
if returncode == 0:
    print_success("Network status retrieved")
    if "8080" in stdout:
        print_success("TailSentry is listening on port 8080")
    elif "8000" in stdout:
        print_success("TailSentry is listening on port 8000")
    else:
        print_warning("TailSentry doesn't appear to be listening on standard ports")
else:
    print_error("Failed to check network status")

# Check for cache files
print_section("Cache Files")
cache_file = Path('data/tailscale_status_cache.json')
if cache_file.exists():
    print_warning(f"Cache file found: {cache_file}")
    # Check if it's real or mock data
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        if "Self" in cache_data and cache_data["Self"].get("HostName") == "tailscale-server":
            print_error("Cache contains mock data!")
        else:
            print_success("Cache appears to contain real data")
    except Exception as e:
        print_error(f"Failed to read cache file: {e}")
else:
    print_success("No cache file found (will generate fresh data)")

# Final recommendations
print_section("Diagnostic Summary")
print_info("If TailSentry is not showing real Tailscale data, try the following:")
print_info("1. Check logs: tail -f logs/tailsentry.log")
print_info("2. Make sure DEVELOPMENT=false and USE_MOCK_DATA=false in .env")
print_info("3. Delete any cache files in the data directory")
print_info("4. Restart the service: sudo systemctl restart tailsentry")
print_info("5. Clear browser cache or use incognito mode")
EOF
    
    # Make it executable
    chmod +x "$DIAG_SCRIPT"
    
    # Run the diagnostic script
    cd "$INSTALL_DIR"
    python3 "$DIAG_SCRIPT"
}

# Check for status and view logs
view_logs() {
    print_header "TailSentry Logs and Status"
    
    # Check service status
    echo -e "${CYAN}TailSentry Service Status:${NC}"
    systemctl status tailsentry.service --no-pager
    
    # Show recent logs
    echo -e "\n${CYAN}Recent TailSentry Logs:${NC}"
    if [ -f "$LOG_DIR/tailsentry.log" ]; then
        tail -n 50 "$LOG_DIR/tailsentry.log"
    else
        echo -e "${RED}Log file not found at $LOG_DIR/tailsentry.log${NC}"
    fi
}

# Main function to show menu
show_menu() {
    clear
    print_header "TailSentry Management Tool"
    
    echo -e "Choose an option:"
    echo -e "  ${BOLD}1)${NC} Install/Upgrade TailSentry"
    echo -e "  ${BOLD}2)${NC} Configure TailSentry"
    echo -e "  ${BOLD}3)${NC} Run Diagnostics"
    echo -e "  ${BOLD}4)${NC} View Logs and Status"
    echo -e "  ${BOLD}5)${NC} Fix Common Issues"
    echo -e "  ${BOLD}6)${NC} Uninstall TailSentry"
    echo -e "  ${BOLD}0)${NC} Exit"
    echo
    
    read -p "Enter your choice: " choice
    
    case $choice in
        1)
            check_root
            install_tailscale
            install_dependencies
            install_tailsentry
            configure_tailsentry
            run_diagnostics
            ;;
        2)
            check_root
            configure_tailsentry
            ;;
        3)
            run_diagnostics
            ;;
        4)
            view_logs
            ;;
        5)
            fix_common_issues
            ;;
        6)
            uninstall_tailsentry
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
    
    read -p "Press Enter to continue..."
    show_menu
}

# Fix common issues
fix_common_issues() {
    print_header "TailSentry Fix Common Issues"
    
    echo -e "Applying fixes for common TailSentry issues..."
    
    # Get Tailscale path
    TAILSCALE_PATH=$(which tailscale)
    if [ -z "$TAILSCALE_PATH" ]; then
        echo -e "${RED}Tailscale binary not found in PATH. Is Tailscale installed?${NC}"
        return
    fi
    
    echo -e "${BLUE}Found Tailscale at: ${GREEN}$TAILSCALE_PATH${NC}"
    
    # 1. Fix permissions on Tailscale binary
    echo -e "${CYAN}Setting permissions on Tailscale binary...${NC}"
    chmod 755 "$TAILSCALE_PATH"
    
    # 2. Clear cache files
    echo -e "${CYAN}Clearing cache files...${NC}"
    CACHE_FILE="$INSTALL_DIR/data/tailscale_status_cache.json"
    if [ -f "$CACHE_FILE" ]; then
        rm "$CACHE_FILE"
        echo "Removed cache file: $CACHE_FILE"
    fi
    
    # 3. Update .env file to disable mock data and development mode
    echo -e "${CYAN}Updating .env configuration...${NC}"
    if [ -f "$INSTALL_DIR/.env" ]; then
        # Update settings
        cd "$INSTALL_DIR"
        TAILSCALE_PATH="$TAILSCALE_PATH" python3 << EOF
import os

# Get the Tailscale path
tailscale_path = os.environ.get('TAILSCALE_PATH', '/usr/bin/tailscale')

# Read .env file
try:
    with open('.env', 'r') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading .env file: {e}")
    exit(1)

# Make sure Tailscale path is set
if "TAILSCALE_PATH=" in content:
    content = content.replace('TAILSCALE_PATH=', f'TAILSCALE_PATH={tailscale_path}')
else:
    content += f"\nTAILSCALE_PATH={tailscale_path}\n"

# Ensure development mode and mock data are disabled
if "DEVELOPMENT=true" in content:
    content = content.replace('DEVELOPMENT=true', 'DEVELOPMENT=false')
elif "DEVELOPMENT=" not in content:
    content += "\nDEVELOPMENT=false\n"
    
if "USE_MOCK_DATA=true" in content:
    content = content.replace('USE_MOCK_DATA=true', 'USE_MOCK_DATA=false')
elif "USE_MOCK_DATA=" not in content:
    content += "\nUSE_MOCK_DATA=false\n"

# Write back to file
try:
    with open('.env', 'w') as f:
        f.write(content)
    print("Configuration file updated successfully")
except Exception as e:
    print(f"Error writing .env file: {e}")
    exit(1)
EOF
    fi
    
    # 4. Update service file to include environment variables
    echo -e "${CYAN}Updating service file...${NC}"
    cat > /etc/systemd/system/tailsentry.service << EOF
[Unit]
Description=TailSentry - Tailscale Management Dashboard
After=network.target tailscaled.service
Requires=tailscaled.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port $SERVICE_PORT
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
    
    # 5. Reload systemd and restart service
    echo -e "${CYAN}Reloading systemd and restarting service...${NC}"
    systemctl daemon-reload
    systemctl restart tailsentry.service
    
    # 6. Print success
    echo -e "${GREEN}Fixes applied successfully!${NC}"
    echo -e "TailSentry should now be using real Tailscale data."
    echo -e "You may need to clear your browser cache or use incognito mode to see the changes."
}

# Uninstall TailSentry
uninstall_tailsentry() {
    print_header "Uninstall TailSentry"
    
    read -p "Are you sure you want to uninstall TailSentry? [y/N] " confirm
    confirm=${confirm:-N}
    
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo "Uninstall cancelled."
        return
    fi
    
    echo -e "${YELLOW}Stopping TailSentry service...${NC}"
    systemctl stop tailsentry.service 2>/dev/null || true
    systemctl disable tailsentry.service 2>/dev/null || true
    rm -f /etc/systemd/system/tailsentry.service
    systemctl daemon-reload
    
    echo -e "${YELLOW}Removing TailSentry files...${NC}"
    rm -rf "$INSTALL_DIR"
    
    read -p "Do you want to also remove logs and data? [y/N] " remove_data
    remove_data=${remove_data:-N}
    
    if [[ $remove_data =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Removing logs and data...${NC}"
        rm -rf "$LOG_DIR"
        rm -rf "$DATA_DIR"
    else
        echo -e "${CYAN}Logs and data preserved at:${NC}"
        echo -e "  - Logs: $LOG_DIR"
        echo -e "  - Data: $DATA_DIR"
    fi
    
    read -p "Do you want to uninstall Tailscale as well? [y/N] " remove_tailscale
    remove_tailscale=${remove_tailscale:-N}
    
    if [[ $remove_tailscale =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Uninstalling Tailscale...${NC}"
        if command_exists apt; then
            apt-get remove -y tailscale
        else
            echo -e "${RED}Automatic uninstall not supported for your system.${NC}"
            echo -e "Please uninstall Tailscale manually if needed."
        fi
    fi
    
    echo -e "${GREEN}TailSentry has been uninstalled.${NC}"
}

# Process command line arguments
process_args() {
    # Check if any arguments are provided
    if [ $# -eq 0 ]; then
        show_menu
        return
    fi
    
    # Process arguments
    case "$1" in
        install|--install)
            check_root
            install_tailscale
            install_dependencies
            install_tailsentry
            configure_tailsentry
            ;;
        upgrade|--upgrade)
            check_root
            install_dependencies
            install_tailsentry
            configure_tailsentry
            ;;
        diagnose|--diagnose)
            run_diagnostics
            ;;
        fix|--fix)
            check_root
            fix_common_issues
            ;;
        logs|--logs)
            view_logs
            ;;
        uninstall|--uninstall)
            check_root
            uninstall_tailsentry
            ;;
        help|--help)
            echo "Usage: $0 [OPTION]"
            echo ""
            echo "Options:"
            echo "  install, --install     Install or upgrade TailSentry"
            echo "  upgrade, --upgrade     Upgrade existing TailSentry installation"
            echo "  diagnose, --diagnose   Run diagnostics on TailSentry installation"
            echo "  fix, --fix             Fix common issues with TailSentry"
            echo "  logs, --logs           View TailSentry logs and status"
            echo "  uninstall, --uninstall Uninstall TailSentry"
            echo "  help, --help           Show this help message"
            echo ""
            echo "If no option is provided, an interactive menu will be shown."
            ;;
        *)
            echo -e "${RED}Invalid option: $1${NC}"
            echo "Use '$0 --help' for usage information."
            exit 1
            ;;
    esac
}

# Execute main functionality based on arguments
process_args "$@"

exit 0
