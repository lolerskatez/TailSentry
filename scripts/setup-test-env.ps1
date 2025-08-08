# setup-test-env.ps1 - Setup testing environment for Windows
param(
    [switch]$Force,
    [switch]$SystemWide,
    [switch]$Help
)

if ($Help) {
    Write-Host "TailSentry Test Environment Setup (Windows)"
    Write-Host "Usage: .\scripts\setup-test-env.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Force      Force recreate virtual environment"
    Write-Host "  -SystemWide Try system-wide installation first"
    Write-Host "  -Help       Show this help"
    exit 0
}

# Helper functions
function Write-Success {
    param($Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param($Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Warning-Custom {
    param($Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Info {
    param($Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Blue
}

Write-Host "🛠️  TailSentry Test Environment Setup (Windows)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Check Python
Write-Info "Checking Python environment..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python found: $pythonVersion"
}
catch {
    Write-Error-Custom "Python is required but not found. Please install Python 3.9+ from python.org"
    exit 1
}

# Check pip
try {
    $pipVersion = pip --version 2>&1
    Write-Success "pip found: $($pipVersion.Split(' ')[1])"
}
catch {
    Write-Error-Custom "pip is required but not found"
    exit 1
}

# Function to test if we can install packages
function Test-PackageInstallation {
    try {
        $testResult = pip install --dry-run requests 2>&1
        return $true
    }
    catch {
        return $false
    }
}

# Setup virtual environment
function Setup-VirtualEnvironment {
    Write-Info "Setting up virtual environment..."
    
    if ((Test-Path "venv") -and !$Force) {
        Write-Info "Virtual environment already exists (use -Force to recreate)"
    }
    else {
        if (Test-Path "venv") {
            Write-Info "Removing existing virtual environment..."
            Remove-Item -Recurse -Force "venv"
        }
        
        Write-Info "Creating virtual environment..."
        python -m venv venv
        Write-Success "Virtual environment created"
    }
    
    # Activate virtual environment
    Write-Info "Activating virtual environment..."
    & "venv\Scripts\Activate.ps1"
    Write-Success "Virtual environment activated"
    
    # Upgrade pip
    Write-Info "Upgrading pip..."
    python -m pip install --upgrade pip | Out-Null
    Write-Success "pip upgraded"
}

# Install dependencies
function Install-Dependencies {
    Write-Info "Installing dependencies..."
    
    # Install main requirements
    if (Test-Path "requirements.txt") {
        Write-Info "Installing main dependencies..."
        try {
            pip install -r requirements.txt
            Write-Success "Main dependencies installed"
        }
        catch {
            Write-Error-Custom "Failed to install main dependencies"
            return $false
        }
    }
    else {
        Write-Warning-Custom "requirements.txt not found"
    }
    
    # Install test requirements
    if (Test-Path "test-requirements.txt") {
        Write-Info "Installing test dependencies..."
        try {
            pip install -r test-requirements.txt
            Write-Success "Test dependencies installed"
        }
        catch {
            Write-Warning-Custom "Some test dependencies failed to install"
        }
    }
    else {
        Write-Info "Installing minimal test dependencies..."
        try {
            pip install requests psutil
            Write-Success "Minimal test dependencies installed"
        }
        catch {
            Write-Warning-Custom "Failed to install test dependencies"
        }
    }
    
    return $true
}

# Verify installation
function Test-Installation {
    Write-Info "Verifying installation..."
    
    # Test core imports
    try {
        python -c "import fastapi, uvicorn, jinja2" 2>$null
        Write-Success "Core TailSentry dependencies available"
    }
    catch {
        Write-Error-Custom "Core dependencies missing"
        return $false
    }
    
    # Test optional imports
    try {
        python -c "import requests" 2>$null
        Write-Success "Testing dependencies available"
    }
    catch {
        Write-Warning-Custom "Some testing dependencies missing"
    }
    
    # Test TailSentry import
    try {
        python -c "import sys; sys.path.insert(0, '.'); import main" 2>$null
        Write-Success "TailSentry imports successfully"
    }
    catch {
        Write-Warning-Custom "TailSentry import issues (may be normal)"
    }
    
    return $true
}

# Create activation script
function New-ActivationScript {
    Write-Info "Creating activation script..."
    
    $activationScript = @"
# activate-test-env.ps1 - Activate TailSentry testing environment
if (Test-Path "venv") {
    & "venv\Scripts\Activate.ps1"
    Write-Host "✅ TailSentry test environment activated" -ForegroundColor Green
    Write-Host "Python: `$(python --version)"
    Write-Host "Location: `$(Get-Command python | Select-Object -ExpandProperty Source)"
    Write-Host ""
    Write-Host "To run tests:"
    Write-Host "  .\scripts\run-all-tests.ps1"
    Write-Host "  python scripts\performance_tester.py"
    Write-Host ""
    Write-Host "To start TailSentry:"
    Write-Host "  python main.py"
    Write-Host ""
    Write-Host "To deactivate: deactivate"
}
else {
    Write-Host "❌ Virtual environment not found. Run .\scripts\setup-test-env.ps1 first" -ForegroundColor Red
}
"@
    
    $activationScript | Out-File -FilePath "activate-test-env.ps1" -Encoding UTF8
    Write-Success "Created activate-test-env.ps1"
}

# Main execution
Write-Host ""
Write-Info "Starting test environment setup..."

# Check if we should try system-wide first
if ($SystemWide) {
    Write-Info "Testing system-wide package installation..."
    if (Test-PackageInstallation) {
        Write-Info "System-wide installation possible"
        $response = Read-Host "Install directly to system? (not recommended) [y/N]"
        if ($response -eq 'y' -or $response -eq 'Y') {
            if (Install-Dependencies) {
                if (Test-Installation) {
                    Write-Success "Setup complete! You can now run tests directly."
                    exit 0
                }
            }
            Write-Error-Custom "System-wide installation failed, falling back to virtual environment"
        }
    }
}

# Use virtual environment
Write-Info "Using virtual environment approach..."
Setup-VirtualEnvironment

if (Install-Dependencies) {
    if (Test-Installation) {
        New-ActivationScript
        
        Write-Host ""
        Write-Success "Test environment setup complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📋 Next steps:" -ForegroundColor Cyan
        Write-Host "1. Activate environment: .\activate-test-env.ps1"
        Write-Host "2. Run tests: .\scripts\run-all-tests.ps1"
        Write-Host "3. Or run individual tests as needed"
        Write-Host ""
        Write-Host "🧪 Available test commands:" -ForegroundColor Cyan
        Write-Host "   .\scripts\run-all-tests.ps1           - Complete test suite"
        Write-Host "   python scripts\performance_tester.py  - Performance analysis"
        Write-Host "   python main.py                        - Start TailSentry"
        
        exit 0
    }
}

Write-Error-Custom "Setup failed. Please check the error messages above."
exit 1
