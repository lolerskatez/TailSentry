#!/usr/bin/env python3
"""
TailSentry Authentication Deep Debug Script
Checks environment variables and authentication flow in detail
"""

import os
import sys
import bcrypt
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    import auth
    load_dotenv()
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

def main():
    print("🔍 TailSentry Deep Authentication Debug")
    print("=" * 60)
    
    # Step 1: Check .env file contents
    print("1. Checking .env file...")
    env_file = Path(".env")
    if not env_file.exists():
        print("   ❌ .env file not found!")
        return
    
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    print("   .env file contents:")
    for line in env_content.split('\n'):
        if line.strip() and not line.startswith('#'):
            key = line.split('=')[0] if '=' in line else line
            if 'PASSWORD_HASH' in key:
                print(f"   {key}=<hash present: {len(line.split('=', 1)[1]) if '=' in line else 0} chars>")
            elif 'SECRET' in key:
                print(f"   {key}=<secret present: {len(line.split('=', 1)[1]) if '=' in line else 0} chars>")
            else:
                print(f"   {line}")
    
    # Step 2: Check environment variables in memory
    print("\n2. Checking loaded environment variables...")
    username_env = os.getenv("ADMIN_USERNAME", "")
    password_hash_env = os.getenv("ADMIN_PASSWORD_HASH", "")
    session_secret_env = os.getenv("SESSION_SECRET", "")
    
    print(f"   ADMIN_USERNAME: '{username_env}' ({'✅' if username_env else '❌'})")
    print(f"   ADMIN_PASSWORD_HASH: {'✅ Present' if password_hash_env else '❌ Missing'} ({len(password_hash_env)} chars)")
    print(f"   SESSION_SECRET: {'✅ Present' if session_secret_env else '❌ Missing'} ({len(session_secret_env)} chars)")
    
    # Step 3: Check auth module globals
    print("\n3. Checking auth module variables...")
    print(f"   auth.ADMIN_USERNAME: '{auth.ADMIN_USERNAME}' ({'✅' if auth.ADMIN_USERNAME else '❌'})")
    print(f"   auth.ADMIN_PASSWORD_HASH: {'✅ Present' if auth.ADMIN_PASSWORD_HASH else '❌ Missing'} ({len(auth.ADMIN_PASSWORD_HASH)} chars)")
    print(f"   auth.SESSION_SECRET: {'✅ Present' if auth.SESSION_SECRET else '❌ Missing'} ({len(auth.SESSION_SECRET)} chars)")
    
    # Step 4: Check setup status based on password hash
    print("\n4. Checking setup status...")
    setup_complete = bool(auth.ADMIN_PASSWORD_HASH)
    print(f"   Setup complete: {setup_complete} ({'✅ Ready' if setup_complete else '❌ Password hash missing'})")
    
    # Step 5: Test password verification
    if auth.ADMIN_PASSWORD_HASH:
        print("\n5. Testing password verification...")
        test_password = input("Enter password to test: ")
        
        # Test with auth module function
        auth_result = auth.verify_password(test_password, auth.ADMIN_PASSWORD_HASH)
        print(f"   auth.verify_password(): {'✅ Match' if auth_result else '❌ No match'}")
        
        # Test with direct bcrypt
        try:
            direct_result = bcrypt.checkpw(test_password.encode(), auth.ADMIN_PASSWORD_HASH.encode())
            print(f"   Direct bcrypt.checkpw(): {'✅ Match' if direct_result else '❌ No match'}")
        except Exception as e:
            print(f"   Direct bcrypt test failed: {e}")
        
        # Test the exact login logic
        print("\n6. Testing exact login logic...")
        username_match = "admin" == auth.ADMIN_USERNAME
        password_match = auth.verify_password(test_password, auth.ADMIN_PASSWORD_HASH)
        print(f"   Username match ('admin' == '{auth.ADMIN_USERNAME}'): {'✅' if username_match else '❌'}")
        print(f"   Password match: {'✅' if password_match else '❌'}")
        print(f"   Login would succeed: {'✅' if (username_match and password_match) else '❌'}")
    else:
        print("\n5. ❌ No password hash found - cannot test password verification")
    
    # Step 6: Check for potential issues
    print("\n7. Potential issues check...")
    issues = []
    
    if not auth.ADMIN_USERNAME:
        issues.append("ADMIN_USERNAME is empty")
    if not auth.ADMIN_PASSWORD_HASH:
        issues.append("ADMIN_PASSWORD_HASH is empty")
    if not auth.SESSION_SECRET or auth.SESSION_SECRET == "changeme":
        issues.append("SESSION_SECRET is not set or default")
    if username_env != auth.ADMIN_USERNAME:
        issues.append(f"Environment variable mismatch: env='{username_env}' vs auth='{auth.ADMIN_USERNAME}'")
    if password_hash_env != auth.ADMIN_PASSWORD_HASH:
        issues.append("Password hash mismatch between environment and auth module")
    
    if issues:
        print("   Issues found:")
        for issue in issues:
            print(f"   ❌ {issue}")
        
        print("\n🔧 Recommended fixes:")
        print("   1. Restart TailSentry service: sudo systemctl restart tailsentry")
        print("   2. If that doesn't work, check .env file permissions")
        print("   3. Verify .env file is in correct directory (/opt/tailsentry)")
        print("   4. Try running setup again if necessary")
    else:
        print("   ✅ No obvious issues found")

if __name__ == "__main__":
    main()
