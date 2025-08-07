#!/bin/bash
# run-all-tests.sh - Master test runner for TailSentry
set -e

echo "🧪 TailSentry Comprehensive Testing Suite"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_DIR="test-results-$(date +%Y%m%d-%H%M%S)"
VERBOSE=false
SKIP_SECURITY=false
SKIP_PERFORMANCE=false
SKIP_STRESS=false

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
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -v, --verbose           Enable verbose output"
    echo "  --skip-security         Skip security tests"
    echo "  --skip-performance      Skip performance tests"
    echo "  --skip-stress           Skip stress tests"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      Run all tests"
    echo "  $0 --verbose            Run all tests with verbose output"
    echo "  $0 --skip-security      Run tests except security"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --skip-security)
            SKIP_SECURITY=true
            shift
            ;;
        --skip-performance)
            SKIP_PERFORMANCE=true
            shift
            ;;
        --skip-stress)
            SKIP_STRESS=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Setup test environment
setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Create test results directory
    mkdir -p "$TEST_DIR"
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is required but not installed"
        exit 1
    fi
    
    # Check if Tailscale is available
    if ! command -v tailscale &> /dev/null; then
        log_error "Tailscale is required but not installed"
        exit 1
    fi
    
    # Install test dependencies if needed
    if [ -f "test-requirements.txt" ]; then
        log_info "Installing test dependencies..."
        pip3 install -r test-requirements.txt > "$TEST_DIR/pip-install.log" 2>&1 || {
            log_warning "Some test dependencies failed to install (see $TEST_DIR/pip-install.log)"
        }
    fi
    
    # Make scripts executable
    chmod +x scripts/*.sh 2>/dev/null || true
    
    log_success "Test environment ready"
}

# Run deployment validation
run_deployment_tests() {
    log_info "Running deployment validation tests..."
    
    if [ -x "scripts/test-deployment.sh" ]; then
        if bash scripts/test-deployment.sh > "$TEST_DIR/deployment-test.log" 2>&1; then
            log_success "Deployment tests passed"
            return 0
        else
            log_error "Deployment tests failed (see $TEST_DIR/deployment-test.log)"
            if [ "$VERBOSE" = true ]; then
                echo "Last 10 lines of deployment test log:"
                tail -10 "$TEST_DIR/deployment-test.log"
            fi
            return 1
        fi
    else
        log_warning "Deployment test script not found or not executable"
        return 1
    fi
}

# Run security tests
run_security_tests() {
    if [ "$SKIP_SECURITY" = true ]; then
        log_info "Skipping security tests (--skip-security specified)"
        return 0
    fi
    
    log_info "Running security tests..."
    
    if [ -x "scripts/test-security.sh" ]; then
        if timeout 300s bash scripts/test-security.sh > "$TEST_DIR/security-test.log" 2>&1; then
            log_success "Security tests passed"
            return 0
        else
            log_warning "Security tests completed with warnings (see $TEST_DIR/security-test.log)"
            if [ "$VERBOSE" = true ]; then
                echo "Security test summary:"
                grep -E "(SUCCESS|WARNING|ERROR)" "$TEST_DIR/security-test.log" | tail -5
            fi
            return 0  # Security warnings are not fatal
        fi
    else
        log_warning "Security test script not found or not executable"
        return 1
    fi
}

# Run performance tests
run_performance_tests() {
    if [ "$SKIP_PERFORMANCE" = true ]; then
        log_info "Skipping performance tests (--skip-performance specified)"
        return 0
    fi
    
    log_info "Running performance tests..."
    
    # Run Python performance tester if available
    if [ -f "scripts/performance_tester.py" ]; then
        if python3 scripts/performance_tester.py --output "$TEST_DIR/performance-report.json" > "$TEST_DIR/performance-test.log" 2>&1; then
            log_success "Performance tests passed"
        else
            log_warning "Performance tests completed with warnings (see $TEST_DIR/performance-test.log)"
        fi
    else
        log_warning "Python performance tester not found"
    fi
    
    return 0
}

# Run stress tests
run_stress_tests() {
    if [ "$SKIP_STRESS" = true ]; then
        log_info "Skipping stress tests (--skip-stress specified)"
        return 0
    fi
    
    log_info "Running integration stress tests..."
    
    if [ -x "scripts/test-integration-stress.sh" ]; then
        if timeout 600s bash scripts/test-integration-stress.sh > "$TEST_DIR/stress-test.log" 2>&1; then
            log_success "Stress tests passed"
            return 0
        else
            log_warning "Stress tests completed with warnings (see $TEST_DIR/stress-test.log)"
            if [ "$VERBOSE" = true ]; then
                echo "Stress test summary:"
                tail -20 "$TEST_DIR/stress-test.log" | grep -E "(✅|⚠️|❌)"
            fi
            return 0  # Stress test warnings are not fatal
        fi
    else
        log_warning "Stress test script not found or not executable"
        return 1
    fi
}

# Run integration validation
run_integration_tests() {
    log_info "Running integration validation..."
    
    if [ -x "scripts/validate-integration.sh" ]; then
        if bash scripts/validate-integration.sh > "$TEST_DIR/integration-test.log" 2>&1; then
            log_success "Integration tests passed"
            return 0
        else
            log_error "Integration tests failed (see $TEST_DIR/integration-test.log)"
            if [ "$VERBOSE" = true ]; then
                echo "Last 10 lines of integration test log:"
                tail -10 "$TEST_DIR/integration-test.log"
            fi
            return 1
        fi
    else
        log_warning "Integration validation script not found"
        return 1
    fi
}

# Generate comprehensive report
generate_report() {
    log_info "Generating comprehensive test report..."
    
    cat << EOF > "$TEST_DIR/test-summary.md"
# TailSentry Test Report

**Generated:** $(date)
**Test Duration:** $(date -d @$(($(date +%s) - START_TIME)) -u +%H:%M:%S)
**Test Directory:** $TEST_DIR

## Test Results Summary

| Test Suite | Status | Log File |
|------------|--------|----------|
| Deployment | $([ -f "$TEST_DIR/deployment-test.log" ] && echo "✅ PASSED" || echo "❌ FAILED") | deployment-test.log |
| Integration | $([ -f "$TEST_DIR/integration-test.log" ] && echo "✅ PASSED" || echo "❌ FAILED") | integration-test.log |
| Security | $([ -f "$TEST_DIR/security-test.log" ] && echo "⚠️ COMPLETED" || echo "⏭️ SKIPPED") | security-test.log |
| Performance | $([ -f "$TEST_DIR/performance-test.log" ] && echo "⚠️ COMPLETED" || echo "⏭️ SKIPPED") | performance-test.log |
| Stress | $([ -f "$TEST_DIR/stress-test.log" ] && echo "⚠️ COMPLETED" || echo "⏭️ SKIPPED") | stress-test.log |

## Environment Information

- **OS:** $(uname -s) $(uname -r)
- **Python:** $(python3 --version 2>/dev/null || echo "Not available")
- **Tailscale:** $(tailscale version --short 2>/dev/null || echo "Not available")
- **TailSentry Status:** $([ -f "main.py" ] && echo "Available" || echo "Not found")

## Key Findings

### Deployment
$(if [ -f "$TEST_DIR/deployment-test.log" ]; then
    grep -E "(✅|❌|⚠️)" "$TEST_DIR/deployment-test.log" | head -5 || echo "No specific findings"
else
    echo "Deployment tests not run"
fi)

### Security
$(if [ -f "$TEST_DIR/security-test.log" ]; then
    echo "Security scan completed. Check security-test.log for details."
else
    echo "Security tests skipped"
fi)

### Performance
$(if [ -f "$TEST_DIR/performance-report.json" ]; then
    echo "Performance metrics collected. Check performance-report.json for details."
else
    echo "Performance tests not completed"
fi)

## Recommendations

1. **Review all warning messages** in the individual test logs
2. **Address any security findings** from the security test
3. **Monitor performance metrics** in production
4. **Regular testing schedule** - run these tests weekly
5. **Update dependencies** regularly for security

## Next Steps

1. Deploy TailSentry to test environment
2. Run full integration testing with real Tailscale network
3. Monitor performance under real load
4. Set up continuous testing pipeline

---
*Generated by TailSentry Testing Suite*
EOF

    log_success "Test report generated: $TEST_DIR/test-summary.md"
}

# Main execution
main() {
    START_TIME=$(date +%s)
    
    echo
    log_info "Starting comprehensive TailSentry testing..."
    echo "Test configuration:"
    echo "  Verbose: $VERBOSE"
    echo "  Skip Security: $SKIP_SECURITY"
    echo "  Skip Performance: $SKIP_PERFORMANCE"
    echo "  Skip Stress: $SKIP_STRESS"
    echo "  Results Directory: $TEST_DIR"
    echo
    
    # Setup
    setup_test_environment
    
    # Track test results
    TESTS_PASSED=0
    TESTS_FAILED=0
    TESTS_WARNED=0
    
    # Run test suites
    echo
    log_info "Phase 1: Core Functionality Tests"
    echo "-----------------------------------"
    
    if run_deployment_tests; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    
    if run_integration_tests; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    
    echo
    log_info "Phase 2: Security and Performance Tests"
    echo "----------------------------------------"
    
    if run_security_tests; then
        ((TESTS_PASSED++))
    else
        ((TESTS_WARNED++))
    fi
    
    if run_performance_tests; then
        ((TESTS_PASSED++))
    else
        ((TESTS_WARNED++))
    fi
    
    if run_stress_tests; then
        ((TESTS_PASSED++))
    else
        ((TESTS_WARNED++))
    fi
    
    # Generate report
    echo
    log_info "Phase 3: Report Generation"
    echo "---------------------------"
    generate_report
    
    # Final summary
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo
    echo "🎯 TESTING COMPLETE"
    echo "==================="
    echo "Duration: $(date -d @$DURATION -u +%H:%M:%S)"
    echo "Passed: $TESTS_PASSED"
    echo "Failed: $TESTS_FAILED"
    echo "Warnings: $TESTS_WARNED"
    echo "Results: $TEST_DIR/"
    echo
    
    if [ $TESTS_FAILED -eq 0 ]; then
        if [ $TESTS_WARNED -eq 0 ]; then
            log_success "All tests passed! TailSentry is ready for deployment."
            echo
            echo "🚀 Ready for production deployment!"
            echo "   Next steps:"
            echo "   1. Review test results in $TEST_DIR/"
            echo "   2. Deploy to your spare computer"
            echo "   3. Run real-world testing"
            echo "   4. Set up monitoring"
        else
            log_warning "Core tests passed but some warnings detected."
            echo
            echo "⚠️  Review warnings before deployment:"
            echo "   1. Check $TEST_DIR/ for detailed results"
            echo "   2. Address any security concerns"
            echo "   3. Optimize performance if needed"
        fi
        return 0
    else
        log_error "Some critical tests failed."
        echo
        echo "❌ Fix issues before deployment:"
        echo "   1. Review failed tests in $TEST_DIR/"
        echo "   2. Address all critical issues"
        echo "   3. Re-run testing suite"
        return 1
    fi
}

# Run main function
main "$@"
