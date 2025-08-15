#!/usr/bin/env python3
"""
TailSentry Authentication Debug Script
Use this to test and fix authentication issues

Run with: /opt/tailsentry/venv/bin/python debug_auth.py
"""

import os
import sys
from pathlib import Path

# Add current directory to path to import auth module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from virtual environment
try:
    import bcrypt
    from dotenv import load_dotenv
    load_dotenv()
except ImportError as e:
    print("❌ Error importing required modules!")
    print("Make sure you're running this with the TailSentry virtual environment:")
    print("   /opt/tailsentry/venv/bin/python debug_auth.py")
    print(f"Error: {e}")
    sys.exit(1)

def test_password_hash(password: str, hash_str: str):
    """Test if a password matches the stored hash"""
    try:
        return bcrypt.checkpw(password.encode(), hash_str.encode())
    except Exception as e:
        print(f"Error checking password: {e}")
        return False

def main():
    print("🔍 TailSentry Authentication Debug")
    print("=" * 50)
    
    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        return
    
    print("✅ .env file found")
    
    # Load and display current values
    load_dotenv()
    username = os.getenv("ADMIN_USERNAME", "")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    session_secret = os.getenv("SESSION_SECRET", "")
    
    print(f"📊 Current Configuration:")
    print(f"   Username: {username or '(not set)'}")
    print(f"   Password Hash: {'✅ Set' if password_hash else '❌ Not set'}")
    print(f"   Session Secret: {'✅ Set' if session_secret else '❌ Not set'}")
    
    if not password_hash:
        print("\n❌ No password hash found! Please run setup again.")
        return
    
    # Test password
    print(f"\n🔑 Testing Password Authentication")
    test_password = input("Enter the password you set during setup: ")
    
    if test_password_hash(test_password, password_hash):
        print("✅ Password matches! Authentication should work.")
        print("\n🎯 Troubleshooting tips:")
        print("   1. Clear browser cookies/cache")
        print("   2. Try incognito/private browsing")
        print("   3. Check if you're being rate limited (wait 15 minutes)")
        print("   4. Restart TailSentry service: sudo systemctl restart tailsentry")
    else:
        print("❌ Password does not match!")
        print("\n🔧 Would you like to reset the password? (y/n)")
        
        if input().lower() == 'y':
            new_password = input("Enter new password (min 8 chars): ")
            if len(new_password) < 8:
                print("❌ Password must be at least 8 characters")
                return
            
            # Generate new hash
            salt = bcrypt.gensalt()
            new_hash = bcrypt.hashpw(new_password.encode(), salt).decode()
            
            # Update .env file
            with open('.env', 'r') as f:
                content = f.read()
            
            # Replace password hash
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('ADMIN_PASSWORD_HASH='):
                    lines[i] = f'ADMIN_PASSWORD_HASH={new_hash}'
                    break
            
            with open('.env', 'w') as f:
                f.write('\n'.join(lines))
            
            print("✅ Password updated! Restart TailSentry service:")
            print("   sudo systemctl restart tailsentry")

if __name__ == "__main__":
    main()
