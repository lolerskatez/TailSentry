#!/bin/bash
# TailSentry Installation Validator
# This script checks if the system is ready for TailSentry installation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                   TailSentry Installation Validator                 ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_ok() {
    echo -e "  ${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "  ${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    ((CHECKS_WARNING++))
}

print_section() {
    echo -e "\n${BLUE}$1${NC}"
    echo "────────────────────────────────────────────────────────────────────────"
}

check_system() {
    print_section "System Requirements"
    
    # Check if running as root
    if [[ "$EUID" -eq 0 ]]; then
        check_ok "Running as root"
    else
        check_warn "Not running as root (will need sudo for installation)"
    fi
    
    # Check OS
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        check_ok "Operating system: $PRETTY_NAME"
        
        # Check for supported OS
        case "$ID" in
            ubuntu|debian|centos|rhel|fedora|arch)
                check_ok "Supported operating system"
                ;;
            *)
                check_warn "Operating system may not be fully supported"
                ;;
        esac
    else
        check_fail "Cannot determine operating system"
    fi
    
    # Check system resources
    local memory_mb
    memory_mb=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    if [[ "$memory_mb" -ge 512 ]]; then
        check_ok "Memory: ${memory_mb}MB (sufficient)"
    else
        check_warn "Memory: ${memory_mb}MB (minimum 512MB recommended)"
    fi
    
    local disk_gb
    disk_gb=$(df / | awk 'NR==2 {printf "%.1f", $4/1024/1024}')
    if (( $(echo "$disk_gb > 1.0" | bc -l) )); then
        check_ok "Free disk space: ${disk_gb}GB"
    else
        check_warn "Free disk space: ${disk_gb}GB (minimum 1GB recommended)"
    fi
}

check_dependencies() {
    print_section "Required Dependencies"
    
    # Check essential commands
    local commands=("systemctl" "curl" "git")
    for cmd in "${commands[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            check_ok "$cmd is installed"
        else
            check_fail "$cmd is not installed"
        fi
    done
    
    # Check Python
    if command -v python3 &> /dev/null; then
        local python_version
        python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        local min_version="3.9"
        
        if [[ "$(printf '%s\n' "$min_version" "$python_version" | sort -V | head -n1)" == "$min_version" ]]; then
            check_ok "Python $python_version (compatible)"
        else
            check_fail "Python $python_version (minimum 3.9 required)"
        fi
        
        # Check pip
        if python3 -m pip --version &> /dev/null; then
            check_ok "pip is available"
        else
            check_fail "pip is not available"
        fi
        
        # Check venv
        if python3 -m venv --help &> /dev/null; then
            check_ok "venv module is available"
        else
            check_fail "venv module is not available"
        fi
    else
        check_fail "Python 3 is not installed"
    fi
    
    # Check package manager
    if command -v apt-get &> /dev/null; then
        check_ok "Package manager: apt (Debian/Ubuntu)"
    elif command -v yum &> /dev/null; then
        check_ok "Package manager: yum (RHEL/CentOS)"
    elif command -v dnf &> /dev/null; then
        check_ok "Package manager: dnf (Fedora)"
    elif command -v pacman &> /dev/null; then
        check_ok "Package manager: pacman (Arch)"
    else
        check_warn "No supported package manager found"
    fi
}

check_tailscale() {
    print_section "Tailscale Integration"
    
    if command -v tailscale &> /dev/null; then
        check_ok "Tailscale CLI is installed"
        
        # Check if Tailscale is running
        if tailscale status &> /dev/null; then
            check_ok "Tailscale is running"
            
            # Get status
            local status
            status=$(tailscale status --json 2>/dev/null || echo '{}')
            
            if echo "$status" | grep -q '"BackendState":"Running"'; then
                check_ok "Tailscale backend is running"
            else
                check_warn "Tailscale backend may not be fully initialized"
            fi
            
        else
            check_warn "Tailscale is installed but not running"
        fi
        
        # Check for Tailscale socket
        if [[ -S /var/run/tailscale/tailscaled.sock ]]; then
            check_ok "Tailscale socket is available"
        else
            check_warn "Tailscale socket not found (may affect some features)"
        fi
        
    else
        check_fail "Tailscale is not installed"
        echo "         Install with: curl -fsSL https://tailscale.com/install.sh | sh"
    fi
}

