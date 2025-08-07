#!/bin/bash
# Auto-update script for TailSentry

set -e  # Exit on any error

# Config
INSTALL_DIR="/opt/tailsentry"
REPO_URL="https://github.com/yourusername/tailsentry"  # Replace with your repo URL
LOG_FILE="/var/log/tailsentry-update.log"

# Log function
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  log "Please run as root"
  exit 1
fi

log "Starting TailSentry update..."

# Create backup
BACKUP_DIR="$INSTALL_DIR/backup_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$BACKUP_DIR"
cp -r "$INSTALL_DIR"/.env "$BACKUP_DIR/" 2>/dev/null || true
log "Backup created at $BACKUP_DIR"

# Update from git
cd "$INSTALL_DIR"
if [ -d ".git" ]; then
  log "Pulling latest changes from git..."
  git pull
else
  log "Git repository not found. Skipping update."
  exit 1
fi

# Update dependencies
log "Updating Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
log "Restarting TailSentry service..."
systemctl restart tailsentry.service

log "Update completed successfully!"
