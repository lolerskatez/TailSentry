#!/bin/bash
# Docker deployment script for TailSentry
# This script helps deploy TailSentry using Docker Compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
}

show_help() {
    cat << EOF
TailSentry Docker Deployment Script

USAGE:
    $0 [COMMAND]

COMMANDS:
    up          Start TailSentry containers
    down        Stop TailSentry containers
    restart     Restart TailSentry containers
    logs        Show container logs
    update      Update to latest image
    build       Build custom image
    status      Show container status
    shell       Access container shell
    help        Show this help

EXAMPLES:
    $0 up           # Start TailSentry
    $0 logs         # View logs
    $0 update       # Update to latest version
EOF
}

docker_up() {
    info "Starting TailSentry containers..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" up -d
    fi
    
    success "TailSentry started successfully"
    info "Access TailSentry at: http://localhost:8080"
}

docker_down() {
    info "Stopping TailSentry containers..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" down
    fi
    
    success "TailSentry stopped"
}

docker_restart() {
    docker_down
    docker_up
}

docker_logs() {
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f tailsentry
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" logs -f tailsentry
    fi
}

docker_update() {
    info "Updating TailSentry to latest version..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" pull
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" pull
        docker compose -f "$DOCKER_COMPOSE_FILE" up -d
    fi
    
    success "TailSentry updated successfully"
}

docker_build() {
    info "Building TailSentry image..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" build
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" build
    fi
    
    success "Image built successfully"
}

docker_status() {
    info "TailSentry container status:"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    else
        docker compose -f "$DOCKER_COMPOSE_FILE" ps
    fi
}

docker_shell() {
    info "Accessing TailSentry container shell..."
    
    local container_name
    if command -v docker-compose &> /dev/null; then
        container_name=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q tailsentry)
    else
        container_name=$(docker compose -f "$DOCKER_COMPOSE_FILE" ps -q tailsentry)
    fi
    
    if [[ -z "$container_name" ]]; then
        error "TailSentry container is not running"
        exit 1
    fi
    
    docker exec -it "$container_name" /bin/bash
}

# Main execution
case "${1:-}" in
    "up")
        check_docker
        docker_up
        ;;
    "down")
        check_docker
        docker_down
        ;;
    "restart")
        check_docker
        docker_restart
        ;;
    "logs")
        check_docker
        docker_logs
        ;;
    "update")
        check_docker
        docker_update
        ;;
    "build")
        check_docker
        docker_build
        ;;
    "status")
        check_docker
        docker_status
        ;;
    "shell")
        check_docker
        docker_shell
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    "")
        error "No command specified"
        echo ""
        show_help
        exit 1
        ;;
    *)
        error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
