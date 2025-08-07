#!/bin/bash
# test-security.sh - Security testing suite for TailSentry
set -e

echo "🔒 TailSentry Security Testing"
echo "==============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8080"
TEMP_DIR="/tmp/tailsentry-security-test"
LOG_FILE="$TEMP_DIR/security-test.log"

# Helper functions
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    echo "[$(date)] SUCCESS: $1" >> "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    echo "[$(date)] ERROR: $1" >> "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    echo "[$(date)] WARNING: $1" >> "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    echo "[$(date)] INFO: $1" >> "$LOG_FILE"
}

# Setup
mkdir -p "$TEMP_DIR"
touch "$LOG_FILE"

# Start application for testing
echo
log_info "Starting TailSentry for security testing..."
timeout 60s python3 main.py &
APP_PID=$!
sleep 5

# Verify app is running
if ! kill -0 $APP_PID 2>/dev/null; then
    log_error "Application failed to start"
    exit 1
fi

log_success "Application started (PID: $APP_PID)"

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    kill $APP_PID 2>/dev/null || true
    wait $APP_PID 2>/dev/null || true
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Test 1: Authentication bypass attempts
echo
log_info "Testing authentication bypass..."

# Test accessing protected endpoints without authentication
PROTECTED_ENDPOINTS=(
    "/dashboard"
    "/api/status"
    "/api/peers"
    "/keys"
    "/tailscale"
)

for endpoint in "${PROTECTED_ENDPOINTS[@]}"; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")
    if [ "$RESPONSE" -eq 302 ] || [ "$RESPONSE" -eq 401 ] || [ "$RESPONSE" -eq 403 ]; then
        log_success "Endpoint $endpoint properly protected (HTTP $RESPONSE)"
    else
        log_error "Endpoint $endpoint not properly protected (HTTP $RESPONSE)"
    fi
done

# Test 2: Rate limiting
echo
log_info "Testing rate limiting..."

# Generate multiple failed login attempts
RATE_LIMIT_TEST_IP="192.168.99.100"
RATE_LIMIT_TRIGGERED=false

for i in {1..15}; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$BASE_URL/login" \
        -H "X-Forwarded-For: $RATE_LIMIT_TEST_IP" \
        -H "X-Real-IP: $RATE_LIMIT_TEST_IP" \
        -d "username=testuser&password=wrongpassword")
    
    if [ "$RESPONSE" -eq 429 ]; then
        RATE_LIMIT_TRIGGERED=true
        break
    fi
    
    sleep 0.1
done

if [ "$RATE_LIMIT_TRIGGERED" = true ]; then
    log_success "Rate limiting triggered after multiple attempts"
else
    log_warning "Rate limiting not triggered - may need adjustment"
fi

# Test 3: Security headers
echo
log_info "Testing security headers..."

HEADERS_RESPONSE=$(curl -s -I "$BASE_URL/login")

# Check for important security headers
SECURITY_HEADERS=(
    "X-Frame-Options"
    "X-Content-Type-Options"
    "X-XSS-Protection"
    "Strict-Transport-Security"
    "Content-Security-Policy"
)

for header in "${SECURITY_HEADERS[@]}"; do
    if echo "$HEADERS_RESPONSE" | grep -qi "$header"; then
        log_success "Security header present: $header"
    else
        log_warning "Security header missing: $header"
    fi
done

# Test 4: CSRF protection
echo
log_info "Testing CSRF protection..."

# Try to perform state-changing operation without CSRF token
CSRF_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$BASE_URL/login" \
    -H "Origin: http://malicious-site.com" \
    -d "username=admin&password=password")

if [ "$CSRF_RESPONSE" -eq 403 ] || [ "$CSRF_RESPONSE" -eq 400 ]; then
    log_success "CSRF protection working (HTTP $CSRF_RESPONSE)"
else
    log_warning "CSRF protection may not be working (HTTP $CSRF_RESPONSE)"
fi

# Test 5: SQL injection attempts (if using database)
echo
log_info "Testing SQL injection protection..."

SQL_INJECTION_PAYLOADS=(
    "admin'; DROP TABLE users; --"
    "admin' OR '1'='1"
    "admin' UNION SELECT * FROM users --"
    "'; EXEC xp_cmdshell('dir'); --"
)

for payload in "${SQL_INJECTION_PAYLOADS[@]}"; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$BASE_URL/login" \
        -d "username=$payload&password=test")
    
    if [ "$RESPONSE" -eq 400 ] || [ "$RESPONSE" -eq 422 ]; then
        log_success "SQL injection payload blocked: ${payload:0:20}..."
    else
        log_warning "SQL injection payload not blocked: ${payload:0:20}..."
    fi
done

# Test 6: XSS protection
echo
log_info "Testing XSS protection..."

XSS_PAYLOADS=(
    "<script>alert('xss')</script>"
    "javascript:alert('xss')"
    "<img src=x onerror=alert('xss')>"
    "'><script>alert('xss')</script>"
)

for payload in "${XSS_PAYLOADS[@]}"; do
    # Test in username field
    RESPONSE=$(curl -s "$BASE_URL/login" \
        -X POST \
        -d "username=$payload&password=test")
    
    if echo "$RESPONSE" | grep -q "<script>" || echo "$RESPONSE" | grep -q "onerror="; then
        log_error "XSS payload not properly escaped: ${payload:0:20}..."
    else
        log_success "XSS payload properly handled: ${payload:0:20}..."
    fi
done

# Test 7: File upload security (if applicable)
echo
log_info "Testing file upload security..."

