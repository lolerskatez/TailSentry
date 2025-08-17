#!/bin/bash
# Quick fix for bcrypt not found error in TailSentry setup

echo "Installing bcrypt for TailSentry setup..."

# Check if pip/pip3 is available
if command -v pip3 &> /dev/null; then
    pip3 install bcrypt
elif command -v pip &> /dev/null; then
    pip install bcrypt
else
    echo "Error: pip not found. Please install pip first."
    exit 1
fi

# Check if it worked
python3 -c "import bcrypt; print('bcrypt installed successfully!')" || {
    echo "Error: Failed to install bcrypt. Try installing manually with: sudo pip3 install bcrypt"
    exit 1
}

# Create a simple script to create a default admin password
cat > create_password.py << EOF
import bcrypt
import os

# Generate default password hash for "admin123"
default_password = "admin123"
password_hash = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt()).decode()

print(f"Generated password hash: {password_hash}")

# Read .env file if it exists
env_file = '.env'
if os.path.exists(env_file):
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update password hash
        if 'ADMIN_PASSWORD_HASH=' in content:
            content = content.replace('ADMIN_PASSWORD_HASH=', f'ADMIN_PASSWORD_HASH={password_hash}')
        else:
            content += f"\nADMIN_PASSWORD_HASH={password_hash}\n"
        
        # Write back to file
        with open(env_file, 'w') as f:
            f.write(content)
        print(f"Updated {env_file} with new password hash")
        print("Default login credentials: admin / admin123")
    except Exception as e:
        print(f"Error updating .env file: {e}")
else:
    print(f"No {env_file} file found. Create one with the following line:")
    print(f"ADMIN_PASSWORD_HASH={password_hash}")
EOF

# Run the password creation script
python3 create_password.py

# Clean up
rm create_password.py

echo "Fix complete. Try running the setup script again."
