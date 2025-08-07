#!/bin/bash
# test-integration-stress.sh - Stress testing for Tailscale integration
set -e

echo "⚡ TailSentry Integration Stress Testing"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STRESS_DURATION=300  # 5 minutes
MAX_CONCURRENT=50
API_CALLS_PER_SECOND=10
TEMP_DIR="/tmp/tailsentry-stress-test"
LOG_FILE="$TEMP_DIR/stress-test.log"

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

# Verify prerequisites
echo
log_info "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    log_error "Python3 not found"
    exit 1
fi

if ! command -v tailscale &> /dev/null; then
    log_error "Tailscale not found"
    exit 1
fi

if ! tailscale status &> /dev/null; then
    log_error "Tailscale not running or not authenticated"
    exit 1
fi

log_success "Prerequisites check passed"

# Start application for testing
echo
log_info "Starting TailSentry for stress testing..."
timeout ${STRESS_DURATION}s python3 main.py > "$TEMP_DIR/app.log" 2>&1 &
APP_PID=$!
sleep 5

# Verify app is running
if ! kill -0 $APP_PID 2>/dev/null; then
    log_error "Application failed to start"
    cat "$TEMP_DIR/app.log"
    exit 1
fi

log_success "Application started (PID: $APP_PID)"

# Cleanup function
cleanup() {
    log_info "Cleaning up stress test..."
    kill $APP_PID 2>/dev/null || true
    wait $APP_PID 2>/dev/null || true
    
    # Kill any remaining background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Test 1: CLI Command Stress Test
echo
log_info "Starting CLI command stress test..."

# Function to test CLI commands
test_cli_commands() {
    local test_id=$1
    local results_file="$TEMP_DIR/cli_results_$test_id.txt"
    local errors=0
    local successes=0
    
    for i in {1..100}; do
        start_time=$(date +%s.%N)
        
        # Test different CLI commands
        case $((i % 4)) in
            0)
                if timeout 5s tailscale status > /dev/null 2>&1; then
                    ((successes++))
                else
                    ((errors++))
                    echo "tailscale status failed at iteration $i" >> "$results_file"
                fi
                ;;
            1)
                if timeout 5s tailscale ip -4 > /dev/null 2>&1; then
                    ((successes++))
                else
                    ((errors++))
                    echo "tailscale ip failed at iteration $i" >> "$results_file"
                fi
                ;;
            2)
                if timeout 5s tailscale ping --c 1 100.64.0.1 > /dev/null 2>&1; then
                    ((successes++))
                else
                    ((errors++))
                    echo "tailscale ping failed at iteration $i" >> "$results_file"
                fi
                ;;
            3)
                if python3 -c "
from tailscale_client import TailscaleClient
try:
    status = TailscaleClient.status_json()
    if status:
        exit(0)
    else:
        exit(1)
except Exception as e:
    exit(1)
" 2>/dev/null; then
                    ((successes++))
                else
                    ((errors++))
                    echo "TailscaleClient.status_json failed at iteration $i" >> "$results_file"
                fi
                ;;
        esac
        
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
        
        # Log slow responses
        if (( $(echo "$duration > 2.0" | bc -l 2>/dev/null || echo "0") )); then
            echo "Slow response: ${duration}s at iteration $i" >> "$results_file"
        fi
        
        # Small delay to prevent overwhelming
        sleep 0.01
    done
    
    echo "$test_id:$successes:$errors" >> "$TEMP_DIR/cli_summary.txt"
}

# Run multiple concurrent CLI tests
for i in {1..10}; do
    test_cli_commands $i &
done

# Wait for CLI tests to complete
wait

# Analyze CLI results
CLI_TOTAL_SUCCESS=0
CLI_TOTAL_ERRORS=0

if [ -f "$TEMP_DIR/cli_summary.txt" ]; then
    while IFS=':' read -r test_id successes errors; do
        CLI_TOTAL_SUCCESS=$((CLI_TOTAL_SUCCESS + successes))
        CLI_TOTAL_ERRORS=$((CLI_TOTAL_ERRORS + errors))
    done < "$TEMP_DIR/cli_summary.txt"
fi

if [ $CLI_TOTAL_ERRORS -eq 0 ]; then
    log_success "CLI stress test: $CLI_TOTAL_SUCCESS successes, 0 errors"
else
    log_warning "CLI stress test: $CLI_TOTAL_SUCCESS successes, $CLI_TOTAL_ERRORS errors"
fi

# Test 2: HTTP API Stress Test
echo
log_info "Starting HTTP API stress test..."

