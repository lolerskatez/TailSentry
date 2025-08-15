#!/usr/bin/env python3
"""
Test script to check Tailscale client functionality
Run this on your test system to debug the API issues
"""

import sys
import os

# Add the current directory to the path so we can import TailSentry modules
sys.path.append('/opt/tailsentry')
sys.path.append('.')

try:
    from tailscale_client import TailscaleClient
    print("✅ Successfully imported TailscaleClient")
except ImportError as e:
    print(f"❌ Failed to import TailscaleClient: {e}")
    exit(1)

print("\n🔍 Testing Tailscale Client Functions")
print("=" * 50)

# Test 1: Check if Tailscale is running
print("\n1. Testing Tailscale connectivity...")
try:
    device_info = TailscaleClient.get_device_info()
    print(f"✅ get_device_info() successful")
    print(f"   Device info keys: {list(device_info.keys()) if device_info else 'None'}")
except Exception as e:
    print(f"❌ get_device_info() failed: {e}")
    print(f"   Error type: {type(e).__name__}")

# Test 2: Check status
print("\n2. Testing Tailscale status...")
try:
    status = TailscaleClient.status_json()
    print(f"✅ status_json() successful")
    print(f"   Status keys: {list(status.keys()) if status else 'None'}")
    if status:
        print(f"   BackendState: {status.get('BackendState', 'Not found')}")
        print(f"   CurrentTailnet: {status.get('CurrentTailnet', 'Not found')}")
except Exception as e:
    print(f"❌ status_json() failed: {e}")
    print(f"   Error type: {type(e).__name__}")

# Test 3: Check environment variables
print("\n3. Checking environment variables...")
from dotenv import load_dotenv
load_dotenv()

tailscale_pat = os.getenv("TAILSCALE_PAT", "")
print(f"TAILSCALE_PAT: {'✅ Set' if tailscale_pat else '❌ Not set'} ({len(tailscale_pat)} chars)")

# Test 4: Check if tailscale CLI is available
print("\n4. Testing Tailscale CLI...")
import subprocess
try:
    result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("✅ Tailscale CLI working")
        print(f"   Status output preview: {result.stdout[:100]}...")
    else:
        print(f"❌ Tailscale CLI error (code {result.returncode})")
        print(f"   Error: {result.stderr}")
except subprocess.TimeoutExpired:
    print("❌ Tailscale CLI timeout")
except FileNotFoundError:
    print("❌ Tailscale CLI not found in PATH")
except Exception as e:
    print(f"❌ Tailscale CLI error: {e}")

print("\n" + "=" * 50)
print("💡 Common issues:")
print("   - Missing TAILSCALE_PAT in .env file")
print("   - Tailscale not running or not authenticated")
print("   - Network connectivity issues")
print("   - Permissions issues with Tailscale CLI")
