# 🧪 TailSentry Testing Quick Start

## **For Your Spare Computer Testing**

### **Option 1: Linux/Ubuntu (Recommended)**

```bash
# Fresh Ubuntu/Debian setup
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-pip curl

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey=YOUR_AUTH_KEY

# Clone and test TailSentry
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry

# Quick validation
chmod +x scripts/*.sh
./scripts/run-all-tests.sh

# If all passes, deploy normally
make install
make setup
make dev
```

### **Option 2: Windows**

```powershell
# Install prerequisites
# - Python 3.9+ from python.org
# - Tailscale from tailscale.com
# - Git from git-scm.com

# Clone and test
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry
.\scripts\run-all-tests.ps1

# If tests pass, deploy
pip install -r requirements.txt
python main.py
```

### **Option 3: Docker (Any Platform)**

```bash
# Using Docker
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry

# Build and test
docker-compose up --build -d
docker-compose logs -f

# Validate
curl http://localhost:8080/health
```

## **What to Expect**

### **✅ Good Results:**
```
🎯 TESTING COMPLETE
===================
Duration: 00:03:45
Passed: 5
Failed: 0
Warnings: 2
```

### **📊 Key Metrics to Watch:**
- **Response Time:** < 1 second for most endpoints
- **Memory Usage:** < 500MB under normal load
- **Tailscale CLI:** < 3 seconds per command
- **Success Rate:** > 95% for all operations

### **🚩 Red Flags:**
- Authentication bypass possible
- Tailscale commands failing
- Memory usage > 1GB
- Response times > 5 seconds
- Application crashes

## **Testing Scenarios**

### **1. Basic Functionality (5 minutes)**
```bash
# Test core features
./scripts/test-deployment.sh
curl http://localhost:8080/health
curl http://localhost:8080/login
```

### **2. Security Testing (10 minutes)**
```bash
# Test security measures
./scripts/test-security.sh
# Check for SQL injection, XSS, CSRF protection
```

### **3. Performance Testing (15 minutes)**
```bash
# Test under load
python3 scripts/performance_tester.py
# 100 requests, concurrent users, stress testing
```

### **4. Integration Testing (20 minutes)**
```bash
# Test Tailscale integration
./scripts/test-integration-stress.sh
# CLI commands, API calls, service management
```

### **5. Real-World Testing (30 minutes)**
```bash
# Simulate actual usage
# - Multiple browser tabs
# - Enable/disable devices
# - Change exit nodes
# - Manage subnets
# - Monitor real-time updates
```

## **Troubleshooting**

### **Test Failures:**

**"Tailscale not found"**
```bash
# Install Tailscale first
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**"Python import errors"**
```bash
# Install dependencies
pip3 install -r requirements.txt
pip3 install -r test-requirements.txt
```

**"Permission denied"**
```bash
# Make scripts executable (Linux/macOS)
chmod +x scripts/*.sh
```

**"Tests timing out"**
```bash
# Check if Tailscale is running
tailscale status
sudo systemctl status tailscaled
```

### **Performance Issues:**

**High memory usage:**
- Check for memory leaks in logs
- Monitor during stress tests
- Consider reducing WebSocket connections

**Slow responses:**
- Check Tailscale network latency
- Monitor CPU usage
- Review database queries if applicable

**CLI timeouts:**
- Verify Tailscale daemon health
- Check network connectivity
- Review subprocess timeout settings

## **Success Checklist**

Before deploying to production:

- [ ] All core tests pass
- [ ] Security tests complete without critical issues
- [ ] Performance metrics within acceptable ranges
- [ ] Integration tests show reliable Tailscale communication
- [ ] Application recovers gracefully from failures
- [ ] Memory usage stable under load
- [ ] Authentication and authorization working
- [ ] Real-time updates functioning
- [ ] Backup and restore procedures tested

## **Next Steps After Testing**

### **If Tests Pass:**
1. Deploy to spare computer permanently
2. Set up reverse proxy (nginx/Cloudflare)
3. Configure SSL certificates
4. Set up monitoring and alerts
5. Create backup schedules
6. Document your specific setup

### **If Tests Have Warnings:**
1. Review detailed logs in test results directory
2. Address security recommendations
3. Optimize performance bottlenecks
4. Re-run tests after fixes
5. Consider staging environment

### **If Tests Fail:**
1. Check prerequisites (Python, Tailscale, dependencies)
2. Review error logs carefully
3. Test individual components
4. Seek help with specific error messages
5. Consider different platform (Windows → Linux)

## **Support Resources**

- **Test Results:** Check `test-results-*/` directory
- **Logs:** Application logs in `logs/` directory
- **Integration:** Review `TAILSCALE_INTEGRATION.md`
- **Security:** Check `SECURITY_COMPARTMENTALIZATION.md`
- **Development:** Use `Makefile` commands

**Happy Testing! 🚀**

Your spare computer is perfect for validating TailSentry before production deployment. The testing suite will give you confidence that everything works reliably in your environment.