# Function to test API endpoints
test_api_endpoints() {
    local test_id=$1
    local results_file="$TEMP_DIR/api_results_$test_id.txt"
    local errors=0
    local successes=0
    
    for i in {1..100}; do
        start_time=$(date +%s.%N)
        
        # Test different API endpoints
        case $((i % 3)) in
            0)
                if curl -s -f "http://localhost:8080/health" > /dev/null 2>&1; then
                    ((successes++))
                else
                    ((errors++))
                    echo "Health endpoint failed at iteration $i" >> "$results_file"
                fi
                ;;
            1)
                response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/login")
                if [ "$response" -eq 200 ]; then
                    ((successes++))
                else
                    ((errors++))
                    echo "Login endpoint failed at iteration $i (HTTP $response)" >> "$results_file"
                fi
                ;;
            2)
                response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/dashboard")
                if [ "$response" -eq 302 ] || [ "$response" -eq 200 ]; then
                    ((successes++))
                else
                    ((errors++))
                    echo "Dashboard endpoint failed at iteration $i (HTTP $response)" >> "$results_file"
                fi
                ;;
        esac
        
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
        
        # Log slow responses
        if (( $(echo "$duration > 1.0" | bc -l 2>/dev/null || echo "0") )); then
            echo "Slow API response: ${duration}s at iteration $i" >> "$results_file"
        fi
        
        sleep 0.05  # Slightly longer delay for HTTP requests
    done
    
    echo "$test_id:$successes:$errors" >> "$TEMP_DIR/api_summary.txt"
}

# Run concurrent API tests
for i in {1..5}; do
    test_api_endpoints $i &
done

# Wait for API tests to complete
wait

# Analyze API results
API_TOTAL_SUCCESS=0
API_TOTAL_ERRORS=0

if [ -f "$TEMP_DIR/api_summary.txt" ]; then
    while IFS=':' read -r test_id successes errors; do
        API_TOTAL_SUCCESS=$((API_TOTAL_SUCCESS + successes))
        API_TOTAL_ERRORS=$((API_TOTAL_ERRORS + errors))
    done < "$TEMP_DIR/api_summary.txt"
fi

if [ $API_TOTAL_ERRORS -eq 0 ]; then
    log_success "API stress test: $API_TOTAL_SUCCESS successes, 0 errors"
else
    log_warning "API stress test: $API_TOTAL_SUCCESS successes, $API_TOTAL_ERRORS errors"
fi

# Test 3: Memory and Resource Monitoring
echo
log_info "Starting resource monitoring..."

# Function to monitor resources
monitor_resources() {
    local monitor_file="$TEMP_DIR/resource_monitor.txt"
    local max_memory=0
    local max_cpu=0
    
    for i in {1..60}; do  # Monitor for 60 seconds
        if kill -0 $APP_PID 2>/dev/null; then
            # Get memory usage in KB
            memory=$(ps -o rss= -p $APP_PID 2>/dev/null || echo "0")
            # Get CPU percentage
            cpu=$(ps -o %cpu= -p $APP_PID 2>/dev/null || echo "0")
            
            # Track maximum values
            if [ "$memory" -gt "$max_memory" ]; then
                max_memory=$memory
            fi
            
            # CPU comparison (basic)
            if (( $(echo "$cpu > $max_cpu" | bc -l 2>/dev/null || echo "0") )); then
                max_cpu=$cpu
            fi
            
            echo "$(date +%s),$memory,$cpu" >> "$monitor_file"
        fi
        
        sleep 1
    done
    
    echo "max_memory:$max_memory" >> "$TEMP_DIR/resource_summary.txt"
    echo "max_cpu:$max_cpu" >> "$TEMP_DIR/resource_summary.txt"
}

monitor_resources &
MONITOR_PID=$!

# Test 4: Concurrent WebSocket Connections (if applicable)
echo
log_info "Testing concurrent connections..."

# Simple connection test
test_concurrent_connections() {
    local connections=20
    local success_count=0
    
    for i in $(seq 1 $connections); do
        (
            if curl -s -f "http://localhost:8080/health" > /dev/null 2>&1; then
                echo "success" >> "$TEMP_DIR/connection_results.txt"
            else
                echo "failure" >> "$TEMP_DIR/connection_results.txt"
            fi
        ) &
    done
    
    wait  # Wait for all connection tests
    
    if [ -f "$TEMP_DIR/connection_results.txt" ]; then
        success_count=$(grep -c "success" "$TEMP_DIR/connection_results.txt" 2>/dev/null || echo "0")
        log_info "Concurrent connections: $success_count/$connections successful"
    fi
}

test_concurrent_connections

# Test 5: Error Recovery Testing
echo
log_info "Testing error recovery..."

# Simulate Tailscale service interruption
test_service_recovery() {
    log_info "Testing service recovery (requires sudo)..."
    
    # This test requires sudo privileges, so we'll simulate instead
    if command -v sudo &> /dev/null && sudo -n true 2>/dev/null; then
        log_info "Stopping Tailscale service temporarily..."
        sudo systemctl stop tailscaled
        sleep 5
        
        # Test TailSentry behavior without Tailscale
        response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/health")
        if [ "$response" -eq 200 ]; then
            log_success "TailSentry remains responsive without Tailscale"
        else
            log_warning "TailSentry affected by Tailscale outage"
        fi
        
        # Restart Tailscale
        sudo systemctl start tailscaled
        sleep 10
        
        # Test recovery
        if tailscale status > /dev/null 2>&1; then
            log_success "Tailscale service recovered"
        else
            log_warning "Tailscale service recovery incomplete"
        fi
    else
        log_info "Skipping service recovery test (requires sudo)"
    fi
}

