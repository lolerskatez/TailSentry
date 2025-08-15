#!/bin/bash
# TailSentry Quick Fix Script
# Fixes authentication issues on existing installation

set -e

echo "🔧 TailSentry Authentication Quick Fix"
echo "======================================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Not in TailSentry directory. Please run from /opt/tailsentry"
    exit 1
fi

echo "1. Setting default admin credentials..."

# Activate virtual environment
source venv/bin/activate

# Update .env with default credentials
python3 << 'EOF'
import bcrypt
import re

# Generate password hash for "admin123"
password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()

# Read .env file
with open('.env', 'r') as f:
    content = f.read()

# Update credentials and development settings
content = re.sub(r'ADMIN_USERNAME=.*', 'ADMIN_USERNAME=admin', content)
content = re.sub(r'ADMIN_PASSWORD_HASH=.*', f'ADMIN_PASSWORD_HASH={password_hash}', content)
content = re.sub(r'DEVELOPMENT=.*', 'DEVELOPMENT=true', content)

# Write back
with open('.env', 'w') as f:
    f.write(content)

print("✅ Credentials updated in .env file")
print("   Username: admin")
print("   Password: admin123")
print("✅ DEVELOPMENT=true set (enables HTTP session cookies)")
EOF

echo ""
echo "2. Stopping TailSentry service..."
sudo systemctl stop tailsentry 2>/dev/null || {
    echo "⚠️  Could not stop service with systemctl. Trying to kill process..."
    pkill -f "uvicorn.*tailsentry" || echo "No running process found"
}

echo ""
echo "3. Starting TailSentry service..."
sudo systemctl start tailsentry 2>/dev/null || {
    echo "⚠️  Could not start with systemctl. Starting manually..."
    nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 > /dev/null 2>&1 &
    echo "Started TailSentry manually"
}

echo ""
echo "4. Waiting for service to start..."
sleep 3

echo ""
echo "5. Testing authentication..."
curl -s http://localhost:8080/debug-auth | python3 -c "
import json
import sys
data = json.load(sys.stdin)
print(f'Username: {data[\"admin_username\"]}')
print(f'Password hash set: {data[\"password_hash_set\"]}')
print(f'Hash length: {data[\"password_hash_length\"]}')
if data['password_hash_set'] and data['password_hash_length'] > 0:
    print('✅ Authentication should work now!')
else:
    print('❌ Still having issues. Service may not have restarted properly.')
"

echo ""
echo "🎉 Quick Fix Complete!"
echo "======================================"
echo "Try logging in with:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "If it still doesn't work, run:"
echo "   sudo systemctl restart tailsentry"
echo "   # or reboot the server"
