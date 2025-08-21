#!/bin/bash
# TailSentry Quick Install Script
# Simple one-liner installer for quick deployments

set -e

INSTALL_DIR="/opt/tailsentry"
REPO_URL="https://github.com/lolerskatez/TailSentry.git"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check root
if [[ "$EUID" -ne 0 ]]; then
    error "Please run as root (use sudo)"
    exit 1
fi

# Download full installer
info "Downloading TailSentry installer..."
curl -fsSL https://raw.githubusercontent.com/lolerskatez/TailSentry/main/tailsentry-installer -o /tmp/tailsentry-installer
chmod +x /tmp/tailsentry-installer

# Run installer
info "Running installer..."
/tmp/tailsentry-installer install

# Cleanup
rm -f /tmp/tailsentry-installer

success "TailSentry installation completed!"
echo ""
echo "Next steps:"
echo "1. Configure Tailscale settings in the web interface"
echo "2. Access TailSentry at: http://localhost:8080"
echo "3. Default login: admin/admin (change immediately)"
echo ""
echo "Manage TailSentry with: tailsentry-installer [command]"
