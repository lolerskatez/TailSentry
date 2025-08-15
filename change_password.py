#!/usr/bin/env python3
"""
TailSentry Password Change Script
Simple script to change the admin password
"""

import os
import sys
import bcrypt
import getpass
import re
from pathlib import Path

def main():
    print("🔑 TailSentry Password Change")
    print("=" * 40)
    
    # Check if .env exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Make sure you're running this from the TailSentry directory.")
        return
    
    print("Current admin username: admin")
    print()
    
    # Get new password
    while True:
        new_password = getpass.getpass("Enter new password (min 8 chars): ")
        if len(new_password) < 8:
            print("❌ Password must be at least 8 characters")
            continue
        
        confirm_password = getpass.getpass("Confirm new password: ")
        if new_password != confirm_password:
            print("❌ Passwords don't match")
            continue
        
        break
    
    try:
        # Generate new hash
        print("🔄 Generating password hash...")
        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        
        # Read current .env
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update password hash
        content = re.sub(r'ADMIN_PASSWORD_HASH=.*', f'ADMIN_PASSWORD_HASH={password_hash}', content)
        
        # Write back
        with open(env_file, 'w') as f:
            f.write(content)
        
        print("✅ Password updated successfully!")
        print()
        print("🔄 Restart TailSentry service for changes to take effect:")
        print("   sudo systemctl restart tailsentry")
        print()
        print("Or if running manually, restart the application.")
        
    except Exception as e:
        print(f"❌ Error updating password: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main() or 0)
