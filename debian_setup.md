# Setting up TailSentry on Debian 12

## Troubleshooting Real Tailscale Data Issues

If TailSentry is not displaying real Tailscale data (IP addresses, devices, etc.) on your Debian system, follow these steps to diagnose and fix the problem.

## Diagnostic Steps

### 1. Verify Tailscale Installation

First, check that Tailscale is properly installed and accessible:

```bash
which tailscale
tailscale version
tailscale status
```

Tailscale binaries on Debian are typically installed in:
- Tailscale client: `/usr/sbin/tailscale`
- Tailscale daemon: `/usr/sbin/tailscaled`

### 2. Run the Diagnostic Tools

TailSentry includes two diagnostic tools to help identify issues:

```bash
# Bash diagnostic script
chmod +x diagnose_tailscale.sh
./diagnose_tailscale.sh

# Python diagnostic tool
python3 diagnose_tailscale.py
```

These tools will:
- Check if Tailscale is installed and accessible
- Retrieve and display raw Tailscale data
- Test if Python can properly access Tailscale data
- Create diagnostic files for troubleshooting

### 3. Check Permissions

Ensure the user running TailSentry has permission to execute Tailscale commands:

```bash
# Add your TailSentry user to appropriate group
sudo usermod -aG sudo tailsentry  # or appropriate group

# Or set specific permissions
sudo chmod +s /usr/sbin/tailscale
```

### 4. Enable Debug Logging

Edit your environment configuration to enable debug logging:

```bash
# In /etc/tailsentry/config.env or similar
LOG_LEVEL=DEBUG
```

### 5. Check Raw JSON Output

Compare the output from Tailscale directly with what TailSentry is receiving:

```bash
# Direct from Tailscale
tailscale status --json | python3 -m json.tool > tailscale_direct.json

# Look at the diagnostic output
cat tailscale_status_raw.json
```

## Common Solutions

1. **Path Issues**: Make sure TailSentry can find the Tailscale binary
   ```bash
   # Add to PATH in service file
   Environment="PATH=/usr/sbin:/usr/bin:/sbin:/bin"
   ```

2. **Permission Issues**: Run TailSentry with appropriate permissions
   ```bash
   # Either run as root or give tailscale sudo permissions
   sudo systemctl edit tailsentry.service
   # Add: User=root
   ```

3. **API vs CLI**: If API access is needed, make sure to set up a Tailscale API key
   ```bash
   # In configuration
   TAILSCALE_PAT=your_personal_access_token
   TAILSCALE_TAILNET=your_tailnet
   ```
