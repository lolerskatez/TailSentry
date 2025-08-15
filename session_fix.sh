#!/bin/bash
# TailSentry Session Fix Script
# Fixes HTTPS-only session cookies for HTTP access

echo "🔧 TailSentry Session Cookie Fix"
echo "================================="

cd /opt/tailsentry
source venv/bin/activate

echo "Setting DEVELOPMENT=true to allow HTTP session cookies..."

python3 << 'EOF'
import re

# Read .env file
with open('.env', 'r') as f:
    content = f.read()

# Update DEVELOPMENT setting
content = re.sub(r'DEVELOPMENT=.*', 'DEVELOPMENT=true', content)

# Write back
with open('.env', 'w') as f:
    f.write(content)

print("✅ DEVELOPMENT=true set in .env")
print("This allows session cookies over HTTP for local network access")
EOF

echo ""
echo "Restarting TailSentry service..."
sudo systemctl restart tailsentry 2>/dev/null || {
    echo "Killing and restarting manually..."
    pkill -f "uvicorn.*tailsentry"
    sleep 2
    nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 > /dev/null 2>&1 &
}

echo ""
echo "Waiting for service to restart..."
sleep 5

echo ""
echo "✅ Session cookie fix complete!"
echo "Try logging in again with:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "The login should now redirect you to the dashboard!"
