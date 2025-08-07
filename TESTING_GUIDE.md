# TailSentry Testing Strategy with Spare Computer

## 🧪 Comprehensive Testing Setup

### **Testing Environment Overview**
- **Primary Machine**: Development environment
- **Spare Computer**: Isolated testing environment
- **Network Setup**: Both machines on Tailscale network

## 🖥️ **Spare Computer Setup Guide**

### **Phase 1: Basic Environment Setup**

#### **1. Operating System Preparation**
```bash
# Recommended: Fresh Ubuntu 22.04 LTS or Debian 12
# This tests real deployment scenarios

# Update system
sudo apt update && sudo apt upgrade -y

# Install basic tools
sudo apt install -y curl wget git python3 python3-pip python3-venv
```

#### **2. Tailscale Installation**
```bash
# Install Tailscale (official method)
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate with a separate auth key
sudo tailscale up --authkey=tskey-auth-xxxxx

# Verify connection
tailscale status
tailscale ping [your-dev-machine-ip]
```

#### **3. TailSentry Deployment**
```bash
# Clone repository
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry

# Run setup
make install
make setup

# Configure environment
cp .env.example .env
# Edit .env with production-like settings
```

### **Phase 2: Testing Scenarios**

#### **🔒 Security Testing**
```bash
# Test 1: Authentication bypass attempts
curl -X POST http://spare-machine:8080/dashboard
# Should redirect to login

# Test 2: Rate limiting
for i in {1..20}; do
  curl -X POST http://spare-machine:8080/login \
    -d "username=wrong&password=wrong"
done
# Should trigger rate limiting

# Test 3: Session security
# Test session timeout, CSRF protection, secure cookies
```

#### **🌐 Network Testing**
```bash
# Test 1: Tailscale connectivity from different devices
tailscale ping spare-machine
tailscale ping dev-machine

# Test 2: Subnet routing functionality
# Configure spare machine as subnet router
sudo tailscale up --advertise-routes=192.168.100.0/24

# Test 3: Exit node testing
# Enable/disable exit node functionality
sudo tailscale up --advertise-exit-node
```

#### **⚡ Performance Testing**
```bash
# Test 1: Load testing with concurrent users
# Install apache bench
sudo apt install apache2-utils

# Test login endpoint
ab -n 1000 -c 10 -p login_data.txt \
   http://spare-machine:8080/login

# Test 2: WebSocket stress testing
# Multiple concurrent WebSocket connections
```

#### **🔄 Integration Testing**
```bash
# Test 1: Tailscale CLI integration
# Simulate various Tailscale states:
sudo systemctl stop tailscaled  # Test offline handling
sudo systemctl start tailscaled # Test recovery

# Test 2: API integration testing
# Test with invalid/expired PAT tokens
# Test API rate limiting
# Test network connectivity issues
```

## 🧪 **Automated Testing Suite**

Let me create comprehensive test scripts:

### **Test Script 1: Deployment Validation**
```bash
#!/bin/bash
# test-deployment.sh
echo "🚀 Testing TailSentry Deployment"

# Test installation
./scripts/validate-integration.sh || exit 1

# Test service startup
make dev &
APP_PID=$!
sleep 10

# Test health endpoint
if curl -f http://localhost:8080/health; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    kill $APP_PID
    exit 1
fi

# Test authentication
if curl -f http://localhost:8080/login > /dev/null; then
    echo "✅ Login page accessible"
else
    echo "❌ Login page failed"
    kill $APP_PID
    exit 1
fi

kill $APP_PID
echo "✅ Deployment test completed"
```

### **Test Script 2: Security Validation**
```bash
#!/bin/bash
# test-security.sh
echo "🔒 Testing Security Features"

BASE_URL="http://localhost:8080"

# Test rate limiting
echo "Testing rate limiting..."
for i in {1..10}; do
    curl -s -X POST $BASE_URL/login \
        -d "username=test&password=wrong" \
        -H "X-Forwarded-For: 192.168.1.$i" > /dev/null
done

# Should get rate limited
if curl -s -X POST $BASE_URL/login \
    -d "username=test&password=wrong" | grep -q "Too many"; then
    echo "✅ Rate limiting works"
else
    echo "⚠️  Rate limiting not triggered"
fi

# Test security headers
echo "Testing security headers..."
HEADERS=$(curl -s -I $BASE_URL)
if echo "$HEADERS" | grep -q "X-Frame-Options"; then
    echo "✅ Security headers present"
else
    echo "❌ Security headers missing"
fi
```

### **Test Script 3: Integration Stress Test**
```bash
#!/bin/bash
# test-integration-stress.sh
echo "⚡ Stress Testing Tailscale Integration"

# Rapid status requests
echo "Testing CLI stress..."
for i in {1..50}; do
    python3 -c "
from tailscale_client import TailscaleClient
import time
start = time.time()
status = TailscaleClient.status_json()
duration = time.time() - start
print(f'Request {i}: {duration:.3f}s')
if duration > 2.0:
    print('❌ Slow response detected')
    exit(1)
" || exit 1
done

echo "✅ Integration stress test passed"
```

## 📊 **Testing Scenarios Matrix**

### **Scenario 1: Clean Installation Testing**
```bash
# On spare computer (fresh OS):
1. Install Tailscale
2. Deploy TailSentry from scratch
3. Verify all features work
4. Test backup/restore procedures
```

### **Scenario 2: Network Isolation Testing**
```bash
# Test network failure scenarios:
1. Disconnect from internet
2. Block Tailscale coordination server
3. Simulate DNS failures
4. Test offline mode behavior
```

