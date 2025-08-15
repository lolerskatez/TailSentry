# TailSentry Update System

TailSentry provides multiple update methods depending on your deployment scenario:

## 🔄 Update Methods

### 1. **Smart Update (Linux/Systemd)**
For traditional Linux installations with systemd service:

```bash
sudo ./smart-update.sh
```

**Features:**
- Interactive menu with multiple update options
- Automatic backup before updates
- Rollback capability
- Health checks after updates
- Dependency management
- Configuration preservation

**Options:**
1. **Quick Update** - Code + dependencies
2. **Full Update** - Code + dependencies + config check
3. **Dependencies Only** - Update Python packages
4. **Code Only** - Git pull latest changes
5. **Check for Updates** - See what's available
6. **Rollback** - Restore previous version

### 2. **Docker Update**
For containerized deployments:

```bash
./docker-update.sh
```

**Features:**
- Container image updates
- Volume backup and restore
- Rebuild from source option
- Container health monitoring
- Log viewing

**Options:**
1. **Update Container** - Pull latest image
2. **Check for Updates** - Compare image versions
3. **Rebuild from Source** - Build new image locally
4. **Rollback** - Restore from backup
5. **View Logs** - Container log monitoring
6. **Container Status** - Resource usage and info

### 3. **Manual Update**
For development or custom setups:

```bash
# 1. Stop the service
sudo systemctl stop tailsentry

# 2. Backup configuration
cp .env .env.backup
cp -r data data.backup

# 3. Update code
git pull origin main

# 4. Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 5. Restart service
sudo systemctl start tailsentry
```

## 📋 Prerequisites

### For Smart Update:
- Root/sudo access
- systemd environment
- Git repository
- Python virtual environment

### For Docker Update:
- Docker installed and running
- Docker volumes for persistence
- Container named 'tailsentry'

## 🔧 Configuration

### Environment Variables
Update scripts respect these environment variables:

```bash
# Smart Update Configuration
INSTALL_DIR="/opt/tailsentry"          # Installation directory
BACKUP_DIR="/opt/tailsentry/backups"   # Backup storage
SERVICE_NAME="tailsentry"              # Systemd service name
LOG_FILE="/var/log/tailsentry-update.log"

# Docker Update Configuration
CONTAINER_NAME="tailsentry"            # Container name
IMAGE_NAME="tailsentry:latest"         # Docker image
DATA_VOLUME="tailsentry_data"          # Data volume
CONFIG_VOLUME="tailsentry_config"      # Config volume
```

## 🛡️ Safety Features

### Automatic Backups
All update methods create automatic backups before making changes:
- Configuration files (.env)
- Data directory
- Database files
- Version information

### Rollback Capability
If an update fails or causes issues:
```bash
# Smart Update
sudo ./smart-update.sh
# Choose option 6 (Rollback)

# Docker Update
./docker-update.sh
# Choose option 4 (Rollback)
```

### Health Checks
After updates, the system automatically verifies:
- Service is running
- Web interface responds
- API endpoints functional
- Database connectivity

## 📊 Version Tracking

### API Endpoints
Check version information programmatically:

```bash
# Current version
curl http://localhost:8000/api/version

# Check for updates
curl http://localhost:8000/api/update/check
```

### Response Format
```json
{
  "version_info": {
    "version": "1.0.0",
    "build_date": "2025-08-15",
    "git_commit": "abc1234",
    "git_dirty": false
  }
}
```

## 🚨 Troubleshooting

### Common Issues

**Service won't start after update:**
```bash
# Check logs
sudo journalctl -u tailsentry -f

# Check service status
sudo systemctl status tailsentry

# Manual restart
sudo systemctl restart tailsentry
```

**Permission issues:**
```bash
# Fix permissions
sudo chown -R tailsentry:tailsentry /opt/tailsentry
sudo chmod +x /opt/tailsentry/*.sh
```

**Docker container issues:**
```bash
# Check container logs
docker logs tailsentry

# Restart container
docker restart tailsentry

# Rebuild if needed
docker stop tailsentry
docker rm tailsentry
docker build -t tailsentry:latest .
```

### Recovery Options

**Complete rollback:**
1. Stop service: `sudo systemctl stop tailsentry`
2. Restore from backup: Choose a backup from `/opt/tailsentry/backups/`
3. Copy files back: `sudo cp -r backup_TIMESTAMP/* /opt/tailsentry/`
4. Restart: `sudo systemctl start tailsentry`

**Emergency restore:**
```bash
# If update scripts fail, manual restore:
sudo systemctl stop tailsentry
cd /opt/tailsentry/backups
sudo cp latest_backup/.env /opt/tailsentry/
sudo cp -r latest_backup/data /opt/tailsentry/
sudo systemctl start tailsentry
```

## 📝 Best Practices

1. **Always backup before updates**
2. **Test updates in development first**
3. **Monitor logs during updates**
4. **Keep multiple backup versions**
5. **Document custom configurations**
6. **Schedule updates during maintenance windows**

## 🔗 Integration

### CI/CD Pipeline
Integrate with your CI/CD system:

```yaml
# GitHub Actions example
- name: Deploy Update
  run: |
    ssh server "cd /opt/tailsentry && sudo ./smart-update.sh"
```

### Monitoring
Set up monitoring for update notifications:
- Version change alerts
- Service restart notifications
- Health check failures
- Backup status updates
