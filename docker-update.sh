#!/bin/bash
# TailSentry Docker Update Script
# For containerized deployments

set -e

# Configuration
CONTAINER_NAME="tailsentry"
IMAGE_NAME="tailsentry:latest"
DATA_VOLUME="tailsentry_data"
CONFIG_VOLUME="tailsentry_config"
BACKUP_DIR="./backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error_exit() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

success() {
    log "${GREEN}✅ $1${NC}"
}

warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

info() {
    log "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is available
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        error_exit "Docker is not installed or not in PATH"
    fi
    
    if ! docker info >/dev/null 2>&1; then
        error_exit "Cannot connect to Docker daemon"
    fi
}

# Get current container version
get_current_version() {
    if docker ps -q -f name="$CONTAINER_NAME" >/dev/null 2>&1; then
        docker exec "$CONTAINER_NAME" python -c "
try:
    from version import VERSION
    print(VERSION)
except:
    print('unknown')
" 2>/dev/null || echo "unknown"
    else
        echo "not_running"
    fi
}

# Create backup of volumes
create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/$timestamp"
    
    info "Creating backup of volumes..."
    mkdir -p "$backup_path"
    
    # Backup data volume
    if docker volume inspect "$DATA_VOLUME" >/dev/null 2>&1; then
        docker run --rm -v "$DATA_VOLUME:/data" -v "$(pwd)/$backup_path:/backup" alpine:latest \
            tar czf /backup/data.tar.gz -C /data .
        success "Data volume backed up"
    fi
    
    # Backup config volume
    if docker volume inspect "$CONFIG_VOLUME" >/dev/null 2>&1; then
        docker run --rm -v "$CONFIG_VOLUME:/config" -v "$(pwd)/$backup_path:/backup" alpine:latest \
            tar czf /backup/config.tar.gz -C /config .
        success "Config volume backed up"
    fi
    
    # Store version info
    echo "$(get_current_version)" > "$backup_path/version.txt"
    
    success "Backup created at $backup_path"
    echo "$backup_path"
}

# Pull latest image
pull_image() {
    info "Pulling latest image..."
    docker pull "$IMAGE_NAME"
    success "Image updated"
}

# Update container
update_container() {
    local backup_path=$(create_backup)
    
    info "Stopping current container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    
    pull_image
    
    info "Starting updated container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p 8000:8000 \
        -v "$DATA_VOLUME:/app/data" \
        -v "$CONFIG_VOLUME:/app/config" \
        "$IMAGE_NAME"
    
    # Wait for container to be ready
    sleep 10
    
    if docker ps -q -f name="$CONTAINER_NAME" >/dev/null 2>&1; then
        success "Container updated successfully"
        info "Backup stored at: $backup_path"
    else
        error_exit "Failed to start updated container"
    fi
}

# Check for updates
check_updates() {
    info "Checking for image updates..."
    
    # Get current image ID
    local current_id=$(docker images -q "$IMAGE_NAME" 2>/dev/null)
    
    # Pull latest and get new ID
    docker pull "$IMAGE_NAME" >/dev/null 2>&1
    local latest_id=$(docker images -q "$IMAGE_NAME" 2>/dev/null)
    
    if [ "$current_id" != "$latest_id" ]; then
        warning "Updates available for $IMAGE_NAME"
        return 0
    else
        success "Already running latest version"
        return 1
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
        
        # Stop current container
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
        
        # Restore volumes
        if [ -f "$backup_path/data.tar.gz" ]; then
            docker run --rm -v "$DATA_VOLUME:/data" -v "$(pwd)/$backup_path:/backup" alpine:latest \
                tar xzf /backup/data.tar.gz -C /data
        fi
        
        if [ -f "$backup_path/config.tar.gz" ]; then
            docker run --rm -v "$CONFIG_VOLUME:/config" -v "$(pwd)/$backup_path:/backup" alpine:latest \
                tar xzf /backup/config.tar.gz -C /config
        fi
        
        # Restart container
        docker run -d \
            --name "$CONTAINER_NAME" \
            --restart unless-stopped \
            -p 8000:8000 \
            -v "$DATA_VOLUME:/app/data" \
            -v "$CONFIG_VOLUME:/app/config" \
            "$IMAGE_NAME"
        
        success "Rollback completed"
    else
        error_exit "Backup not found: $backup_path"
    fi
}

# Show menu
show_menu() {
    echo -e "${BLUE}"
    echo "🐳 TailSentry Docker Update System"
    echo "==================================="
    echo -e "${NC}"
    echo "Current version: $(get_current_version)"
    echo "Container status: $(docker ps -f name="$CONTAINER_NAME" --format "table {{.Status}}" | tail -n +2 || echo "Not running")"
    echo ""
    echo "Update options:"
    echo "1. Update Container (pull latest image)"
    echo "2. Check for Updates"
    echo "3. Rebuild from Source"
    echo "4. Rollback to Previous Version"
    echo "5. View Logs"
    echo "6. Container Status"
    echo "7. Exit"
    echo ""
}

# Rebuild from source
rebuild_from_source() {
    info "Rebuilding from source..."
    
    if [ ! -f "Dockerfile" ]; then
        error_exit "Dockerfile not found in current directory"
    fi
    
    local backup_path=$(create_backup)
    
    # Stop container
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    
    # Build new image
    docker build -t "$IMAGE_NAME" .
    
    # Start container
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p 8000:8000 \
        -v "$DATA_VOLUME:/app/data" \
        -v "$CONFIG_VOLUME:/app/config" \
        "$IMAGE_NAME"
    
    success "Rebuilt and restarted from source"
}

# View logs
view_logs() {
    if docker ps -q -f name="$CONTAINER_NAME" >/dev/null 2>&1; then
        docker logs -f --tail=50 "$CONTAINER_NAME"
    else
        error_exit "Container is not running"
    fi
}

# Container status
container_status() {
    echo "Container Information:"
    echo "====================="
    docker ps -f name="$CONTAINER_NAME"
    echo ""
    echo "Resource Usage:"
    docker stats --no-stream "$CONTAINER_NAME" 2>/dev/null || echo "Container not running"
    echo ""
    echo "Volumes:"
    docker volume ls | grep tailsentry || echo "No TailSentry volumes found"
}

# Main function
main() {
    check_docker
    mkdir -p "$BACKUP_DIR"
    
    while true; do
        show_menu
        read -p "Choose an option (1-7): " choice
        
        case $choice in
            1)
                update_container
                ;;
            2)
                check_updates
                ;;
            3)
                rebuild_from_source
                ;;
            4)
                rollback
                ;;
            5)
                view_logs
                ;;
            6)
                container_status
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

main
