#!/bin/bash
# setup-test-env.sh - Setup testing environment with proper virtual environment handling
set -e

echo "🛠️  TailSentry Test Environment Setup"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if we're in a virtual environment or externally managed
check_python_environment() {
    log_info "Checking Python environment..."
    
    # Check Python version
    PYTHON_VERSION=$(python3 --version 2>&1)
    log_success "Python found: $PYTHON_VERSION"
    
    # Try to import pip
    if python3 -c "import pip" 2>/dev/null; then
        log_success "pip is available"
    else
        log_error "pip is not available"
        return 1
    fi
    
    # Check if we can install packages
    if python3 -c "import tempfile, subprocess, sys; subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--dry-run', 'requests'])" >/dev/null 2>&1; then
        log_success "Can install packages directly"
        return 0
    else
        log_warning "Cannot install packages directly (externally managed environment)"
        return 1
    fi
}

# Setup virtual environment
setup_virtual_environment() {
    log_info "Setting up virtual environment..."
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    log_success "Virtual environment activated"
    
    # Upgrade pip
    pip install --upgrade pip > /dev/null 2>&1
    log_success "pip upgraded"
    
    return 0
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    # Install main requirements
    if [ -f "requirements.txt" ]; then
        if pip install -r requirements.txt; then
            log_success "Main dependencies installed"
        else
            log_error "Failed to install main dependencies"
            return 1
        fi
    else
        log_warning "requirements.txt not found"
    fi
    
    # Install test requirements
    if [ -f "test-requirements.txt" ]; then
        if pip install -r test-requirements.txt; then
            log_success "Test dependencies installed"
        else
            log_warning "Some test dependencies failed to install"
        fi
    else
        log_info "test-requirements.txt not found, creating minimal test setup..."
        pip install requests psutil
    fi
    
    return 0
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    # Test core imports
    if python -c "import fastapi, uvicorn, jinja2" 2>/dev/null; then
        log_success "Core TailSentry dependencies available"
    else
        log_error "Core dependencies missing"
        return 1
    fi
    
    # Test optional imports
    if python -c "import requests, psutil" 2>/dev/null; then
        log_success "Testing dependencies available"
    else
        log_warning "Some testing dependencies missing"
    fi
    
    # Test TailSentry import
    if python -c "import sys; sys.path.insert(0, '.'); import main" 2>/dev/null; then
        log_success "TailSentry imports successfully"
    else
        log_warning "TailSentry import issues (may be normal if dependencies missing)"
    fi
    
    return 0
}

# Create activation script
create_activation_script() {
    log_info "Creating activation script..."
    
    cat > activate-test-env.sh << 'EOF'
#!/bin/bash
# Activate TailSentry testing environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ TailSentry test environment activated"
    echo "Python: $(python --version)"
    echo "Location: $(which python)"
    echo ""
    echo "To run tests:"
    echo "  ./scripts/run-all-tests.sh"
    echo "  ./scripts/test-deployment.sh"
    echo "  python scripts/performance_tester.py"
    echo ""
    echo "To start TailSentry:"
    echo "  python main.py"
    echo ""
    echo "To deactivate: deactivate"
else
    echo "❌ Virtual environment not found. Run ./scripts/setup-test-env.sh first"
fi
EOF
    
    chmod +x activate-test-env.sh
    log_success "Created activate-test-env.sh"
}

# Main execution
main() {
    echo
    log_info "Starting test environment setup..."
    
    # Check current environment
    if check_python_environment; then
        log_info "Direct package installation possible"
        
        # Ask user preference
        echo
        echo "You can either:"
        echo "1. Install directly to system (not recommended on modern Linux)"
        echo "2. Use virtual environment (recommended)"
        echo
        read -p "Use virtual environment? [Y/n]: " use_venv
        use_venv=${use_venv:-Y}
        
        if [[ $use_venv =~ ^[Nn]$ ]]; then
            log_info "Installing directly to system..."
            if install_dependencies; then
                verify_installation
                log_success "Setup complete! You can now run tests directly."
            else
                log_error "Direct installation failed"
                return 1
            fi
        else
            setup_virtual_environment
            install_dependencies
            verify_installation
            create_activation_script
        fi
    else
        log_info "Externally managed environment detected, using virtual environment..."
        setup_virtual_environment
        install_dependencies
        verify_installation
        create_activation_script
    fi
    
    echo
    log_success "Test environment setup complete!"
    echo
    echo "📋 Next steps:"
    if [ -f "activate-test-env.sh" ]; then
        echo "1. Activate environment: source activate-test-env.sh"
        echo "2. Run tests: ./scripts/run-all-tests.sh"
        echo "3. Or run individual tests as needed"
    else
        echo "1. Run tests: ./scripts/run-all-tests.sh"
        echo "2. Or run individual tests as needed"
    fi
    echo
    echo "🧪 Available test commands:"
    echo "   ./scripts/test-deployment.sh       - Basic deployment validation"
    echo "   ./scripts/test-security.sh         - Security testing"
    echo "   ./scripts/test-integration-stress.sh - Integration stress testing"
    echo "   python scripts/performance_tester.py - Performance analysis"
    echo "   ./scripts/run-all-tests.sh         - Complete test suite"
}

main "$@"
