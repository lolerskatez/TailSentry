#!/bin/bash
# TailSentry Diagnostic Script for Debian
# This script helps diagnose issues with real Tailscale data

echo "=== TailSentry Diagnostic Tool ==="
echo ""

# Check for Tailscale binary
echo "1. Checking Tailscale binary location..."
TAILSCALE_PATH=$(which tailscale)
if [ -n "$TAILSCALE_PATH" ]; then
    echo "   Found at: $TAILSCALE_PATH"
    echo "   Is executable: $([ -x "$TAILSCALE_PATH" ] && echo "Yes" || echo "No")"
else
    echo "   Not found in PATH"
    # Check common locations
    for path in /usr/bin/tailscale /usr/sbin/tailscale /usr/local/bin/tailscale; do
        if [ -f "$path" ]; then
            echo "   Found at: $path"
            echo "   Is executable: $([ -x "$path" ] && echo "Yes" || echo "No")"
            TAILSCALE_PATH=$path
            break
        fi
    done
fi

if [ -z "$TAILSCALE_PATH" ]; then
    echo "ERROR: Tailscale binary not found. Please install Tailscale first."
    exit 1
fi

# Check Tailscale status
echo ""
echo "2. Raw Tailscale status output:"
echo "-------------------------------"
$TAILSCALE_PATH status
echo "-------------------------------"

# Check JSON output
echo ""
echo "3. Raw JSON status output (shortened):"
echo "-------------------------------"
$TAILSCALE_PATH status --json | head -n 20
echo "... (output truncated)"
echo "-------------------------------"

# Check current IP
echo ""
echo "4. Tailscale IP address:"
$TAILSCALE_PATH ip
echo ""

# Check if TailSentry can access this data
echo "5. Testing TailSentry access:"
echo "-------------------------------"
# Create a simple Python script for testing
cat > tailscale_test.py << EOF
import subprocess
import json
import sys

def get_tailscale_path():
    return "$TAILSCALE_PATH"

def check_output():
    try:
        cmd = ["$TAILSCALE_PATH", "status", "--json"]
        print(f"Running command: {' '.join(cmd)}")
        output = subprocess.check_output(cmd, stderr=subprocess.PIPE, timeout=10)
        data = json.loads(output.decode('utf-8'))
        print("Command successful!")
        
        # Print key data points
        if "Self" in data:
            print(f"Device name: {data['Self'].get('HostName', 'N/A')}")
            print(f"Tailscale IP: {data['Self'].get('TailscaleIPs', ['N/A'])[0]}")
            print(f"Peers: {len(data.get('Peer', {}))}")
        else:
            print("No 'Self' data found!")
            
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = check_output()
    sys.exit(0 if success else 1)
EOF

python3 tailscale_test.py
echo "-------------------------------"

# Check permissions
echo ""
echo "6. Checking permissions:"
ls -la "$TAILSCALE_PATH"
echo ""

# Cleanup
rm -f tailscale_test.py

echo "=== Diagnostic Complete ==="
echo ""
echo "If your test script successfully showed real Tailscale data but TailSentry doesn't,"
echo "there may be an issue with how TailSentry processes the data or permissions when run as a service."
