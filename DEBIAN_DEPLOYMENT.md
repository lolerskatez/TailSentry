# Deploying TailSentry on Debian 12

This guide provides instructions for deploying TailSentry on a Debian 12 system with a real Tailscale installation.

## Prerequisites

- Debian 12 (Bookworm) system
- Root or sudo access
- Internet connection

## Installation Steps

### 1. Install Tailscale (if not already installed)

```bash
# Add Tailscale's GPG key and repository
curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/debian/bookworm.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list

# Update and install
sudo apt-get update
sudo apt-get install -y tailscale

# Start Tailscale service
sudo systemctl enable --now tailscaled

# Set up Tailscale with your account
sudo tailscale up
```

### 2. Install TailSentry

You can use our automated installation script:

```bash
sudo ./debian_install.sh
```

Or follow these manual steps:

```bash
# Create application directory
sudo mkdir -p /opt/tailsentry

# Copy TailSentry files
sudo cp -r * /opt/tailsentry/
cd /opt/tailsentry

# Create Python virtual environment
sudo python3 -m venv venv
sudo source venv/bin/activate

# Install dependencies
sudo pip install -r requirements.txt

# Create data directory with proper permissions
sudo mkdir -p /opt/tailsentry/data
sudo chmod 750 /opt/tailsentry/data

# Create logs directory with proper permissions
sudo mkdir -p /opt/tailsentry/logs
sudo chmod 750 /opt/tailsentry/logs

# Setup systemd service
sudo cp tailsentry.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tailsentry.service
sudo systemctl start tailsentry.service
```

### 3. Set Admin Password

```bash
cd /opt/tailsentry
python change_password.py admin
```

### 4. Access the Dashboard

Open your browser and navigate to:

```
http://<server-ip>:8000
```

## Troubleshooting

### Check Tailscale Status

```bash
tailscale status
```

### Check TailSentry Service Status

```bash
systemctl status tailsentry
```

### View TailSentry Logs

```bash
tail -f /opt/tailsentry/logs/tailsentry.log
```

### Common Issues

1. **Permission Denied**: Make sure the user running TailSentry has access to the tailscale binary and can execute commands.

2. **Tailscale Not Found**: Verify that Tailscale is installed and in the PATH or adjust the TailscaleClient.get_tailscale_path() method.

3. **Service Won't Start**: Check the journal logs with `journalctl -u tailsentry` for more detailed error information.

## Security Considerations

1. TailSentry requires root or elevated permissions to interact with Tailscale
2. Access to the TailSentry dashboard should be restricted to authorized users
3. Consider using HTTPS with a valid certificate for production deployments
