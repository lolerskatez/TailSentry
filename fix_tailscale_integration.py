#!/usr/bin/env python3
"""
Fix for the issue where TailSentry shows example data instead of real Tailscale data.

This script:
1. Removes any cached Tailscale status data
2. Tests direct Tailscale integration
3. Updates the TailSentry configuration
"""

import os
import sys
import json
import shutil
from pathlib import Path
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("tailsentry.fix")

# Constants
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATUS_CACHE_FILE = os.path.join(DATA_DIR, "tailscale_status_cache.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
TAILSCALE_PATHS = {
    "Linux": ["/usr/bin/tailscale", "/usr/sbin/tailscale", "/usr/local/bin/tailscale"],
    "Darwin": ["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "/usr/local/bin/tailscale"],
    "Windows": ["C:\\Program Files\\Tailscale\\tailscale.exe", "tailscale.exe"]
}

def get_tailscale_path():
    """Find the Tailscale binary path"""
    import platform
    system = platform.system()
    
    # Check common paths for the current OS
    paths = TAILSCALE_PATHS.get(system, ["tailscale"])
    for path in paths:
        try:
            if os.path.exists(path):
                return path
            if system == "Windows" and shutil.which(path):
                return shutil.which(path)
        except:
            continue
            
    # Fall back to just the binary name (rely on PATH)
    return "tailscale" if system != "Windows" else "tailscale.exe"

def test_tailscale_integration():
    """Test direct integration with Tailscale CLI"""
    tailscale_path = get_tailscale_path()
    logger.info(f"Using Tailscale binary at: {tailscale_path}")
    
    try:
        # Run tailscale status --json
        cmd = [tailscale_path, "status", "--json"]
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, check=True)
        output = result.stdout.decode('utf-8')
        
        # Check if output is valid JSON
        data = json.loads(output)
        if "Self" not in data:
            logger.warning("Self data not found in status output")
            return False
            
        hostname = data.get("Self", {}).get("HostName", "unknown")
        ip = data.get("Self", {}).get("TailscaleIPs", ["none"])[0]
        logger.info(f"✅ Tailscale integration working: {hostname} ({ip})")
        
        # Write status to a file for debugging
        debug_file = os.path.join(DATA_DIR, "status_debug.json")
        with open(debug_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved status to {debug_file} for debugging")
        
        return True
    except Exception as e:
        logger.error(f"❌ Tailscale integration test failed: {str(e)}")
        return False

def clear_cache():
    """Remove any cached status files"""
    if os.path.exists(STATUS_CACHE_FILE):
        try:
            os.remove(STATUS_CACHE_FILE)
            logger.info(f"Removed cached status file: {STATUS_CACHE_FILE}")
        except Exception as e:
            logger.error(f"Could not remove cache file: {str(e)}")
    
    # Check for other cache files
    for file in os.listdir(DATA_DIR):
        if "cache" in file.lower() or "status" in file.lower():
            try:
                cache_path = os.path.join(DATA_DIR, file)
                if os.path.isfile(cache_path):
                    os.remove(cache_path)
                    logger.info(f"Removed additional cache file: {file}")
            except Exception:
                pass

def update_env_config():
    """Update .env configuration file"""
    if not os.path.exists(ENV_FILE):
        logger.warning(f".env file not found at {ENV_FILE}")
        return False
        
    try:
        # Read current config
        with open(ENV_FILE, "r") as f:
            lines = f.readlines()
            
        # Check and update config settings
        has_changes = False
        new_lines = []
        found_settings = {
            "DEVELOPMENT": False,
            "TAILSENTRY_DATA_DIR": False,
        }
        
        for line in lines:
            # Skip comments and empty lines
            if line.strip().startswith("#") or not line.strip():
                new_lines.append(line)
                continue
                
            # Check if it's a setting we want to update
            if line.startswith("DEVELOPMENT="):
                found_settings["DEVELOPMENT"] = True
                if "true" in line.lower():
                    new_lines.append("DEVELOPMENT=true\n")
                    logger.info("Keeping DEVELOPMENT=true")
                else:
                    new_lines.append("DEVELOPMENT=false\n")
                    logger.info("Setting DEVELOPMENT=false")
                has_changes = True
            elif line.startswith("TAILSENTRY_DATA_DIR="):
                found_settings["TAILSENTRY_DATA_DIR"] = True
                data_dir = os.path.abspath(DATA_DIR)
                new_lines.append(f"TAILSENTRY_DATA_DIR={data_dir}\n")
                logger.info(f"Setting TAILSENTRY_DATA_DIR={data_dir}")
                has_changes = True
            else:
                new_lines.append(line)
        
        # Add settings if not found
        for setting, found in found_settings.items():
            if not found:
                if setting == "DEVELOPMENT":
                    new_lines.append("DEVELOPMENT=false\n")
                    logger.info("Added DEVELOPMENT=false")
                    has_changes = True
                elif setting == "TAILSENTRY_DATA_DIR":
                    data_dir = os.path.abspath(DATA_DIR)
                    new_lines.append(f"TAILSENTRY_DATA_DIR={data_dir}\n")
                    logger.info(f"Added TAILSENTRY_DATA_DIR={data_dir}")
                    has_changes = True
        
        # Write updated config if changes were made
        if has_changes:
            with open(ENV_FILE, "w") as f:
                f.writelines(new_lines)
            logger.info("Updated .env configuration")
        else:
            logger.info("No changes needed in .env configuration")
            
        return True
    except Exception as e:
        logger.error(f"Error updating .env file: {str(e)}")
        return False

def modify_tailscale_client_debugging():
    """Add additional debugging to tailscale_client.py"""
    client_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tailscale_client.py")
    
    if not os.path.exists(client_path):
        logger.error(f"Tailscale client not found at {client_path}")
        return False
    
    try:
        # Create a backup
        backup_path = f"{client_path}.bak"
        shutil.copy2(client_path, backup_path)
        logger.info(f"Created backup at {backup_path}")
        
        # Find and modify the status_json method to add more logging
        with open(client_path, "r") as f:
            content = f.read()
            
        # We're not making changes to the file directly yet, just suggesting them
        logger.info("Backup created. Manual modifications may be needed.")
        return True
    except Exception as e:
        logger.error(f"Error modifying tailscale_client.py: {str(e)}")
        return False

def main():
    """Main fix routine"""
    logger.info("Starting TailSentry data fix...")
    
    # Make sure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Step 1: Clear any cached data
    clear_cache()
    
    # Step 2: Test Tailscale integration
    if not test_tailscale_integration():
        logger.error("Tailscale integration test failed. Please check that Tailscale is installed and running.")
        sys.exit(1)
    
    # Step 3: Update environment config
    update_env_config()
    
    # Step 4: Add additional debugging if needed
    modify_tailscale_client_debugging()
    
    logger.info("Fix completed. Please restart TailSentry for changes to take effect.")
    logger.info("If the issue persists, check the logs and run 'debug_api_error.py' for more details.")

if __name__ == "__main__":
    main()