check_network() {
    print_section "Network Connectivity"
    
    # Check internet connectivity
    if curl -s --connect-timeout 5 https://google.com &> /dev/null; then
        check_ok "Internet connectivity"
    else
        check_fail "No internet connectivity"
    fi
    
    # Check GitHub access
    if curl -s --connect-timeout 5 https://github.com &> /dev/null; then
        check_ok "GitHub access"
    else
        check_fail "Cannot access GitHub"
    fi
    
    # Check if port 8080 is available
    if ! ss -tlpn 2>/dev/null | grep -q ":8080 "; then
        check_ok "Port 8080 is available"
    else
        check_warn "Port 8080 is in use (TailSentry uses this port)"
    fi
}

check_permissions() {
    print_section "Permissions and Security"
    
    # Check write access to /opt
    if [[ -w /opt ]] || [[ "$EUID" -eq 0 ]]; then
        check_ok "Can write to /opt directory"
    else
        check_warn "Cannot write to /opt directory (will need sudo)"
    fi
    
    # Check systemd access
    if systemctl --version &> /dev/null; then
        check_ok "systemd is available"
        
        if [[ "$EUID" -eq 0 ]] || groups | grep -q sudo; then
            check_ok "Can manage systemd services"
        else
            check_warn "May not be able to manage systemd services"
        fi
    else
        check_fail "systemd is not available"
    fi
    
    # Check if SELinux is enforcing
    if command -v getenforce &> /dev/null; then
        local selinux_status
        selinux_status=$(getenforce 2>/dev/null || echo "Unknown")
        if [[ "$selinux_status" == "Enforcing" ]]; then
            check_warn "SELinux is enforcing (may require additional configuration)"
        else
            check_ok "SELinux is not enforcing"
        fi
    fi
}

check_existing_installation() {
    print_section "Existing Installation"
    
    if [[ -d /opt/tailsentry ]]; then
        check_warn "TailSentry is already installed in /opt/tailsentry"
        
        if systemctl is-active --quiet tailsentry 2>/dev/null; then
            check_warn "TailSentry service is running"
        else
            check_ok "TailSentry service is not running"
        fi
        
        if [[ -f /opt/tailsentry/version.py ]]; then
            local version
            version=$(cd /opt/tailsentry && python3 -c "from version import VERSION; print(VERSION)" 2>/dev/null || echo "Unknown")
            echo "         Current version: $version"
        fi
    else
        check_ok "No existing installation found"
    fi
    
    if [[ -f /etc/systemd/system/tailsentry.service ]]; then
        check_warn "TailSentry systemd service file exists"
    else
        check_ok "No conflicting systemd service"
    fi
}

generate_install_command() {
    print_section "Installation Commands"
    
    echo "Based on the validation results, you can install TailSentry using:"
    echo ""
    
    if [[ "$CHECKS_FAILED" -eq 0 ]]; then
        echo -e "${GREEN}Quick Installation:${NC}"
        echo "  curl -fsSL https://raw.githubusercontent.com/lolerskatez/TailSentry/main/quick-install.sh | sudo bash"
        echo ""
        echo -e "${GREEN}Manual Installation:${NC}"
        echo "  wget https://raw.githubusercontent.com/lolerskatez/TailSentry/main/tailsentry-installer"
        echo "  chmod +x tailsentry-installer"
        echo "  sudo ./tailsentry-installer install"
    else
        echo -e "${RED}Please fix the failed checks before installing.${NC}"
    fi
    
    if [[ "$CHECKS_WARNING" -gt 0 ]]; then
        echo ""
        echo -e "${YELLOW}Note: There are warnings that may require attention.${NC}"
    fi
}

print_summary() {
    print_section "Validation Summary"
    
    echo -e "  ${GREEN}Checks passed:${NC} $CHECKS_PASSED"
    echo -e "  ${YELLOW}Warnings:${NC} $CHECKS_WARNING"
    echo -e "  ${RED}Checks failed:${NC} $CHECKS_FAILED"
    echo ""
    
    if [[ "$CHECKS_FAILED" -eq 0 ]]; then
        echo -e "${GREEN}✓ System is ready for TailSentry installation!${NC}"
    elif [[ "$CHECKS_FAILED" -le 2 ]]; then
        echo -e "${YELLOW}⚠ System may be ready with minor fixes${NC}"
    else
        echo -e "${RED}✗ System requires fixes before installation${NC}"
    fi
}

# Main execution
main() {
    print_header
    check_system
    check_dependencies
    check_tailscale
    check_network
    check_permissions
    check_existing_installation
    generate_install_command
    print_summary
}

main "$@"
