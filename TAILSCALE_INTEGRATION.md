# TailSentry ↔ Tailscale Integration Guide

## 🔗 Communication Overview

TailSentry communicates with Tailscale through two main channels:

### 1. **Tailscale CLI** (Primary Interface)
- **Status Monitoring**: `tailscale status --json`
- **Configuration**: `tailscale up --advertise-routes=...`
- **Service Control**: `systemctl start/stop/restart tailscaled`

### 2. **Tailscale HTTP API** (Secondary Interface)
- **Key Management**: Create/revoke auth keys
- **Device Management**: List devices, get device info
- **ACL Management**: Policy updates (future)

## 📋 Prerequisites Checklist

### ✅ **Required Components**

1. **Tailscale Installation**
   ```bash
   # Check installation
   which tailscale
   tailscale version
   
   # Install if missing (Ubuntu/Debian)
   curl -fsSL https://tailscale.com/install.sh | sh
   ```

2. **Tailscaled Service**
   ```bash
   # Check service status
   systemctl status tailscaled
   
   # Enable if needed
   sudo systemctl enable --now tailscaled
   ```

3. **Authentication**
   ```bash
   # Authenticate device
   sudo tailscale up
   
   # Verify connection
   tailscale status
   ```

### ⚙️ **Configuration Requirements**

1. **Environment Variables**
   ```bash
   # Required for API access (optional but recommended)
   TAILSCALE_PAT=tskey-api-xxxxx
   
   # Optional customization
   TAILSCALE_TAILNET=-  # Use "-" for personal tailnet
   TAILSCALE_API_TIMEOUT=10
   ```

2. **System Permissions**
   ```bash
   # TailSentry needs access to:
   - tailscale CLI commands (usually available to all users)
   - systemctl commands (requires sudo or proper user groups)
   - JSON output parsing (requires modern tailscale version)
   ```

## 🔧 **Integration Validation**

Run the validation script to check your setup:

```bash
# Make the script executable
chmod +x scripts/validate-integration.sh

# Run validation
./scripts/validate-integration.sh
```

### **Manual Validation Steps**

1. **Test CLI Access**
   ```bash
   # Basic status
   tailscale status
   
   # JSON output (required)
   tailscale status --json | jq '.'
   
   # Service status
   systemctl status tailscaled
   ```

2. **Test API Access** (if PAT configured)
   ```bash
   curl -H "Authorization: Bearer $TAILSCALE_PAT" \
        "https://api.tailscale.com/api/v2/tailnet/-/devices"
   ```

3. **Test Python Integration**
   ```python
   from tailscale_client import TailscaleClient
   
   # Test status retrieval
   status = TailscaleClient.status_json()
   print(f"Device count: {len(status.get('Peer', {}))}")
   
   # Test device info
   info = TailscaleClient.get_device_info()
   print(f"Device IP: {info.get('tailscale', {}).get('ip')}")
   ```

## 🐛 **Common Integration Issues**

### **Issue 1: "tailscale command not found"**
```bash
# Solution: Add Tailscale to PATH or install
export PATH="/usr/local/bin:$PATH"
# OR install Tailscale if missing
```

### **Issue 2: "Permission denied" for systemctl**
```bash
# Solution: Add user to systemd-journal group or run as sudo
sudo usermod -a -G systemd-journal $USER
# OR run TailSentry with sudo (not recommended for production)
```

### **Issue 3: "tailscale not authenticated"**
```bash
# Solution: Authenticate device
sudo tailscale up --authkey=tskey-auth-xxxxx
# OR authenticate interactively
sudo tailscale up
```

### **Issue 4: "JSON output not supported"**
```bash
# Solution: Update Tailscale to newer version
sudo tailscale update
# OR install newer version manually
```

### **Issue 5: "API access denied"**
```bash
# Solution: Generate and configure API Access Token
# 1. Go to https://login.tailscale.com/admin/settings/keys
# 2. Generate API key
# 3. Add to .env: TAILSCALE_PAT=tskey-api-xxxxx
```