# Test various file types and sizes
if curl -s "$BASE_URL" | grep -q "file\|upload"; then
    log_info "File upload functionality detected, testing..."
    
    # Create test files
    echo "<?php system(\$_GET['cmd']); ?>" > "$TEMP_DIR/malicious.php"
    echo "<script>alert('xss')</script>" > "$TEMP_DIR/malicious.html"
    dd if=/dev/zero of="$TEMP_DIR/large.txt" bs=1M count=100 2>/dev/null
    
    # Test malicious file upload (this would need actual upload endpoint)
    log_warning "Manual file upload testing required"
else
    log_info "No file upload functionality detected"
fi

# Test 8: Session security
echo
log_info "Testing session security..."

# Get a session cookie
SESSION_RESPONSE=$(curl -s -c "$TEMP_DIR/cookies.txt" "$BASE_URL/login")

if [ -f "$TEMP_DIR/cookies.txt" ]; then
    # Check session cookie attributes
    COOKIE_CONTENT=$(cat "$TEMP_DIR/cookies.txt")
    
    if echo "$COOKIE_CONTENT" | grep -q "HttpOnly"; then
        log_success "Session cookie has HttpOnly flag"
    else
        log_warning "Session cookie missing HttpOnly flag"
    fi
    
    if echo "$COOKIE_CONTENT" | grep -q "Secure"; then
        log_info "Session cookie has Secure flag (good for HTTPS)"
    else
        log_warning "Session cookie missing Secure flag"
    fi
    
    if echo "$COOKIE_CONTENT" | grep -q "SameSite"; then
        log_success "Session cookie has SameSite attribute"
    else
        log_warning "Session cookie missing SameSite attribute"
    fi
fi

# Test 9: Information disclosure
echo
log_info "Testing information disclosure..."

# Check for verbose error messages
ERROR_RESPONSE=$(curl -s "$BASE_URL/nonexistent-endpoint")
if echo "$ERROR_RESPONSE" | grep -qi "traceback\|stack trace\|exception\|debug"; then
    log_warning "Verbose error messages detected - may reveal sensitive info"
else
    log_success "Error messages properly sanitized"
fi

# Check for server information leakage
SERVER_HEADERS=$(curl -s -I "$BASE_URL/")
if echo "$SERVER_HEADERS" | grep -qi "server: "; then
    SERVER_INFO=$(echo "$SERVER_HEADERS" | grep -i "server: " | head -1)
    log_warning "Server information exposed: $SERVER_INFO"
else
    log_success "Server information properly hidden"
fi

# Test 10: Password security
echo
log_info "Testing password security..."

# Test weak password acceptance (if registration is available)
WEAK_PASSWORDS=(
    "123456"
    "password"
    "admin"
    "test"
    "qwerty"
)

for weak_pwd in "${WEAK_PASSWORDS[@]}"; do
    # This would need actual registration endpoint
    log_info "Weak password test: $weak_pwd (manual testing required)"
done

# Test 11: Directory traversal
echo
log_info "Testing directory traversal..."

TRAVERSAL_PAYLOADS=(
    "../../../etc/passwd"
    "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts"
    "....//....//....//etc/passwd"
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
)

for payload in "${TRAVERSAL_PAYLOADS[@]}"; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/$payload")
    if [ "$RESPONSE" -eq 404 ] || [ "$RESPONSE" -eq 403 ]; then
        log_success "Directory traversal blocked: ${payload:0:20}..."
    else
        log_warning "Directory traversal response: HTTP $RESPONSE for ${payload:0:20}..."
    fi
done

# Test 12: Command injection
echo
log_info "Testing command injection..."

COMMAND_PAYLOADS=(
    "; ls -la"
    "| whoami"
    "\$(id)"
    "&& cat /etc/passwd"
    "; ping -c 1 127.0.0.1"
)

for payload in "${COMMAND_PAYLOADS[@]}"; do
    # Test in various input fields
    RESPONSE=$(curl -s "$BASE_URL/login" \
        -X POST \
        -d "username=admin$payload&password=test")
    
    if echo "$RESPONSE" | grep -q "uid=\|gid=\|root:\|PING"; then
        log_error "Command injection vulnerability detected with: $payload"
    else
        log_success "Command injection blocked: $payload"
    fi
done

# Generate security report
echo
echo "🛡️  Security Test Summary"
echo "=========================="
echo
log_info "Generating security report..."

cat << EOF > "$TEMP_DIR/security-report.txt"
TailSentry Security Test Report
Generated: $(date)

Test Results Summary:
$(grep -c "SUCCESS" "$LOG_FILE") tests passed
$(grep -c "WARNING" "$LOG_FILE") warnings found
$(grep -c "ERROR" "$LOG_FILE") errors found

Detailed Results:
$(cat "$LOG_FILE")

Recommendations:
1. Ensure all security headers are properly configured
2. Implement strong password policies
3. Regular security audits and penetration testing
4. Keep dependencies updated
5. Monitor logs for suspicious activity
6. Implement proper error handling
7. Use HTTPS in production
8. Regular backup and recovery testing

Next Steps:
- Review all warnings and errors
- Implement missing security controls
- Schedule regular security testing
- Consider professional security audit
EOF

log_success "Security report saved to: $TEMP_DIR/security-report.txt"
echo
log_info "Security testing completed. Please review the report for recommendations."

# Show summary
echo
echo "📊 Test Summary:"
echo "✅ Passed: $(grep -c "SUCCESS" "$LOG_FILE")"
echo "⚠️  Warnings: $(grep -c "WARNING" "$LOG_FILE")"
echo "❌ Errors: $(grep -c "ERROR" "$LOG_FILE")"
echo
echo "Full report: $TEMP_DIR/security-report.txt"
