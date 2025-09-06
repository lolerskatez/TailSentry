# TailSentry Linux Deployment Guide

## 🐧 **Secure Linux Deployment**

### **System Requirements**
- Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / RHEL 8+
- Python 3.8+ 
- 2GB RAM minimum, 4GB recommended
- 20GB disk space

### **1. System Preparation**

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# OR
sudo dnf update -y  # RHEL/CentOS/Fedora

# Install required system packages
sudo apt install python3 python3-venv python3-pip git curl -y  # Ubuntu/Debian
# OR  
sudo dnf install python3 python3-venv python3-pip git curl -y  # RHEL/CentOS/Fedora

# Create dedicated user for TailSentry
sudo adduser --system --group --home /opt/tailsentry tailsentry
sudo mkdir -p /opt/tailsentry
sudo chown tailsentry:tailsentry /opt/tailsentry
```

### **2. Application Setup**

```bash
# Switch to tailsentry user
sudo -u tailsentry -s

# Navigate to application directory
cd /opt/tailsentry

# Clone repository
git clone https://github.com/lolerskatez/TailSentry.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy example configurations
cp config/tailsentry_config.json.example config/tailsentry_config.json
cp config/discord_config.json.example config/discord_config.json
```

### **3. Security Hardening**

```bash
# Run security hardening script
chmod +x security_hardening.sh
./security_hardening.sh

# Set up firewall (adjust ports as needed)
sudo ufw allow ssh
sudo ufw allow 8000/tcp  # TailSentry web interface
sudo ufw --force enable

# Configure log rotation
sudo cp logrotate.conf /etc/logrotate.d/tailsentry
sudo chown root:root /etc/logrotate.d/tailsentry
sudo chmod 644 /etc/logrotate.d/tailsentry
```

### **4. Service Configuration**

```bash
# Install systemd service
sudo cp tailsentry.service.template /etc/systemd/system/tailsentry.service

# Edit service file with your specific paths
sudo nano /etc/systemd/system/tailsentry.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable tailsentry
sudo systemctl start tailsentry

# Check service status
sudo systemctl status tailsentry
```

### **5. SSL/TLS Setup (Production)**

```bash
# Install Certbot for Let's Encrypt SSL
sudo apt install certbot python3-certbot-nginx -y  # Ubuntu/Debian
# OR
sudo dnf install certbot python3-certbot-nginx -y  # RHEL/CentOS/Fedora

# Install Nginx reverse proxy
sudo apt install nginx -y  # Ubuntu/Debian
# OR
sudo dnf install nginx -y  # RHEL/CentOS/Fedora

# Configure Nginx (see nginx config below)
sudo nano /etc/nginx/sites-available/tailsentry

# Enable site
sudo ln -s /etc/nginx/sites-available/tailsentry /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### **6. Nginx Configuration**

