import subprocess
import json
import httpx
import os
import time
import socket
import platform
import re
import logging
import asyncio
import ipaddress
import base64
import shutil
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Union, Optional, Tuple, Set
from functools import lru_cache, wraps
from dotenv import load_dotenv

def safe_get_dict(obj, key, default=None):
    if isinstance(obj, dict):
        val = obj.get(key, default if default is not None else {})
        if isinstance(val, dict):
            return val
    return default if default is not None else {}
import json
import httpx
import os
import time
import socket
import platform
import re
import logging
import asyncio
import ipaddress
import base64
import shutil
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Union, Optional, Tuple, Set
from functools import lru_cache, wraps
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger("tailsentry.tailscale")

load_dotenv()

# Configuration from environment
TAILSCALE_API_KEY = os.getenv("TAILSCALE_API_KEY")
if not TAILSCALE_API_KEY:
    logger.warning("TAILSCALE_API_KEY is not set. Tailscale integration will be disabled until an API Key is provided.")
TAILNET = os.getenv("TAILSCALE_TAILNET", "-")  # Default to "-" for personal tailnet
API_TIMEOUT = int(os.getenv("TAILSCALE_API_TIMEOUT", "10"))  # API timeout in seconds
DATA_DIR = os.getenv("TAILSENTRY_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))

# Set this to True to always use live data
FORCE_LIVE_DATA = os.getenv("TAILSENTRY_FORCE_LIVE_DATA", "true").lower() == "true"
USE_MOCK_DATA = os.getenv("TAILSENTRY_USE_MOCK_DATA", "false").lower() == "true"

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Constants
DEFAULT_STATUS_CACHE_SECONDS = 5
METRICS_HISTORY_FILE = os.path.join(DATA_DIR, "metrics_history.json")
ACL_POLICY_FILE = os.path.join(DATA_DIR, "policy.json")
ACL_BACKUP_DIR = os.path.join(DATA_DIR, "acl_backups")
STATUS_CACHE_FILE = os.path.join(DATA_DIR, "tailscale_status_cache.json")

# Common Tailscale binary paths by platform
TAILSCALE_PATHS = {
    "Linux": ["/usr/bin/tailscale", "/usr/sbin/tailscale", "/usr/local/bin/tailscale"],
    "Darwin": ["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "/usr/local/bin/tailscale"],
    "Windows": ["C:\\Program Files\\Tailscale\\tailscale.exe", "tailscale.exe"]
}

# Create ACL backup directory if it doesn't exist
os.makedirs(ACL_BACKUP_DIR, exist_ok=True)

def retry(max_attempts=3, delay=1):
    """Decorator for retrying functions that might fail temporarily"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            last_error = None
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    attempts += 1
                    if attempts < max_attempts:
                        logger.warning(f"Attempt {attempts} failed, retrying in {delay}s: {str(e)}")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed: {str(e)}")
                        raise
            
            # This should never happen, but just in case
            if last_error:
                raise last_error
            return None
        return wrapper
    return decorator

class TailscaleMetrics:
    """Store and retrieve Tailscale metrics history"""
    
    @staticmethod
    def save_metrics(metrics: Dict):
        """Save metrics snapshot to history file"""
        timestamp = int(time.time())
        
        try:
            # Load existing metrics
            if os.path.exists(METRICS_HISTORY_FILE):
                with open(METRICS_HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            else:
                history = {"datapoints": []}
                
            # Add new datapoint
            datapoint = {
                "timestamp": timestamp,
                "metrics": metrics
            }
            history["datapoints"].append(datapoint)
            
            # Keep only the last 24 hours of data (assuming 5-minute intervals)
            cutoff = timestamp - (24 * 60 * 60)
            history["datapoints"] = [dp for dp in history["datapoints"] 
                                     if dp["timestamp"] > cutoff]
            
            # Save updated history
            with open(METRICS_HISTORY_FILE, 'w') as f:
                json.dump(history, f)
                
            return True
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")
            return False
    
    @staticmethod
    def get_metrics_history(hours=24):
        """Get metrics history for the last N hours"""
        try:
            if not os.path.exists(METRICS_HISTORY_FILE):
                return {"datapoints": []}
                
            with open(METRICS_HISTORY_FILE, 'r') as f:
                history = json.load(f)
                
            # Filter by requested timeframe
            cutoff = int(time.time()) - (hours * 60 * 60)
            history["datapoints"] = [dp for dp in history["datapoints"] 
                                    if dp["timestamp"] > cutoff]
                                    
            return history
        except Exception as e:
            logger.error(f"Failed to load metrics history: {str(e)}")
            return {"error": str(e), "datapoints": []}

class TailscaleACL:
    """Manage Tailscale ACL policy files"""
    
    @staticmethod
    def load_policy():
        """Load the current ACL policy file"""
        try:
            if os.path.exists(ACL_POLICY_FILE):
                with open(ACL_POLICY_FILE, 'r') as f:
                    return json.load(f)
            else:
                # Return a default empty policy structure
                default_policy = {
                    "acls": [
                        {"action": "accept", "users": ["*"], "ports": ["*:*"]}
                    ],
                    "tagOwners": {},
                    "autoApprovers": {},
                    "nodeAttrs": []
                }
                return default_policy
        except Exception as e:
            logger.error(f"Failed to load ACL policy: {str(e)}")
            raise
    
    @staticmethod
    def save_policy(policy: Dict, create_backup=True):
        """Save ACL policy to file with optional backup"""
        try:
            # Create backup of current policy if it exists
            if create_backup and os.path.exists(ACL_POLICY_FILE):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(ACL_BACKUP_DIR, f"policy_{timestamp}.json")
                shutil.copy2(ACL_POLICY_FILE, backup_path)
                logger.info(f"Created ACL policy backup at {backup_path}")
                
            # Save the new policy
            with open(ACL_POLICY_FILE, 'w') as f:
                json.dump(policy, f, indent=2)
            
            logger.info("ACL policy saved successfully")
            return {"success": True, "message": "Policy saved successfully"}
        except Exception as e:
            logger.error(f"Failed to save ACL policy: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_backup_list():
        """Get list of available ACL policy backups"""
        try:
            if not os.path.exists(ACL_BACKUP_DIR):
                return []
                
            backups = []
            for filename in os.listdir(ACL_BACKUP_DIR):
                if filename.startswith("policy_") and filename.endswith(".json"):
                    file_path = os.path.join(ACL_BACKUP_DIR, filename)
                    timestamp = filename[7:-5]  # Extract timestamp from filename
                    stat = os.stat(file_path)
                    
                    backups.append({
                        "filename": filename,
                        "path": file_path,
                        "timestamp": timestamp,
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
            
            # Sort by creation time (newest first)
            return sorted(backups, key=lambda x: x["created"], reverse=True)
        except Exception as e:
            logger.error(f"Failed to list ACL backups: {str(e)}")
            return []
            
    @staticmethod
    def restore_backup(backup_filename):
        """Restore an ACL policy from backup"""
        backup_path = os.path.join(ACL_BACKUP_DIR, backup_filename)
        
        if not os.path.exists(backup_path):
            return {"success": False, "error": f"Backup file not found: {backup_filename}"}
            
        try:
            # Validate that the backup is valid JSON before restoring
            with open(backup_path, 'r') as f:
                policy = json.load(f)
            
            # Make backup of current policy before restoring
            TailscaleACL.save_policy(TailscaleACL.load_policy(), create_backup=True)
            
            # Copy the backup to the current policy file
            shutil.copy2(backup_path, ACL_POLICY_FILE)
            
            return {
                "success": True, 
                "message": f"Successfully restored policy from backup: {backup_filename}"
            }
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON in backup file"}
        except Exception as e:
            logger.error(f"Failed to restore backup: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def add_acl_rule(users: List[str], ports: List[str], action="accept", description=""):
        """Add a new ACL rule to the policy"""
        try:
            policy = TailscaleACL.load_policy()
            
            if "acls" not in policy:
                policy["acls"] = []
                
            new_rule = {
                "action": action,
                "users": users,
                "ports": ports
            }
            
            if description:
                new_rule["description"] = description
                
            policy["acls"].append(new_rule)
            
            return TailscaleACL.save_policy(policy)
        except Exception as e:
            logger.error(f"Failed to add ACL rule: {str(e)}")
            return {"success": False, "error": str(e)}
            
    @staticmethod
    def apply_policy():
        """Apply the current ACL policy to Tailscale using API"""
        # This would typically involve calling the Tailscale API to apply the policy
        # For now, we'll just return a placeholder result
        logger.info("ACL policy application functionality not yet implemented")
        return {
            "success": False, 
            "error": "Policy application not implemented. Use the Tailscale web admin interface."
        }


class TailscaleClient:

    @staticmethod
    def set_exit_node_advanced(advertised_routes=None, firewall=None, hostname=None):
        """
        Enable/disable exit node with full control, always including all non-default flags.
        This method merges current Tailscale state with requested changes and builds a robust tailscale up command.
        """
        import platform
        # Get current Tailscale state
        status = TailscaleClient.status_json()
        self_obj = safe_get_dict(status, "Self")
        # Gather current settings
        current_hostname = self_obj.get("HostName") or platform.node()
        current_adv_routes = self_obj.get("AdvertisedRoutes", [])
        capabilities = self_obj.get("Capabilities", {})
        if isinstance(capabilities, dict):
            current_accept_routes = capabilities.get("AcceptRoutes", True)
        else:
            current_accept_routes = True
        # Merge with requested changes
        merged_hostname = hostname or current_hostname
        # If enabling exit node, ensure 0.0.0.0/0 is present in advertise_routes
        merged_adv_routes = list(advertised_routes) if advertised_routes is not None else list(current_adv_routes)
        if advertised_routes is not None and ("0.0.0.0/0" not in merged_adv_routes and "::/0" not in merged_adv_routes):
            # Check if user is enabling exit node (by intent)
            if firewall or (hasattr(advertised_routes, '__len__') and len(advertised_routes) == 0):
                merged_adv_routes.append("0.0.0.0/0")
        merged_firewall = firewall if firewall is not None else False
        # Build args (match set_exit_node logic)
        args = ["--reset"]  # Use --reset to avoid needing all non-default flags
        if merged_hostname:
            args += ["--hostname", str(merged_hostname)]
        # Accept routes (always explicit)
        if current_accept_routes:
            args.append("--accept-routes")
        else:
            args.append("--no-accept-routes")
        # Advertised subnet routes (not exit node)
        subnet_routes = [r for r in merged_adv_routes if r not in ("0.0.0.0/0", "::/0")]
        # Always include --advertise-routes, even if empty, to satisfy Tailscale's strict flag requirements
        if subnet_routes:
            args += ["--advertise-routes", ",".join(subnet_routes)]
        # Exit node flags
        if "0.0.0.0/0" in merged_adv_routes or "::/0" in merged_adv_routes:
            args.append("--advertise-exit-node")
        # Firewall flag removed due to lack of support in current Tailscale version
        logger.info(f"Running tailscale up with args: {args}")
        return TailscaleClient.up(extra_args=args)
    @staticmethod
    def get_tailscale_path():
        """Find the tailscale binary path for the current platform, robust to platform module bugs on Windows."""
        # Defensive: ensure platform.system() always returns a string
        try:
            system = platform.system()
        except Exception as e:
            # Fallback: try subprocess and decode output
            try:
                out = subprocess.check_output([sys.executable, '-c', 'import platform; print(platform.system())'])
                system = out.decode('utf-8').strip()
            except Exception:
                system = 'Windows' if os.name == 'nt' else 'Linux'

        # Look in common locations based on platform
        possible_paths = TAILSCALE_PATHS.get(system, ["tailscale"])

        # Add the system PATH to our search locations
        if os.environ.get("PATH"):
            path_dirs = os.environ["PATH"].split(os.pathsep)
            for path_dir in path_dirs:
                if system == "Windows":
                    possible_paths.append(os.path.join(path_dir, "tailscale.exe"))
                else:
                    possible_paths.append(os.path.join(path_dir, "tailscale"))

        # Try each path
        for path in possible_paths:
            try:
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
                # On Windows, shutil.which can help find executables
                if system == "Windows" and shutil.which(path):
                    return shutil.which(path)
            except Exception:
                continue

        # Fall back to just the binary name (rely on PATH)
        return "tailscale" if system != "Windows" else "tailscale.exe"
    
    # Cache status result for 5 seconds to prevent hammering the CLI
    @staticmethod
    @lru_cache(maxsize=1)
    def _status_json_cached():
        """Internal cached version of status_json with 5-second TTL"""
        # Add timestamp to control cache invalidation
        timestamp = int(time.time() / DEFAULT_STATUS_CACHE_SECONDS)  # Changes every N seconds
        try:
            # Get the Tailscale binary path
            tailscale_path = TailscaleClient.get_tailscale_path()
            logger.debug(f"Using Tailscale binary at: {tailscale_path}")
            
            # Validate path exists
            if tailscale_path is not None and not os.path.exists(tailscale_path) and '/' in tailscale_path:
                logger.error(f"Tailscale binary not found at {tailscale_path}")
                return {"error": f"Tailscale binary not found at {tailscale_path}"}, timestamp
            
            # Run the status command with full path
            cmd = [tailscale_path, "status", "--json"]
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run the command
            out = subprocess.run(cmd, capture_output=True, check=True, timeout=10)
            
            # Properly handle the output as bytes
            output_text = out.stdout.decode('utf-8')
            logger.debug(f"Command output length: {len(output_text)} bytes")
            
            # Parse the JSON
            data = json.loads(output_text)
            
            # Save metrics if this is real data (not an error)
            if "Self" in data and "TXBytes" in data["Self"]:
                metrics = {
                    "tx_bytes": data["Self"]["TXBytes"],
                    "rx_bytes": data["Self"]["RXBytes"],
                    "peers_count": len(data.get("Peer", {})),
                    "exit_node_active": any(peer.get("ExitNode", False) 
                                          for peer in data.get("Peer", {}).values())
                }
                TailscaleMetrics.save_metrics(metrics)
                
            return data, timestamp
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in Tailscale status: {e}")
            return {"error": f"JSON decode error: {str(e)}"}, timestamp
        except subprocess.CalledProcessError as e:
            logger.error(f"Tailscale command failed: {e}")
            error_msg = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
            return {"error": f"Command failed with code {e.returncode}: {error_msg}"}, timestamp
        except subprocess.TimeoutExpired:
            logger.error("Tailscale status command timed out")
            return {"error": "Command timed out after 10 seconds"}, timestamp
        except Exception as e:
            logger.exception("Unexpected error getting Tailscale status")
            return {"error": str(e)}, timestamp
    
    @staticmethod
    def status_json():
        """Get Tailscale status as JSON (cached for 5 seconds)"""
        # Force live data - disable mock data completely
        if USE_MOCK_DATA and not FORCE_LIVE_DATA:
            logger.warning("USE_MOCK_DATA is enabled but FORCE_LIVE_DATA overrides it")
        
        # Always bypass cache when forcing live data
        if FORCE_LIVE_DATA:
            logger.info("FORCE_LIVE_DATA is enabled, bypassing cache")
            TailscaleClient._status_json_cached.cache_clear()
            
        result, _ = TailscaleClient._status_json_cached()
        
        # Enhanced logging for debugging
        if isinstance(result, dict) and "error" not in result:
            self_obj = result.get("Self", {})
            peer_obj = result.get("Peer", {})
            
            if isinstance(self_obj, dict):
                hostname = self_obj.get("HostName", "unknown")
                ip = self_obj.get("TailscaleIPs", ["none"])[0] if self_obj.get("TailscaleIPs") else "none"
            else:
                hostname = "unknown"
                ip = "none"
                
            if isinstance(peer_obj, dict):
                peer_count = len(peer_obj)
            else:
                peer_count = 0
                
            logger.info(f"Returning real Tailscale data: {hostname} ({ip}) with {peer_count} peers")
        else:
            error = result.get("error", "unknown error") if isinstance(result, dict) else "not a dict"
            logger.error(f"Error in Tailscale status: {error}")
        return result
        
    @staticmethod
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

    @staticmethod
    def get_all_devices():
        """Get all devices in the tailnet from tailscale status command"""
        try:
            tailscale_path = TailscaleClient.get_tailscale_path()
            cmd = [tailscale_path, "status"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                devices = TailscaleClient._parse_status_output(result.stdout)
                logger.info(f"Found {len(devices)} devices in tailnet")
                return devices
            else:
                logger.error(f"Tailscale status command failed: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting all devices: {str(e)}")
            return []

    @staticmethod
    def _parse_status_output(output):
        """Parse the text output of tailscale status to extract device information"""
        devices = []
        
        # Get JSON status for additional data like timestamps
        json_status = TailscaleClient.status_json()
        peer_data = json_status.get("Peer", {}) if isinstance(json_status, dict) else {}
        
        # Split output into lines and process each device line
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines, comments, and health check lines
            if not line or line.startswith('#') or 'Health check:' in line:
                continue
                
            # Parse device line format: IP HOSTNAME USER OS STATUS
            # Example: 100.74.214.67   godzilla             d.d.rodriquez@ windows idle; offers exit node
            parts = line.split()
            
            if len(parts) >= 4:
                try:
                    ip = parts[0]
                    hostname = parts[1]
                    
                    # Find the OS (usually the 4th or 5th part)
                    os_part = ""
                    status_start = -1
                    
                    # Look for OS keywords
                    for i, part in enumerate(parts[2:], 2):
                        if part in ['windows', 'linux', 'macOS', 'iOS', 'android', 'unknown']:
                            os_part = part
                            status_start = i + 1
                            break
                    
                    # If no OS found, assume it's at position 3
                    if not os_part and len(parts) >= 4:
                        os_part = parts[3] if len(parts) > 3 else "unknown"
                        status_start = 4
                    
                    # Get status (everything after OS)
                    status_parts = parts[status_start:] if status_start > 0 else []
                    status = ' '.join(status_parts) if status_parts else ""
                    
                    # Determine online status from text parsing as fallback
                    is_online = 'active' in status or 'idle' in status
                    
                    # Get proper lastSeen timestamp and online status from JSON data
                    last_seen = None
                    json_online = None
                    if isinstance(peer_data, dict):
                        for peer_key, peer_info in peer_data.items():
                            if isinstance(peer_info, dict):
                                peer_hostname = peer_info.get('HostName', '')
                                peer_ip = peer_info.get('TailscaleIPs', [None])[0]
                                if peer_hostname == hostname or (peer_ip and peer_ip == ip):
                                    # Found matching peer, get the data
                                    last_seen_raw = peer_info.get('LastSeen')
                                    if last_seen_raw and last_seen_raw != '0001-01-01T00:00:00Z':
                                        last_seen = last_seen_raw
                                    
                                    # Use JSON Online field as primary source of truth
                                    json_online = peer_info.get('Online', None)
                                    break
                    
                    # Also check Self data for current device
                    json_status = TailscaleClient.status_json()
                    if isinstance(json_status, dict) and not json_online:
                        self_info = json_status.get("Self", {})
                        if isinstance(self_info, dict):
                            self_hostname = self_info.get('HostName', '')
                            self_ip = self_info.get('TailscaleIPs', [None])[0]
                            if self_hostname == hostname or (self_ip and self_ip == ip):
                                # This is the current device
                                last_seen_raw = self_info.get('LastSeen')
                                if last_seen_raw and last_seen_raw != '0001-01-01T00:00:00Z':
                                    last_seen = last_seen_raw
                                json_online = True  # Current device is always online
                    
                    # Use JSON online status if available, otherwise fall back to text parsing
                    if json_online is not None:
                        is_online = json_online
                    
                    # Check for exit node status
                    is_exit_node = 'offers exit node' in status
                    is_exit_node_user = 'exit node' in status and 'offers' not in status
                    
                    # Check for subnet router
                    is_subnet_router = 'subnet router' in status
                    
                    # Check for tagged devices
                    is_tagged = 'tagged' in status or '@' in hostname
                    
                    # Check for devices advertising subnet routes
                    is_advertising_subnets = False  # Will be determined from JSON if available
                    
                    # Fallback to text-based determination if no timestamp found
                    if not last_seen:
                        last_seen = "recent" if is_online else "unknown"
                    
                    device = {
                        "id": f"device_{len(devices)}",  # Generate simple ID
                        "hostname": hostname,
                        "ip": ip,
                        "os": os_part,
                        "online": is_online,
                        "status": status,
                        "isExitNode": is_exit_node,
                        "isExitNodeUser": is_exit_node_user,
                        "isSubnetRouter": is_subnet_router,
                        "isTagged": is_tagged,
                        "isAdvertisingSubnets": is_advertising_subnets,
                        "lastSeen": last_seen
                    }
                    
                    devices.append(device)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse device line '{line}': {str(e)}")
                    continue
        
        return devices

    @staticmethod
    def up(authkey=None, extra_args=None):
        tailscale_path = TailscaleClient.get_tailscale_path()
        cmd = [tailscale_path, "up"]
        if authkey:
            # Validate authkey format to prevent injection
            if not isinstance(authkey, str) or not all(c.isalnum() or c in "-_" for c in authkey):
                return "Invalid auth key format"
            cmd += ["--authkey", authkey]
        if extra_args:
            # Validate extra_args - ensure it's a list of safe strings
            if not isinstance(extra_args, list):
                return "Invalid extra_args format - must be a list"
            # Check each arg individually
            for arg in extra_args:
                if not isinstance(arg, str) or not all(c.isalnum() or c in "=,.-_/:@" for c in arg):
                    return f"Invalid argument format: {arg}"
            cmd += extra_args
        try:
            logger.info(f"Running Tailscale command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
            
            if result.returncode == 0:
                if result.stdout:
                    logger.info(f"Tailscale stdout: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Tailscale stderr: {result.stderr}")
                logger.info(f"Tailscale command completed successfully with return code {result.returncode}")
                return True
            else:
                error_msg = f"Command failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f", stderr: {result.stderr}"
                if result.stdout:
                    error_msg += f", stdout: {result.stdout}"
                logger.error(f"Tailscale command failed: {error_msg}")
                return error_msg
        except subprocess.TimeoutExpired:
            logger.error("Tailscale command timed out")
            return "Command timed out"
        except Exception as e:
            logger.error(f"Tailscale command exception: {str(e)}")
            return str(e)

    @staticmethod
    def _set_advertised_routes(routes):
        """Set advertised routes using tailscale set command"""
        tailscale_path = TailscaleClient.get_tailscale_path()
        
        # Build the advertise-routes argument
        if routes:
            routes_str = ",".join(routes)
            cmd = [tailscale_path, "set", "--advertise-routes", routes_str]
        else:
            # Clear advertised routes
            cmd = [tailscale_path, "set", "--advertise-routes", ""]
        
        try:
            logger.info(f"Running Tailscale set command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                if result.stdout:
                    logger.info(f"Tailscale set stdout: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Tailscale set stderr: {result.stderr}")
                logger.info(f"Tailscale set command completed successfully")
                return True
            else:
                error_msg = f"tailscale set failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f", stderr: {result.stderr}"
                if result.stdout:
                    error_msg += f", stdout: {result.stdout}"
                logger.error(f"Tailscale set command failed: {error_msg}")
                return error_msg
        except Exception as e:
            logger.error(f"Tailscale set command exception: {str(e)}")
            return str(e)

    @staticmethod
    def down():
        """Run tailscale down to disconnect from the tailnet"""
        tailscale_path = TailscaleClient.get_tailscale_path()
        cmd = [tailscale_path, "down"]
        try:
            logger.info(f"Running Tailscale command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                if result.stdout:
                    logger.info(f"Tailscale stdout: {result.stdout}")
                return True
            else:
                error_msg = f"Command failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f", stderr: {result.stderr}"
                if result.stdout:
                    error_msg += f", stdout: {result.stdout}"
                logger.error(f"Tailscale down command failed: {error_msg}")
                return error_msg
        except Exception as e:
            logger.error(f"Tailscale down command exception: {str(e)}")
            return str(e)

    @staticmethod
    def set_hostname(hostname: str):
        """Set the hostname for this Tailscale device"""
        if not hostname or not hostname.strip():
            return {"error": "Hostname cannot be empty"}
            
        tailscale_path = TailscaleClient.get_tailscale_path()
        cmd = [tailscale_path, "set", "--hostname", hostname.strip()]
        
        try:
            logger.info(f"Setting Tailscale hostname: {hostname}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                logger.info(f"Hostname set successfully to: {hostname}")
                return {"success": True, "hostname": hostname}
            else:
                error_msg = f"Failed to set hostname (exit code {result.returncode})"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                logger.error(error_msg)
                return {"error": error_msg}
        except Exception as e:
            logger.error(f"Exception setting hostname: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def subnet_routes() -> List[str]:
        """Get all advertised subnet routes for this device"""
        try:
            # Use tailscale status command to get advertised routes
            tailscale_path = TailscaleClient.get_tailscale_path()
            cmd = [tailscale_path, "status", "--json"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
            
            if result.returncode == 0:
                status = json.loads(result.stdout)
                self_obj = safe_get_dict(status, "Self")
                
                # Check if there's an AdvertisedRoutes field
                advertised_routes = self_obj.get("AdvertisedRoutes", [])
                if advertised_routes:
                    # Filter out exit node routes
                    subnet_routes = [route for route in advertised_routes if route not in ("0.0.0.0/0", "::/0")]
                    logger.info(f"Advertised subnet routes from status: {subnet_routes}")
                    return subnet_routes
                
                # Fallback: try to get from AllowedIPs but be more careful
                allowed_ips = self_obj.get("AllowedIPs", [])
                tailscale_ip = None
                for ip in allowed_ips:
                    if ip.endswith("/32") or ip.endswith("/128"):
                        tailscale_ip = ip
                        break
                
                subnet_routes = []
                for ip in allowed_ips:
                    if (ip not in ("0.0.0.0/0", "::/0") and 
                        ip != tailscale_ip and 
                        not (ip.endswith("/32") or ip.endswith("/128"))):
                        subnet_routes.append(ip)
                
                logger.info(f"Advertised subnet routes from AllowedIPs: {subnet_routes}")
                return subnet_routes
            else:
                logger.warning(f"Tailscale status command failed: {result.stderr}")
                return []
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError) as e:
            logger.error(f"Error getting subnet routes: {e}")
            return []
            
    @staticmethod
    def detect_local_subnets() -> List[Dict[str, str]]:
        """Detect all available local subnets on this device, normalized to network address"""
        import ipaddress
        detected_subnets = []
        try:
            # Linux/macOS specific method - will fail on Windows
            if platform.system() != "Windows":
                interfaces_output = subprocess.check_output(
                    ["ip", "-json", "addr"],
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                interfaces = json.loads(interfaces_output)
                for iface in interfaces:
                    if iface.get("link_type") == "loopback":
                        continue  # Skip loopback interface
                    name = iface.get("ifname", "")
                    for addr_info in iface.get("addr_info", []):
                        if addr_info.get("family") == "inet":  # IPv4 only
                            try:
                                ipnet = ipaddress.IPv4Network(f"{addr_info['local']}/{addr_info['prefixlen']}", strict=False)
                                cidr = str(ipnet)
                            except Exception as e:
                                logger.warning(f"Failed to normalize subnet: {e}")
                                cidr = f"{addr_info['local']}/{addr_info['prefixlen']}"
                            detected_subnets.append({
                                "interface": name,
                                "cidr": cidr,
                                "family": "IPv4"
                            })
            else:
                # Enhanced Windows subnet detection
                try:
                    from services.windows_network import WindowsNetworkDetector
                    windows_subnets = WindowsNetworkDetector.detect_local_subnets()
                    # Convert to the expected format
                    for subnet in windows_subnets:
                        detected_subnets.append({
                            "interface": subnet.get("interface", "Unknown"),
                            "cidr": subnet.get("cidr", ""),
                            "family": subnet.get("family", "IPv4")
                        })
                    logger.info(f"Windows subnet detection completed: found {len(detected_subnets)} subnets")
                except ImportError:
                    logger.warning("Windows network detection module not available, falling back to basic detection")
                    logger.info("Local subnet detection not fully supported on Windows")
                except Exception as e:
                    logger.error(f"Windows subnet detection failed: {e}")
                    logger.info("Local subnet detection not fully supported on Windows")
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error detecting local subnets: {str(e)}")
        return detected_subnets

    @staticmethod
    def set_subnet_routes(routes):
        """Set the subnet routes to advertise, always including all non-default flags for robust tailscale up invocation."""
        # Validate routes format
        if not isinstance(routes, list):
            logger.error("Invalid routes parameter: not a list")
            return "Routes must be a list"
        # Basic CIDR validation
        cidr_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$')
        for route in routes:
            if not isinstance(route, str) or not cidr_pattern.match(route):
                logger.error(f"Invalid CIDR format: {route}")
                return f"Invalid CIDR format: {route}"
        # Further validate CIDR syntax with ipaddress module
        try:
            import ipaddress
            for route in routes:
                ipaddress.ip_network(route)
        except ValueError as e:
            logger.error(f"Invalid network address: {str(e)}")
            return f"Invalid network address: {str(e)}"

        # Get current device info for all non-default flags
        status = TailscaleClient.status_json()
        self_obj = safe_get_dict(status, "Self")
        hostname = self_obj.get("HostName") or socket.gethostname()
        accept_routes = self_obj.get("AcceptRoutes", True)
        adv_routes = list(routes)  # Only subnets, not exit node
        adv_exit = True  # Always include --advertise-exit-node for robust compatibility

        args = []
        if hostname:
            args += ["--hostname", str(hostname)]
        if accept_routes:
            args.append("--accept-routes")
        else:
            args.append("--no-accept-routes")
        if adv_routes:
            args += [f"--advertise-routes={','.join(adv_routes)}"]
        if adv_exit:
            args.append("--advertise-exit-node")
        logger.info(f"Setting subnet routes: {adv_routes}")
        
        # Use tailscale set command for advertised routes (this is the correct approach)
        result = TailscaleClient._set_advertised_routes(adv_routes)
        
        # Add a small delay to allow Tailscale to apply the changes
        if result is True:
            import time
            time.sleep(2)  # Wait 2 seconds for changes to take effect
            logger.info(f"Subnet routes applied successfully: {adv_routes}")
            
            # Verify the routes were applied
            updated_routes = TailscaleClient.subnet_routes()
            if set(updated_routes) == set(adv_routes):
                logger.info("Subnet routes verification successful")
            else:
                logger.warning(f"Subnet routes verification failed. Expected: {adv_routes}, Got: {updated_routes}")
        else:
            logger.error(f"Failed to apply subnet routes: {result}")
        
        return result

    @staticmethod
    def set_exit_node(enable=True, settings=None):
        """Enable or disable this device as an exit node, always including all non-default flags for robust tailscale up invocation. Accepts a settings dict."""
        import platform
        if settings is None:
            # Fallback: load from file if not provided
            settings_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'tailscale_settings.json')
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read tailscale_settings.json: {e}")
                settings = {}

        # Enforce defaults for all required settings
        hostname = settings.get("hostname") or platform.node()
        accept_routes = settings.get("accept_routes")
        if accept_routes is None:
            accept_routes = True
        adv_routes = settings.get("advertise_routes")
        if not isinstance(adv_routes, list):
            adv_routes = []

        # Always merge with current status to ensure all non-default flags are present
        status = TailscaleClient.status_json()
        self_obj = safe_get_dict(status, "Self")
        current_adv_routes = self_obj.get("AdvertisedRoutes", [])
        # Always preserve all current subnet routes
        subnet_routes = [r for r in set(adv_routes + [r for r in current_adv_routes if r not in ("0.0.0.0/0", "::/0")])]  # dedup
        # Always preserve exit node advertising if currently enabled or requested
        adv_exit = enable or any(r in current_adv_routes for r in ("0.0.0.0/0", "::/0"))

        args = []
        if hostname:
            args += ["--hostname", str(hostname)]
        if accept_routes:
            args.append("--accept-routes")
        else:
            args.append("--no-accept-routes")
        if subnet_routes:
            args += ["--advertise-routes", ",".join(subnet_routes)]
        # Only add --advertise-exit-node if enabling or currently enabled
        if adv_exit:
            args.append("--advertise-exit-node")
        # If disabling exit node and no subnets, use --reset
        if not enable and not subnet_routes:
            args.append("--reset")
        logger.info(f"{'Enabling' if enable else 'Disabling'} exit node functionality with args: {args}")
        return TailscaleClient.up(extra_args=args)
        
    @staticmethod
    def get_active_exit_node() -> Optional[Dict[str, Any]]:
        """Get information about the currently active exit node"""
        status = TailscaleClient.status_json()
        
        if isinstance(status, dict) and "error" in status:
            logger.warning(f"Error getting exit node info: {status['error']}")
            return None
            
        try:
            # Find which device is currently the active exit node
            for id, peer in safe_get_dict(status, "Peer").items():
                if peer.get("ExitNode", False):
                    return {
                        "id": id,
                        "name": peer.get("HostName", ""),
                        "ip": peer.get("TailscaleIPs", [""])[0],
                        "online": peer.get("Online", False),
                        "last_seen": peer.get("LastSeen", ""),
                        "os": peer.get("OS", ""),
                    }
                    
            # No active exit node found
            return None
        except (AttributeError, TypeError) as e:
            logger.error(f"Error parsing exit node info: {str(e)}")
            return None

    @staticmethod
    def get_exit_node_clients() -> List[Dict[str, Any]]:
        """Get devices that are likely using this device as an exit node"""
        try:
            status = TailscaleClient.status_json()
            
            if isinstance(status, dict) and "error" in status:
                logger.warning(f"Error getting exit node clients: {status['error']}")
                return []
            
            # Check if this device is advertising as an exit node
            self_data = safe_get_dict(status, "Self")
            advertised_routes = self_data.get("AdvertisedRoutes", [])
            
            # Check if we're advertising exit node routes (0.0.0.0/0 or ::/0)
            is_advertising_exit = any(
                route in ["0.0.0.0/0", "::/0"] for route in advertised_routes
            )
            
            if not is_advertising_exit:
                logger.info("This device is not advertising as an exit node")
                return []
            
            exit_node_clients = []
            peers = safe_get_dict(status, "Peer")
            
            # For each peer, determine if they might be using this as exit node
            for peer_id, peer in peers.items():
                if not isinstance(peer, dict):
                    continue
                    
                # Check if peer has recent activity and is online
                is_online = peer.get("Online", False)
                last_seen = peer.get("LastSeen", "")
                
                # If peer is using an exit node, they might be using this one
                # Unfortunately, Tailscale status doesn't directly tell us which specific
                # exit node a peer is using, so we use heuristics
                peer_using_exit = peer.get("ExitNode", False)
                peer_exit_option = peer.get("ExitNodeOption", False)
                
                # Consider a peer as an exit node user if:
                # 1. ExitNode is true (currently using exit node)
                # 2. ExitNodeOption is true (configured to use exit node)
                is_exit_node_user = peer_using_exit or peer_exit_option
                
                # Additional heuristics: recent activity, data transfer
                has_recent_activity = (
                    is_online or 
                    (last_seen and last_seen != "0001-01-01T00:00:00Z")
                )
                
                tx_bytes = peer.get("TxBytes", 0)
                rx_bytes = peer.get("RxBytes", 0)
                has_data_transfer = tx_bytes > 0 or rx_bytes > 0
                
                # Only include peers that are configured to use exit nodes
                if is_exit_node_user:
                    client_info = {
                        "id": peer.get("ID", peer_id),  # Use the peer's ID field, fallback to dict key
                        "hostname": peer.get("HostName", "Unknown"),
                        "ip": peer.get("TailscaleIPs", [""])[0] if peer.get("TailscaleIPs") else "",
                        "online": is_online,
                        "last_seen": last_seen,
                        "os": peer.get("OS", ""),
                        "tx_bytes": tx_bytes,
                        "rx_bytes": rx_bytes,
                        "is_exit_node_user": is_exit_node_user,
                        "confidence": "high" if peer_using_exit else "medium"
                    }
                    exit_node_clients.append(client_info)
            
            logger.info(f"Found {len(exit_node_clients)} potential exit node clients")
            return exit_node_clients
            
        except Exception as e:
            logger.error(f"Error getting exit node clients: {str(e)}")
            return []

    @staticmethod
    def service_control(action):
        """Control the tailscaled service: start/stop/restart/status/down"""
        # Validate action to prevent command injection
        allowed_actions = ["start", "stop", "restart", "status", "down"]
        if action not in allowed_actions:
            logger.error(f"Invalid service action: {action}")
            return f"Invalid action: {action}. Must be one of {allowed_actions}"
            
        # Handle special case for "down" action - this should run "tailscale down"
        if action == "down":
            return TailscaleClient.down()
            
        logger.info(f"Performing service {action} on tailscaled")
        
        try:
            system = platform.system()
            
            if system == "Windows":
                # Try multiple approaches for Windows
                return TailscaleClient._windows_service_control(action)
            else:
                # Linux/macOS - try systemctl first, then service command
                return TailscaleClient._linux_service_control(action)
                
        except Exception as e:
            logger.exception(f"Error controlling service: {str(e)}")
            return str(e)

    @staticmethod
    def _windows_service_control(action):
        """Handle Windows service control with multiple fallback methods"""
        try:
            # Method 1: Try Windows Service Control Manager (SCM)
            service_names = ["Tailscale", "tailscaled", "Tailscale Service"]
            
            for service_name in service_names:
                try:
                    if action == "status":
                        cmd = ["sc", "query", service_name]
                    else:
                        cmd = ["sc", action, service_name]
                    
                    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=10)
                    logger.info(f"Windows service control successful using service: {service_name}")
                    return output.decode('utf-8', errors='replace')
                except subprocess.CalledProcessError:
                    continue  # Try next service name
            
            # Method 2: If service control fails, try direct tailscale commands
            logger.info("Service control failed, trying direct tailscale commands")
            if action == "status":
                # For status, try to get tailscale status
                tailscale_path = TailscaleClient.get_tailscale_path()
                if tailscale_path:
                    cmd = [tailscale_path, "status", "--json"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        return "Tailscale service appears to be running (status check successful)"
                    else:
                        return "Tailscale service status unknown or not running"
                else:
                    return "Could not find tailscale binary"
            elif action in ["start", "stop"]:
                # For start/stop, inform user that manual intervention may be needed
                return f"Service {action} requires manual intervention. Tailscale may not be installed as a Windows service. Try running Tailscale from the system tray."
            else:
                return f"Unsupported action for Windows: {action}"
                
        except subprocess.TimeoutExpired:
            logger.error("Windows service control command timed out")
            return "Command timed out after 10 seconds"
        except Exception as e:
            logger.exception(f"Error in Windows service control: {str(e)}")
            return f"Windows service control error: {str(e)}"

    @staticmethod
    def _linux_service_control(action):
        """Handle Linux service control with multiple fallback methods"""
        try:
            # Method 1: Try systemctl (modern systems)
            try:
                if action == "status":
                    cmd = ["systemctl", "status", "tailscaled", "--no-pager", "--lines=10"]
                else:
                    cmd = ["systemctl", action, "tailscaled"]
                
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=15)
                logger.info("Linux service control successful using systemctl")
                return output.decode('utf-8', errors='replace')
            except subprocess.CalledProcessError as e:
                logger.warning(f"systemctl failed: {e}")
                
                # Method 2: Try systemctl with sudo
                try:
                    if action == "status":
                        cmd = ["sudo", "systemctl", "status", "tailscaled", "--no-pager", "--lines=10"]
                    else:
                        cmd = ["sudo", "systemctl", action, "tailscaled"]
                    
                    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=15)
                    logger.info("Linux service control successful using sudo systemctl")
                    return output.decode('utf-8', errors='replace')
                except subprocess.CalledProcessError:
                    logger.warning("sudo systemctl also failed")
                
                # Method 3: Try service command (older systems)
                try:
                    cmd = ["service", "tailscaled", action]
                    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=15)
                    logger.info("Linux service control successful using service command")
                    return output.decode('utf-8', errors='replace')
                except subprocess.CalledProcessError as e2:
                    logger.warning(f"service command also failed: {e2}")
                    
                    # Method 4: Try service command with sudo
                    try:
                        cmd = ["sudo", "service", "tailscaled", action]
                        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=15)
                        logger.info("Linux service control successful using sudo service")
                        return output.decode('utf-8', errors='replace')
                    except subprocess.CalledProcessError:
                        logger.warning("sudo service also failed")
                    
                    # Method 5: Try direct process management
                    return TailscaleClient._linux_process_control(action)
                    
        except subprocess.TimeoutExpired:
            logger.error("Linux service control command timed out")
            return "Command timed out after 15 seconds"
        except Exception as e:
            logger.exception(f"Error in Linux service control: {str(e)}")
            return f"Linux service control error: {str(e)}"

    @staticmethod
    def _linux_process_control(action):
        """Handle Linux process control when service managers fail"""
        try:
            if action == "status":
                # Check if tailscaled process is running
                result = subprocess.run(["pgrep", "-f", "tailscaled"], capture_output=True, text=True)
                if result.returncode == 0:
                    return "Tailscale daemon is running (process found)"
                else:
                    return "Tailscale daemon is not running (no process found)"
                    
            elif action == "stop":
                # Try to kill tailscaled processes gracefully
                result = subprocess.run(["pkill", "-TERM", "tailscaled"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return "Tailscale daemon stopped (process terminated)"
                else:
                    return "Failed to stop Tailscale daemon (no process found or permission denied)"
                    
            elif action == "start":
                # Try to start tailscaled directly
                tailscale_path = TailscaleClient.get_tailscale_path()
                if tailscale_path:
                    cmd = [tailscale_path.replace("tailscale", "tailscaled")]
                    # Note: This might require root privileges
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        return "Tailscale daemon started successfully"
                    else:
                        return f"Failed to start Tailscale daemon directly: {result.stderr}"
                else:
                    return "Could not find tailscale binary path"
            else:
                return f"Unsupported process control action: {action}"
                
        except subprocess.TimeoutExpired:
            return "Process control command timed out"
        except Exception as e:
            logger.exception(f"Error in Linux process control: {str(e)}")
            return f"Process control error: {str(e)}"

    @staticmethod
    def logs(lines=100):
        try:
            # Validate lines parameter
            try:
                lines_int = int(lines)
                if lines_int <= 0 or lines_int > 1000:  # Set a reasonable upper limit
                    return "Lines parameter must be between 1 and 1000"
            except ValueError:
                return "Lines parameter must be an integer"
            
            if platform.system() == "Windows":
                # On Windows, use PowerShell to get logs from event viewer
                cmd = ["powershell.exe", "Get-WinEvent", "-FilterHashtable", 
                       "@{ProviderName='Tailscale'; LogName='Application'}", "-MaxEvents", str(lines_int)]
                try:
                    out = subprocess.check_output(cmd, stderr=subprocess.PIPE)
                    return out.decode('utf-8', errors='replace')
                except subprocess.CalledProcessError as e:
                    # If no events are found, return an informative message instead of error
                    if "No events were found" in e.stderr.decode('utf-8', errors='replace'):
                        return "No Tailscale events found in the Windows Event Log"
                    raise
            else:
                # Linux/macOS use journalctl
                out = subprocess.check_output(["journalctl", "-u", "tailscaled", "-n", str(lines_int)])
                return out.decode('utf-8', errors='replace')
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
            logger.error(f"Getting logs failed: {error_msg}")
            return f"Failed to get logs: {error_msg}"
        except Exception as e:
            logger.exception(f"Error getting logs: {str(e)}")
            return f"Error retrieving logs: {str(e)}"
    
    @staticmethod
    def get_network_metrics():
        """Get current network metrics from Tailscale status"""
        try:
            status = TailscaleClient.status_json()
            if isinstance(status, dict) and "error" in status:
                logger.warning(f"Error getting network metrics: {status['error']}")
                return {"error": status["error"]}
            metrics = {}
            self_data = safe_get_dict(status, "Self")
            metrics["tx_bytes"] = self_data.get("TXBytes", 0)
            metrics["rx_bytes"] = self_data.get("RXBytes", 0)
            peers_data = safe_get_dict(status, "Peer")
            peers_metrics = []
            total_tx = 0
            total_rx = 0
            active_peers = 0
            for peer_id, peer in peers_data.items():
                if isinstance(peer, dict):
                    tx = peer.get("TXBytes", 0)
                    rx = peer.get("RXBytes", 0)
                    peers_metrics.append({
                        "id": peer_id,
                        "hostname": peer.get("HostName", "Unknown"),
                        "tx_bytes": tx,
                        "rx_bytes": rx,
                        "last_seen": peer.get("LastSeen", ""),
                        "online": peer.get("Online", False)
                    })
                    total_tx += tx
                    total_rx += rx
                    if peer.get("Online", False):
                        active_peers += 1
            metrics["peers"] = peers_metrics
            metrics["total_peer_tx"] = total_tx
            metrics["total_peer_rx"] = total_rx
            metrics["active_peers"] = active_peers
            metrics["total_peers"] = len(peers_metrics)
            metrics["timestamp"] = int(time.time())
            return metrics
        except Exception as e:
            logger.exception(f"Error getting network metrics: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def analyze_bandwidth_usage(days=7):
        """Analyze bandwidth usage over time"""
        try:
            # Get historical metrics
            history = TailscaleMetrics.get_metrics_history(hours=days*24)
            
            if "error" in history:
                return history
                
            datapoints = history.get("datapoints", [])
            if not datapoints:
                return {"message": "No historical data available for analysis"}
                
            # Initialize analysis result
            result = {
                "period_start": datapoints[0]["timestamp"],
                "period_end": datapoints[-1]["timestamp"] if datapoints else int(time.time()),
                "total_days": days,
                "tx_bytes_total": 0,
                "rx_bytes_total": 0,
                "avg_tx_per_day": 0,
                "avg_rx_per_day": 0,
                "peak_usage_day": None,
                "peak_usage_bytes": 0,
                "daily_summary": [],
                "active_peer_summary": []
            }
            
            # Group data by day for daily analysis
            daily_data = {}
            
            for dp in datapoints:
                metrics = dp.get("metrics", {})
                timestamp = dp["timestamp"]
                day_key = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                
                if day_key not in daily_data:
                    daily_data[day_key] = {
                        "day": day_key,
                        "points": [],
                        "tx_start": None,
                        "rx_start": None,
                        "tx_end": None,
                        "rx_end": None,
                        "tx_diff": 0,
                        "rx_diff": 0
                    }
                
                # Store the datapoint
                daily_data[day_key]["points"].append({
                    "timestamp": timestamp,
                    "tx": metrics.get("tx_bytes", 0),
                    "rx": metrics.get("rx_bytes", 0)
                })
            
            # Calculate metrics for each day
            for day, data in daily_data.items():
                if not data["points"]:
                    continue
                    
                # Sort points by timestamp
                data["points"].sort(key=lambda x: x["timestamp"])
                
                # Set start and end values
                data["tx_start"] = data["points"][0]["tx"]
                data["rx_start"] = data["points"][0]["rx"]
                data["tx_end"] = data["points"][-1]["tx"]
                data["rx_end"] = data["points"][-1]["rx"]
                
                # Calculate differences
                data["tx_diff"] = data["tx_end"] - data["tx_start"]
                data["rx_diff"] = data["rx_end"] - data["rx_start"]
                
                # Add to totals
                result["tx_bytes_total"] += data["tx_diff"]
                result["rx_bytes_total"] += data["rx_diff"]
                
                # Track peak usage day
                day_total = data["tx_diff"] + data["rx_diff"]
                if day_total > result["peak_usage_bytes"]:
                    result["peak_usage_bytes"] = day_total
                    result["peak_usage_day"] = day
                    
                # Add to daily summary
                result["daily_summary"].append({
                    "day": day,
                    "tx_bytes": data["tx_diff"],
                    "rx_bytes": data["rx_diff"],
                    "total_bytes": day_total
                })
                
            # Calculate averages
            if days > 0:
                result["avg_tx_per_day"] = result["tx_bytes_total"] / days
                result["avg_rx_per_day"] = result["rx_bytes_total"] / days
            
            # Sort daily summary by date
            result["daily_summary"].sort(key=lambda x: x["day"])
            
            return result
        except Exception as e:
            logger.exception(f"Error analyzing bandwidth usage: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def identify_top_consumers(days=7, top_n=5):
        """Identify top bandwidth consumers in the network"""
        try:
            # Get current status to have the latest peer information
            status = TailscaleClient.status_json()
            peers = status.get("Peer", {})
            
            # Get historical metrics to analyze usage patterns
            metrics_history = TailscaleMetrics.get_metrics_history(hours=days*24)
            if not metrics_history or not metrics_history.get("datapoints"):
                return {"error": "No historical metrics available"}
                
            # Create peer lookup dict for quick access
            peer_stats = {}
            
            # Initialize each peer we know about
            if not isinstance(peers, dict):
                peers = {}
            for peer_id, peer_data in peers.items():
                if not isinstance(peer_data, dict):
                    continue
                peer_stats[peer_id] = {
                    "id": peer_id,
                    "hostname": peer_data.get("HostName", "Unknown"),
                    "tx_bytes": 0,  # Data sent to this peer
                    "rx_bytes": 0,  # Data received from this peer
                    "last_seen": peer_data.get("LastSeen", ""),
                    "online": peer_data.get("Online", False)
                }
            
            # We would need to analyze individual peer metrics over time
            # This would require more detailed metrics collection than we currently have
            # For now, we'll just return the current peer bandwidth stats
            
            # Sort peers by total bandwidth (tx + rx)
            peers_by_bandwidth = sorted(
                peer_stats.values(), 
                key=lambda p: p["tx_bytes"] + p["rx_bytes"],
                reverse=True
            )
            
            # Return top N consumers
            return {
                "top_consumers": peers_by_bandwidth[:top_n],
                "analysis_period_days": days,
                "total_peers_analyzed": len(peer_stats)
            }
        except Exception as e:
            logger.exception(f"Error identifying top consumers: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def service_status():
        try:
            out = subprocess.check_output(["systemctl", "status", "tailscaled"])
            return out.decode()
        except Exception as e:
            return str(e)

    @staticmethod
    def get_hostname():
        # Use platform-independent way to get hostname
        import socket
        return socket.gethostname()

    @staticmethod
    def get_ip():
        """Get the primary Tailscale IP of this device"""
        status = TailscaleClient.status_json()
        # Handle potential error response
        if isinstance(status, dict) and "error" in status:
            logger.warning(f"Error getting Tailscale IP: {status['error']}")
            return "Not available"
        
        try:
            self_obj = safe_get_dict(status, "Self")
            if not isinstance(self_obj, dict):
                self_obj = {}
            return self_obj.get("TailscaleIPs", [None])[0] or "Not available"
        except (KeyError, IndexError, TypeError, AttributeError):
            logger.warning("Failed to extract Tailscale IP from status")
            return "Not available"
            
    @staticmethod
    def get_device_info() -> Dict[str, Any]:
        """Get comprehensive information about this device"""
        status = TailscaleClient.status_json()
        if isinstance(status, dict) and "error" in status:
            return {"error": status["error"]}

        result = {
            "hostname": TailscaleClient.get_hostname(),
            "os": platform.system(),
            "version": platform.version(),
            "tailscale": {}
        }

        try:
            self_info = status.get("Self", {}) if isinstance(status, dict) else {}
            # If Self is a list, use the first element
            if isinstance(self_info, list) and self_info:
                self_info = self_info[0]
            if not isinstance(self_info, dict):
                self_info = {}
            capabilities = self_info.get("Capabilities", {}) if isinstance(self_info, dict) else {}
            if not isinstance(capabilities, dict):
                capabilities = {}
            result["tailscale"] = {
                "id": self_info.get("ID", ""),
                "name": self_info.get("HostName", ""),
                "ip": self_info.get("TailscaleIPs", [""])[0],
                "is_exit_node": capabilities.get("ExitNode", False),
                "is_subnet_router": capabilities.get("SubnetRouter", False),
                "advertised_routes": self_info.get("AdvertisedRoutes", []),
                "tx_bytes": self_info.get("TXBytes", 0),
                "rx_bytes": self_info.get("RXBytes", 0),
                "version": self_info.get("ClientVersion", ""),
                "last_seen": self_info.get("LastSeen", ""),
                "online": self_info.get("Online", False),
            }
        except (TypeError, AttributeError, IndexError) as e:
            logger.error(f"Error parsing device info: {str(e)}")
            result["error"] = f"Failed to parse device information: {str(e)}"

        return result

    # --- Tailscale API ---
    @staticmethod
    def _api_request(method: str, endpoint: str, data: Optional[Dict] = None, 
                    params: Optional[Dict] = None) -> Dict:
        """Base method for Tailscale API requests"""
        if not TAILSCALE_API_KEY:
            logger.error("Tailscale API request failed: No API Key set")
            return {"error": "No Tailscale API Key set. Please add to .env file."}
            
        base_url = "https://api.tailscale.com/api/v2"
        # Replace '-' with actual tailnet if specified
        endpoint = endpoint.replace("TAILNET", TAILNET)
        url = f"{base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {TAILSCALE_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            if method.lower() == 'get':
                response = httpx.get(url, headers=headers, params=params, timeout=10)
            elif method.lower() == 'post':
                response = httpx.post(url, headers=headers, json=data, timeout=10)
            elif method.lower() == 'delete':
                response = httpx.delete(url, headers=headers, timeout=10)
            elif method.lower() == 'put':
                response = httpx.put(url, headers=headers, json=data, timeout=10)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}
                
            # Check for error status codes
            if response.status_code >= 400:
                logger.error(f"Tailscale API error: {response.status_code} - {response.text}")
                error_msg = f"API error {response.status_code}"
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg = f"{error_msg}: {error_data['message']}"
                except:
                    error_msg = f"{error_msg}: {response.text[:100]}"
                return {"error": error_msg, "status_code": response.status_code}
                
            # Handle 204 No Content responses (typically from DELETE)
            if response.status_code == 204:
                return {"success": True}
                
            # Parse JSON response for all other successful responses
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"Tailscale API network error: {str(e)}")
            return {"error": f"Network error: {str(e)}"}
        except json.JSONDecodeError as e:
            logger.error(f"Tailscale API returned invalid JSON: {str(e)}")
            return {"error": f"Invalid response format: {str(e)}"}
        except Exception as e:
            logger.exception("Unexpected error in Tailscale API request")
            return {"error": f"Unexpected error: {str(e)}"}

    @staticmethod
    def api_list_keys():
        """List all auth keys for the tailnet"""
        return TailscaleClient._api_request('get', '/tailnet/TAILNET/keys')

    @staticmethod
    def api_create_key(expiry, reusable, ephemeral, description):
        """Create a new auth key"""
        data = {
            "capabilities": {
                "devices": {
                    "create": {
                        "reusable": bool(reusable),
                        "ephemeral": bool(ephemeral),
                        "tags": [],  # Optional: Add default tags here
                        "preauthorized": True
                    }
                }
            },
            "expirySeconds": int(expiry),
            "description": description
        }
        
        return TailscaleClient._api_request('post', '/tailnet/TAILNET/keys', data=data)

    @staticmethod
    def api_revoke_key(key_id):
        """Revoke an auth key by its ID"""
        if not key_id or not isinstance(key_id, str):
            return {"error": "Invalid key ID"}
            
        # Validate key ID format - typically a UUID format but being extra cautious
        if not re.match(r'^[a-zA-Z0-9\-_]+$', key_id):
            return {"error": "Invalid key ID format"}
            
        result = TailscaleClient._api_request('delete', f'/tailnet/TAILNET/keys/{key_id}')
        # Convert to boolean result for backward compatibility
        return result.get("success", False) if "success" in result else False
        
    @staticmethod
    def api_list_devices():
        """List all devices in the tailnet"""
        return TailscaleClient._api_request('get', '/tailnet/TAILNET/devices')
        
    @staticmethod
    def api_get_device(device_id):
        """Get a specific device by ID"""
        if not device_id or not isinstance(device_id, str):
            return {"error": "Invalid device ID"}
            
        return TailscaleClient._api_request('get', f'/tailnet/TAILNET/devices/{device_id}')

    @staticmethod
    def check_tailsentry_instances(devices, force_refresh=False):
        """Check which devices are running TailSentry by pinging their health endpoints"""
        import asyncio
        import aiohttp
        
        # Check cache first (unless force refresh is requested)
        cache_time = 300  # 5 minutes cache
        if not force_refresh and hasattr(TailscaleClient, '_tailsentry_cache'):
            cache_data, cache_timestamp = TailscaleClient._tailsentry_cache
            if time.time() - cache_timestamp < cache_time:
                # Return cached data but update with current device list
                cached_devices = {d.get('id', d.get('ip', '')): d for d in cache_data}
                updated_devices = []
                for device in devices:
                    device_id = device.get('id', device.get('ip', ''))
                    if device_id in cached_devices:
                        # Use cached TailSentry info but update device data
                        cached_device = cached_devices[device_id]
                        updated_device = {**device}
                        updated_device['isTailsentry'] = cached_device.get('isTailsentry', False)
                        updated_device['tailsentry_status'] = cached_device.get('tailsentry_status', 'unknown')
                        if 'tailsentry_info' in cached_device:
                            updated_device['tailsentry_info'] = cached_device['tailsentry_info']
                        updated_devices.append(updated_device)
                    else:
                        # New device, mark as not checked yet
                        updated_device = {**device, 'isTailsentry': False, 'tailsentry_status': 'not_checked'}
                        updated_devices.append(updated_device)
                return updated_devices
        
        async def check_device(device):
            """Check if a single device is running TailSentry"""
            try:
                ip = device.get("ip", "").strip()
                if not ip:
                    return {**device, "isTailsentry": False, "tailsentry_status": "no_ip"}
                
                # Special handling for current device - use localhost
                hostname = device.get("hostname", "").lower()
                current_hostname = socket.gethostname().lower()
                
                # Get current device IP for comparison
                status = TailscaleClient.status_json()
                current_ip = None
                if isinstance(status, dict) and "Self" in status:
                    self_info = status["Self"]
                    if isinstance(self_info, dict):
                        current_ip = self_info.get("TailscaleIPs", [None])[0]
                
                if hostname == current_hostname or ip == current_ip:
                    # This is the current device, use localhost
                    url = "http://localhost:8080/api/health"
                else:
                    # Remote device, use Tailscale IP
                    url = f"http://{ip}:8080/api/health"
                
                timeout = aiohttp.ClientTimeout(total=3)  # Reduced timeout to 3 seconds
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            return {
                                **device,
                                "isTailsentry": True,
                                "tailsentry_status": "healthy",
                                "tailsentry_info": health_data
                            }
                        else:
                            return {**device, "isTailsentry": False, "tailsentry_status": f"http_{response.status}"}
                            
            except asyncio.TimeoutError:
                return {**device, "isTailsentry": False, "tailsentry_status": "timeout"}
            except aiohttp.ClientError as e:
                return {**device, "isTailsentry": False, "tailsentry_status": f"connection_error"}
            except Exception as e:
                logger.warning(f"Error checking TailSentry status for {device.get('hostname', 'unknown')}: {str(e)}")
                return {**device, "isTailsentry": False, "tailsentry_status": "error"}
        
        async def check_all_devices():
            """Check all devices concurrently"""
            # Only check online devices to improve performance
            online_devices = [d for d in devices if d.get('online', False)]
            
            if not online_devices:
                # No online devices, return all as offline
                return [{**device, "isTailsentry": False, "tailsentry_status": "offline"} for device in devices]
            
            tasks = [check_device(device) for device in online_devices]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions that occurred
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Exception checking device {online_devices[i].get('hostname', 'unknown')}: {str(result)}")
                    processed_results.append({
                        **online_devices[i],
                        "isTailsentry": False,
                        "tailsentry_status": "check_failed"
                    })
                else:
                    processed_results.append(result)
            
            # Add offline devices
            offline_devices = [d for d in devices if not d.get('online', False)]
            for device in offline_devices:
                processed_results.append({**device, "isTailsentry": False, "tailsentry_status": "offline"})
            
            return processed_results
        
        # Run the async check - handle existing event loop properly
        try:
            # Check if we're in an existing event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in a running loop, create a task for this
                import concurrent.futures
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(check_all_devices())
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    result = future.result(timeout=15)  # 15 second timeout
                    
                    # Cache the result
                    TailscaleClient._tailsentry_cache = (result, time.time())
                    
                    return result
                    
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                result = asyncio.run(check_all_devices())
                
                # Cache the result
                TailscaleClient._tailsentry_cache = (result, time.time())
                
                return result
                
        except Exception as e:
            logger.error(f"Error in TailSentry instance checking: {str(e)}")
            # Return devices with default status if checking fails
            return [{**device, "isTailsentry": False, "tailsentry_status": "check_error"} for device in devices]

    @staticmethod
    def clear_tailsentry_cache():
        """Clear the TailSentry instance cache"""
        if hasattr(TailscaleClient, '_tailsentry_cache'):
            delattr(TailscaleClient, '_tailsentry_cache')
            logger.info("TailSentry instance cache cleared")


class NetworkViz:
    """Helper class for network visualization"""
    
    @staticmethod
    def format_metrics_for_chart(metrics_history, chart_type="line"):
        """Format metrics history for various chart types"""
        try:
            if not metrics_history or "datapoints" not in metrics_history:
                return {"error": "No metrics data available"}
                
            datapoints = metrics_history.get("datapoints", [])
            if not datapoints:
                return {"labels": [], "datasets": []}
                
            # Sort datapoints by timestamp
            datapoints.sort(key=lambda x: x.get("timestamp", 0))
            
            # Format for chart.js
            if chart_type == "line":
                # Line chart for time series data
                labels = []
                tx_data = []
                rx_data = []
                
                for dp in datapoints:
                    # Format timestamp as readable date/time
                    ts = datetime.fromtimestamp(dp.get("timestamp", 0))
                    labels.append(ts.strftime("%Y-%m-%d %H:%M"))
                    
                    metrics = dp.get("metrics", {})
                    tx_data.append(metrics.get("tx_bytes", 0) / 1024 / 1024)  # Convert to MB
                    rx_data.append(metrics.get("rx_bytes", 0) / 1024 / 1024)  # Convert to MB
                
                return {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Sent (MB)",
                            "data": tx_data,
                            "borderColor": "#3e95cd",
                            "fill": False
                        },
                        {
                            "label": "Received (MB)",
                            "data": rx_data,
                            "borderColor": "#8e5ea2",
                            "fill": False
                        }
                    ]
                }
            elif chart_type == "bar":
                # Group by day for bar chart
                daily_data = {}
                
                for dp in datapoints:
                    metrics = dp.get("metrics", {})
                    timestamp = dp.get("timestamp", 0)
                    day_key = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                    
                    if day_key not in daily_data:
                        daily_data[day_key] = {
                            "tx_bytes": 0,
                            "rx_bytes": 0,
                            "datapoints": 0
                        }
                        
                    # Accumulate data
                    daily_data[day_key]["tx_bytes"] += metrics.get("tx_bytes", 0)
                    daily_data[day_key]["rx_bytes"] += metrics.get("rx_bytes", 0)
                    daily_data[day_key]["datapoints"] += 1
                
                # Sort days
                days = sorted(daily_data.keys())
                
                # Calculate daily averages
                tx_data = []
                rx_data = []
                
                for day in days:
                    day_metrics = daily_data[day]
                    if day_metrics["datapoints"] > 0:
                        # Convert to MB and take average for the day
                        tx_mb = day_metrics["tx_bytes"] / 1024 / 1024
                        rx_mb = day_metrics["rx_bytes"] / 1024 / 1024
                        tx_data.append(tx_mb)
                        rx_data.append(rx_mb)
                
                return {
                    "labels": days,
                    "datasets": [
                        {
                            "label": "Sent (MB)",
                            "data": tx_data,
                            "backgroundColor": "#3e95cd"
                        },
                        {
                            "label": "Received (MB)",
                            "data": rx_data,
                            "backgroundColor": "#8e5ea2"
                        }
                    ]
                }
            elif chart_type == "network_graph":
                # Create network visualization data (nodes and edges)
                # First get latest status
                status = TailscaleClient.status_json()
                
                if isinstance(status, dict) and "error" in status:
                    return {"error": status["error"]}
                    
                # Create nodes
                nodes = []
                edges = []
                
                # Add self node
                self_node = safe_get_dict(status, "Self")
                if not isinstance(self_node, dict):
                    self_node = {}
                if self_node:
                    nodes.append({
                        "id": "self",
                        "label": self_node.get("HostName", "This Device"),
                        "group": "self",
                        "shape": "dot",
                        "size": 15
                    })
                    
                # Add peer nodes
                peers = safe_get_dict(status, "Peer")
                for peer_id, peer in peers.items():
                    if not isinstance(peer, dict):
                        continue
                    # Determine node group
                    group = "offline"
                    if peer.get("Online", False):
                        if peer.get("ExitNode", False):
                            group = "exit_node"
                        elif peer.get("Capabilities", {}).get("SubnetRouter", False):
                            group = "subnet_router"
                        else:
                            group = "online"
                    nodes.append({
                        "id": peer_id,
                        "label": peer.get("HostName", "Unknown"),
                        "group": group,
                        "title": f"IP: {peer.get('TailscaleIPs', [''])[0]}"
                    })
                    
                    # Add edge from self to this peer
                    edges.append({
                        "from": "self",
                        "to": peer_id,
                        "width": 2,
                        "length": 200
                    })
                
                return {
                    "nodes": nodes,
                    "edges": edges
                }
            
            # Default case - return raw data
            return {"datapoints": datapoints}
        except Exception as e:
            logger.exception(f"Error formatting metrics for chart: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def generate_network_topology():
        """Generate a network topology visualization"""
        # Get network status
        status = TailscaleClient.status_json()
        
        # Handle error case
        if isinstance(status, dict) and "error" in status:
            return {"error": status["error"]}
        
        try:
            # Initialize topology data
            topology = {
                "self": {},
                "exit_nodes": [],
                "subnet_routers": [],
                "peers": [],
                "routes": {},
                "connections": []
            }
            
            # Extract self information
            self_info = safe_get_dict(status, "Self")
            if self_info:
                topology["self"] = {
                    "id": self_info.get("ID", ""),
                    "name": self_info.get("HostName", ""),
                    "ip": self_info.get("TailscaleIPs", [""])[0],
                    "is_exit_node": self_info.get("Capabilities", {}).get("ExitNode", False),
                    "is_subnet_router": self_info.get("Capabilities", {}).get("SubnetRouter", False),
                    "advertised_routes": self_info.get("AdvertisedRoutes", [])
                }
                # Add self routes if it's a subnet router
                if topology["self"]["is_subnet_router"]:
                    topology["routes"][topology["self"]["name"]] = topology["self"]["advertised_routes"]
            # Extract peer information
            peers = safe_get_dict(status, "Peer")
            for peer_id, peer in peers.items():
                if not isinstance(peer, dict):
                    continue
                    
                peer_info = {
                    "id": peer_id,
                    "name": peer.get("HostName", "Unknown"),
                    "ip": peer.get("TailscaleIPs", [""])[0] if peer.get("TailscaleIPs") else "",
                    "is_exit_node": peer.get("ExitNode", False),
                    "is_subnet_router": peer.get("Capabilities", {}).get("SubnetRouter", False),
                    "advertised_routes": peer.get("AdvertisedRoutes", []),
                    "online": peer.get("Online", False)
                }
                
                # Check if device is advertising approved subnet routes
                advertised_routes = peer_info["advertised_routes"]
                peer_info["is_advertising_subnets"] = bool(advertised_routes and 
                    any(route not in ('0.0.0.0/0', '::/0') for route in advertised_routes))
                
                # Add to appropriate category
                if peer_info["is_exit_node"]:
                    topology["exit_nodes"].append(peer_info)
                elif peer_info["is_subnet_router"]:
                    topology["subnet_routers"].append(peer_info)
                    # Add routes for this subnet router
                    if peer_info["advertised_routes"]:
                        topology["routes"][peer_info["name"]] = peer_info["advertised_routes"]
                else:
                    topology["peers"].append(peer_info)
                    
                # Add connection to self
                topology["connections"].append({
                    "from": "self",
                    "to": peer_id,
                    "active": peer_info["online"]
                })
            
            return topology
        except Exception as e:
            logger.exception(f"Error generating network topology: {str(e)}")
            return {"error": str(e)}
