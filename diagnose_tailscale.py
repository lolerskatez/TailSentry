#!/usr/bin/env python3
"""
TailSentry Diagnostic Tool
This script helps diagnose issues with real Tailscale data in TailSentry
"""

import os
import sys
import json
import subprocess
import platform
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("tailscale-diagnostic")

# Common Tailscale paths by platform
TAILSCALE_PATHS = {
    "Linux": ["/usr/bin/tailscale", "/usr/sbin/tailscale", "/usr/local/bin/tailscale"],
    "Darwin": ["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "/usr/local/bin/tailscale"],
    "Windows": ["C:\\Program Files\\Tailscale\\tailscale.exe", "tailscale.exe"]
}

def get_tailscale_path():
    """Find the tailscale binary path for the current platform"""
    # Get the system platform
    system = platform.system()
    
    # Look in common locations based on platform
    possible_paths = TAILSCALE_PATHS.get(system, ["tailscale"])
    
    # Check PATH
    for path in possible_paths:
        try:
            # On Windows, subprocess.run works differently
            if system == "Windows":
                cmd = ["where", path]
            else:
                cmd = ["which", path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                found_path = result.stdout.strip().split("\n")[0]
                logger.info(f"Found Tailscale at: {found_path}")
                return found_path
        except Exception as e:
            logger.debug(f"Error checking path {path}: {e}")
    
    # Check common locations directly
    for path in possible_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            logger.info(f"Found Tailscale at fixed path: {path}")
            return path
    
    logger.warning("Tailscale binary not found in common locations")
    return "tailscale" if system != "Windows" else "tailscale.exe"

def get_tailscale_status(tailscale_path):
    """Get Tailscale status output"""
    logger.info(f"Getting status from: {tailscale_path}")
    
    try:
        cmd = [tailscale_path, "status", "--json"]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Command failed with return code {result.returncode}")
            logger.error(f"Error: {result.stderr}")
            return None
        
        try:
            data = json.loads(result.stdout)
            logger.info("Successfully parsed JSON data")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Raw output: {result.stdout[:500]}...")
            return None
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return None

def analyze_tailscale_data(data):
    """Analyze Tailscale data for common issues"""
    if not data:
        logger.error("No Tailscale data available to analyze")
        return
    
    # Check for Self information
    if "Self" not in data:
        logger.error("No 'Self' data found in Tailscale status")
        logger.info(f"Available keys: {', '.join(data.keys())}")
        return
    
    # Check for basic information
    self_data = data["Self"]
    logger.info("=== Device Information ===")
    logger.info(f"Hostname: {self_data.get('HostName', 'N/A')}")
    
    if "TailscaleIPs" in self_data and self_data["TailscaleIPs"]:
        logger.info(f"Tailscale IP: {self_data['TailscaleIPs'][0]}")
    else:
        logger.warning("No Tailscale IP found")
    
    # Check peers
    if "Peer" in data:
        peers = data["Peer"]
        logger.info(f"Connected peers: {len(peers)}")
        
        # Show details for up to 5 peers
        count = 0
        for peer_id, peer in peers.items():
            if count >= 5:
                break
            logger.info(f"  Peer: {peer.get('HostName', 'Unknown')} - {peer.get('TailscaleIPs', ['N/A'])[0] if peer.get('TailscaleIPs') else 'No IP'}")
            count += 1
    else:
        logger.warning("No peer information found")
    
    # Check for common issues
    if "BackendState" in data:
        logger.info(f"Backend state: {data['BackendState']}")
        if data['BackendState'] != "Running":
            logger.warning("Tailscale backend is not in 'Running' state")

def main():
    print("=== TailSentry Tailscale Diagnostic Tool ===\n")
    
    # Find Tailscale binary
    print("1. Locating Tailscale binary...")
    tailscale_path = get_tailscale_path()
    print(f"   Using Tailscale at: {tailscale_path}\n")
    
    # Get Tailscale status
    print("2. Getting Tailscale status...")
    status_data = get_tailscale_status(tailscale_path)
    
    if status_data:
        print("   Successfully retrieved status data\n")
        
        # Save the raw data for inspection
        with open("tailscale_status_raw.json", "w") as f:
            json.dump(status_data, f, indent=2)
        print(f"   Raw data saved to tailscale_status_raw.json\n")
        
        # Analyze the data
        print("3. Analyzing Tailscale data...")
        analyze_tailscale_data(status_data)
    else:
        print("   Failed to retrieve status data\n")
    
    print("\n=== Diagnostic Complete ===")
    print("If this script successfully showed real Tailscale data but TailSentry doesn't,")
    print("check how TailSentry processes the data or if there are permission issues when run as a service.")

if __name__ == "__main__":
    main()
