#!/bin/bash

# TailSentry Exit Node Diagnostic and Enable Script

echo "=== TailSentry Exit Node Diagnosis ==="
echo ""

echo "1. Current Tailscale Status:"
echo "ExitNodeOption: $(tailscale status --json | python3 -c "import json,sys; print(json.load(sys.stdin)['Self'].get('ExitNodeOption', False))")"
echo "ExitNode: $(tailscale status --json | python3 -c "import json,sys; print(json.load(sys.stdin)['Self'].get('ExitNode', False))")"
echo "AllowedIPs: $(tailscale status --json | python3 -c "import json,sys; print(json.load(sys.stdin)['Self'].get('AllowedIPs', []))")"
echo ""

echo "2. Current TailSentry Settings:"
if [ -f "/opt/tailsentry/config/tailscale_settings.json" ]; then
    echo "advertise_exit_node: $(cat /opt/tailsentry/config/tailscale_settings.json | python3 -c "import json,sys; print(json.load(sys.stdin).get('advertise_exit_node', False))")"
else
    echo "No TailSentry settings file found"
fi
echo ""

echo "3. To enable exit node through TailSentry:"
echo "   - Go to TailSentry web interface"
echo "   - Navigate to Settings > Tailscale Settings"
echo "   - Enable 'Advertise as Exit Node'"
echo "   - Click 'Apply Settings'"
echo ""

echo "4. To enable exit node manually:"
echo "   sudo tailscale up --advertise-exit-node"
echo ""

echo "5. After enabling, the status should show:"
echo "   ExitNodeOption: True"
echo "   AllowedIPs should include: ['0.0.0.0/0', '::/0']"
