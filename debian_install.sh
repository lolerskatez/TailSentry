#!/bin/bash
# TailSentry Deployment Script for Debian 12
# This script will set up TailSentry on a Debian 12 system with Tailscale installed

set -e  # Exit on any error

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Check if Tailscale is installed
if ! command -v tailscale &> /dev/null; then
    echo "Tailscale is not installed. Installing now..."
    # Add Tailscale's GPG key and repository
    curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
    curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list
    
    # Update and install
    apt-get update
    apt-get install -y tailscale
    
    # Start Tailscale service
    systemctl enable --now tailscaled
    
    echo "Tailscale installed. Please authenticate with 'sudo tailscale up' before continuing."
    echo "Press Enter when ready to continue..."
    read
fi

# Create application directory
APP_DIR="/opt/tailsentry"
mkdir -p $APP_DIR

# Copy TailSentry files
echo "Copying TailSentry files to $APP_DIR..."
cp -r * $APP_DIR/
cd $APP_DIR

# Create Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create data directory with proper permissions
mkdir -p $APP_DIR/data
chmod 750 $APP_DIR/data

# Create logs directory with proper permissions
mkdir -p $APP_DIR/logs
chmod 750 $APP_DIR/logs

# Setup systemd service
echo "Setting up TailSentry service..."
cat > /etc/systemd/system/tailsentry.service << EOF
[Unit]
Description=TailSentry - Tailscale Management Dashboard
After=network.target tailscaled.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
systemctl daemon-reload
systemctl enable tailsentry.service
systemctl start tailsentry.service

echo "TailSentry installation complete!"
echo "Dashboard available at http://localhost:8000"
echo ""
echo "Initial login credentials:"
echo "Username: admin"
echo "Password: Please set it using the change_password.py script"
echo ""
echo "Run the following to set your admin password:"
echo "cd $APP_DIR && python change_password.py admin"
