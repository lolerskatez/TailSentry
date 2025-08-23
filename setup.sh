#!/bin/bash
# TailSentry Interactive Setup & Management Script
# Version: 2.0.0
# 
# This script handles:
# - Fresh installation
# - Installation with override (complete reinstall)
# - Updates/upgrades
# - Uninstallation
# - Service management
# - System validation

set -e  # Exit on any error

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_VERSION="2.0.0"
APP_NAME="TailSentry"
INSTALL_DIR="/opt/tailsentry"
SERVICE_NAME="tailsentry"
SERVICE_FILE="/etc/systemd/system/tailsentry.service"
REPO_URL="https://github.com/lolerskatez/TailSentry.git"
BACKUP_DIR="/opt/tailsentry-backups"
LOG_FILE="/tmp/tailsentry-setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

info() {
    log "${BLUE}[INFO]${NC} $1"
}

success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

error() {
    log "${RED}[ERROR]${NC} $1"
}

fatal() {
    error "$1"
    echo -e "\n${RED}Installation failed. Check log: $LOG_FILE${NC}"
    exit 1
}

print_header() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                      $APP_NAME SETUP & MANAGER                       ║"
    echo "║                        Version: $SCRIPT_VERSION                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_separator() {
    echo -e "${CYAN}════════════════════════════════════════════════════════════════════════${NC}"
}

confirm() {
    local prompt="$1"
    local expected="${2:-y}"
    local response
    
    if [[ "$expected" == "yes" ]]; then
        read -p "$prompt (type 'yes' to confirm): " response
        [[ "$response" == "yes" ]]
    else
        read -p "$prompt (y/N): " -n 1 -r response
        echo
        [[ $response =~ ^[Yy]$ ]]
    fi
}

pause() {
    echo
    read -p "Press Enter to continue..." _
    echo
}

# ============================================================================
# SYSTEM VALIDATION
# ============================================================================

check_root() {
    if [[ "$EUID" -ne 0 ]]; then
        fatal "This script must be run as root. Please use 'sudo $0'"
    fi
}

check_system() {
    info "Checking system requirements..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        fatal "Unsupported operating system"
    fi
    
    source /etc/os-release
    info "Operating System: $PRETTY_NAME"
    
    # Check for required commands
    local required_commands=("systemctl" "python3" "git" "curl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            fatal "$cmd is not installed. Please install it first."
        fi
    done
    
    # Check Python version
    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local min_version="3.9"
    
    if [[ "$(printf '%s\n' "$min_version" "$python_version" | sort -V | head -n1)" != "$min_version" ]]; then
        fatal "Python $min_version or higher is required. Found: $python_version"
    fi
    
    info "Python version: $python_version ✓"
    
    # Check for Tailscale
    if ! command -v tailscale &> /dev/null; then
        warning "Tailscale is not installed. Please install it first:"
        echo "  curl -fsSL https://tailscale.com/install.sh | sh"
        if ! confirm "Continue without Tailscale? (Not recommended)"; then
            exit 1
        fi
    else
        info "Tailscale is installed ✓"
    fi
    
    success "System requirements check passed"
}

install_dependencies() {
    info "Installing system dependencies..."
    
    # Detect package manager and install dependencies
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y python3 python3-venv python3-pip git curl logrotate
    elif command -v yum &> /dev/null; then
        yum install -y python3 python3-venv python3-pip git curl logrotate
    elif command -v dnf &> /dev/null; then
        dnf install -y python3 python3-venv python3-pip git curl logrotate
    elif command -v pacman &> /dev/null; then
        pacman -Sy --noconfirm python python-pip git curl logrotate
    else
        fatal "Unsupported package manager. Please install dependencies manually."
    fi
    
    success "Dependencies installed"
}

# ============================================================================
# BACKUP FUNCTIONS
# ============================================================================

create_backup() {
    if [[ ! -d "$INSTALL_DIR" ]]; then
        warning "No installation found to backup"
        return 0
    fi
    
    local backup_name="tailsentry-backup-$(date +%Y%m%d-%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name.tar.gz"
    
    info "Creating backup: $backup_name"
    mkdir -p "$BACKUP_DIR"
    
    # Stop service during backup
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    # Create backup
    tar -czf "$backup_path" -C "$(dirname "$INSTALL_DIR")" "$(basename "$INSTALL_DIR")" 2>/dev/null || {
        warning "Backup failed, but continuing..."
        return 0
    }
    
    # Restart service
    systemctl start "$SERVICE_NAME" 2>/dev/null || true
    
    success "Backup created: $backup_path"
    
    # Keep only last 5 backups
    ls -t "$BACKUP_DIR"/tailsentry-backup-*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
}

list_backups() {
    echo -e "\n${BLUE}Available Backups:${NC}"
    if [[ -d "$BACKUP_DIR" ]]; then
        ls -la "$BACKUP_DIR"/tailsentry-backup-*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}' || echo "  No backups found"
    else
        echo "  No backup directory found"
    fi
}

