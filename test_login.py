#!/usr/bin/env python3
"""
TailSentry Login Test Script
Test the login functionality directly
"""

import os
import sys
import requests
from pathlib import Path

def test_login(base_url, username, password):
    """Test login functionality"""
    print(f"🔍 Testing TailSentry Login at {base_url}")
    print("=" * 60)
    
    session = requests.Session()
    
    try:
        # Test 1: Check if login page loads
        print("1. Testing login page access...")
        login_response = session.get(f"{base_url}/login")
        print(f"   Status: {login_response.status_code}")
        
        if login_response.status_code != 200:
            print(f"   ❌ Login page failed: {login_response.text}")
            return False
        
        print("   ✅ Login page accessible")
        
        # Test 2: Attempt login
        print("\n2. Testing login submission...")
        login_data = {
            "username": username,
            "password": password
        }
        
        post_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        print(f"   Status: {post_response.status_code}")
        print(f"   Headers: {dict(post_response.headers)}")
        
        if post_response.status_code == 302:
            redirect_location = post_response.headers.get('location', '')
            print(f"   ✅ Login successful - Redirecting to: {redirect_location}")
            
            # Test 3: Follow redirect
            if redirect_location:
                print("\n3. Testing redirect follow...")
                final_response = session.get(f"{base_url}{redirect_location}")
                print(f"   Status: {final_response.status_code}")
                
                if final_response.status_code == 200:
                    print("   ✅ Dashboard accessible after login")
                    return True
                else:
                    print(f"   ❌ Dashboard failed: {final_response.status_code}")
                    return False
        else:
            print(f"   ❌ Login failed: {post_response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error during test: {str(e)}")
        return False

def main():
    print("🧪 TailSentry Login Test")
    print("=" * 40)
    
    # Get parameters
    base_url = input("Enter TailSentry URL (e.g., http://192.168.1.125:8080): ").strip()
    if not base_url:
        base_url = "http://localhost:8080"
    
    username = input("Enter username [admin]: ").strip() or "admin"
    password = input("Enter password: ").strip()
    
    if not password:
        print("❌ Password is required")
        return
    
    # Remove trailing slash
    base_url = base_url.rstrip('/')
    
    print(f"\nTesting with:")
    print(f"   URL: {base_url}")
    print(f"   Username: {username}")
    print(f"   Password: {'*' * len(password)}")
    print()
    
    success = test_login(base_url, username, password)
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Login test PASSED - Authentication is working!")
    else:
        print("❌ Login test FAILED - Check server logs for details")
        print("\nTroubleshooting tips:")
        print("   1. Verify TailSentry service is running")
        print("   2. Check server logs: sudo journalctl -u tailsentry -f")
        print("   3. Try restarting service: sudo systemctl restart tailsentry")
        print("   4. Verify .env configuration")

if __name__ == "__main__":
    main()
