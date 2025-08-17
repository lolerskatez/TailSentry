#!/usr/bin/env python3
"""
Quick verification that the TailSentry fixes are working
"""

import subprocess
import json
import sys
import os

def check_tailscale_status():
    """Check if Tailscale is available and working"""
    print("🔍 Checking Tailscale status...")
    
    try:
        # Test direct tailscale command
        result = subprocess.run(['tailscale', 'status', '--json'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if "Self" in data:
                hostname = data["Self"].get("HostName", "unknown")
                peer_count = len(data.get("Peer", {}))
                print(f"✅ Tailscale working: {hostname} with {peer_count} peers")
                return True
            else:
                print("❌ Tailscale command succeeded but no Self data found")
                return False
        else:
            print(f"❌ Tailscale command failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ Tailscale command not found - is Tailscale installed?")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Tailscale command timed out")
        return False
    except Exception as e:
        print(f"❌ Error running Tailscale: {e}")
        return False

def check_environment():
    """Check environment configuration"""
    print("\n🔍 Checking environment configuration...")
    
    env_file = ".env"
    if os.path.exists(env_file):
        print("✅ .env file exists")
        
        with open(env_file, 'r') as f:
            content = f.read()
            
        if "TAILSENTRY_FORCE_LIVE_DATA=true" in content:
            print("✅ FORCE_LIVE_DATA is enabled")
        else:
            print("⚠️ FORCE_LIVE_DATA not found or not set to true")
            
    else:
        print("⚠️ .env file not found - using defaults")

def check_file_changes():
    """Check that our key files were modified"""
    print("\n🔍 Checking file modifications...")
    
    files_to_check = [
        ("static/dashboard.js", "loadRealData"),
        ("routes/api.py", "Enhanced logging"),
        ("tailscale_client.py", "FORCE_LIVE_DATA"),
        ("templates/index.html", "management dashboard")
    ]
    
    for filename, expected_content in files_to_check:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if expected_content in content:
                print(f"✅ {filename} contains expected changes")
            else:
                print(f"❌ {filename} missing expected content: {expected_content}")
        else:
            print(f"❌ {filename} not found")

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("TailSentry Fix Verification")
    print("=" * 60)
    
    # Check Tailscale
    tailscale_ok = check_tailscale_status()
    
    # Check environment
    check_environment()
    
    # Check file changes
    check_file_changes()
    
    print("\n" + "=" * 60)
    print("Summary:")
    
    if tailscale_ok:
        print("✅ Tailscale is working and should provide real data")
        print("✅ TailSentry should now display real Tailscale data")
        print("\n📋 Next steps:")
        print("   1. Start TailSentry: python main.py")
        print("   2. Open http://localhost:8000 in your browser")
        print("   3. Login and verify real data is displayed")
        print("   4. Run test_real_data.py to verify API endpoints")
    else:
        print("❌ Tailscale issues detected")
        print("\n📋 Fix Tailscale first:")
        print("   1. Ensure Tailscale is installed and running")
        print("   2. Run 'tailscale status' to verify connectivity")
        print("   3. Then restart TailSentry")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
