#!/usr/bin/env python3
"""
Test API endpoints directly with authentication
"""

import requests
import sys

# Test the API endpoints
base_url = "http://localhost:8080"

print("🔍 Testing TailSentry API Endpoints")
print("=" * 40)

# Create a session
session = requests.Session()

print("\n1. Testing login...")
try:
    # First, login to get a session
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"Login response: {login_response.status_code}")
    
    if login_response.status_code == 302:
        print("✅ Login successful (redirect to dashboard)")
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text[:200]}")
        
except Exception as e:
    print(f"❌ Login error: {e}")
    sys.exit(1)

print("\n2. Testing /api/config...")
try:
    config_response = session.get(f"{base_url}/api/config")
    print(f"Config API response: {config_response.status_code}")
    
    if config_response.status_code == 200:
        print("✅ Config API working")
        data = config_response.json()
        print(f"Config keys: {list(data.keys())}")
    else:
        print(f"❌ Config API failed: {config_response.status_code}")
        print(f"Response: {config_response.text[:200]}")
        
except Exception as e:
    print(f"❌ Config API error: {e}")

print("\n3. Testing /api/traffic...")
try:
    traffic_response = session.get(f"{base_url}/api/traffic")
    print(f"Traffic API response: {traffic_response.status_code}")
    
    if traffic_response.status_code == 200:
        print("✅ Traffic API working")
        data = traffic_response.json()
        print(f"Traffic keys: {list(data.keys())}")
    else:
        print(f"❌ Traffic API failed: {traffic_response.status_code}")
        print(f"Response: {traffic_response.text[:200]}")
        
except Exception as e:
    print(f"❌ Traffic API error: {e}")

print("\n" + "=" * 40)
print("💡 If APIs are failing, check:")
print("   - Authentication session handling")
print("   - TailscaleClient errors")
print("   - Environment variable loading")
