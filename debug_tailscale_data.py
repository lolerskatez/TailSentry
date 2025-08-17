#!/usr/bin/env python3
"""
Debug script to check what's happening with Tailscale client data
"""

import os
import sys
import json
import logging
from pathlib import Path
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("tailsentry.debug")

# Make imports from parent directory work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("\n=== TailSentry Tailscale Data Debugger ===\n")
    
    print("1. Importing TailscaleClient...")
    from tailscale_client import TailscaleClient
    print("   ✅ Import successful")
    
    print("2. Getting Tailscale path...")
    tailscale_path = TailscaleClient.get_tailscale_path()
    print(f"   ✅ Found at: {tailscale_path}")
    
    print("3. Testing direct Tailscale command...")
    try:
        cmd = [tailscale_path, "status", "--json"]
        print(f"   Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, check=True)
        direct_output = result.stdout.decode('utf-8')
        direct_data = json.loads(direct_output)
        if "Self" in direct_data:
            direct_hostname = direct_data.get("Self", {}).get("HostName", "unknown")
            direct_ip = direct_data.get("Self", {}).get("TailscaleIPs", ["none"])[0]
            print(f"   ✅ Direct command worked: {direct_hostname} ({direct_ip})")
        else:
            print("   ❌ 'Self' data not found in direct output")
            
        # Save direct output for comparison
        with open("tailscale_direct_output.json", "w") as f:
            json.dump(direct_data, f, indent=2)
        print("   📝 Direct output saved to tailscale_direct_output.json")
    except Exception as e:
        print(f"   ❌ Direct command failed: {str(e)}")
    
    print("4. Getting status via TailscaleClient...")
    status = TailscaleClient.status_json()
    
    # Check for errors
    if isinstance(status, dict) and "error" in status:
        print(f"   ❌ Error in status: {status['error']}")
    
    # Check for expected data
    if isinstance(status, dict) and "Self" in status:
        hostname = status.get("Self", {}).get("HostName", "unknown")
        ip = status.get("Self", {}).get("TailscaleIPs", ["none"])[0]
        peers = len(status.get("Peer", {}))
        print(f"   ✅ Client data looks good: {hostname} ({ip}) with {peers} peers")
        
        # Compare with direct output
        if 'direct_hostname' in locals() and direct_hostname != hostname:
            print(f"   ⚠️ Hostname mismatch: direct={direct_hostname}, client={hostname}")
        if 'direct_ip' in locals() and direct_ip != ip:
            print(f"   ⚠️ IP mismatch: direct={direct_ip}, client={ip}")
    else:
        print("   ❌ 'Self' data not found in client output")
    
    # Save client output for comparison
    with open("tailscale_client_output.json", "w") as f:
        json.dump(status, f, indent=2)
    print("   📝 Client output saved to tailscale_client_output.json")
    
    print("\n5. Testing peer data...")
    if isinstance(status, dict) and "Peer" in status:
        peers = status.get("Peer", {})
        print(f"   Found {len(peers)} peers:")
        for peer_id, peer in peers.items():
            if isinstance(peer, dict):
                hostname = peer.get("HostName", "Unknown")
                ip = peer.get("TailscaleIPs", ["unknown"])[0] if peer.get("TailscaleIPs") else "unknown"
                print(f"   - {hostname}: {ip}")
    else:
        print("   ❌ No peer data found")
    
    print("\n=== Debug Complete ===")
    print("Check the saved JSON files to compare direct vs. client data")
    
except Exception as e:
    logger.exception("Unexpected error during debugging")
    print(f"\n❌ ERROR: {str(e)}")
    sys.exit(1)
