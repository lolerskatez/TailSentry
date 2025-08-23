# TailSentry Production Deployment Guide

## 🚀 Quick Deployment

### Prerequisites
- Linux server (Ubuntu 20.04+ or Debian 11+ recommended)
- Tailscale installed and authenticated
- Root access for installation

### One-Line Installation
```bash
wget https://raw.githubusercontent.com/lolerskatez/TailSentry/main/setup.sh && chmod +x setup.sh && sudo ./setup.sh install
```

## 🔧 Manual Deployment

### 1. System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-venv python3-pip git

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### 2. Application Installation
```bash
# Create installation directory
sudo mkdir -p /opt/tailsentry
cd /opt/tailsentry

# Clone repository
sudo git clone https://github.com/lolerskatez/TailSentry.git .

# Set up Python environment
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt

# Configure environment
sudo cp .env.example .env
# Edit .env with your settings
```

### 3. Service Installation
```bash
# Install systemd service
sudo cp tailsentry.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tailsentry
sudo systemctl start tailsentry

# Check status
sudo systemctl status tailsentry
```

## 🔒 Production Security

### Firewall Configuration
```bash
# UFW (Ubuntu/Debian)
sudo ufw allow from 100.64.0.0/10 to any port 8080
sudo ufw enable

# Or for firewalld (RHEL/CentOS)
sudo firewall-cmd --permanent --add-rich-rule="rule family='ipv4' source address='100.64.0.0/10' port port='8080' protocol='tcp' accept"
sudo firewall-cmd --reload
```

### Reverse Proxy (Recommended)
Using Nginx:
```bash
sudo apt install nginx
sudo cat > /etc/nginx/sites-available/tailsentry << 'EOF'
server {
    listen 80;
    server_name tailsentry.local;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/tailsentry /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 📊 Monitoring

### Log Files
```bash
# Application logs
sudo tail -f /opt/tailsentry/logs/tailsentry.log

# Service logs
sudo journalctl -u tailsentry -f

# Nginx logs (if using reverse proxy)
sudo tail -f /var/log/nginx/access.log
```

### Health Checks
```bash
# Built-in health endpoint
curl http://localhost:8080/health

# Automated monitoring script
sudo cp scripts/health-check.sh /usr/local/bin/
echo "*/5 * * * * /usr/local/bin/health-check.sh" | sudo crontab -
```

## 🔄 Updates

### Automatic Updates
```bash
# Create update script
sudo cp update.sh /usr/local/bin/tailsentry-update
sudo chmod +x /usr/local/bin/tailsentry-update

# Schedule weekly updates (optional)
echo "0 2 * * 0 /usr/local/bin/tailsentry-update" | sudo crontab -
```

### Manual Updates
```bash
cd /opt/tailsentry
sudo git pull
sudo ./venv/bin/pip install -r requirements.txt
sudo systemctl restart tailsentry
```

## 🛠 Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   sudo journalctl -u tailsentry -n 50
   sudo systemctl status tailsentry
   ```

2. **Permission denied errors**
   ```bash
   sudo chown -R root:root /opt/tailsentry
   sudo chmod +x /opt/tailsentry/venv/bin/uvicorn
   ```

3. **Tailscale not found**
   ```bash
   which tailscale
   sudo ln -s /usr/bin/tailscale /usr/local/bin/tailscale
   ```

4. **Port already in use**
   ```bash
   sudo netstat -tlnp | grep :8080
   sudo lsof -i :8080
   ```

### Support
- Check the logs: `/opt/tailsentry/logs/tailsentry.log`
- Validate integration: `./scripts/validate-integration.sh`
- Run tests: `python3 tests.py`
- GitHub Issues: https://github.com/lolerskatez/TailSentry/issues
