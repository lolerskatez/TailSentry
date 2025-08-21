# TailSentry Installation Guide

This guide covers all installation methods for TailSentry, including bare metal Linux installation, Docker deployment, and management.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Installation](#quick-installation)
3. [Manual Installation](#manual-installation)
4. [Docker Installation](#docker-installation)
5. [Configuration](#configuration)
6. [Management Commands](#management-commands)
7. [Troubleshooting](#troubleshooting)
8. [Upgrading](#upgrading)
9. [Uninstallation](#uninstallation)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+, or similar)
- **Python**: 3.9 or higher
- **Memory**: Minimum 512MB RAM, 1GB+ recommended
- **Storage**: 1GB+ free space
- **Network**: Internet access for installation and updates

### Required Software

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

## Quick Installation

The fastest way to install TailSentry:

```bash
# Download and run the quick installer
curl -fsSL https://raw.githubusercontent.com/lolerskatez/TailSentry/main/quick-install.sh | sudo bash
```

This will:
- Download the full installer
- Install system dependencies
- Set up TailSentry with default configuration
- Start the service automatically

## Manual Installation

### Step 1: Download the Installer

```bash
# Download the installer
curl -fsSL https://raw.githubusercontent.com/lolerskatez/TailSentry/main/tailsentry-installer -o /usr/local/bin/tailsentry-installer

# Make it executable
chmod +x /usr/local/bin/tailsentry-installer
```

### Step 2: Run Installation

```bash
# Interactive installation
sudo tailsentry-installer

# Or direct installation
sudo tailsentry-installer install
```

### Step 3: Configure TailSentry

1. **Access the web interface**: http://localhost:8080
2. **Default credentials**: admin/admin (change immediately!)
3. **Configure Tailscale settings** in the web interface

## Docker Installation

### Option 1: Using Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/lolerskatez/TailSentry.git
   cd TailSentry
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   nano .env  # Configure your settings
   ```

3. **Start TailSentry**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Option 2: Using Docker Run

```bash
# Create volumes
docker volume create tailsentry_data
docker volume create tailsentry_logs
docker volume create tailsentry_config

# Run container
docker run -d \
  --name tailsentry \
  --restart unless-stopped \
  -p 8080:8080 \
  -v tailsentry_data:/app/data \
  -v tailsentry_logs:/app/logs \
  -v tailsentry_config:/app/config \
  -v /var/run/tailscale/tailscaled.sock:/var/run/tailscale/tailscaled.sock:ro \
  -e SESSION_SECRET="$(openssl rand -hex 32)" \
  tailsentry:latest
```

### Option 3: Docker Deploy Script

```bash
# Download the deploy script
curl -fsSL https://raw.githubusercontent.com/lolerskatez/TailSentry/main/docker-deploy.sh -o docker-deploy.sh
chmod +x docker-deploy.sh

# Deploy TailSentry
./docker-deploy.sh up
```

## Configuration

### Environment Variables (Docker)

Key environment variables for Docker deployment:

```bash
# Required
SESSION_SECRET=your-32-char-hex-string
TAILSCALE_PAT=tskey-auth-xxxxxxxxxx
ADMIN_PASSWORD_HASH=hashed-password

# Optional
TZ=UTC
LOG_LEVEL=INFO
SESSION_TIMEOUT_MINUTES=30
MAX_LOGIN_ATTEMPTS=5
```

### Configuration Files (Bare Metal)

Configuration files are located in `/opt/tailsentry/config/`:

- `tailsentry_config.json`: Main application configuration
- `tailscale_settings.json`: Tailscale-specific settings

Example `tailsentry_config.json`:
```json
{
    "host": "0.0.0.0",
    "port": 8080,
    "debug": false,
    "secret_key": "your-secret-key",
    "database_path": "data/users.db",
    "log_level": "INFO",
    "max_login_attempts": 5,
    "lockout_duration": 300,
    "session_timeout": 3600
}
```

## Management Commands

### Bare Metal Installation

```bash
# Service management
sudo tailsentry-installer start        # Start service
sudo tailsentry-installer stop         # Stop service
sudo tailsentry-installer restart      # Restart service
sudo tailsentry-installer status       # Show status

# Application management
sudo tailsentry-installer update       # Update application
sudo tailsentry-installer update-deps  # Update dependencies only
sudo tailsentry-installer backup       # Create backup
sudo tailsentry-installer restore      # Restore from backup

# Maintenance
sudo tailsentry-installer logs         # View logs
sudo tailsentry-installer list-backups # List available backups
```

### Docker Installation

```bash
# Using docker-deploy script
./docker-deploy.sh up          # Start containers
./docker-deploy.sh down        # Stop containers
./docker-deploy.sh restart     # Restart containers
./docker-deploy.sh logs        # View logs
./docker-deploy.sh update      # Update to latest image
./docker-deploy.sh status      # Show status

# Using docker-compose directly
docker-compose -f docker-compose.prod.yml up -d    # Start
docker-compose -f docker-compose.prod.yml down     # Stop
docker-compose -f docker-compose.prod.yml logs -f  # Logs
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check service status
sudo systemctl status tailsentry

# Check logs
sudo journalctl -u tailsentry -f

# Check configuration
sudo tailsentry-installer status
```

#### 2. Can't Access Web Interface

- Check if service is running: `sudo tailsentry-installer status`
- Verify port 8080 is not blocked by firewall
- Check if another service is using port 8080: `sudo netstat -tlnp | grep :8080`

#### 3. Tailscale Integration Issues

- Verify Tailscale is running: `sudo tailscale status`
- Check Tailscale PAT is valid and has proper permissions
- Ensure TailSentry has access to Tailscale socket

#### 4. Permission Issues

```bash
# Fix ownership
sudo chown -R root:root /opt/tailsentry

# Fix permissions
sudo chmod 755 /opt/tailsentry
sudo chmod 600 /opt/tailsentry/config/*.json
```

#### 5. Docker Issues

```bash
# Check container logs
docker logs tailsentry

# Check container status
docker ps -a

# Restart container
docker restart tailsentry

# Check volumes
docker volume ls | grep tailsentry
```

### Debug Mode

Enable debug mode for detailed logging:

**Bare Metal**:
```bash
# Edit config file
sudo nano /opt/tailsentry/config/tailsentry_config.json
# Set "debug": true and "log_level": "DEBUG"

# Restart service
sudo tailsentry-installer restart
```

**Docker**:
```bash
# Set environment variables
DEBUG=true
LOG_LEVEL=DEBUG

# Restart container
docker-compose restart
```

## Upgrading

### Bare Metal

```bash
# Update to latest version
sudo tailsentry-installer update

# Update dependencies only
sudo tailsentry-installer update-deps
```

### Docker

```bash
# Update images and restart
./docker-deploy.sh update

# Or manually
docker-compose pull
docker-compose up -d
```

## Backup and Restore

### Automatic Backups

Automatic backups are created:
- Before updates
- According to configured schedule (default: daily)
- Stored in `/opt/tailsentry-backups/`

### Manual Backup

```bash
# Create backup
sudo tailsentry-installer backup

# List backups
sudo tailsentry-installer list-backups

# Restore from backup
sudo tailsentry-installer restore
```

### Docker Backup

```bash
# Backup volumes
docker run --rm -v tailsentry_data:/data -v $(pwd):/backup alpine tar czf /backup/tailsentry-data-backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v tailsentry_data:/data -v $(pwd):/backup alpine tar xzf /backup/tailsentry-data-backup.tar.gz -C /data
```

## Uninstallation

### Bare Metal

```bash
# Complete removal
sudo tailsentry-installer uninstall

# Keep backups when prompted, or remove everything with:
sudo rm -rf /opt/tailsentry-backups
```

### Docker

```bash
# Stop and remove containers
./docker-deploy.sh down

# Remove images and volumes
docker rmi tailsentry:latest
docker volume rm tailsentry_data tailsentry_logs tailsentry_config
```

## Security Considerations

1. **Change default credentials** immediately after installation
2. **Use strong passwords** and consider 2FA
3. **Keep TailSentry updated** to latest version
4. **Secure your Tailscale PAT** - treat it like a password
5. **Monitor access logs** regularly
6. **Use HTTPS** when exposing to internet (consider reverse proxy)

## Support

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/lolerskatez/TailSentry/issues)
- **Documentation**: Check the repository README and wiki
- **Logs**: Always include relevant logs when reporting issues

## Next Steps

After installation:

1. **Change default admin password**
2. **Configure Tailscale integration**
3. **Set up notifications** (optional)
4. **Configure backups** (automatic)
5. **Review security settings**
6. **Test functionality** with your Tailnet

---

For more detailed information, see the [main README](README.md) and project documentation.
