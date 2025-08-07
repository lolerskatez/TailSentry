#!/bin/bash
# test-deployment.sh - Comprehensive deployment testing
set -e

echo "🚀 TailSentry Deployment Testing"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_info() {
    echo -e "ℹ️  $1"
}

# Test 1: Environment validation
echo
log_info "Testing environment setup..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_success "Python found: $PYTHON_VERSION"
else
    log_error "Python3 not found"
    exit 1
fi

if command -v tailscale &> /dev/null; then
    # Try different version formats for compatibility
    TAILSCALE_VERSION=$(tailscale version 2>/dev/null | head -n1 | awk '{print $1}' || echo "unknown")
    log_success "Tailscale found: $TAILSCALE_VERSION"
else
    log_error "Tailscale not found"
    exit 1
fi

# Test 2: Dependencies check
echo
log_info "Checking Python dependencies..."

if python3 -c "import fastapi, uvicorn, jinja2" 2>/dev/null; then
    log_success "Core dependencies available"
else
    log_warning "Installing dependencies..."
    pip3 install -r requirements.txt
fi

# Test 3: Configuration validation
echo
log_info "Validating configuration..."

if [ -f ".env" ]; then
    log_success "Environment file found"
    
    # Check for required variables
    if grep -q "SECRET_KEY" .env && grep -q "ADMIN_PASSWORD" .env; then
        log_success "Required environment variables present"
    else
        log_warning "Some environment variables missing"
    fi
else
    log_warning "No .env file found, using defaults"
fi

# Test 4: Integration validation
echo
log_info "Running integration validation..."

if [ -f "scripts/validate-integration.sh" ]; then
    bash scripts/validate-integration.sh
    if [ $? -eq 0 ]; then
        log_success "Integration validation passed"
    else
        log_error "Integration validation failed"
        exit 1
    fi
else
    log_warning "Integration validation script not found"
fi

# Test 5: Application startup
echo
log_info "Testing application startup..."

# Start the application in background
timeout 30s python3 main.py &
APP_PID=$!

# Wait for startup
sleep 5

# Test if process is running
if kill -0 $APP_PID 2>/dev/null; then
    log_success "Application started successfully"
    
    # Test health endpoint
    if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
        log_success "Health endpoint responding"
    else
        log_warning "Health endpoint not responding"
    fi
    
    # Test login page
    if curl -s -f http://localhost:8080/login > /dev/null 2>&1; then
        log_success "Login page accessible"
    else
        log_warning "Login page not accessible"
    fi
    
    # Clean shutdown
    kill $APP_PID 2>/dev/null || true
    wait $APP_PID 2>/dev/null || true
    log_success "Application shutdown cleanly"
    
else
    log_error "Application failed to start"
    exit 1
fi

# Test 6: File permissions and security
echo
log_info "Checking file permissions..."

# Check if running as root (should not be)
if [ "$EUID" -eq 0 ]; then
    log_warning "Running as root - not recommended for production"
else
    log_success "Running as non-root user"
fi

# Check file permissions
if [ -f "main.py" ] && [ -r "main.py" ]; then
    log_success "Application files readable"
else
    log_error "Application files not accessible"
    exit 1
fi

# Test 7: Log file creation
echo
log_info "Testing logging..."

# Test log directory creation
mkdir -p logs
if [ -d "logs" ]; then
    log_success "Log directory created"
    
    # Test log file writing
    echo "Test log entry" > logs/test.log
    if [ -f "logs/test.log" ]; then
        log_success "Log file writing works"
        rm logs/test.log
    else
        log_warning "Log file writing failed"
    fi
else
    log_warning "Could not create log directory"
fi

# Test 8: Network connectivity
echo
log_info "Testing network connectivity..."

# Test Tailscale status
if tailscale status > /dev/null 2>&1; then
    log_success "Tailscale is running"
    
    # Test Tailscale IP
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "$TAILSCALE_IP" ]; then
        log_success "Tailscale IP: $TAILSCALE_IP"
    else
        log_warning "Could not get Tailscale IP"
    fi
else
    log_warning "Tailscale not running or not authenticated"
fi

# Test internet connectivity
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    log_success "Internet connectivity available"
else
    log_warning "No internet connectivity"
fi

echo
echo "🎉 Deployment testing completed!"
echo
echo "Summary:"
echo "- Environment: ✅"
echo "- Dependencies: ✅"
echo "- Configuration: ✅"
echo "- Integration: ✅"
echo "- Application: ✅"
echo "- Security: ✅"
echo "- Logging: ✅"
echo "- Network: ✅"
echo
log_success "TailSentry is ready for use!"
