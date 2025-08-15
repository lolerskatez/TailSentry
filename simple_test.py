#!/usr/bin/env python3
"""
Simple test script to check Tailscale client functionality
Run this from the TailSentry directory with: sudo python3 simple_test.py
"""

import sys
import os
import subprocess

# Add the current directory to the path
sys.path.append('/opt/tailsentry')
sys.path.append('.')

print("🔍 TailSentry Tailscale Debug")
print("=" * 40)

# Test 1: Check if we can load dotenv
print("\n1. Testing python-dotenv...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ python-dotenv working")
    
    # Check PAT
    tailscale_pat = os.getenv("TAILSCALE_PAT", "")
    print(f"   TAILSCALE_PAT: {'✅ Set' if tailscale_pat else '❌ Not set'} ({len(tailscale_pat)} chars)")
    
except ImportError as e:
    print(f"❌ python-dotenv not available: {e}")
    print("   This might be the issue - run from venv or install dependencies")
    
    # Try to read .env manually
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
        if 'TAILSCALE_PAT=' in env_content and 'tskey-' in env_content:
            print("   Manual .env check: ✅ TAILSCALE_PAT appears to be set")
        else:
            print("   Manual .env check: ❌ TAILSCALE_PAT not found or empty")
    except Exception as e:
        print(f"   Manual .env check failed: {e}")

# Test 2: Check Tailscale CLI
print("\n2. Testing Tailscale CLI...")
try:
    result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("✅ Tailscale CLI working")
        lines = result.stdout.strip().split('\n')
        print(f"   Output lines: {len(lines)}")
        if lines:
            print(f"   First line: {lines[0][:60]}...")
    else:
        print(f"❌ Tailscale CLI error (code {result.returncode})")
        print(f"   Error: {result.stderr[:100]}...")
except subprocess.TimeoutExpired:
    print("❌ Tailscale CLI timeout")
except FileNotFoundError:
    print("❌ Tailscale CLI not found")
except Exception as e:
    print(f"❌ Tailscale CLI error: {e}")

# Test 3: Try to import TailscaleClient
print("\n3. Testing TailscaleClient import...")
try:
    from tailscale_client import TailscaleClient
    print("✅ TailscaleClient imported successfully")
    
    # Test basic functions
    try:
        device_info = TailscaleClient.get_device_info()
        print(f"✅ get_device_info() working: {type(device_info)}")
        if device_info:
            print(f"   Keys: {list(device_info.keys())[:5]}...")
    except Exception as e:
        print(f"❌ get_device_info() failed: {e}")
    
    try:
        status = TailscaleClient.status_json()
        print(f"✅ status_json() working: {type(status)}")
        if status:
            print(f"   BackendState: {status.get('BackendState', 'Not found')}")
    except Exception as e:
        print(f"❌ status_json() failed: {e}")
        
except ImportError as e:
    print(f"❌ TailscaleClient import failed: {e}")

print("\n" + "=" * 40)
print("💡 Next steps:")
print("   - If dotenv failed: run 'source venv/bin/activate' first")
print("   - If Tailscale CLI failed: check if Tailscale is running")
print("   - If TailscaleClient failed: check the actual error above")
