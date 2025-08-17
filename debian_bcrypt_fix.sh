#!/bin/bash
# Fix for bcrypt installation on Debian systems with externally managed environment restrictions
# 
# Usage: ./debian_bcrypt_fix.sh [password_file]
# If password_file is provided, reads password from the file
# If not provided, uses default "admin123"

# ANSI colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get password from file or use default
PASSWORD="admin123"  # Default password
if [ -n "$1" ] && [ -f "$1" ]; then
    PASSWORD=$(cat "$1")
    echo >&2 "Using password from provided file"
else
    echo >&2 "Using default password: admin123"
fi

echo >&2 -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo >&2 -e "${BLUE}       TailSentry Debian Python Package Fix${NC}"
echo >&2 -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo >&2 ""

# Try to install bcrypt via apt (Debian's preferred way)
echo >&2 -e "${YELLOW}Attempting to install bcrypt via apt...${NC}"
apt-get update >/dev/null 2>&1 || sudo apt-get update >/dev/null 2>&1
apt-get install -y python3-bcrypt >/dev/null 2>&1 || sudo apt-get install -y python3-bcrypt >/dev/null 2>&1
apt-get install -y python3-venv >/dev/null 2>&1 || sudo apt-get install -y python3-venv >/dev/null 2>&1

# Create a temporary virtual environment
echo >&2 -e "${GREEN}Creating virtual environment for bcrypt...${NC}"
TEMP_ENV="/tmp/bcrypt_env_$$"
python3 -m venv $TEMP_ENV
source $TEMP_ENV/bin/activate

# Install bcrypt in the virtual environment
echo >&2 -e "${YELLOW}Installing bcrypt in virtual environment...${NC}"
pip install bcrypt >/dev/null 2>&1

# Generate the password hash
echo >&2 -e "${GREEN}Generating password hash...${NC}"
HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw('${PASSWORD}'.encode(), bcrypt.gensalt()).decode())")

# Output the hash to stdout (will be captured by the calling script)
echo "$HASH"

# Clean up
echo >&2 "Cleaning up..."
deactivate
rm -rf $TEMP_ENV

echo >&2 -e "${GREEN}bcrypt hash generation completed successfully!${NC}"

# Run the script
cd "$INSTALL_DIR"
python3 "$INSTALL_DIR/create_password.py"

# Clean up
rm "$INSTALL_DIR/create_password.py"

echo -e "\n${GREEN}Fix complete!${NC}"
echo "You can now continue with the setup process."
echo ""
echo "If you are prompted for a Tailscale PAT, you can:"
echo "1. Enter it to enable full Tailscale management functionality"
echo "2. Press Enter to skip and configure it later in the dashboard"
echo ""
echo "Default login credentials: admin / admin123"
