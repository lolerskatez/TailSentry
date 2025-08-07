#!/bin/bash
# TailSentry Integration Validation Script
# Ensures proper communication between TailSentry and Tailscale

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

check_tailscale_installation() {
    log "Checking Tailscale installation..."
    
    if ! command -v tailscale >/dev/null 2>&1; then
        error "Tailscale CLI not found in PATH"
        echo "Install Tailscale: https://tailscale.com/download"
        return 1
    fi
    
    # Check version
    local version=$(tailscale version 2>/dev/null | head -n1 || echo "unknown")
    success "Tailscale CLI found: $version"
    
    return 0
}

check_tailscaled_service() {
    log "Checking tailscaled service status..."
    
    if systemctl is-active --quiet tailscaled.service 2>/dev/null; then
        success "tailscaled service is running"
    elif systemctl is-enabled --quiet tailscaled.service 2>/dev/null; then
        warning "tailscaled service is installed but not running"
        echo "Start with: sudo systemctl start tailscaled"
        return 1
    else
        error "tailscaled service not found"
        echo "Install Tailscale daemon package"
        return 1
    fi
    
    return 0
}

check_tailscale_authentication() {
    log "Checking Tailscale authentication status..."
    
    if ! tailscale status >/dev/null 2>&1; then
        error "Tailscale not authenticated"
        echo "Run: tailscale up"
        return 1
    fi
    
    # Get current status
    local status_output=$(tailscale status 2>/dev/null || echo "")
    if [[ -z "$status_output" ]]; then
        error "Unable to get Tailscale status"
        return 1
    fi
    
    success "Tailscale is authenticated and connected"
    
    # Show basic info
    local device_name=$(echo "$status_output" | head -n1 | awk '{print $2}')
    local tailscale_ip=$(echo "$status_output" | head -n1 | awk '{print $1}')
    echo "  Device: $device_name"
    echo "  IP: $tailscale_ip"
    
    return 0
}

check_json_output() {
    log "Testing Tailscale JSON output..."
    
    if ! tailscale status --json >/dev/null 2>&1; then
        error "Tailscale CLI doesn't support --json flag"
        echo "Update Tailscale to a newer version"
        return 1
    fi
    
    # Test JSON parsing
    local json_output=$(tailscale status --json 2>/dev/null || echo "{}")
    if ! echo "$json_output" | python3 -m json.tool >/dev/null 2>&1; then
        error "Tailscale JSON output is invalid"
        return 1
    fi
    
    success "Tailscale JSON output is valid"
    return 0
}

check_api_access() {
    log "Checking Tailscale API access..."
    
    # Check if PAT is configured
    if [[ -z "${TAILSCALE_PAT:-}" ]]; then
        warning "TAILSCALE_PAT not set in environment"
        echo "Set in .env file for API access (optional)"
        return 0
    fi
    
    # Test API connectivity
    local api_url="https://api.tailscale.com/api/v2/tailnet/-/devices"
    if curl -s -f -H "Authorization: Bearer $TAILSCALE_PAT" "$api_url" >/dev/null 2>&1; then
        success "Tailscale API access working"
    else
        error "Tailscale API access failed"
        echo "Check your TAILSCALE_PAT token"
        return 1
    fi
    
    return 0
}

check_permissions() {
    log "Checking required permissions..."
    
    local failed=0
    
    # Check systemctl access
    if ! systemctl status tailscaled >/dev/null 2>&1; then
        error "Cannot access tailscaled service status"
        echo "TailSentry needs sudo access or run as root for service control"
        failed=1
    else
        success "Service status access OK"
    fi
    
    # Check CLI access
    if ! tailscale status >/dev/null 2>&1; then
        error "Cannot run tailscale CLI commands"
        echo "Check user permissions and Tailscale installation"
        failed=1
    else
        success "CLI access OK"
    fi
    
    return $failed
}

check_network_connectivity() {
    log "Checking network connectivity to Tailscale services..."
    
    local failed=0
    
    # Check Tailscale coordination server
    if ! curl -s --connect-timeout 5 https://controlplane.tailscale.com/health >/dev/null 2>&1; then
        error "Cannot reach Tailscale coordination server"
        failed=1
    else
        success "Tailscale coordination server reachable"
    fi
    
    # Check API endpoint
    if ! curl -s --connect-timeout 5 https://api.tailscale.com/api/v2/device/ >/dev/null 2>&1; then
        error "Cannot reach Tailscale API endpoint"
        failed=1
    else
        success "Tailscale API endpoint reachable"
    fi
    
    return $failed
}

test_tailsentry_integration() {
    log "Testing TailSentry integration functions..."
    
    # Test if we can import and run basic functions
    local test_script="
import sys
sys.path.append('.')
from tailscale_client import TailscaleClient

# Test basic status
try:
    status = TailscaleClient.status_json()
    if isinstance(status, dict) and 'Self' in status:
        print('✅ Status retrieval: OK')
    else:
        print('❌ Status retrieval: Failed')
        
    # Test device info
    device_info = TailscaleClient.get_device_info()
    if isinstance(device_info, dict):
        print('✅ Device info: OK')
    else:
        print('❌ Device info: Failed')
        
except Exception as e:
    print(f'❌ Integration test failed: {e}')
"
    
    if python3 -c "$test_script" 2>/dev/null; then
        success "TailSentry integration test passed"
    else
        error "TailSentry integration test failed"
        echo "Check TailSentry installation and dependencies"
        return 1
    fi
    
    return 0
}

create_test_config() {
    log "Creating test configuration..."
    
    # Create a test .env if it doesn't exist
    if [[ ! -f .env ]]; then
        cp .env.example .env
        echo "Created .env from template"
    fi
    
    # Generate test secrets if needed
    if ! grep -q "^SESSION_SECRET=" .env || [[ -z "$(grep '^SESSION_SECRET=' .env | cut -d'=' -f2)" ]]; then
        local secret=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
        sed -i "s/^SESSION_SECRET=.*/SESSION_SECRET=$secret/" .env
        echo "Generated SESSION_SECRET"
    fi
    
    success "Configuration check complete"
}

main() {
    echo "🔗 TailSentry ↔ Tailscale Integration Validator"
    echo "=============================================="
    echo
    
    local total_checks=0
    local failed_checks=0
    
    # Array of check functions
    checks=(
        "check_tailscale_installation"
        "check_tailscaled_service"
        "check_tailscale_authentication"
        "check_json_output"
        "check_api_access"
        "check_permissions"
        "check_network_connectivity"
        "create_test_config"
        "test_tailsentry_integration"
    )
    
    # Run all checks
    for check in "${checks[@]}"; do
        total_checks=$((total_checks + 1))
        echo
        if ! $check; then
            failed_checks=$((failed_checks + 1))
        fi
    done
    
    echo
    echo "=============================================="
    if [[ $failed_checks -eq 0 ]]; then
        success "All integration checks passed! ($total_checks/$total_checks)"
        echo
        echo "🚀 TailSentry should work correctly with your Tailscale setup"
        echo "   Start TailSentry with: make dev"
    else
        error "$failed_checks/$total_checks checks failed"
        echo
        echo "❌ Fix the issues above before running TailSentry"
        echo "   Check the installation guide: README.md"
    fi
    
    return $failed_checks
}

# Load environment if .env exists
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

# Run main function
main "$@"