### **Scenario 3: Multi-Device Testing**
```bash
# With multiple Tailscale devices:
1. Test peer management from TailSentry
2. Verify subnet routing across devices
3. Test exit node switching
4. Validate real-time updates
```

### **Scenario 4: Production Simulation**
```bash
# Simulate production environment:
1. Deploy with Docker
2. Setup reverse proxy (nginx)
3. Configure SSL certificates
4. Test backup schedules
5. Simulate failure recovery
```

## 🔧 **Environment-Specific Testing**

### **Container Testing**
```bash
# Test Docker deployment
docker-compose up -d
docker-compose logs -f tailsentry

# Test container security
docker exec tailsentry whoami  # Should not be root
docker exec tailsentry ls -la /app  # Check permissions

# Test resource limits
docker stats tailsentry
```

### **Service Testing**
```bash
# Test systemd integration
sudo systemctl status tailsentry
sudo systemctl restart tailsentry
sudo journalctl -u tailsentry -f

# Test auto-restart on failure
sudo kill -9 $(pgrep -f tailsentry)
# Should auto-restart
```

## 📈 **Performance Benchmarking**

### **Response Time Testing**
```python
# test_performance.py
import time
import requests
import statistics

def test_endpoint_performance(url, iterations=100):
    times = []
    for _ in range(iterations):
        start = time.time()
        response = requests.get(url)
        end = time.time()
        if response.status_code == 200:
            times.append(end - start)
    
    if times:
        print(f"Avg: {statistics.mean(times):.3f}s")
        print(f"P95: {statistics.quantiles(times, n=20)[18]:.3f}s")
        print(f"Max: {max(times):.3f}s")

# Test various endpoints
test_endpoint_performance("http://spare-machine:8080/health")
test_endpoint_performance("http://spare-machine:8080/api/status")
```

### **Memory Usage Monitoring**
```bash
# Monitor resource usage during testing
#!/bin/bash
echo "Monitoring TailSentry resource usage..."
while true; do
    ps aux | grep tailsentry | grep -v grep
    free -h
    sleep 30
done
```

## 🎯 **Recommended Testing Schedule**

### **Week 1: Basic Functionality**
- Day 1-2: Fresh installation and basic setup
- Day 3-4: Core functionality testing
- Day 5-6: Security testing
- Day 7: Performance baseline

### **Week 2: Advanced Testing**
- Day 1-2: Integration stress testing
- Day 3-4: Network failure scenarios
- Day 5-6: Multi-device testing
- Day 7: Production simulation

### **Ongoing: Regression Testing**
- Weekly automated test runs
- Monthly full test suite
- Before major releases

## 🚨 **Failure Scenario Testing**

### **Critical Failure Tests**
1. **Tailscale Service Down**
   ```bash
   sudo systemctl stop tailscaled
   # Verify TailSentry handles gracefully
   ```

2. **Network Partition**
   ```bash
   # Block Tailscale traffic
   sudo iptables -A OUTPUT -p udp --dport 41641 -j DROP
   ```

3. **API Rate Limiting**
   ```bash
   # Exhaust API quota
   # Test fallback to CLI-only mode
   ```

4. **Disk Space Exhaustion**
   ```bash
   # Fill up disk space
   # Test log rotation and cleanup
   ```

## 📋 **Testing Checklist**

### **Before Each Test Session**
- [ ] Spare computer has fresh OS/clean state
- [ ] Tailscale is properly configured
- [ ] Network connectivity is verified
- [ ] Test data and scripts are prepared

### **During Testing**
- [ ] Document all issues found
- [ ] Capture logs and screenshots
- [ ] Monitor resource usage
- [ ] Test recovery procedures

### **After Testing**
- [ ] Clean up test environment
- [ ] Update test documentation
- [ ] Report issues and improvements
- [ ] Plan next testing iteration

## 🛠️ **Quick Start Testing Commands**

### **For Linux/macOS (Recommended)**
```bash
# 1. Setup spare computer
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# 2. Deploy TailSentry
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry
make install && make setup

# 3. Run comprehensive testing
./scripts/run-all-tests.sh

# Or run individual tests
./scripts/test-deployment.sh
./scripts/test-security.sh
./scripts/test-integration-stress.sh
python3 scripts/performance_tester.py
```

### **For Windows**
```powershell
# 1. Setup spare computer (install Tailscale from tailscale.com)
# 2. Deploy TailSentry
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry

# 3. Run comprehensive testing
.\scripts\run-all-tests.ps1

# Or install requirements manually
pip install -r requirements.txt
pip install -r test-requirements.txt
python main.py
```

### **Testing Results**
After running tests, check the `test-results-YYYYMMDD-HHMMSS/` directory for:
- `test-summary.md` - Complete test report
- `deployment-test.log` - Deployment validation
- `security-test.log` - Security scan results
- `performance-report.json` - Performance metrics
- `stress-test.log` - Stress test results

## 🎯 **Expected Results**

### **✅ Successful Test Run Should Show:**
- All core functionality working
- Tailscale integration validated
- Security headers present
- Response times under 1 second
- No memory leaks during stress testing
- All endpoints properly protected

### **⚠️ Common Warnings (Normal):**
- Some security headers missing (configure reverse proxy)
- Performance warnings under high load
- CLI timeouts during stress tests

### **❌ Critical Issues to Fix:**
- Authentication bypass
- Tailscale communication failures
- Application crashes
- Memory usage > 500MB
- Response times > 5 seconds

This comprehensive testing approach will help you validate TailSentry's reliability, security, and performance in real-world scenarios!
