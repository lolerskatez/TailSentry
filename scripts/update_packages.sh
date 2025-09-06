#!/bin/bash
# Cross-platform package update script for Linux
# Run with: ./update_packages.sh

set -e

echo "🔄 Updating critical security packages on Linux..."

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not detected. Activating..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ No virtual environment found. Creating one..."
        python3 -m venv venv
        source venv/bin/activate
        echo "✅ Virtual environment created and activated"
    fi
fi

# Update pip first
echo "📦 Updating pip..."
python -m pip install --upgrade pip

# Update Discord.py first (most critical for bot)
echo "🤖 Updating Discord.py..."
pip install --upgrade discord.py==2.6.3

# Update cryptography (security library)
echo "🔐 Updating cryptography..."
pip install --upgrade cryptography==45.0.7

# Update web framework
echo "🌐 Updating FastAPI..."
pip install --upgrade fastapi==0.116.1

# Update other security-related packages
echo "🔧 Updating other security packages..."
pip install --upgrade certifi requests urllib3 uvicorn

# Install additional security tools for Linux
echo "🛡️ Installing Linux security tools..."
pip install safety pip-audit

# Run security scan
echo "🔍 Running security vulnerability scan..."
if command -v safety &> /dev/null; then
    echo "Running Safety scan..."
    pip freeze | safety check --stdin || echo "⚠️ Safety scan found issues (see above)"
fi

if command -v pip-audit &> /dev/null; then
    echo "Running pip-audit scan..."
    pip-audit || echo "⚠️ pip-audit found issues (see above)"
fi

# Check for breaking changes
echo "⚠️  IMPORTANT: Test all functionality after updates!"
echo "   - Test Discord bot commands"
echo "   - Test web dashboard"
echo "   - Check for deprecation warnings"

# Regenerate requirements file
echo "📝 Regenerating requirements-frozen.txt..."
pip freeze > requirements-frozen.txt

# Set secure permissions on requirements file
chmod 644 requirements-frozen.txt

echo "✅ Package updates complete!"

# Check Python version compatibility
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
echo "🐍 Python version: $PYTHON_VERSION"

if python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "✅ Python version is compatible"
else
    echo "⚠️  Python 3.8+ recommended for best security support"
fi
