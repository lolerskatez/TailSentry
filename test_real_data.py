#!/usr/bin/env python3
"""
Quick test to verify real data is flowing to the web interface
"""

import sys
import os
import requests
import json

# Add current directory to path
sys.path.append('.')

def test_api_endpoints():
    """Test that API endpoints return real data"""
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/api/status",
        "/api/peers", 
        "/api/device",
        "/api/subnet-routes"
    ]
    
    print("Testing TailSentry API endpoints for real data...\n")
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            print(f"GET {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if endpoint == "/api/status":
                    if "Self" in data:
                        hostname = data["Self"].get("HostName", "unknown")
                        print(f"  ✅ Real device: {hostname}")
                        
                        # Check if this looks like mock data
                        if hostname == "tailscale-server":
                            print("  ⚠️ This might be mock data!")
                        else:
                            print("  ✅ Appears to be real Tailscale data")
                    else:
                        print("  ❌ No 'Self' data found")
                        
                elif endpoint == "/api/peers":
                    peer_count = len(data.get("peers", {}))
                    print(f"  ✅ Found {peer_count} peers")
                    
            else:
                print(f"  ❌ Error: {response.status_code}")
                if response.status_code == 401:
                    print("  ⚠️ Authentication required - need to login first")
                
        except Exception as e:
            print(f"  ❌ Failed to connect: {e}")
            
        print()

def test_tailscale_direct():
    """Test direct Tailscale client access"""
    print("Testing direct TailscaleClient access...\n")
    
    try:
        from tailscale_client import TailscaleClient
        
        print("Getting Tailscale status directly...")
        status = TailscaleClient.status_json()
        
        if isinstance(status, dict):
            if "error" in status:
                print(f"❌ Error: {status['error']}")
            elif "Self" in status:
                hostname = status["Self"].get("HostName", "unknown")
                peer_count = len(status.get("Peer", {}))
                print(f"✅ Direct access works: {hostname} with {peer_count} peers")
                
                # Check for signs of mock data
                if hostname == "tailscale-server" and peer_count == 3:
                    print("⚠️ This looks like mock data")
                else:
                    print("✅ This appears to be real Tailscale data")
            else:
                print("❌ No 'Self' data in response")
                print(f"Keys available: {list(status.keys())}")
        else:
            print(f"❌ Invalid response type: {type(status)}")
            
    except Exception as e:
        print(f"❌ Direct access failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("TailSentry Real Data Test")
    print("=" * 60)
    
    # Test direct access first
    test_tailscale_direct()
    
    print("\n" + "=" * 60)
    
    # Test API endpoints
    test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("Test complete!")
