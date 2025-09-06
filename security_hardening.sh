#!/bin/bash
# Security hardening script for TailSentry on Linux
# Run with: chmod +x security_hardening.sh && ./security_hardening.sh

set -e  # Exit on any error

echo "🔒 TailSentry Linux Security Hardening"
echo "======================================"

# Check if running as root (should not be)
if [ "$EUID" -eq 0 ]; then
    echo "❌ ERROR: Do not run this script as root!"
    echo "   Create a dedicated user: sudo adduser tailsentry"
    exit 1
fi

# Create secure directories
echo "📁 Setting up secure directories..."
mkdir -p logs config data/acl_backups
mkdir -p services middleware routes static templates scripts

# Set secure file permissions
echo "🔐 Setting secure file permissions..."

# Configuration files (owner read/write only)
find config/ -name "*.json" -type f -exec chmod 600 {} \; 2>/dev/null || true
find . -name "*.env" -type f -exec chmod 600 {} \; 2>/dev/null || true

# Python files (owner read/write, group/others read)
find . -name "*.py" -type f -exec chmod 644 {} \;

# Scripts (owner read/write/execute, group/others read/execute)
find scripts/ -name "*.sh" -type f -exec chmod 755 {} \; 2>/dev/null || true
find . -name "*.sh" -type f -exec chmod 755 {} \;

# Log files (owner read/write only)
find logs/ -type f -exec chmod 600 {} \; 2>/dev/null || true

# Database files (owner read/write only)  
find data/ -name "*.db" -type f -exec chmod 600 {} \; 2>/dev/null || true

# Directory permissions
chmod 700 config data logs
chmod 755 services middleware routes static templates scripts

echo "🔍 Checking for exposed secrets..."

# Check for potential secrets in files
SECRETS_FOUND=false

# Discord tokens
if grep -r "discord.*token" --include="*.py" --include="*.json" --include="*.md" . 2>/dev/null | grep -v "REDACTED" | grep -v "YOUR_TOKEN" | grep -v "example"; then
    echo "⚠️  Potential Discord tokens found in files!"
    SECRETS_FOUND=true
fi

# API keys
if grep -r "api.*key" --include="*.py" --include="*.json" --include="*.md" . 2>/dev/null | grep -v "REDACTED" | grep -v "YOUR_API_KEY" | grep -v "example"; then
    echo "⚠️  Potential API keys found in files!"
    SECRETS_FOUND=true
fi

# Passwords
if grep -r "password.*=" --include="*.py" --include="*.json" . 2>/dev/null | grep -v "REDACTED" | grep -v "example" | grep -v "your_password"; then
    echo "⚠️  Potential passwords found in files!"
    SECRETS_FOUND=true
fi

if [ "$SECRETS_FOUND" = true ]; then
    echo "🚨 Please review and secure any exposed secrets!"
else
    echo "✅ No obvious secrets found in files"
fi

# Check Python environment
echo "🐍 Checking Python environment security..."

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Recommend using: python -m venv venv && source venv/bin/activate"
else
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
fi

# Check file ownership
echo "👤 Checking file ownership..."
CURRENT_USER=$(whoami)
WRONG_OWNER=$(find . -not -user "$CURRENT_USER" -type f 2>/dev/null | head -5)

if [ -n "$WRONG_OWNER" ]; then
    echo "⚠️  Some files not owned by current user:"
    echo "$WRONG_OWNER"
    echo "   Fix with: sudo chown -R $CURRENT_USER:$CURRENT_USER ."
else
    echo "✅ File ownership looks correct"
fi

# Check for world-writable files
echo "🌍 Checking for world-writable files..."
WORLD_WRITABLE=$(find . -type f -perm -002 2>/dev/null | head -5)

if [ -n "$WORLD_WRITABLE" ]; then
    echo "⚠️  World-writable files found:"
    echo "$WORLD_WRITABLE"
    echo "   Fix with: chmod o-w [filename]"
else
    echo "✅ No world-writable files found"
fi

# Create systemd service file template
echo "🚀 Creating systemd service template..."
cat > tailsentry.service.template << 'EOF'
[Unit]
Description=TailSentry Discord Bot and Dashboard
After=network.target

[Service]
Type=simple
User=tailsentry
Group=tailsentry
WorkingDirectory=/opt/tailsentry
Environment=PATH=/opt/tailsentry/venv/bin
ExecStart=/opt/tailsentry/venv/bin/python main.py
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/tailsentry/logs /opt/tailsentry/data
CapabilityBoundingSet=

# Environment security
Environment=PYTHONPATH=/opt/tailsentry
Environment=PYTHONDONTWRITEBYTECODE=1

[Install]
WantedBy=multi-user.target
EOF

echo "📋 Security hardening complete!"
echo ""
echo "🔧 Next steps:"
echo "   1. Review any warnings above"
echo "   2. Install service: sudo cp tailsentry.service.template /etc/systemd/system/tailsentry.service"
echo "   3. Enable service: sudo systemctl enable tailsentry"
echo "   4. Configure firewall: sudo ufw allow ssh && sudo ufw allow 8000 && sudo ufw enable"
echo "   5. Set up log rotation: sudo cp logrotate.conf /etc/logrotate.d/tailsentry"
echo ""
echo "✅ TailSentry security hardening completed successfully!"
