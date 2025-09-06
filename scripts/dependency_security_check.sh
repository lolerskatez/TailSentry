#!/bin/bash
# Cross-platform dependency security check for Linux/macOS
# Run with: chmod +x dependency_security_check.sh && ./dependency_security_check.sh

set -e

echo "🔍 TailSentry Dependency Security Check (Linux/macOS)"
echo "===================================================="

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not detected"
    if [ -f "venv/bin/activate" ]; then
        echo "🔄 Activating virtual environment..."
        source venv/bin/activate
    else
        echo "❌ No virtual environment found. Please create one first:"
        echo "   python3 -m venv venv && source venv/bin/activate"
        exit 1
    fi
fi

# Install/update security tools
echo "🛠️  Installing security scanning tools..."
pip install --upgrade safety pip-audit || echo "⚠️ Could not install all security tools"

echo "🔍 Scanning for known vulnerabilities in Python packages..."

# Check for known vulnerabilities using safety
if command -v safety &> /dev/null; then
    echo "📋 Running Safety vulnerability scan..."
    pip freeze | safety check --stdin || echo "⚠️ Safety scan found vulnerabilities (see above)"
else
    echo "⚠️ Safety not available, skipping vulnerability scan"
fi

# Additional scan with pip-audit if available
if command -v pip-audit &> /dev/null; then
    echo "📋 Running pip-audit scan..."
    pip-audit || echo "⚠️ pip-audit found vulnerabilities (see above)"
else
    echo "⚠️ pip-audit not available, install with: pip install pip-audit"
fi

# Check for outdated packages
echo "📦 Checking for outdated packages..."
pip list --outdated --format=columns

# Audit Discord.py specifically (most critical dependency)
echo "🤖 Discord.py security information:"
pip show discord.py | grep -E "(Version|Author|Summary)" || echo "Discord.py not installed"

# Check requirements files for version pinning
echo "📌 Checking version pinning in requirements files..."
requirements_files=("requirements.txt" "requirements-frozen.txt" "requirements-dev.txt")

for file in "${requirements_files[@]}"; do
    if [ -f "$file" ]; then
        echo "Checking $file:"
        unpinned=$(grep -E "^[^#]*[^=<>~!]$" "$file" | head -5 || true)
        if [ -n "$unpinned" ]; then
            echo "⚠️  Unpinned dependencies found:"
            echo "$unpinned"
        else
            echo "✅ All dependencies properly pinned"
        fi
    else
        echo "⚠️  $file not found"
    fi
done

# Check for development dependencies in production
echo "🔍 Checking for development dependencies..."
dev_packages=$(pip list | grep -i -E "(test|dev|debug|mock|pytest|coverage)" || true)
if [ -n "$dev_packages" ]; then
    echo "⚠️  Development packages detected:"
    echo "$dev_packages"
else
    echo "✅ No obvious development packages found"
fi

# Check Python version
python_version=$(python --version 2>&1)
echo "🐍 Python version: $python_version"

# Check for known vulnerable Python versions
if python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo "✅ Python version is supported"
else
    echo "⚠️  Python 3.8+ recommended for security support"
fi

# Check for insecure package sources
echo "🔗 Checking pip configuration..."
pip_conf_locations=(
    "$HOME/.pip/pip.conf"
    "$HOME/.config/pip/pip.conf"
    "/etc/pip.conf"
)

insecure_found=false
for conf_file in "${pip_conf_locations[@]}"; do
    if [ -f "$conf_file" ]; then
        if grep -i "trusted-host" "$conf_file" 2>/dev/null; then
            echo "⚠️  Insecure trusted-host found in $conf_file"
            insecure_found=true
        fi
        if grep -i "http://" "$conf_file" 2>/dev/null; then
            echo "⚠️  HTTP (insecure) sources found in $conf_file"
            insecure_found=true
        fi
    fi
done

if [ "$insecure_found" = false ]; then
    echo "✅ No insecure pip configuration found"
fi

echo "✅ Dependency security scan complete!"
echo ""
echo "💡 Recommendations:"
echo "   - Run this scan weekly: ./scripts/dependency_security_check.sh"
echo "   - Update packages regularly: ./scripts/update_packages.sh"
echo "   - Consider using 'pip-tools' for dependency management"
echo "   - Monitor security advisories for your dependencies"
echo "   - Use 'requirements-frozen.txt' for production deployments"
