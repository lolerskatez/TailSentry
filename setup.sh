#!/bin/bash
# TailSentry Windows 98-Style CLI Installer Wizard
set -e

# ┌───────────────────────────────────────────────────────────────┐
# │                  TAILSENTRY INSTALLER WIZARD                 │
# └───────────────────────────────────────────────────────────────┘

INSTALL_DIR="/opt/tailsentry"
REPO_URL="https://github.com/lolerskatez/TailSentry.git"

function draw_box() {
  local msg="$1"
  local width=${2:-60}
  local border=""
  for ((i=0; i<$width; i++)); do border+="─"; done
  echo "┌$border┐"
  printf "│%*s%*s│\n" $(( (${#msg} + $width) / 2 )) "$msg" $(( $width - (${#msg} + $width) / 2 )) ""
  echo "└$border┘"
}

function step_header() {
  local step="$1"
  local title="$2"
  draw_box " STEP $step: $title " 60
}

function pause() {
  echo
  read -p "Press Enter to continue..." _
  echo
}

step_header 1 "SYSTEM CHECKS"
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] THIS INSTALLER MUST BE RUN AS ROOT."
  exit 1
fi
if ! command -v tailscale &> /dev/null; then
  echo "[ERROR] TAILSCALE IS NOT INSTALLED. PLEASE INSTALL IT FIRST."
  exit 1
fi
echo "[OK] SYSTEM CHECKS PASSED."
pause

step_header 2 "INSTALLING DEPENDENCIES"
echo "Updating package lists..."
apt-get update
apt-get install -y python3 python3-venv python3-pip git
echo "[OK] Dependencies installed."
pause

step_header 3 "PREPARING INSTALLATION DIRECTORY"
if [ -d "$INSTALL_DIR" ]; then
  echo "[INFO] EXISTING INSTALLATION FOUND. STOPPING SERVICE..."
  systemctl stop tailsentry.service 2>/dev/null || true
  echo "[INFO] REMOVING EXISTING INSTALLATION..."
  rm -rf "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR"
echo "[OK] Directory ready: $INSTALL_DIR"
pause

step_header 4 "DOWNLOADING TAILSENTRY"
echo "Cloning repository..."
git clone "$REPO_URL" "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo "[OK] Repository cloned."
pause

step_header 5 "SETTING UP PYTHON ENVIRONMENT"
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "[OK] Python environment ready."
pause

step_header 6 "TAILSCALE AUTHENTICATION KEY CONFIGURATION"
echo "┌───────────────────────────────────────────────────────────────┐"
echo "│  TAILSENTRY REQUIRES A TAILSCALE AUTHENTICATION KEY TO MANAGE │"
echo "│  YOUR TAILSCALE NETWORK.                                      │"
echo "│                                                               │"
echo "│  • ENTER IT NOW FOR FULL FUNCTIONALITY                        │"
echo "│  • OR SKIP AND CONFIGURE LATER IN THE DASHBOARD               │"
echo "└───────────────────────────────────────────────────────────────┘"
echo ""
echo "GET YOUR KEY AT: https://login.tailscale.com/admin/settings/keys"
echo ""
read -s -p "[STEP 6] ENTER TAILSCALE AUTHENTICATION KEY (OR PRESS ENTER TO SKIP): " TS_PAT
echo
mkdir -p config
python3 << EOF
import json
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
print(f"[OK] Saved Tailscale Authentication Key to {settings_path}")
EOF
pause

step_header 7 "INSTALLING SYSTEMD SERVICE"
cp tailsentry.service /etc/systemd/system/
echo "[OK] Service file installed."
pause

step_header 8 "NETWORK ACCESS CONFIGURATION"
echo "TailSentry can be accessed from your local and Tailscale networks."
read -p "Enable network access for local/Tailscale networks? (Y/n) [Y]: " ENABLE_NETWORK
ENABLE_NETWORK=${ENABLE_NETWORK:-Y}
if [[ $ENABLE_NETWORK =~ ^[Nn]$ ]]; then
  echo "[INFO] Configuring for localhost-only access (127.0.0.1:8080)..."
  echo "[WARNING] You'll only be able to access TailSentry from this server directly."
  sed -i 's/--host 0.0.0.0/--host 127.0.0.1/' /etc/systemd/system/tailsentry.service
else
  echo "[INFO] Configuring for network access (0.0.0.0:8080)..."
  echo "[OK] TailSentry will be accessible from local and Tailscale networks."
  # Service file already has 0.0.0.0 binding
fi
pause

step_header 9 "STARTING SERVICE"
systemctl daemon-reload
systemctl enable tailsentry.service
systemctl start tailsentry.service
echo "[OK] Service started."
pause

step_header 10 "FIREWALL CONFIGURATION"
if [[ ! $ENABLE_NETWORK =~ ^[Nn]$ ]]; then
  echo "Configuring firewall for network access..."
  if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
      echo "[OK] UFW firewall is active, adding rule for port 8080..."
      ufw allow 8080
      echo "[OK] Port 8080 has been opened in UFW firewall."
    else
      echo "[INFO] UFW firewall is installed but not active."
    fi
  elif command -v firewall-cmd &> /dev/null; then
    echo "[INFO] Configuring firewalld..."
    firewall-cmd --permanent --add-port=8080/tcp
    firewall-cmd --reload
    echo "[OK] Port 8080 has been opened in firewalld."
  else
    echo "[WARNING] No supported firewall detected (UFW or firewalld)."
    echo "[INFO] You may need to manually open port 8080 if accessing remotely."
  fi
else
  echo "[INFO] Skipping firewall configuration (localhost-only access)."
fi
pause

step_header 11 "INSTALLATION COMPLETE"
echo ""
draw_box " INSTALLATION COMPLETE! " 60
echo ""
echo "TailSentry is now running and managing your Tailscale network!"
echo ""
if [[ ! $ENABLE_NETWORK =~ ^[Nn]$ ]]; then
  echo "[ACCESS] Local:     http://localhost:8080"
  echo "[ACCESS] Network:   http://$(hostname -I | awk '{print $1}'):8080"
  echo "[ACCESS] External:  http://$(curl -s ifconfig.me 2>/dev/null || echo "your-public-ip"):8080"
else
  echo "[ACCESS] Local:     http://localhost:8080"
  echo "[ACCESS] Network:   Disabled (localhost-only)"
  echo "[INFO] To enable network access later:"
  echo "   sudo sed -i 's/127.0.0.1/0.0.0.0/' /etc/systemd/system/tailsentry.service"
  echo "   sudo systemctl daemon-reload && sudo systemctl restart tailsentry.service"
  echo "   sudo ufw allow 8080  # Open firewall for network access"
fi
echo ""
echo "[CREDENTIALS] Username: admin"
echo "[CREDENTIALS] Password: admin123"
echo "[SECURITY] IMPORTANT: Change the default password after first login!"
echo ""
echo "[NEXT STEPS] 1. Open TailSentry in your browser"
echo "[NEXT STEPS] 2. Login with admin / admin123"
echo "[NEXT STEPS] 3. Change your password in the settings"
echo "[NEXT STEPS] 4. Configure your Tailscale Authentication Key if not set during installation"
echo ""
echo "[INFO] To change password later: Visit the dashboard settings or run: python3 change_password.py"
echo ""
draw_box " TAILSENTRY IS NOW MANAGING YOUR TAILSCALE NETWORK! " 60
echo
