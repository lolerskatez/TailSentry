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
apt-get install -y python3 python3-venv python3-pip

# Create directory
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Clone repo or copy files
if [ -z "$REPO_URL" ]; then
  # Copy from current directory if no repo specified
  echo "Copying files..."
  cp -r . "$INSTALL_DIR"
else
  echo "Cloning repository..."
  apt-get install -y git
  git clone "$REPO_URL" .
fi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup .env file
if [ ! -f .env ]; then
  cp .env.example .env
  # Generate secure random key
  SESSION_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
  sed -i "s/SESSION_SECRET=/SESSION_SECRET=$SESSION_SECRET/" .env
  
  # Prompt for admin password
  read -s -p "Enter admin password: " ADMIN_PASS
  echo
  
  # Hash password
  ADMIN_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw('$ADMIN_PASS'.encode(), bcrypt.gensalt()).decode())")
  sed -i "s/ADMIN_PASSWORD_HASH=/ADMIN_PASSWORD_HASH=$ADMIN_HASH/" .env
  
  # Prompt for Tailscale PAT
  read -s -p "Enter Tailscale Personal Access Token (optional): " TS_PAT
  echo
  if [ ! -z "$TS_PAT" ]; then
    sed -i "s/TAILSCALE_PAT=/TAILSCALE_PAT=$TS_PAT/" .env
  fi
fi

# Install systemd service
cp tailsentry.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable tailsentry.service
systemctl start tailsentry.service

echo "TailSentry has been installed!"
echo "Open http://localhost:8080 in your browser"
echo "Log in with username: admin and the password you provided"
