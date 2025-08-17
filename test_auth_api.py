#!/usr/bin/env python3
"""
Test TailSentry with proper authentication
"""

import requests
import json

def test_with_login():
    """Test TailSentry API with proper login"""
    base_url = "http://localhost:8080"
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("🔐 Testing TailSentry with authentication...")
    
    # Step 1: Get login page (to get any CSRF tokens if needed)
    try:
        login_page = session.get(f"{base_url}/login")
        print(f"✅ Login page accessible: {login_page.status_code}")
    except Exception as e:
        print(f"❌ Cannot access login page: {e}")
        return
    
    # Step 2: Attempt login (you'll need to provide credentials)
    login_data = {
        "username": "admin",  # Replace with your username
        "password": "admin"   # Replace with your password
    }
    
    try:
        login_response = session.post(f"{base_url}/login", data=login_data)
        print(f"🔐 Login attempt: {login_response.status_code}")
        
        if login_response.status_code == 200 and "dashboard" in login_response.text.lower():
            print("✅ Login successful!")
        elif login_response.status_code == 302:
            print("✅ Login successful (redirected)!")
        else:
            print(f"❌ Login may have failed: {login_response.status_code}")
            
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return
    
    # Step 3: Test API endpoints with session
    endpoints = ["/api/status", "/api/peers", "/api/device"]
    
    for endpoint in endpoints:
        try:
            response = session.get(f"{base_url}{endpoint}")
            print(f"\n📡 {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if endpoint == "/api/status" and "Self" in data:
                    hostname = data["Self"].get("HostName", "unknown")
                    peer_count = len(data.get("Peer", {}))
                    print(f"  ✅ Real device: {hostname} with {peer_count} peers")
                    
                    if hostname == "tailsentry-router":
                        print("  🎉 SUCCESS: Real data is flowing to the API!")
                    else:
                        print(f"  ⚠️ Unexpected hostname: {hostname}")
                        
                elif endpoint == "/api/peers":
                    peer_count = len(data.get("peers", {}))
                    print(f"  ✅ Found {peer_count} peers")
                    
                else:
                    print(f"  ✅ Data received: {len(str(data))} chars")
                    
            else:
                print(f"  ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("TailSentry Authentication Test")
    print("=" * 60)
    test_with_login()
    print("\n" + "=" * 60)
    print("Note: You may need to update the username/password in this script")
    print("=" * 60)
