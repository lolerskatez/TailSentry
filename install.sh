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

# Prompt for Tailscale PAT and save to tailscale_settings.json
clear
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 TailSentry Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 TailSentry requires a Tailscale Authentication Key to manage your Tailscale network."
echo "   You can:"
echo "   • Enter it now for full functionality"
echo "   • Skip it and configure later in the dashboard"
echo ""
echo "🔗 Get your Tailscale Authentication Key at: https://login.tailscale.com/admin/settings/keys"
echo ""
echo

tskey = os.environ.get('TS_PAT', '') or '''$TS_PAT'''
read -s -p "🔑 Enter Tailscale Authentication Key (or press Enter to skip): " TS_PAT
echo
# Save the Tailscale Authentication Key as 'auth_key' in config/tailscale_settings.json
mkdir -p config
python3 << EOF
import os
tskey = os.environ.get('TS_PAT', '') or '''$TS_PAT'''
config_dir = os.path.join(os.getcwd(), 'config')
settings_path = os.path.join(config_dir, 'tailscale_settings.json')
os.makedirs(config_dir, exist_ok=True)
if os.path.exists(settings_path):
  try:
    with open(settings_path, 'r') as f:
      settings = json.load(f)
  except Exception:
    settings = {}
else:
  settings = {}
if tskey:
  settings['auth_key'] = tskey
with open(settings_path, 'w') as f:
  json.dump(settings, f, indent=2)
print(f"Saved Tailscale Authentication Key to {settings_path}")
EOF

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
echo "   4. Configure your Tailscale Authentication Key if not set during installation"
echo ""
echo "🔧 To change password later:"
echo "   Visit the dashboard settings or run: python3 change_password.py"
echo ""
echo "🔥 TailSentry is now managing your Tailscale network!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
