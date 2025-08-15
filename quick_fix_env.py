#!/usr/bin/env python3
"""
Quick fix script to create a working .env file
Run this on your test system if the installation script didn't create proper credentials
"""

import secrets
import bcrypt
import shutil
import os

print("🔧 TailSentry Quick Fix - Creating .env file")
print("=" * 50)

# Check if we're in the right directory
if not os.path.exists('.env.example'):
    print("❌ Error: .env.example not found. Please run this script from the TailSentry directory.")
    exit(1)

# Backup existing .env if it exists
if os.path.exists('.env'):
    print("📄 Backing up existing .env to .env.backup")
    shutil.copy('.env', '.env.backup')

# Copy from example
print("📋 Copying .env.example to .env")
shutil.copy('.env.example', '.env')

# Generate credentials
print("🔐 Generating secure credentials...")
session_secret = secrets.token_hex(32)
password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()

# Read and update .env
with open('.env', 'r') as f:
    content = f.read()

print("📝 Updating .env with credentials...")

# Update the content
content = content.replace('ADMIN_USERNAME=admin', 'ADMIN_USERNAME=admin')
content = content.replace('ADMIN_PASSWORD_HASH=', f'ADMIN_PASSWORD_HASH={password_hash}')
content = content.replace('SESSION_SECRET=', f'SESSION_SECRET={session_secret}')
content = content.replace('DEVELOPMENT=false', 'DEVELOPMENT=true')

# Write back
with open('.env', 'w') as f:
    f.write(content)

# Verify
with open('.env', 'r') as f:
    verify_content = f.read()

print(f"✅ .env file created successfully ({len(verify_content)} bytes)")
print()
print("🔑 Credentials set:")
print("   Username: admin")
print("   Password: admin123")
print()
print("🧪 Testing password hash...")
try:
    test_result = bcrypt.checkpw("admin123".encode(), password_hash.encode())
    print(f"   Hash verification: {'✅ PASS' if test_result else '❌ FAIL'}")
except Exception as e:
    print(f"   Hash verification: ❌ ERROR - {e}")

print()
print("🚀 You can now restart TailSentry and login!")
print("   sudo systemctl restart tailsentry.service")
