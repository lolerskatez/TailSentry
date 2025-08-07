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
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Union, Optional, Tuple, Set
from functools import lru_cache, wraps
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger("tailsentry.tailscale")

load_dotenv()

# Configuration from environment
TAILSCALE_PAT = os.getenv("TAILSCALE_PAT")
TAILNET = os.getenv("TAILSCALE_TAILNET", "-")  # Default to "-" for personal tailnet
API_TIMEOUT = int(os.getenv("TAILSCALE_API_TIMEOUT", "10"))  # API timeout in seconds
DATA_DIR = os.getenv("TAILSENTRY_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Constants
DEFAULT_STATUS_CACHE_SECONDS = 5
METRICS_HISTORY_FILE = os.path.join(DATA_DIR, "metrics_history.json")
ACL_POLICY_FILE = os.path.join(DATA_DIR, "policy.json")
ACL_BACKUP_DIR = os.path.join(DATA_DIR, "acl_backups")

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
    # Cache status result for 5 seconds to prevent hammering the CLI
    @staticmethod
    @lru_cache(maxsize=1)
    def _status_json_cached():
        """Internal cached version of status_json with 5-second TTL"""
        # Add timestamp to control cache invalidation
        timestamp = int(time.time() / DEFAULT_STATUS_CACHE_SECONDS)  # Changes every N seconds
        try:
            out = subprocess.check_output(["tailscale", "status", "--json"], 
                                         stderr=subprocess.PIPE, timeout=10)
            # Properly handle the output as bytes
            data = json.loads(out.decode('utf-8'))
            
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
        result, _ = TailscaleClient._status_json_cached()
        return result

    @staticmethod
    def up(authkey=None, extra_args=None):
        cmd = ["tailscale", "up"]
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
            subprocess.check_call(cmd)
            return True
        except Exception as e:
            return str(e)

    @staticmethod
    def subnet_routes() -> List[str]:
        """Get all advertised subnet routes for this device"""
        status = TailscaleClient.status_json()
        # Handle potential error response
        if isinstance(status, dict) and "error" in status:
            logger.warning(f"Error getting subnet routes: {status['error']}")
            return []
        
        try:
            return status.get("Self", {}).get("AdvertisedRoutes", [])
        except (AttributeError, TypeError):
            logger.error("Failed to parse subnet routes from status")
            return []
            
    @staticmethod
    def detect_local_subnets() -> List[Dict[str, str]]:
        """Detect all available local subnets on this device"""
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
                            cidr = f"{addr_info['local']}/{addr_info['prefixlen']}"
                            detected_subnets.append({
                                "interface": name,
                                "cidr": cidr,
                                "family": "IPv4"
                            })
            else:
                # Basic Windows support - will miss some subnets but provides basic functionality
                # Use 'ipconfig' output parsing or WMI in a more comprehensive implementation
                logger.info("Local subnet detection not fully supported on Windows")
                
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error detecting local subnets: {str(e)}")
            
        return detected_subnets

    @staticmethod
    def set_subnet_routes(routes):
        """Set the subnet routes to advertise"""
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
                
        args = ["--advertise-routes", ",".join(routes)]
        logger.info(f"Setting subnet routes: {routes}")
        return TailscaleClient.up(extra_args=args)

    @staticmethod
    def set_exit_node(enable=True):
        """Enable or disable this device as an exit node"""
        args = ["--advertise-exit-node"] if enable else ["--reset"]
        logger.info(f"{'Enabling' if enable else 'Disabling'} exit node functionality")
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
            for id, peer in status.get("Peer", {}).items():
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
    def service_control(action):
        """Control the tailscaled service: start/stop/restart/status"""
        # Validate action to prevent command injection
        allowed_actions = ["start", "stop", "restart", "status"]
        if action not in allowed_actions:
            logger.error(f"Invalid service action: {action}")
            return f"Invalid action: {action}. Must be one of {allowed_actions}"
            
        logger.info(f"Performing service {action} on tailscaled")
        
        try:
            if platform.system() == "Windows":
                # Windows uses different commands for service control
                if action == "status":
                    cmd = ["sc", "query", "tailscaled"]
                else:
                    cmd = ["sc", action, "tailscaled"]
            else:
                # Linux/macOS use systemctl
                cmd = ["systemctl", action, "tailscaled"]
                
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=10)
            return output.decode('utf-8', errors='replace')
        except subprocess.CalledProcessError as e:
            error_msg = e.output.decode('utf-8', errors='replace') if e.output else str(e)
            logger.error(f"Service control failed: {error_msg}")
            return f"Command failed with code {e.returncode}: {error_msg}"
        except subprocess.TimeoutExpired:
            logger.error("Service control command timed out")
            return "Command timed out after 10 seconds"
        except Exception as e:
            logger.exception(f"Error controlling service: {str(e)}")
            return str(e)

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
            # Handle potential error response
            if isinstance(status, dict) and "error" in status:
                logger.warning(f"Error getting network metrics: {status['error']}")
                return {"error": status["error"]}
                
            metrics = {}
            
            # Extract self metrics
            self_data = status.get("Self", {})
            if self_data:
                metrics["tx_bytes"] = self_data.get("TXBytes", 0)
                metrics["rx_bytes"] = self_data.get("RXBytes", 0)
                
            # Get peer metrics
            peers_data = status.get("Peer", {})
            if peers_data:
                peers_metrics = []
                total_tx = 0
                total_rx = 0
                active_peers = 0
                
                for peer_id, peer in peers_data.items():
                    # Skip if this is not a proper peer object
                    if not isinstance(peer, dict):
                        continue
                        
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
                
            # Add timestamp
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
            return status.get("Self", {}).get("TailscaleIPs", [None])[0] or "Not available"
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
            self_info = status.get("Self", {})
            result["tailscale"] = {
                "id": self_info.get("ID", ""),
                "name": self_info.get("HostName", ""),
                "ip": self_info.get("TailscaleIPs", [""])[0],
                "is_exit_node": self_info.get("Capabilities", {}).get("ExitNode", False),
                "is_subnet_router": self_info.get("Capabilities", {}).get("SubnetRouter", False),
                "advertised_routes": self_info.get("AdvertisedRoutes", []),
                "tx_bytes": self_info.get("TXBytes", 0),
                "rx_bytes": self_info.get("RXBytes", 0),
                "version": self_info.get("ClientVersion", ""),
                "last_seen": self_info.get("LastSeen", ""),
                "online": self_info.get("Online", False),
            }
        except (TypeError, AttributeError) as e:
            logger.error(f"Error parsing device info: {str(e)}")
            result["error"] = f"Failed to parse device information: {str(e)}"
            
        return result

    # --- Tailscale API ---
    @staticmethod
    def _api_request(method: str, endpoint: str, data: Optional[Dict] = None, 
                    params: Optional[Dict] = None) -> Dict:
        """Base method for Tailscale API requests"""
        if not TAILSCALE_PAT:
            logger.error("Tailscale API request failed: No PAT set")
            return {"error": "No Tailscale Personal Access Token set. Please add to .env file."}
            
        base_url = "https://api.tailscale.com/api/v2"
        # Replace '-' with actual tailnet if specified
        endpoint = endpoint.replace("TAILNET", TAILNET)
        url = f"{base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {TAILSCALE_PAT}",
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
        except httpx.TimeoutException:
            logger.error("Tailscale API request timed out")
            return {"error": "Request timed out after 10 seconds"}
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
                self_node = status.get("Self", {})
                if self_node:
                    nodes.append({
                        "id": "self",
                        "label": self_node.get("HostName", "This Device"),
                        "group": "self",
                        "shape": "dot",
                        "size": 15
                    })
                    
                # Add peer nodes
                peers = status.get("Peer", {})
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
            self_info = status.get("Self", {})
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
            peers = status.get("Peer", {})
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
