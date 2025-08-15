#!/bin/bash
# TailSentry Smart Update Script
# Provides multiple update options with safety checks and rollback capability

set -e

# Configuration
INSTALL_DIR="/opt/tailsentry"
BACKUP_DIR="/opt/tailsentry/backups"
LOG_FILE="/var/log/tailsentry-update.log"
SERVICE_NAME="tailsentry"
REPO_URL="https://github.com/lolerskatez/TailSentry.git"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

# Success message
success() {
    log "${GREEN}✅ $1${NC}"
}

# Warning message
warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

# Info message
info() {
    log "${BLUE}ℹ️  $1${NC}"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error_exit "Please run as root (use sudo)"
    fi
}

# Get current version
get_current_version() {
    if [ -f "$INSTALL_DIR/main.py" ]; then
        grep -o 'version="[^"]*"' "$INSTALL_DIR/main.py" | head -1 | cut -d'"' -f2
    else
        echo "unknown"
    fi
}

# Create backup
create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/$timestamp"
    
    info "Creating backup..."
    mkdir -p "$backup_path"
    
    # Backup critical files
    [ -f "$INSTALL_DIR/.env" ] && cp "$INSTALL_DIR/.env" "$backup_path/"
    [ -d "$INSTALL_DIR/data" ] && cp -r "$INSTALL_DIR/data" "$backup_path/"
    [ -d "$INSTALL_DIR/logs" ] && cp -r "$INSTALL_DIR/logs" "$backup_path/"
    
    # Store current version info
    echo "$(get_current_version)" > "$backup_path/version.txt"
    
    success "Backup created at $backup_path"
    echo "$backup_path"
}

# Check service status
check_service() {
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "active"
    else
        echo "inactive"
    fi
}

# Stop service safely
stop_service() {
    if [ "$(check_service)" = "active" ]; then
        info "Stopping TailSentry service..."
        systemctl stop "$SERVICE_NAME"
        sleep 2
    fi
}

# Start service
start_service() {
    info "Starting TailSentry service..."
    systemctl start "$SERVICE_NAME"
    sleep 3
    
    if [ "$(check_service)" = "active" ]; then
        success "Service started successfully"
    else
        error_exit "Failed to start service"
    fi
}

# Update dependencies only
update_dependencies() {
    info "Updating Python dependencies..."
    cd "$INSTALL_DIR"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install -r requirements.txt --upgrade
        success "Dependencies updated"
    else
        warning "Virtual environment not found, skipping dependency update"
    fi
}

# Update code from git
update_code() {
    info "Updating code from repository..."
    cd "$INSTALL_DIR"
    
    if [ -d ".git" ]; then
        # Stash any local changes
        git stash push -m "Auto-stash before update $(date)"
        
        # Pull latest changes
        git pull origin main
        
        success "Code updated from repository"
    else
        error_exit "Git repository not found. Cannot update code."
    fi
}

# Configuration update (preserve user settings)
update_config() {
    info "Checking configuration updates..."
    
    # Check if there's a new .env.example
    if [ -f "$INSTALL_DIR/.env.example" ] && [ -f "$INSTALL_DIR/.env" ]; then
        # Compare and suggest new settings
        if ! diff -q "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env" >/dev/null 2>&1; then
            warning "New configuration options available in .env.example"
            info "Review .env.example for new settings"
        fi
    fi
}

# Health check
health_check() {
    info "Running health check..."
    
    # Check if service is running
    if [ "$(check_service)" != "active" ]; then
        error_exit "Service is not running after update"
    fi
    
    # Check if web interface is responding
    if command -v curl >/dev/null 2>&1; then
        if curl -f http://localhost:8000 >/dev/null 2>&1; then
            success "Web interface is responding"
        else
            warning "Web interface may not be responding correctly"
        fi
    fi
}

# Show update menu
show_menu() {
    echo -e "${BLUE}"
    echo "🔄 TailSentry Smart Update System"
    echo "=================================="
    echo -e "${NC}"
    echo "Current version: $(get_current_version)"
    echo "Service status: $(check_service)"
    echo ""
    echo "Update options:"
    echo "1. Quick Update (code + dependencies)"
    echo "2. Full Update (code + dependencies + config check)"
    echo "3. Dependencies Only"
    echo "4. Code Only"
    echo "5. Check for Updates (no install)"
    echo "6. Rollback to Previous Version"
    echo "7. Exit"
    echo ""
}

# Check for available updates
check_updates() {
    info "Checking for available updates..."
    cd "$INSTALL_DIR"
    
    if [ -d ".git" ]; then
        git fetch origin main
        local commits_behind=$(git rev-list --count HEAD..origin/main)
        
        if [ "$commits_behind" -gt 0 ]; then
            warning "Updates available: $commits_behind commits behind"
            git log --oneline HEAD..origin/main | head -5
        else
            success "Already up to date"
        fi
    else
        warning "Cannot check for updates without git repository"
    fi
}

# Rollback function
rollback() {
    echo "Available backups:"
    ls -la "$BACKUP_DIR/" 2>/dev/null | grep "^d" | tail -5
    echo ""
    read -p "Enter backup timestamp (YYYYMMDD_HHMMSS) to rollback to: " backup_timestamp
    
    local backup_path="$BACKUP_DIR/$backup_timestamp"
    if [ -d "$backup_path" ]; then
        info "Rolling back to backup: $backup_timestamp"
        
        stop_service
        
        # Restore files
        [ -f "$backup_path/.env" ] && cp "$backup_path/.env" "$INSTALL_DIR/"
        [ -d "$backup_path/data" ] && cp -r "$backup_path/data" "$INSTALL_DIR/"
        
        start_service
        success "Rollback completed"
    else
        error_exit "Backup not found: $backup_path"
    fi
}

# Main update functions
quick_update() {
    info "Starting quick update..."
    local backup_path=$(create_backup)
    
    stop_service
    update_code
    update_dependencies
    start_service
    health_check
    
    success "Quick update completed successfully!"
}

full_update() {
    info "Starting full update..."
    local backup_path=$(create_backup)
    
    stop_service
    update_code
    update_dependencies
    update_config
    start_service
    health_check
    
    success "Full update completed successfully!"
    info "Backup stored at: $backup_path"
}

# Main script
main() {
    check_root
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    while true; do
        show_menu
        read -p "Choose an option (1-7): " choice
        
        case $choice in
            1)
                quick_update
                ;;
            2)
                full_update
                ;;
            3)
                create_backup
                update_dependencies
                systemctl restart "$SERVICE_NAME"
                success "Dependencies updated"
                ;;
            4)
                create_backup
                stop_service
                update_code
                start_service
                success "Code updated"
                ;;
            5)
                check_updates
                ;;
            6)
                rollback
                ;;
            7)
                info "Exiting..."
                exit 0
                ;;
            *)
                error_exit "Invalid option"
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
        clear
    done
}

# Check if install directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    error_exit "TailSentry installation directory not found: $INSTALL_DIR"
fi

# Run main function
main
