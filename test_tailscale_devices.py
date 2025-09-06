#!/usr/bin/env python3
"""
Test script to check what TailscaleClient.get_all_devices() returns
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_tailscale_devices():
    """Test the TailscaleClient device retrieval"""
    print("🔍 Testing TailscaleClient.get_all_devices()...")
    
    try:
        from services.tailscale_service import TailscaleClient
        print("✅ Successfully imported TailscaleClient")
        
        # Get devices
        devices = TailscaleClient.get_all_devices()
        print(f"📱 Found {len(devices) if devices else 0} devices")
        
        if devices:
            print("\n📋 Device list:")
            for i, device in enumerate(devices, 1):
                print(f"  {i}. {device}")
                print(f"     Name: {device.get('name', 'Unknown')}")
                print(f"     Online: {device.get('online', 'Unknown')}")
                print(f"     OS: {device.get('os', 'Unknown')}")
                print(f"     IP: {device.get('addresses', ['Unknown'])[0] if device.get('addresses') else 'Unknown'}")
                print()
        else:
            print("❌ No devices found or empty response")
            
    except ImportError as e:
        print(f"❌ Failed to import TailscaleClient: {e}")
    except Exception as e:
        print(f"❌ Error getting devices: {e}")
        import traceback
        traceback.print_exc()

def test_tailscale_command():
    """Test direct tailscale status command"""
    print("\n🔍 Testing direct 'tailscale status' command...")
    
    try:
        import subprocess
        result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Tailscale status command successful")
            print(f"📋 Raw output:\n{result.stdout}")
        else:
            print(f"❌ Tailscale status failed: {result.stderr}")
            
    except FileNotFoundError:
        print("❌ 'tailscale' command not found in PATH")
    except Exception as e:
        print(f"❌ Error running tailscale status: {e}")

if __name__ == "__main__":
    print("🧪 TailSentry Tailscale Device Test")
    print("=" * 50)
    
    test_tailscale_devices()
    test_tailscale_command()
    
    print("\n✅ Test complete!")
