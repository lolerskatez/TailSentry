#!/usr/bin/env python3
"""
Get the full error response from API endpoints
"""

import requests
import sys

base_url = "http://localhost:8080"
session = requests.Session()

print("🔍 Getting Full Error Details")
print("=" * 40)

# Login first
login_data = {"username": "admin", "password": "admin123"}
login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)

if login_response.status_code != 302:
    print(f"❌ Login failed: {login_response.status_code}")
    sys.exit(1)

print("✅ Login successful")

# Test config API and get full response
print("\n📍 Testing /api/config...")
config_response = session.get(f"{base_url}/api/config")
print(f"Status: {config_response.status_code}")
print(f"Headers: {dict(config_response.headers)}")
print(f"Content-Type: {config_response.headers.get('content-type', 'unknown')}")
print("\n📄 Full Response:")
print("-" * 60)
print(config_response.text)
print("-" * 60)

# Test traffic API
print("\n📍 Testing /api/traffic...")
traffic_response = session.get(f"{base_url}/api/traffic")
print(f"Status: {traffic_response.status_code}")
print("\n📄 First 500 chars of response:")
print("-" * 60)
print(traffic_response.text[:500])
print("-" * 60)
