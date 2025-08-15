#!/bin/bash
# TailSentry Installation Script

set -e  # Exit on any error

# Config
INSTALL_DIR="/opt/tailsentry"
REPO_URL="https://github.com/lolerskatez/TailSentry.git"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Check for Tailscale
if ! command -v tailscale &> /dev/null; then
  echo "Tailscale is not installed. Please install it first."
  exit 1
fi

echo "Installing TailSentry..."

# Install dependencies
apt-get update
apt-get install -y python3 python3-venv python3-pip git

# Handle existing installation
if [ -d "$INSTALL_DIR" ]; then
  echo "Existing TailSentry installation found. Stopping service..."
  systemctl stop tailsentry.service 2>/dev/null || true
  echo "Removing existing installation..."
  rm -rf "$INSTALL_DIR"
fi

# Create fresh installation directory
mkdir -p "$INSTALL_DIR"

# Clone repository
echo "Downloading TailSentry..."
git clone "$REPO_URL" "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup .env file
if [ ! -f .env ]; then
  cp .env.example .env
  
  # Clear screen and prompt for Tailscale PAT
  clear
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔧 TailSentry Configuration"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
  
  # Use Python to safely update .env file with default password
  TS_PAT="$TS_PAT" python3 << EOF
import secrets
import bcrypt
import os

# Get the Tailscale PAT from environment if provided
ts_pat = os.environ.get('TS_PAT', '')

# Generate secure session secret
session_secret = secrets.token_hex(32)

# Generate default password hash for "admin123"
default_password = "admin123"
password_hash = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt()).decode()

# Read .env file
try:
    with open('.env', 'r') as f:
        content = f.read()
    print(f"Read .env file successfully ({len(content)} bytes)")
except Exception as e:
    print(f"Error reading .env file: {e}")
    exit(1)

# Replace session secret and set default admin credentials
content = content.replace('SESSION_SECRET=', f'SESSION_SECRET={session_secret}')
content = content.replace('ADMIN_USERNAME=admin', f'ADMIN_USERNAME=admin')
content = content.replace('ADMIN_PASSWORD_HASH=', f'ADMIN_PASSWORD_HASH={password_hash}')
content = content.replace('DEVELOPMENT=false', 'DEVELOPMENT=true')

# Add Tailscale PAT if provided
if ts_pat:
    content = content.replace('TAILSCALE_PAT=', f'TAILSCALE_PAT={ts_pat}')

# Write back to file
try:
    with open('.env', 'w') as f:
        f.write(content)
    print(f"Wrote .env file successfully ({len(content)} bytes)")
except Exception as e:
    print(f"Error writing .env file: {e}")
    exit(1)

print("Configuration file updated successfully")
print("Default admin credentials set: admin / admin123")
print("DEVELOPMENT=true set (enables HTTP session cookies for local/Tailscale networks)")
EOF
fi

# Install systemd service
cp tailsentry.service /etc/systemd/system/

# Ask user about network access
echo ""
echo "TailSentry is designed to be accessed from your local and Tailscale networks."
read -p "Enable network access for local/Tailscale networks? (Y/n) [Y]: " ENABLE_NETWORK
ENABLE_NETWORK=${ENABLE_NETWORK:-Y}

if [[ $ENABLE_NETWORK =~ ^[Nn]$ ]]; then
  echo "Configuring for localhost-only access (127.0.0.1:8080)..."
  echo "⚠️  Note: You'll only be able to access TailSentry from this server directly."
  sed -i 's/--host 0.0.0.0/--host 127.0.0.1/' /etc/systemd/system/tailsentry.service
else
  echo "Configuring for network access (0.0.0.0:8080)..."
  echo "✅ TailSentry will be accessible from local and Tailscale networks"
  # Service file already has 0.0.0.0 binding
fi

systemctl daemon-reload
systemctl enable tailsentry.service
systemctl start tailsentry.service

# Configure firewall
if [[ ! $ENABLE_NETWORK =~ ^[Nn]$ ]]; then
  echo "Configuring firewall for network access..."
  if command -v ufw &> /dev/null; then
    # UFW is installed
    if ufw status | grep -q "Status: active"; then
      echo "UFW firewall is active, adding rule for port 8080..."
      ufw allow 8080
      echo "Port 8080 has been opened in UFW firewall"
    else
      echo "UFW firewall is installed but not active"
    fi
  elif command -v firewall-cmd &> /dev/null; then
    # firewalld (CentOS/RHEL/Fedora)
    echo "Configuring firewalld..."
    firewall-cmd --permanent --add-port=8080/tcp
    firewall-cmd --reload
    echo "Port 8080 has been opened in firewalld"
  else
    echo "No supported firewall detected (UFW or firewalld)"
    echo "You may need to manually open port 8080 if accessing remotely"
  fi
else
  echo "Skipping firewall configuration (localhost-only access)"
fi

# Clear screen for final summary
clear

echo "🎉 Installation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📡 TailSentry is now running and managing your Tailscale network!"
echo ""

if [[ ! $ENABLE_NETWORK =~ ^[Nn]$ ]]; then
  echo "📍 Local access:     http://localhost:8080"
  echo "📍 Network access:   http://$(hostname -I | awk '{print $1}'):8080"
  echo "🌐 External access:  http://$(curl -s ifconfig.me 2>/dev/null || echo "your-public-ip"):8080"
else
  echo "📍 Local access:     http://localhost:8080"
  echo "🔒 Network access:   Disabled (localhost-only)"
  echo "💡 To enable network access later:"
  echo "   sudo sed -i 's/127.0.0.1/0.0.0.0/' /etc/systemd/system/tailsentry.service"
  echo "   sudo systemctl daemon-reload && sudo systemctl restart tailsentry.service"
  echo "   sudo ufw allow 8080  # Open firewall for network access"
fi

echo "👤 Username:         admin"
echo "🔑 Password:         admin123"
echo "⚠️  IMPORTANT: Change the default password after first login!"
echo ""
echo "🎯 Next Steps:"
echo "   1. Open TailSentry in your browser"
echo "   2. Login with admin / admin123"
echo "   3. Change your password in the settings"
echo "   4. Configure your Tailscale PAT if not set during installation"
echo ""
echo "🔧 To change password later:"
echo "   Visit the dashboard settings or run: python3 change_password.py"
echo ""
echo "🔥 TailSentry is now managing your Tailscale network!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
