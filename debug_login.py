#!/usr/bin/env python3
"""
Debug script to check login authentication issues
"""

import os
import bcrypt
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("🔍 Login Authentication Debug")
print("=" * 50)

# Check environment variables
admin_username = os.getenv("ADMIN_USERNAME", "")
admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
session_secret = os.getenv("SESSION_SECRET", "")

print(f"ADMIN_USERNAME: '{admin_username}' (length: {len(admin_username)})")
print(f"ADMIN_PASSWORD_HASH: {'✓ Set' if admin_password_hash else '✗ Empty'} (length: {len(admin_password_hash)})")
print(f"SESSION_SECRET: {'✓ Set' if session_secret else '✗ Empty'} (length: {len(session_secret)})")

print("\n" + "=" * 50)

if admin_password_hash:
    print(f"Password hash preview: {admin_password_hash[:20]}...")
    
    # Test the expected password
    test_password = "admin123"
    print(f"\n🧪 Testing password: '{test_password}'")
    
    try:
        # Test using the same logic as the app
        result = bcrypt.checkpw(test_password.encode(), admin_password_hash.encode())
        print(f"Password verification result: {'✅ SUCCESS' if result else '❌ FAILED'}")
        
        if not result:
            print("\n🔧 Debugging hash format...")
            print(f"Hash starts with: {admin_password_hash[:10]}")
            print(f"Expected bcrypt prefix: $2a$, $2b$, $2x$, or $2y$")
            
            # Check if it's a valid bcrypt hash
            if admin_password_hash.startswith(('$2a$', '$2b$', '$2x$', '$2y$')):
                print("✅ Hash format looks like bcrypt")
            else:
                print("❌ Hash format doesn't look like bcrypt")
                
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        print(f"Error type: {type(e).__name__}")

else:
    print("❌ No password hash found in environment")

print("\n" + "=" * 50)

# Test generating a new hash for comparison
print("🔧 Generating fresh hash for 'admin123'...")
try:
    fresh_salt = bcrypt.gensalt()
    fresh_hash = bcrypt.hashpw("admin123".encode(), fresh_salt)
    fresh_hash_str = fresh_hash.decode()
    
    print(f"Fresh hash: {fresh_hash_str}")
    print(f"Fresh hash verification: {'✅' if bcrypt.checkpw('admin123'.encode(), fresh_hash) else '❌'}")
    
    if admin_password_hash and admin_password_hash != fresh_hash_str:
        print(f"\n📊 Hash comparison:")
        print(f"Stored:  {admin_password_hash}")
        print(f"Fresh:   {fresh_hash_str}")
        print("Note: Hashes will be different due to different salts, but both should verify")
        
except Exception as e:
    print(f"❌ Error generating fresh hash: {e}")

print("\n" + "=" * 50)
print("💡 If the stored hash fails but the fresh hash works,")
print("   the issue is with how the hash was generated during installation.")
