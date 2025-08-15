#!/bin/bash
# TailSentry Uninstall Script
# Completely removes TailSentry installation

set -e

echo "🗑️  TailSentry Uninstall Script"
echo "==============================="
echo "⚠️  This will completely remove TailSentry from your system."
echo ""
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 1
fi

echo ""
echo "1. Stopping TailSentry service..."
sudo systemctl stop tailsentry 2>/dev/null || {
    echo "⚠️  Service not running or not found"
}

echo ""
echo "2. Disabling TailSentry service..."
sudo systemctl disable tailsentry 2>/dev/null || {
    echo "⚠️  Service not enabled or not found"
}

echo ""
echo "3. Removing systemd service file..."
sudo rm -f /etc/systemd/system/tailsentry.service
sudo systemctl daemon-reload

echo ""
echo "4. Killing any running TailSentry processes..."
pkill -f "uvicorn.*tailsentry" 2>/dev/null || echo "No running processes found"
pkill -f "python.*main.py" 2>/dev/null || echo "No main.py processes found"

echo ""
echo "5. Removing TailSentry directory..."
if [ -d "/opt/tailsentry" ]; then
    sudo rm -rf /opt/tailsentry
    echo "✅ Removed /opt/tailsentry"
else
    echo "⚠️  /opt/tailsentry not found"
fi

echo ""
echo "6. Removing logs..."
if [ -d "/var/log/tailsentry" ]; then
    sudo rm -rf /var/log/tailsentry
    echo "✅ Removed /var/log/tailsentry"
else
    echo "⚠️  /var/log/tailsentry not found"
fi

echo ""
echo "7. Removing logrotate configuration..."
if [ -f "/etc/logrotate.d/tailsentry" ]; then
    sudo rm -f /etc/logrotate.d/tailsentry
    echo "✅ Removed logrotate configuration"
else
    echo "⚠️  Logrotate configuration not found"
fi

echo ""
echo "8. Checking for firewall rules..."
# Check if ufw is active and has tailsentry rules
if command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "8080"; then
    echo "Found firewall rule for port 8080. Removing..."
    sudo ufw delete allow 8080 2>/dev/null || echo "Could not remove firewall rule"
fi

echo ""
echo "9. Removing TailSentry user (if exists)..."
if id "tailsentry" &>/dev/null; then
    sudo userdel -r tailsentry 2>/dev/null || echo "Could not remove user"
    echo "✅ Removed tailsentry user"
else
    echo "⚠️  tailsentry user not found"
fi

echo ""
echo "10. Cleaning up any remaining files..."
# Remove any remaining config files
sudo rm -f /etc/tailsentry.conf 2>/dev/null || true
sudo rm -f /etc/default/tailsentry 2>/dev/null || true

# Remove any cron jobs
sudo crontab -l 2>/dev/null | grep -v tailsentry | sudo crontab - 2>/dev/null || true

echo ""
echo "🎉 TailSentry Uninstall Complete!"
echo "=================================="
echo "TailSentry has been completely removed from your system."
echo ""
echo "To reinstall TailSentry:"
echo "  1. Clone the repository:"
echo "     git clone https://github.com/lolerskatez/TailSentry.git"
echo "  2. Run the installation script:"
echo "     cd TailSentry && sudo bash install.sh"
echo ""
echo "Note: This script did not remove any Tailscale configuration."
echo "Your Tailscale installation remains unchanged."