Create `/etc/nginx/sites-available/tailsentry`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=tailsentry:10m rate=10r/m;
    limit_req zone=tailsentry burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Static files
    location /static/ {
        alias /opt/tailsentry/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

### **7. Monitoring and Logging**

```bash
# Set up log monitoring
sudo apt install fail2ban -y  # Ubuntu/Debian
# OR
sudo dnf install fail2ban -y  # RHEL/CentOS/Fedora

# Configure fail2ban for TailSentry
sudo nano /etc/fail2ban/jail.local
```

Add to `/etc/fail2ban/jail.local`:

```ini
[tailsentry]
enabled = true
port = 8000
filter = tailsentry
logpath = /opt/tailsentry/logs/tailsentry.log
maxretry = 5
bantime = 3600
findtime = 600
```

Create `/etc/fail2ban/filter.d/tailsentry.conf`:

```ini
[Definition]
failregex = AUDIT_ALERT.*"success":\s*false.*"user_id":\s*"<HOST>"
ignoreregex =
```

### **8. Backup Configuration**

```bash
# Create backup script
sudo nano /opt/tailsentry/scripts/backup.sh
```

```bash
#!/bin/bash
# TailSentry backup script

BACKUP_DIR="/opt/backups/tailsentry"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/tailsentry"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup configuration and data
tar -czf "$BACKUP_DIR/tailsentry_backup_$DATE.tar.gz" \
    -C "$APP_DIR" \
    config/ data/ logs/

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "tailsentry_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: tailsentry_backup_$DATE.tar.gz"
```

```bash
# Make executable and add to cron
chmod +x /opt/tailsentry/scripts/backup.sh

# Add to crontab (daily backup at 3 AM)
sudo crontab -e
# Add: 0 3 * * * /opt/tailsentry/scripts/backup.sh
```

### **9. Security Checklist**

- [ ] **User Isolation**: Running as dedicated `tailsentry` user
- [ ] **File Permissions**: Config files 600, directories 700
- [ ] **Firewall**: Only necessary ports open (SSH, HTTPS, TailSentry)
- [ ] **SSL/TLS**: HTTPS enabled with valid certificate
- [ ] **Log Rotation**: Prevents disk space issues
- [ ] **Fail2ban**: Automated IP blocking for failed attempts
- [ ] **Regular Backups**: Daily automated backups
- [ ] **System Updates**: Automated security updates enabled
- [ ] **Monitoring**: Service status and log monitoring

### **10. Maintenance Commands**

```bash
# Check service status
sudo systemctl status tailsentry

# View logs
sudo journalctl -u tailsentry -f

# Restart service
sudo systemctl restart tailsentry

# Update application
sudo -u tailsentry git pull
sudo systemctl restart tailsentry

# Run security updates
./scripts/update_packages.sh
sudo systemctl restart tailsentry

# Check disk usage
df -h
du -sh /opt/tailsentry/logs/
```

### **11. Troubleshooting**

```bash
# Check Python environment
sudo -u tailsentry /opt/tailsentry/venv/bin/python --version

# Test configuration
sudo -u tailsentry /opt/tailsentry/venv/bin/python -c "
import json
with open('/opt/tailsentry/config/tailsentry_config.json') as f:
    config = json.load(f)
    print('Config loaded successfully')
"

# Check network connectivity
sudo -u tailsentry curl -I https://discord.com/api/v10/gateway

# Validate file permissions
find /opt/tailsentry/config -ls
```

## 🚀 **Quick Deployment Script**

For automated deployment, save as `deploy_linux.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 TailSentry Linux Quick Deploy"
echo "================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please run as regular user with sudo privileges"
    exit 1
fi

# System setup
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-venv python3-pip git curl nginx certbot python3-certbot-nginx fail2ban -y

# Create user
sudo adduser --system --group --home /opt/tailsentry tailsentry
sudo mkdir -p /opt/tailsentry
sudo chown tailsentry:tailsentry /opt/tailsentry

# Clone and setup
cd /opt/tailsentry
sudo -u tailsentry git clone https://github.com/lolerskatez/TailSentry.git .
sudo -u tailsentry python3 -m venv venv
sudo -u tailsentry /opt/tailsentry/venv/bin/pip install --upgrade pip
sudo -u tailsentry /opt/tailsentry/venv/bin/pip install -r requirements.txt

# Security hardening
sudo -u tailsentry chmod +x security_hardening.sh
sudo -u tailsentry ./security_hardening.sh

# Service setup
sudo cp tailsentry.service.template /etc/systemd/system/tailsentry.service
sudo systemctl daemon-reload
sudo systemctl enable tailsentry

echo "✅ Deployment complete!"
echo "📝 Next steps:"
echo "   1. Configure Discord bot token in config/discord_config.json"
echo "   2. Configure TailSentry settings in config/tailsentry_config.json"
echo "   3. Start service: sudo systemctl start tailsentry"
echo "   4. Set up SSL: sudo certbot --nginx -d your-domain.com"
```

This guide provides comprehensive Linux deployment with security best practices!
