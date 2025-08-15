#!/usr/bin/env python3
"""
Test the API functions directly without going through FastAPI
"""

import sys
import os
sys.path.append('/opt/tailsentry')
sys.path.append('.')

from dotenv import load_dotenv
load_dotenv()

print("🔍 Testing API Functions Directly")
print("=" * 40)

# Test 1: Import the API modules
try:
    from routes.config import get_config, get_traffic_stats
    print("✅ Successfully imported API functions")
except ImportError as e:
    print(f"❌ Failed to import API functions: {e}")
    sys.exit(1)

# Test 2: Create a mock request object
class MockRequest:
    def __init__(self):
        self.session = {"user": "admin", "expires_at": "2025-08-15T10:00:00"}

mock_request = MockRequest()

# Test 3: Test get_config function directly
print("\n📍 Testing get_config function...")
try:
    import asyncio
    result = asyncio.run(get_config(mock_request))
    print(f"✅ get_config() successful: {type(result)}")
    if isinstance(result, dict):
        print(f"   Keys: {list(result.keys())}")
    else:
        print(f"   Result: {result}")
except Exception as e:
    print(f"❌ get_config() failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

# Test 4: Test get_traffic_stats function directly
print("\n📍 Testing get_traffic_stats function...")
try:
    result = asyncio.run(get_traffic_stats(mock_request))
    print(f"✅ get_traffic_stats() successful: {type(result)}")
    if isinstance(result, dict):
        print(f"   Keys: {list(result.keys())}")
    else:
        print(f"   Result: {result}")
except Exception as e:
    print(f"❌ get_traffic_stats() failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 40)
print("💡 This test bypasses FastAPI and authentication")
print("   to check if the core functions work properly.")