# Only run if we have sudo access
test_service_recovery

# Wait for resource monitoring to complete
wait $MONITOR_PID 2>/dev/null || true

# Analyze resource usage
if [ -f "$TEMP_DIR/resource_summary.txt" ]; then
    MAX_MEMORY=$(grep "max_memory:" "$TEMP_DIR/resource_summary.txt" | cut -d: -f2)
    MAX_CPU=$(grep "max_cpu:" "$TEMP_DIR/resource_summary.txt" | cut -d: -f2)
    
    # Convert memory to MB
    MAX_MEMORY_MB=$((MAX_MEMORY / 1024))
    
    log_info "Peak memory usage: ${MAX_MEMORY_MB}MB"
    log_info "Peak CPU usage: ${MAX_CPU}%"
    
    # Check if usage is reasonable
    if [ "$MAX_MEMORY_MB" -lt 500 ]; then
        log_success "Memory usage is reasonable (< 500MB)"
    else
        log_warning "High memory usage detected (${MAX_MEMORY_MB}MB)"
    fi
    
    if (( $(echo "$MAX_CPU < 80" | bc -l 2>/dev/null || echo "1") )); then
        log_success "CPU usage is reasonable (< 80%)"
    else
        log_warning "High CPU usage detected (${MAX_CPU}%)"
    fi
fi

# Test 6: Long-running Stability Test
echo
log_info "Running stability test (30 seconds)..."

STABILITY_ERRORS=0
for i in {1..30}; do
    if ! kill -0 $APP_PID 2>/dev/null; then
        log_error "Application crashed during stability test"
        ((STABILITY_ERRORS++))
        break
    fi
    
    # Quick health check
    if ! curl -s -f "http://localhost:8080/health" > /dev/null 2>&1; then
        log_warning "Health check failed at second $i"
        ((STABILITY_ERRORS++))
    fi
    
    sleep 1
done

if [ $STABILITY_ERRORS -eq 0 ]; then
    log_success "Stability test passed (30 seconds)"
else
    log_warning "Stability test had $STABILITY_ERRORS errors"
fi

# Generate stress test report
echo
echo "⚡ Stress Test Summary"
echo "======================"

cat << EOF > "$TEMP_DIR/stress-report.txt"
TailSentry Integration Stress Test Report
Generated: $(date)
Duration: ${STRESS_DURATION} seconds

Test Results:
- CLI Operations: $CLI_TOTAL_SUCCESS successes, $CLI_TOTAL_ERRORS errors
- API Operations: $API_TOTAL_SUCCESS successes, $API_TOTAL_ERRORS errors
- Peak Memory: ${MAX_MEMORY_MB:-Unknown}MB
- Peak CPU: ${MAX_CPU:-Unknown}%
- Stability Errors: $STABILITY_ERRORS

Performance Analysis:
$(if [ -f "$TEMP_DIR/cli_results_1.txt" ]; then
    echo "CLI Performance Issues:"
    grep "Slow response" "$TEMP_DIR"/cli_results_*.txt | head -5
fi)

$(if [ -f "$TEMP_DIR/api_results_1.txt" ]; then
    echo "API Performance Issues:"
    grep "Slow API response" "$TEMP_DIR"/api_results_*.txt | head -5
fi)

Recommendations:
1. Monitor memory usage in production
2. Consider connection pooling for high loads
3. Implement circuit breakers for external dependencies
4. Set up proper monitoring and alerting
5. Regular performance testing
6. Consider horizontal scaling for high loads

Status: $(if [ $CLI_TOTAL_ERRORS -eq 0 ] && [ $API_TOTAL_ERRORS -eq 0 ] && [ $STABILITY_ERRORS -eq 0 ]; then
    echo "PASSED"
else
    echo "WARNINGS DETECTED"
fi)
EOF

log_success "Stress test report saved to: $TEMP_DIR/stress-report.txt"

# Show final summary
echo
echo "📊 Final Results:"
echo "CLI Tests: ✅ $CLI_TOTAL_SUCCESS / ❌ $CLI_TOTAL_ERRORS"
echo "API Tests: ✅ $API_TOTAL_SUCCESS / ❌ $API_TOTAL_ERRORS" 
echo "Memory Peak: ${MAX_MEMORY_MB:-Unknown}MB"
echo "CPU Peak: ${MAX_CPU:-Unknown}%"
echo "Stability: $(if [ $STABILITY_ERRORS -eq 0 ]; then echo "✅ STABLE"; else echo "⚠️  $STABILITY_ERRORS ERRORS"; fi)"
echo
echo "Full report: $TEMP_DIR/stress-report.txt"

if [ $CLI_TOTAL_ERRORS -eq 0 ] && [ $API_TOTAL_ERRORS -eq 0 ] && [ $STABILITY_ERRORS -eq 0 ]; then
    log_success "Integration stress test completed successfully!"
    exit 0
else
    log_warning "Integration stress test completed with warnings"
    exit 1
fi