restore_backup() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        error "No backup directory found"
        return 1
    fi
    
    local backups=($(ls -t "$BACKUP_DIR"/tailsentry-backup-*.tar.gz 2>/dev/null))
    if [[ ${#backups[@]} -eq 0 ]]; then
        error "No backups found"
        return 1
    fi
    
    echo -e "\n${BLUE}Available Backups:${NC}"
    for i in "${!backups[@]}"; do
        echo "  $((i+1)). $(basename "${backups[$i]}")"
    done
    
    read -p "Select backup to restore (1-${#backups[@]}): " choice
    choice=$((choice-1))
    
    if [[ $choice -lt 0 || $choice -ge ${#backups[@]} ]]; then
        error "Invalid selection"
        return 1
    fi
    
    local backup_file="${backups[$choice]}"
    warning "This will stop TailSentry and restore from backup: $(basename "$backup_file")"
    if ! confirm "Continue with restore?"; then
        return 1
    fi
    
    # Stop service
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    # Remove current installation
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    # Restore from backup
    mkdir -p "$(dirname "$INSTALL_DIR")"
    tar -xzf "$backup_file" -C "$(dirname "$INSTALL_DIR")"
    
    # Restart service
    systemctl daemon-reload
    systemctl start "$SERVICE_NAME"
    
    success "Backup restored successfully"
}

# ============================================================================
# INSTALLATION FUNCTIONS
# ============================================================================

download_application() {
    info "Downloading $APP_NAME..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
    fi
    
    mkdir -p "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR" || fatal "Failed to download application"
    
    success "Application downloaded"
}

setup_python_environment() {
    info "Setting up Python environment..."
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    python3 -m venv venv || fatal "Failed to create virtual environment"
    
    # Activate and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt || fatal "Failed to install Python dependencies"
    
    success "Python environment configured"
}

configure_application() {
    info "Configuring application..."
    
    cd "$INSTALL_DIR"
    
    # Create config directory
    mkdir -p config data logs
    
    # Generate session secret
    local session_secret=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Create .env file
    cat > .env << EOF
# TailSentry Environment Configuration
# Generated on $(date)

# Security Settings
SESSION_SECRET='$session_secret'
SESSION_TIMEOUT_MINUTES=30

# Development Mode (change to false for production)
DEVELOPMENT=false

# Application Settings
LOG_LEVEL=INFO
LOG_FORMAT='%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Tailscale Integration
TAILSCALE_TAILNET=-
TAILSCALE_API_TIMEOUT=10
TAILSENTRY_FORCE_LIVE_DATA=true
TAILSENTRY_DATA_DIR='$INSTALL_DIR/data'

# Health Check and Backup Settings
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=300
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30

# CORS Settings
ALLOWED_ORIGIN=*
EOF

    chmod 600 .env
    
    # Prompt for Tailscale PAT
    echo
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                     TAILSCALE CONFIGURATION                         ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo "TailSentry requires a Tailscale Authentication Key to manage your network."
    echo "• Enter it now for full functionality"
    echo "• Or skip and configure later in the dashboard"
    echo
    echo "Get your key at: https://login.tailscale.com/admin/settings/keys"
    echo
    read -s -p "Enter Tailscale Authentication Key (or press Enter to skip): " TS_PAT
    echo
    
    # Save Tailscale settings
    if [[ -n "$TS_PAT" ]]; then
        python3 << EOF
import json
import os

config_dir = 'config'
settings_path = os.path.join(config_dir, 'tailscale_settings.json')
os.makedirs(config_dir, exist_ok=True)

settings = {'auth_key': '$TS_PAT'}
with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
print("Tailscale Authentication Key saved")
EOF
    else
        echo '{"auth_key": ""}' > config/tailscale_settings.json
        echo "Tailscale key can be configured later in the dashboard"
    fi
    
    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"
    chmod 600 "$INSTALL_DIR"/config/*.json 2>/dev/null || true
    
    success "Application configured"
}

install_service() {
    info "Installing systemd service..."
    
    # Copy service file
    cp "$INSTALL_DIR/tailsentry.service" "$SERVICE_FILE" || fatal "Failed to copy service file"
    
    # Configure network access
    echo
    echo "Network Access Configuration:"
    echo "• Local only: Access restricted to localhost (127.0.0.1:8080)"
    echo "• Network: Access from local and Tailscale networks (0.0.0.0:8080)"
    echo
    if confirm "Enable network access? (recommended)"; then
        info "Configuring for network access (0.0.0.0:8080)"
        # Service file already has 0.0.0.0 binding
    else
        info "Configuring for localhost-only access (127.0.0.1:8080)"
        sed -i 's/--host 0.0.0.0/--host 127.0.0.1/' "$SERVICE_FILE"
    fi
    
    # Install logrotate configuration
    cat > /etc/logrotate.d/tailsentry << EOF
$INSTALL_DIR/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 root root
    postrotate
        systemctl reload tailsentry.service 2>/dev/null || true
    endscript
}
EOF
    
    # Enable and start service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    
    success "Service installed and started"
}

configure_firewall() {
    info "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        if ufw status | grep -q "Status: active"; then
            ufw allow 8080
            success "UFW firewall configured for port 8080"
        else
            info "UFW firewall is not active"
        fi
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=8080/tcp
        firewall-cmd --reload
        success "firewalld configured for port 8080"
    else
        warning "No supported firewall detected. You may need to manually open port 8080"
    fi
}

# ============================================================================
# MAIN INSTALLATION FUNCTIONS
# ============================================================================

fresh_install() {
    print_header
    echo -e "${GREEN}Fresh Installation${NC}"
    print_separator
    
    # Check if already installed
    if [[ -d "$INSTALL_DIR" ]] || systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        error "TailSentry is already installed!"
        echo
        echo "Choose one of these options:"
        echo "• Use 'Update/Upgrade' to update existing installation"
        echo "• Use 'Install with Override' to completely reinstall"
        echo "• Use 'Uninstall' to remove current installation first"
        pause
        return 1
    fi
    
    echo "This will install TailSentry on your system."
    if ! confirm "Continue with fresh installation?"; then
        return 1
    fi
    
    check_system
    install_dependencies
    download_application
    setup_python_environment
    configure_application
    install_service
    configure_firewall
    
    show_completion_message
}

install_with_override() {
    print_header
    echo -e "${RED}Install with Override (Complete Reinstall)${NC}"
    print_separator
    
    echo -e "${RED}⚠️  WARNING: This will completely remove the existing installation!${NC}"
    echo
    echo "This operation will:"
    echo "• Stop the TailSentry service"
    echo "• Delete ALL configuration files"
    echo "• Delete ALL user data and settings"
    echo "• Delete ALL logs and backups"
    echo "• Perform a fresh installation"
    echo
    echo -e "${RED}ALL DATA WILL BE PERMANENTLY LOST!${NC}"
    echo
    
    if ! confirm "Do you understand that ALL data will be lost?" "yes"; then
        return 1
    fi
    
    echo
    echo -e "${RED}Last chance to abort!${NC}"
    if ! confirm "Type 'yes' to continue with complete reinstall" "yes"; then
        return 1
    fi
    
    # Stop service
    info "Stopping TailSentry service..."
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    
    # Remove everything
    info "Removing existing installation..."
    rm -rf "$INSTALL_DIR"
    rm -f "$SERVICE_FILE"
    rm -f /etc/logrotate.d/tailsentry
    rm -rf "$BACKUP_DIR"
    
    # Clean systemd
    systemctl daemon-reload
    
    success "Previous installation removed"
    
    # Proceed with fresh installation
    check_system
    install_dependencies
    download_application
    setup_python_environment
    configure_application
    install_service
    configure_firewall
    
    show_completion_message
}

update_installation() {
    print_header
    echo -e "${BLUE}Update/Upgrade Installation${NC}"
    print_separator
    
    # Check if installed
    if [[ ! -d "$INSTALL_DIR" ]]; then
        error "TailSentry is not installed. Use 'Fresh Install' instead."
        pause
        return 1
    fi
    
    echo "This will update TailSentry while preserving your data and configuration."
    if ! confirm "Continue with update?"; then
        return 1
    fi
    
    # Create backup
    create_backup
    
    # Stop service
    info "Stopping TailSentry service..."
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    # Backup current config
    local temp_config="/tmp/tailsentry-config-backup"
    mkdir -p "$temp_config"
    cp -r "$INSTALL_DIR"/config/* "$temp_config"/ 2>/dev/null || true
    cp "$INSTALL_DIR"/.env "$temp_config"/ 2>/dev/null || true
    
    # Update application
    cd "$INSTALL_DIR"
    git fetch origin
    git reset --hard origin/main
    
    # Update Python dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Restore config
    cp -r "$temp_config"/* "$INSTALL_DIR"/config/ 2>/dev/null || true
    cp "$temp_config"/.env "$INSTALL_DIR"/ 2>/dev/null || true
    rm -rf "$temp_config"
    
    # Update service file if needed
    if [[ -f "$INSTALL_DIR/tailsentry.service" ]]; then
        cp "$INSTALL_DIR/tailsentry.service" "$SERVICE_FILE"
    fi
    
    # Restart service
    systemctl daemon-reload
    systemctl start "$SERVICE_NAME"
    
    success "TailSentry updated successfully"
    show_status
    pause
}

uninstall_application() {
    print_header
    echo -e "${RED}Uninstall TailSentry${NC}"
    print_separator
    
    if [[ ! -d "$INSTALL_DIR" ]] && ! systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        warning "TailSentry does not appear to be installed"
        pause
        return 0
    fi
    
    echo -e "${RED}⚠️  This will completely remove TailSentry from your system!${NC}"
    echo
    echo "This will remove:"
    echo "• TailSentry application and all files"
    echo "• Service configuration"
    echo "• All user data and configuration"
    echo "• All logs"
    echo "• Backups will be preserved in $BACKUP_DIR"
    echo
    
    if ! confirm "Are you sure you want to uninstall TailSentry?" "yes"; then
        return 1
    fi
    
    # Create final backup
    create_backup
    
    # Stop and disable service
    info "Stopping TailSentry service..."
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    
    # Remove files
    info "Removing application files..."
    rm -rf "$INSTALL_DIR"
    rm -f "$SERVICE_FILE"
    rm -f /etc/logrotate.d/tailsentry
    
    # Clean systemd
    systemctl daemon-reload
    
    # Kill any remaining processes
    pkill -f "uvicorn.*tailsentry" 2>/dev/null || true
    pkill -f "python.*main.py" 2>/dev/null || true
    
    success "TailSentry has been completely uninstalled"
    echo
    echo "Backups are preserved in: $BACKUP_DIR"
    echo "To reinstall, run this script again and choose 'Fresh Install'"
    pause
}

# ============================================================================
# STATUS AND MANAGEMENT
# ============================================================================

show_status() {
    print_header
    echo -e "${BLUE}TailSentry Status${NC}"
    print_separator
    
    # Check installation
    if [[ -d "$INSTALL_DIR" ]]; then
        echo -e "${GREEN}✓${NC} Installation directory: $INSTALL_DIR"
    else
        echo -e "${RED}✗${NC} Installation directory not found"
        return 1
    fi
    
    # Check service
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✓${NC} Service: Running"
    else
        echo -e "${RED}✗${NC} Service: Stopped"
    fi
    
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✓${NC} Service: Enabled (starts on boot)"
    else
        echo -e "${YELLOW}⚠${NC} Service: Disabled"
    fi
    
    # Check network
    if curl -s --connect-timeout 5 http://localhost:8080/health &>/dev/null; then
        echo -e "${GREEN}✓${NC} Web interface: Accessible at http://localhost:8080"
    else
        echo -e "${YELLOW}⚠${NC} Web interface: Not responding"
    fi
    
    # Check Tailscale
    if command -v tailscale &>/dev/null; then
        if tailscale status &>/dev/null; then
            echo -e "${GREEN}✓${NC} Tailscale: Connected"
        else
            echo -e "${YELLOW}⚠${NC} Tailscale: Not connected"
        fi
    else
        echo -e "${RED}✗${NC} Tailscale: Not installed"
    fi
    
    # Show version
    if [[ -f "$INSTALL_DIR/version.py" ]]; then
        local version=$(python3 -c "import sys; sys.path.insert(0, '$INSTALL_DIR'); from version import VERSION; print(VERSION)" 2>/dev/null)
        echo -e "${BLUE}ℹ${NC} Version: ${version:-Unknown}"
    fi
    
    # Show resource usage
    local disk_usage=$(du -sh "$INSTALL_DIR" 2>/dev/null | cut -f1)
    echo -e "${BLUE}ℹ${NC} Disk usage: ${disk_usage:-Unknown}"
    
    echo
}

service_management() {
    while true; do
        print_header
        echo -e "${BLUE}Service Management${NC}"
        print_separator
        
        # Show current status
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo -e "Current status: ${GREEN}Running${NC}"
        else
            echo -e "Current status: ${RED}Stopped${NC}"
        fi
        echo
        
        echo "1. Start service"
        echo "2. Stop service"
        echo "3. Restart service"
        echo "4. Enable auto-start"
        echo "5. Disable auto-start"
        echo "6. View logs"
        echo "0. Back to main menu"
        echo
        
        read -p "Choose an option: " choice
        
        case $choice in
            1)
                systemctl start "$SERVICE_NAME"
                success "Service started"
                ;;
            2)
                systemctl stop "$SERVICE_NAME"
                success "Service stopped"
                ;;
            3)
                systemctl restart "$SERVICE_NAME"
                success "Service restarted"
                ;;
            4)
                systemctl enable "$SERVICE_NAME"
                success "Auto-start enabled"
                ;;
            5)
                systemctl disable "$SERVICE_NAME"
                success "Auto-start disabled"
                ;;
            6)
                echo "Showing last 50 lines of logs (Ctrl+C to exit):"
                journalctl -u "$SERVICE_NAME" -n 50 -f
                ;;
            0)
                break
                ;;
            *)
                error "Invalid option"
                ;;
        esac
        
        if [[ $choice != 6 ]]; then
            pause
        fi
    done
}

show_completion_message() {
    clear
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                    INSTALLATION COMPLETE!                           ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
    echo -e "${GREEN}🎉 TailSentry is now running and managing your Tailscale network!${NC}"
    echo
    echo -e "${BLUE}Access Information:${NC}"
    echo "• Local:     http://localhost:8080"
    echo "• Network:   http://$(hostname -I | awk '{print $1}' 2>/dev/null):8080"
    echo
    echo -e "${BLUE}Default Credentials:${NC}"
    echo "• Username: admin"
    echo "• Password: admin123"
    echo
    echo -e "${RED}⚠️  IMPORTANT: Change the default password after first login!${NC}"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Open TailSentry in your browser"
    echo "2. Login with admin / admin123"
    echo "3. Change your password in the settings"
    echo "4. Configure your Tailscale Authentication Key if not set during installation"
    echo
    echo -e "${BLUE}Management:${NC}"
    echo "• Run this script again to manage your installation"
    echo "• Use 'systemctl status tailsentry' to check service status"
    echo "• View logs with 'journalctl -u tailsentry -f'"
    echo
    pause
}

# ============================================================================
# MAIN MENU
# ============================================================================

show_main_menu() {
    while true; do
        print_header
        echo -e "${BLUE}Main Menu${NC}"
        print_separator
        
        # Show current status
        if [[ -d "$INSTALL_DIR" ]]; then
            if systemctl is-active --quiet "$SERVICE_NAME"; then
                echo -e "Status: ${GREEN}Installed and Running${NC}"
            else
                echo -e "Status: ${YELLOW}Installed but Stopped${NC}"
            fi
        else
            echo -e "Status: ${RED}Not Installed${NC}"
        fi
        echo
        
        echo -e "${GREEN}Installation Options:${NC}"
        echo "1. Fresh Install - New installation (fails if already exists)"
        echo "2. Install with Override - ⚠️  Complete reinstall (destroys all data)"
        echo "3. Update/Upgrade - Preserve data, apply updates"
        echo "4. Uninstall - Remove TailSentry completely"
        echo
        echo -e "${BLUE}Management Options:${NC}"
        echo "5. Show Status - Detailed installation status"
        echo "6. Service Management - Start/stop/restart service"
        echo "7. Backup Management - Create/restore backups"
        echo
        echo -e "${PURPLE}Other:${NC}"
        echo "8. View Installation Guide"
        echo "0. Exit"
        echo
        
        read -p "Choose an option (0-8): " choice
        
        case $choice in
            1)
                fresh_install
                ;;
            2)
                install_with_override
                ;;
            3)
                update_installation
                ;;
            4)
                uninstall_application
                ;;
            5)
                show_status
                pause
                ;;
            6)
                service_management
                ;;
            7)
                backup_management
                ;;
            8)
                show_installation_guide
                ;;
            0)
                echo -e "\n${GREEN}Thank you for using TailSentry Setup!${NC}"
                exit 0
                ;;
            *)
                error "Invalid option. Please choose 0-8."
                pause
                ;;
        esac
    done
}

backup_management() {
    while true; do
        print_header
        echo -e "${BLUE}Backup Management${NC}"
        print_separator
        
        echo "1. Create backup"
        echo "2. List backups"
        echo "3. Restore from backup"
        echo "0. Back to main menu"
        echo
        
        read -p "Choose an option: " choice
        
        case $choice in
            1)
                create_backup
                pause
                ;;
            2)
                list_backups
                pause
                ;;
            3)
                restore_backup
                pause
                ;;
            0)
                break
                ;;
            *)
                error "Invalid option"
                pause
                ;;
        esac
    done
}

show_installation_guide() {
    print_header
    echo -e "${BLUE}TailSentry Installation Guide${NC}"
    print_separator
    
    echo "For complete installation documentation, visit:"
    echo "https://github.com/lolerskatez/TailSentry/blob/main/INSTALLATION_GUIDE.md"
    echo
    echo -e "${BLUE}Quick Start:${NC}"
    echo "1. Ensure Tailscale is installed and running"
    echo "2. Run this script as root: sudo ./setup.sh"
    echo "3. Choose 'Fresh Install' from the menu"
    echo "4. Follow the prompts to configure TailSentry"
    echo "5. Access the web interface at http://localhost:8080"
    echo
    echo -e "${BLUE}System Requirements:${NC}"
    echo "• Linux system with systemd"
    echo "• Python 3.9 or higher"
    echo "• Git, curl, and standard build tools"
    echo "• Tailscale installed and configured"
    echo "• 512MB+ RAM and 1GB+ free disk space"
    echo
    echo -e "${BLUE}Support:${NC}"
    echo "• GitHub Issues: https://github.com/lolerskatez/TailSentry/issues"
    echo "• Documentation: https://github.com/lolerskatez/TailSentry"
    echo
    pause
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    # Handle command line arguments
    case "${1:-}" in
        install)
            check_root
            fresh_install
            ;;
        install-override)
            check_root
            install_with_override
            ;;
        update)
            check_root
            update_installation
            ;;
        uninstall)
            check_root
            uninstall_application
            ;;
        status)
            show_status
            ;;
        --help|-h)
            echo "TailSentry Setup Script v$SCRIPT_VERSION"
            echo "Usage: $0 [command]"
            echo
            echo "Commands:"
            echo "  install         - Fresh installation"
            echo "  install-override - Complete reinstall (destroys data)"
            echo "  update          - Update existing installation"
            echo "  uninstall       - Remove TailSentry"
            echo "  status          - Show installation status"
            echo
            echo "Run without arguments for interactive menu."
            ;;
        *)
            check_root
            show_main_menu
            ;;
    esac
}

# Run main function with all arguments
main "$@"
