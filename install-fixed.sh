#!/bin/bash
# TailSentry Installation Script (Fixed Version)

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
  
  # Prompt for admin password
  read -s -p "Enter admin password: " ADMIN_PASS
  echo
  
  # Prompt for Tailscale PAT
  read -s -p "Enter Tailscale Personal Access Token (optional): " TS_PAT
  echo
  
  # Use Python to safely update .env file with special characters
  python3 << EOF
import secrets
import bcrypt
import os

# Generate secure session secret
session_secret = secrets.token_hex(32)

# Hash the admin password
admin_hash = bcrypt.hashpw('$ADMIN_PASS'.encode(), bcrypt.gensalt()).decode()

# Read .env file
with open('.env', 'r') as f:
    content = f.read()

# Replace values safely
content = content.replace('SESSION_SECRET=', f'SESSION_SECRET={session_secret}')
content = content.replace('ADMIN_PASSWORD_HASH=', f'ADMIN_PASSWORD_HASH={admin_hash}')

# Add Tailscale PAT if provided
if '$TS_PAT':
    content = content.replace('TAILSCALE_PAT=', f'TAILSCALE_PAT=$TS_PAT')

# Write back to file
with open('.env', 'w') as f:
    f.write(content)

print("Configuration file updated successfully")
EOF
fi

# Install systemd service
cp tailsentry.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable tailsentry.service
systemctl start tailsentry.service

# Configure firewall
echo "Configuring firewall..."
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

echo "TailSentry has been installed!"
echo ""
echo "🎉 Installation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 Local access:     http://localhost:8080"
echo "📍 Network access:   http://$(hostname -I | awk '{print $1}'):8080"
echo "👤 Username:         admin"
echo "🔑 Password:         (the password you just set)"
echo ""
echo "🔥 TailSentry is now managing your Tailscale network!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
