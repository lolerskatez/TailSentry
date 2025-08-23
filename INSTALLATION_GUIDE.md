# TailSentry Installation Guide

This comprehensive guide covers all installation methods for TailSentry, including system requirements, installation options, configuration, and troubleshooting.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Installation Methods](#installation-methods)
4. [Configuration](#configuration)
5. [Management](#management)
6. [Troubleshooting](#troubleshooting)
7. [Security](#security)
8. [Backup and Recovery](#backup-and-recovery)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+, Fedora 34+)
- **Python**: 3.9 or higher
- **Memory**: Minimum 512MB RAM, 1GB+ recommended
- **Storage**: 1GB+ free space
- **Network**: Internet access for installation and updates
- **Processor**: x86_64 architecture

### Required Software

Before installing TailSentry, ensure these components are available:

- **Tailscale**: Must be installed and configured
- **Git**: For downloading the application
- **Python 3**: With pip and venv support
- **systemd**: For service management
- **curl**: For health checks and downloads

### Tailscale Setup

1. Install Tailscale on your system:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```

2. Authenticate with your Tailnet:
   ```bash
   sudo tailscale up
   ```

3. Get a Personal Access Token (PAT) from [Tailscale Admin Console](https://login.tailscale.com/admin/settings/keys)

## Quick Start

The fastest way to get TailSentry running:

```bash
# Download the setup script
wget https://raw.githubusercontent.com/lolerskatez/TailSentry/main/setup.sh

# Verify you have the correct version (should be 2.0.1+)
chmod +x setup.sh
./setup.sh --version

# If version is older than 2.0.1, force refresh:
wget https://raw.githubusercontent.com/lolerskatez/TailSentry/main/setup.sh?$(date +%s) -O setup.sh

# Run interactive installation
sudo ./setup.sh
```

Choose option 1 (Fresh Install) from the menu and follow the prompts.

## Installation Methods

### Method 1: Interactive Installation (Recommended)

The interactive setup script provides a user-friendly menu with multiple options:

```bash
sudo ./setup.sh
```

**Available Options:**

1. **Fresh Install** - New installation (fails safely if already exists)
2. **Install with Override** - ⚠️ Complete reinstall (destroys all data)
3. **Update/Upgrade** - Preserve data, apply updates
4. **Uninstall** - Remove TailSentry completely
5. **Show Status** - Detailed installation status
6. **Service Management** - Start/stop/restart service
7. **Backup Management** - Create/restore backups
8. **View Installation Guide** - This guide

### Method 2: Command Line Installation

For automation or scripting, use direct commands:

```bash
# Fresh installation
sudo ./setup.sh install

# Update existing installation
sudo ./setup.sh update

# Complete reinstall (destroys data)
sudo ./setup.sh install-override

# Remove installation
sudo ./setup.sh uninstall

# Show status
sudo ./setup.sh status
```

### Method 3: Manual Installation

For advanced users who want full control:

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git curl logrotate

# Clone repository
sudo git clone https://github.com/lolerskatez/TailSentry.git /opt/tailsentry
cd /opt/tailsentry

# Setup Python environment
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt

# Configure application (see Configuration section)
# Install service (see Service Management section)
```

## Configuration

### Environment Variables

TailSentry uses a `.env` file for configuration. The setup script creates this automatically, but you can customize it:

```bash
# Edit configuration
sudo nano /opt/tailsentry/.env
```

**Key Settings:**

```bash
# Security
SESSION_SECRET='your-32-char-secret'
SESSION_TIMEOUT_MINUTES=30
DEVELOPMENT=false

# Application
LOG_LEVEL=INFO
TAILSENTRY_DATA_DIR='/opt/tailsentry/data'

# Tailscale Integration
TAILSCALE_TAILNET='-'
TAILSCALE_API_TIMEOUT=10

# Health Check
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=300

# Backup
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
```

### Tailscale Configuration

Configure Tailscale integration during installation or later through the web interface:

1. **During Installation**: Enter your Tailscale PAT when prompted
2. **After Installation**: Configure in Settings > System > Tailscale Settings

### Network Configuration

The installer offers two network access modes:

- **Network Access** (default): Accessible from local and Tailscale networks (0.0.0.0:8080)
- **Local Only**: Restricted to localhost (127.0.0.1:8080)

To change after installation:
```bash
# Enable network access
sudo sed -i 's/127.0.0.1/0.0.0.0/' /etc/systemd/system/tailsentry.service
sudo systemctl daemon-reload && sudo systemctl restart tailsentry

# Restrict to localhost
sudo sed -i 's/0.0.0.0/127.0.0.1/' /etc/systemd/system/tailsentry.service
sudo systemctl daemon-reload && sudo systemctl restart tailsentry
```

## Management

### Service Management

TailSentry runs as a systemd service:

```bash
# Check status
sudo systemctl status tailsentry

# Start/stop/restart
sudo systemctl start tailsentry
sudo systemctl stop tailsentry
sudo systemctl restart tailsentry

# Enable/disable auto-start
sudo systemctl enable tailsentry
sudo systemctl disable tailsentry

# View logs
sudo journalctl -u tailsentry -f
```

### Using the Setup Script

The setup script provides convenient management options:

```bash
# Interactive service management
sudo ./setup.sh
# Choose option 6: Service Management

# Direct commands
sudo ./setup.sh status
```

### Web Interface

Access TailSentry through your web browser:

- **Local**: http://localhost:8080
- **Network**: http://YOUR_SERVER_IP:8080
- **Tailscale**: http://YOUR_TAILSCALE_IP:8080

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

⚠️ **Important**: Change the default password immediately after first login!

### Firewall Configuration

The installer automatically configures common firewalls:

**UFW (Ubuntu):**
```bash
sudo ufw allow 8080
```

**firewalld (CentOS/RHEL/Fedora):**
```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check service status
sudo systemctl status tailsentry

# Check logs
sudo journalctl -u tailsentry -n 50

# Check configuration
sudo ./setup.sh status
```

#### 2. Can't Access Web Interface

- Verify service is running: `sudo systemctl status tailsentry`
- Check firewall: `sudo ufw status` or `sudo firewall-cmd --list-ports`
- Verify port isn't in use: `sudo netstat -tlnp | grep :8080`

#### 3. Tailscale Integration Issues

- Check Tailscale status: `sudo tailscale status`
- Verify PAT in web interface: Settings > System > Tailscale Settings
- Check socket permissions: `ls -la /var/run/tailscale/`

#### 4. Python/Dependency Issues

```bash
# Reinstall dependencies
cd /opt/tailsentry
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -r requirements.txt
```

#### 5. Permission Issues

```bash
# Fix ownership
sudo chown -R root:root /opt/tailsentry

# Fix permissions
sudo chmod 755 /opt/tailsentry
sudo chmod 600 /opt/tailsentry/config/*.json
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Edit configuration
sudo nano /opt/tailsentry/.env

# Set these values:
# LOG_LEVEL=DEBUG
# DEVELOPMENT=true

# Restart service
sudo systemctl restart tailsentry

# Watch logs
sudo journalctl -u tailsentry -f
```

### Log Files

TailSentry logs to multiple locations:

- **Service logs**: `sudo journalctl -u tailsentry`
- **Application logs**: `/opt/tailsentry/logs/tailsentry.log`
- **Installation logs**: `/tmp/tailsentry-setup.log`

## Security

### Best Practices

1. **Change Default Password**: Immediately after installation
2. **Use Strong Passwords**: Minimum 12 characters, mixed case, numbers, symbols
3. **Regular Updates**: Keep TailSentry and system updated
4. **Firewall**: Only allow necessary ports
5. **Monitoring**: Regularly check logs for suspicious activity

### Security Configuration

```bash
# Generate secure session secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env file with new secret
sudo nano /opt/tailsentry/.env
```

### Access Control

- TailSentry includes built-in authentication
- Configure user accounts through the web interface
- Use Tailscale ACLs to limit network access

## Backup and Recovery

### Automatic Backups

The setup script provides comprehensive backup functionality:

```bash
# Create manual backup
sudo ./setup.sh
# Choose option 7: Backup Management > Create backup

# List available backups
sudo ./setup.sh
# Choose option 7: Backup Management > List backups

# Restore from backup
sudo ./setup.sh
# Choose option 7: Backup Management > Restore from backup
```

### Backup Locations

- **Backups**: `/opt/tailsentry-backups/`
- **Retention**: Automatically keeps last 5 backups
- **Format**: Compressed tar archives with timestamps

### Manual Backup

```bash
# Create backup directory
sudo mkdir -p /opt/tailsentry-backups

# Stop service
sudo systemctl stop tailsentry

# Create backup
sudo tar -czf /opt/tailsentry-backups/manual-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
    -C /opt tailsentry

# Restart service
sudo systemctl start tailsentry
```

### Disaster Recovery

1. **Install TailSentry** on new system
2. **Stop service**: `sudo systemctl stop tailsentry`
3. **Restore backup**: Extract backup to `/opt/tailsentry`
4. **Fix permissions**: `sudo chown -R root:root /opt/tailsentry`
5. **Start service**: `sudo systemctl start tailsentry`

## Updating TailSentry

### Using Setup Script (Recommended)

```bash
sudo ./setup.sh update
```

This preserves your configuration and data while updating the application.

### Manual Update

```bash
# Stop service
sudo systemctl stop tailsentry

# Backup current installation
sudo cp -r /opt/tailsentry /opt/tailsentry-backup-$(date +%Y%m%d)

# Update code
cd /opt/tailsentry
sudo git pull origin main

# Update dependencies
sudo venv/bin/pip install -r requirements.txt

# Restart service
sudo systemctl start tailsentry
```

## Uninstalling TailSentry

### Complete Removal

```bash
sudo ./setup.sh uninstall
```

This removes:
- Application files
- Service configuration
- User data and configuration
- Logs (backups are preserved)

### Manual Removal

```bash
# Stop and disable service
sudo systemctl stop tailsentry
sudo systemctl disable tailsentry

# Remove files
sudo rm -rf /opt/tailsentry
sudo rm -f /etc/systemd/system/tailsentry.service
sudo rm -f /etc/logrotate.d/tailsentry

# Clean systemd
sudo systemctl daemon-reload
```

## Support and Resources

- **GitHub Repository**: https://github.com/lolerskatez/TailSentry
- **Issues**: https://github.com/lolerskatez/TailSentry/issues
- **Documentation**: https://github.com/lolerskatez/TailSentry/wiki
- **Tailscale Documentation**: https://tailscale.com/docs/

## Appendix

### System Service File

Location: `/etc/systemd/system/tailsentry.service`

```ini
[Unit]
Description=TailSentry Dashboard
After=network.target tailscaled.service
Requires=tailscaled.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/tailsentry
ExecStart=/opt/tailsentry/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
Environment=PATH=/opt/tailsentry/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/opt/tailsentry

[Install]
WantedBy=multi-user.target
```

### Directory Structure

```
/opt/tailsentry/
├── config/                 # Configuration files
│   ├── tailscale_settings.json
│   └── tailsentry_config.json
├── data/                   # Application data
│   └── users.db
├── logs/                   # Log files
│   └── tailsentry.log
├── venv/                   # Python virtual environment
├── .env                    # Environment configuration
├── main.py                 # Main application file
├── requirements.txt        # Python dependencies
└── tailsentry.service      # SystemD service file
```

This guide provides comprehensive coverage of TailSentry installation and management. For additional help, please refer to the GitHub repository or create an issue for support.
