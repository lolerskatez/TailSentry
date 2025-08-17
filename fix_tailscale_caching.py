#!/usr/bin/env python3
"""
Fix the Tailscale data issue by ensuring the cache is being properly handled
"""

import sys
import os
import re
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("tailsentry.fix")

def modify_tailscale_client():
    """
    Modify the tailscale_client.py file to fix the caching behavior
    """
    file_path = Path("tailscale_client.py")
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    # Create backup
    backup_path = file_path.with_suffix(".py.bak")
    with open(file_path, "r") as src, open(backup_path, "w") as dst:
        dst.write(src.read())
    logger.info(f"Created backup: {backup_path}")
    
    # Read the file content
    with open(file_path, "r") as f:
        content = f.read()
    
    # Check if the fix has already been applied
    if "FORCE_LIVE_DATA" in content:
        logger.info("Fix already applied, skipping")
        return True
    
    # Add new environment variable
    env_pattern = r"(# Configuration from environment.*?TAILNET = os\.getenv\([^)]+\))"
    env_replacement = r"\1\n\n# Set this to True to always use live data\nFORCE_LIVE_DATA = os.getenv(\"TAILSENTRY_FORCE_LIVE_DATA\", \"false\").lower() == \"true\""
    
    content = re.sub(env_pattern, env_replacement, content, flags=re.DOTALL)
    
    # Modify the status_json method to bypass cache if FORCE_LIVE_DATA is True
    status_json_pattern = r"(@staticmethod\s+def status_json\(\):\s+\"\"\"Get Tailscale status as JSON \(cached for 5 seconds\)\"\"\"\s+result, _ = TailscaleClient\._status_json_cached\(\))"
    status_json_replacement = r'''@staticmethod
    def status_json():
        """Get Tailscale status as JSON (cached for 5 seconds)"""
        # If FORCE_LIVE_DATA is enabled, bypass the cache
        if FORCE_LIVE_DATA:
            logger.info("FORCE_LIVE_DATA is enabled, bypassing cache")
            # Clear the cache by invalidating it (only keep fresh data)
            TailscaleClient._status_json_cached.cache_clear()
            
        # Get the cached or fresh result
        result, _ = TailscaleClient._status_json_cached()'''
    
    content = re.sub(status_json_pattern, status_json_replacement, content, flags=re.DOTALL)
    
    # Add a clear_cache function
    if "def clear_cache():" not in content:
        cache_clear_method = '''    @staticmethod
    def clear_cache():
        """Clear the status cache to force fresh data on next query"""
        TailscaleClient._status_json_cached.cache_clear()
        logger.info("Tailscale status cache cleared")
        
        # Also remove any cached file if it exists
        if os.path.exists(STATUS_CACHE_FILE):
            try:
                os.remove(STATUS_CACHE_FILE)
                logger.info(f"Removed cache file: {STATUS_CACHE_FILE}")
            except Exception as e:
                logger.error(f"Failed to remove cache file: {str(e)}")
        return True
'''
        
        # Find a good place to add the method (after the status_json method)
        pattern = r"(def status_json.*?\n\s+return result\n)"
        content = re.sub(pattern, r"\1\n" + cache_clear_method, content, flags=re.DOTALL)
    
    # Write the changes
    with open(file_path, "w") as f:
        f.write(content)
    
    logger.info(f"Updated {file_path}")
    return True

def modify_env_example():
    """Add the new environment variable to .env.example"""
    file_path = Path(".env.example")
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    # Read the file
    with open(file_path, "r") as f:
        lines = f.readlines()
    
    # Check if the variable already exists
    if any("TAILSENTRY_FORCE_LIVE_DATA" in line for line in lines):
        logger.info("TAILSENTRY_FORCE_LIVE_DATA already in .env.example")
        return True
    
    # Find the application settings section
    app_settings_index = -1
    for i, line in enumerate(lines):
        if "=== Application Settings ===" in line:
            app_settings_index = i
            break
    
    if app_settings_index == -1:
        logger.warning("Application Settings section not found, adding to the end")
        lines.append("\n# Force using live Tailscale data (no caching)\n")
        lines.append("TAILSENTRY_FORCE_LIVE_DATA=false\n")
    else:
        # Insert after the application settings section
        insert_pos = app_settings_index + 1
        while insert_pos < len(lines) and not lines[insert_pos].strip().startswith("#"):
            insert_pos += 1
        
        lines.insert(insert_pos, "# Force using live Tailscale data (no caching)\n")
        lines.insert(insert_pos + 1, "TAILSENTRY_FORCE_LIVE_DATA=false\n\n")
    
    # Write the changes
    with open(file_path, "w") as f:
        f.writelines(lines)
    
    logger.info(f"Updated {file_path}")
    return True

def update_env_file():
    """Add the new environment variable to the user's .env file if it exists"""
    file_path = Path(".env")
    
    if not file_path.exists():
        logger.warning(".env file not found, skipping")
        return True
    
    # Read the file
    with open(file_path, "r") as f:
        content = f.read()
    
    # Check if the variable already exists
    if "TAILSENTRY_FORCE_LIVE_DATA" in content:
        logger.info("TAILSENTRY_FORCE_LIVE_DATA already in .env")
        return True
    
    # Add the new variable
    with open(file_path, "a") as f:
        f.write("\n# Force using live Tailscale data (no caching)\n")
        f.write("TAILSENTRY_FORCE_LIVE_DATA=true\n")
    
    logger.info("Added TAILSENTRY_FORCE_LIVE_DATA=true to .env")
    return True

def fix_test_script():
    """Fix the test script to clear the cache before testing"""
    file_path = Path("test_tailscale.py")
    
    if not file_path.exists():
        logger.warning(f"Test file not found: {file_path}, skipping")
        return True
    
    # Read the file
    with open(file_path, "r") as f:
        content = f.read()
    
    # Check if we already have a call to clear_cache
    if "clear_cache" in content:
        logger.info("clear_cache call already in test script")
        return True
    
    # Add a call to clear_cache before any test
    pattern = r"(def test_\w+\([^)]*\):)"
    replacement = r"\1\n    # Clear cache before test\n    TailscaleClient.clear_cache()\n"
    
    modified_content = re.sub(pattern, replacement, content)
    
    # Write changes if modifications were made
    if modified_content != content:
        with open(file_path, "w") as f:
            f.write(modified_content)
        logger.info(f"Updated {file_path}")
    else:
        logger.warning("No tests found to update in test script")
    
    return True

def main():
    """Main function to apply all fixes"""
    logger.info("Applying Tailscale data fixes...")
    
    # Apply changes
    modified_tailscale = modify_tailscale_client()
    modified_env_example = modify_env_example()
    updated_env = update_env_file()
    fixed_tests = fix_test_script()
    
    if all([modified_tailscale, modified_env_example, updated_env, fixed_tests]):
        logger.info("All fixes applied successfully")
        
        # Print instructions
        print("\n=== Fix Applied Successfully ===")
        print("The following changes were made:")
        print("1. Added FORCE_LIVE_DATA option to bypass caching")
        print("2. Modified tailscale_client.py to respect this option")
        print("3. Added clear_cache() method to explicitly clear cached data")
        print("4. Updated test scripts to clear cache before tests")
        print("\nYour .env file has been updated to enable FORCE_LIVE_DATA by default.")
        print("You should now restart TailSentry for changes to take effect.")
    else:
        logger.error("Some fixes could not be applied")
        print("\n⚠️ Some fixes could not be applied. See log for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