## 🔒 **Security Considerations**

### **Service User Setup** (Recommended)
```bash
# Create dedicated user
sudo useradd -r -s /bin/false -d /opt/tailsentry tailsentry

# Grant necessary permissions
sudo usermod -a -G systemd-journal tailsentry

# Update systemd service
sudo systemctl edit tailsentry.service
# Add:
# [Service]
# User=tailsentry
# Group=tailsentry
```

### **API Token Security**
- Store PAT in secure environment variables
- Use least-privilege API keys when available
- Rotate tokens regularly
- Monitor API usage

### **Container Deployment**
```yaml
# Docker socket mounting for CLI access
volumes:
  - /var/run/tailscale/tailscaled.sock:/var/run/tailscale/tailscaled.sock:ro
  
# Environment variables
environment:
  - TAILSCALE_PAT=${TAILSCALE_PAT}
```

## 📊 **Monitoring Integration Health**

### **Built-in Health Checks**
TailSentry includes automatic health monitoring:

```python
# Health check endpoint: /health
# WebSocket status updates every 5 seconds
# Background status cache updates every minute
```

### **Integration Metrics**
Monitor these key indicators:

- **CLI Response Time**: < 2 seconds for status commands
- **API Response Time**: < 1 second for HTTP requests  
- **Success Rate**: > 99% for status retrievals
- **Cache Hit Rate**: > 80% for frequent requests

### **Alerting Setup**
```bash
# Add to cron for periodic validation
0 */4 * * * /opt/tailsentry/scripts/validate-integration.sh > /var/log/tailsentry-health.log 2>&1
```

## 🚀 **Performance Optimization**

### **Caching Strategy**
TailSentry implements smart caching:

```python
# Status cached for 5 seconds to prevent CLI spam
@lru_cache(maxsize=1)
def _status_json_cached():
    # Cached implementation
```

### **Connection Pooling**
For API requests:

```python
# HTTP connection reuse
client = httpx.Client(timeout=10)
# Reuse connections for multiple requests
```

### **Background Updates**
```python
# Non-blocking status updates
scheduler.add_job(update_status_cache, 'interval', minutes=1)
```

## 🔄 **Fallback Strategies**

### **CLI Failure Recovery**
```python
try:
    status = subprocess.check_output(["tailscale", "status", "--json"])
except subprocess.CalledProcessError:
    # Fallback to basic status without JSON
    status = subprocess.check_output(["tailscale", "status"])
    # Parse text output
```

### **API Failure Handling**
```python
try:
    api_response = TailscaleClient._api_request('get', '/devices')
except Exception:
    # Fallback to CLI-only mode
    logger.warning("API unavailable, using CLI only")
```

### **Service Recovery**
```python
def auto_restart_tailscaled():
    """Automatic service recovery"""
    if not is_tailscaled_running():
        logger.warning("tailscaled not running, attempting restart")
        subprocess.run(["systemctl", "restart", "tailscaled"])
```

## 📝 **Testing Integration**

### **Unit Tests**
```python
# Mock Tailscale responses for testing
@patch('subprocess.check_output')
def test_status_parsing(mock_subprocess):
    mock_subprocess.return_value = json.dumps(test_status)
    result = TailscaleClient.status_json()
    assert 'Self' in result
```

### **Integration Tests**
```bash
# Run full integration test suite
python3 -m pytest tests.py -v -k "integration"
```

### **Load Testing**
```python
# Test CLI performance under load
for i in range(100):
    start = time.time()
    TailscaleClient.status_json()
    duration = time.time() - start
    assert duration < 2.0  # Should complete in < 2s
```

## 🎯 **Best Practices Summary**

1. **Always validate integration** before deployment
2. **Use caching** to prevent CLI overload
3. **Implement fallbacks** for CLI/API failures
4. **Monitor integration health** continuously
5. **Secure API tokens** properly
6. **Test error scenarios** regularly
7. **Keep Tailscale updated** for latest features
8. **Use dedicated service user** in production
