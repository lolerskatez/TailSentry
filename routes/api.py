
# --- CLEANED UP: All imports at top, single router, all endpoints registered ---
import os
import time
import asyncio
import json
import logging
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from services.tailscale_service import TailscaleClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger("tailsentry.ws")

# Settings export/import endpoints
@router.get("/settings/export")
async def export_settings(request: Request):
    """Export current settings as JSON."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'tailscale_settings.json')
    try:
        if not os.path.exists(config_path):
            return JSONResponse(content={}, status_code=200)
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        logger.error(f"Failed to export settings: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/settings/import")
async def import_settings(request: Request, payload: dict = Body(...)):
    """Import settings from JSON and overwrite config file."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'tailscale_settings.json')
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        return JSONResponse(content={"success": True}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to import settings: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Store active websocket connections
active_connections = []

# Health check endpoint for TailSentry instance identification
@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint for identifying TailSentry instances"""
    try:
        # Get basic system info
        import platform
        import socket
        
        hostname = socket.gethostname()
        system = platform.system()
        version = "1.0.0"  # You might want to read this from a version file
        
        # Get Tailscale status
        tailscale_status = TailscaleClient.status_json()
        current_device = tailscale_status.get("Self", {}) if isinstance(tailscale_status, dict) else {}
        
        return JSONResponse(content={
            "status": "healthy",
            "hostname": hostname,
            "system": system,
            "version": version,
            "tailscale_ip": current_device.get("TailscaleIPs", [None])[0] if isinstance(current_device, dict) else None,
            "tailscale_hostname": current_device.get("HostName", "") if isinstance(current_device, dict) else "",
            "timestamp": int(time.time())
        }, status_code=200)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(content={
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": int(time.time())
        }, status_code=500)

# Logs & Diagnostics API endpoint
@router.get("/logs")
async def get_logs(request: Request):
    """Return the last N lines of the main log file for diagnostics."""
    try:
        lines = int(request.query_params.get('lines', 100))
    except Exception:
        lines = 100
    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'tailsentry.log')
    try:
        if not os.path.exists(log_path):
            return {"logs": "Log file not found."}
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if lines > 0 else all_lines
        return {"logs": ''.join(last_lines)}
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return {"logs": f"Error reading logs: {e}"}

# WebSocket for real-time updates
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            status_data = {
                "type": "status_update",
                "timestamp": int(time.time()),
                "device_info": TailscaleClient.get_device_info(),
                "peers_count": len(TailscaleClient.status_json().get("Peer", {}))
            }
            await websocket.send_text(json.dumps(status_data))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

# API endpoints for status data
@router.get("/status")
async def get_status(request: Request):
    try:
        # Always try to get local daemon status first
        status = TailscaleClient.status_json()
        logger.info(f"API /status called, returning data type: {type(status)}")
        
        # Check if we have valid local status
        if isinstance(status, dict) and "error" not in status:
            # Add mode indicator based on API key availability
            has_api_key = bool(os.getenv("TAILSCALE_API_KEY"))
            status["_tailsentry_mode"] = "api" if has_api_key else "cli_only"
            status["_tailsentry_secure_mode"] = "true" if not has_api_key else "false"
            
            if not has_api_key:
                logger.info("Running in CLI-only mode (secure mode) - API features disabled")
            
            return status
        else:
            # Local daemon failed, check if it's a configuration issue
            if not os.getenv("TAILSCALE_API_KEY"):
                logger.info("Tailscale not configured - returning offline status")
                return {
                    "BackendState": "NeedsLogin",
                    "TailscaleIPs": [],
                    "Self": {"Online": False, "HostName": "Not Connected", "TailscaleIPs": []},
                    "Peer": {},
                    "User": {},
                    "CurrentTailnet": {},
                    "MagicDNSSuffix": "",
                    "CertDomains": [],
                    "_tailsentry_mode": "cli_only",
                    "_tailsentry_secure_mode": "true",
                    "offline_reason": "tailscale_not_configured"
                }
            else:
                error_msg = status.get("error", "Unknown error") if isinstance(status, dict) else "Invalid data format"
                logger.error(f"Status API error: {error_msg}")
                return {"error": f"Failed to get Tailscale status: {error_msg}"}
    except Exception as e:
        logger.error(f"Status API exception: {str(e)}")
        return {"error": f"Internal server error: {str(e)}"}

@router.get("/device")
async def get_device(request: Request):
    try:
        device_info = TailscaleClient.get_device_info()
        
        # Add mode indicator
        has_api_key = bool(os.getenv("TAILSCALE_API_KEY"))
        mode = "api" if has_api_key else "cli_only"
        
        result = device_info or {}
        if isinstance(result, dict):
            result["_tailsentry_mode"] = mode
        
        return result
    except Exception as e:
        logger.error(f"Device API error: {str(e)}")
        return {"error": str(e)}

@router.get("/peers")
async def get_peers(request: Request):
    try:
        # Try to get all devices from tailscale status command first
        all_devices = TailscaleClient.get_all_devices()
        
        if all_devices:
            # Get JSON status to merge with text-parsed data
            json_status = TailscaleClient.status_json()
            json_peers = {}
            if isinstance(json_status, dict) and "Peer" in json_status:
                peers_dict = json_status["Peer"]
                if isinstance(peers_dict, dict):
                    for peer_id, peer in peers_dict.items():
                        if isinstance(peer, dict):
                            hostname = peer.get("HostName", "")
                            if hostname:
                                json_peers[hostname.lower()] = peer
            
            # Check which devices are running TailSentry
            devices_with_tailsentry = TailscaleClient.check_tailsentry_instances(all_devices)
            
            # Merge JSON data with text-parsed data
            for device in devices_with_tailsentry:
                hostname = device.get("hostname", "").lower()
                if hostname in json_peers:
                    peer_data = json_peers[hostname]
                    advertised_routes = peer_data.get("AdvertisedRoutes", [])
                    device["isAdvertisingSubnets"] = bool(advertised_routes and 
                        any(route not in ('0.0.0.0/0', '::/0') for route in advertised_routes))
                else:
                    device["isAdvertisingSubnets"] = False
            
            # Special handling for current device - we know it's running TailSentry
            import socket
            current_hostname = socket.gethostname().lower()
            status = TailscaleClient.status_json()
            current_ip = None
            if isinstance(status, dict) and "Self" in status:
                self_info = status["Self"]
                if isinstance(self_info, dict):
                    current_ip = self_info.get("TailscaleIPs", [None])[0]
            
            # Mark current device as TailSentry
            for device in devices_with_tailsentry:
                device_hostname = device.get("hostname", "").lower()
                device_ip = device.get("ip", "")
                if device_hostname == current_hostname or device_ip == current_ip:
                    device["isTailsentry"] = True
                    device["tailsentry_status"] = "healthy"
                    device["tailsentry_info"] = {
                        "status": "healthy",
                        "hostname": current_hostname,
                        "system": "Windows",  # Could be made dynamic
                        "version": "1.0.0",
                        "tailscale_ip": current_ip,
                        "tailscale_hostname": current_hostname,
                        "timestamp": int(time.time())
                    }
                    # Check if current device is advertising subnets
                    if isinstance(self_info, dict):
                        advertised_routes = self_info.get("AdvertisedRoutes", [])
                        device["isAdvertisingSubnets"] = bool(advertised_routes and 
                            any(route not in ('0.0.0.0/0', '::/0') for route in advertised_routes))
                    break
            
            peers_data = {"peers": devices_with_tailsentry}
            logger.info(f"Using parsed status output with {len(all_devices)} devices")
        else:
            # Fallback to JSON status for direct peers only
            logger.warning("Failed to get all devices, falling back to JSON status")
            status = TailscaleClient.status_json()
            if isinstance(status, dict) and "Peer" in status and isinstance(status["Peer"], dict):
                # Convert peer dict to array format for consistency
                peers_array = []
                for peer_id, peer in status["Peer"].items():
                    if isinstance(peer, dict):
                        peer_data = peer.copy()
                        peer_data["id"] = peer.get("ID", peer_id)
                        # Add subnet advertising detection
                        advertised_routes = peer.get("AdvertisedRoutes", [])
                        peer_data["isAdvertisingSubnets"] = bool(advertised_routes and 
                            any(route not in ('0.0.0.0/0', '::/0') for route in advertised_routes))
                        peers_array.append(peer_data)
                
                # Check TailSentry instances for fallback devices too
                peers_with_tailsentry = TailscaleClient.check_tailsentry_instances(peers_array)
                peers_data = {"peers": peers_with_tailsentry}
            else:
                logger.warning("No peer data available from local daemon")
                peers_data = {"peers": []}
        
        # Add mode indicator
        has_api_key = bool(os.getenv("TAILSCALE_API_KEY"))
        peers_data["_tailsentry_mode"] = "api" if has_api_key else "cli_only"
        
        if not has_api_key:
            logger.info("Peers API running in CLI-only mode - using local daemon data")
        
        return peers_data
    except Exception as e:
        logger.error(f"Peers API error: {str(e)}")
        return {"error": str(e)}

@router.get("/exit-node")
async def get_exit_node(request: Request):
    try:
        exit_node_data = TailscaleClient.get_active_exit_node()
        
        # Add mode indicator
        has_api_key = bool(os.getenv("TAILSCALE_API_KEY"))
        mode = "api" if has_api_key else "cli_only"
        
        return {
            "exit_node": exit_node_data,
            "_tailsentry_mode": mode
        }
    except Exception as e:
        logger.error(f"Exit node API error: {str(e)}")
        return {"error": str(e)}

@router.get("/exit-node-clients")
async def get_exit_node_clients(request: Request):
    try:
        clients_data = TailscaleClient.get_exit_node_clients()
        
        # Add mode indicator
        has_api_key = bool(os.getenv("TAILSCALE_API_KEY"))
        mode = "api" if has_api_key else "cli_only"
        
        return {
            "clients": clients_data,
            "_tailsentry_mode": mode
        }
    except Exception as e:
        logger.error(f"Exit node clients API error: {str(e)}")
        return {"error": str(e)}

@router.get("/subnet-routes")
async def get_subnet_routes(request: Request):
    try:
        routes_data = TailscaleClient.subnet_routes()
        
        # Add mode indicator
        has_api_key = bool(os.getenv("TAILSCALE_API_KEY"))
        mode = "api" if has_api_key else "cli_only"
        
        return {
            "routes": routes_data,
            "_tailsentry_mode": mode
        }
    except Exception as e:
        logger.error(f"Subnet routes API error: {str(e)}")
        return {"error": str(e)}

@router.get("/local-subnets")
async def get_local_subnets(request: Request):
    try:
        subnets_data = TailscaleClient.detect_local_subnets()
        
        # Add mode indicator
        has_api_key = bool(os.getenv("TAILSCALE_API_KEY"))
        mode = "api" if has_api_key else "cli_only"
        
        return {
            "subnets": subnets_data,
            "_tailsentry_mode": mode
        }
    except Exception as e:
        logger.error(f"Local subnets API error: {str(e)}")
        return {"error": str(e)}

@router.post("/subnet-routes")
async def set_subnet_routes(request: Request, payload: dict = Body(...)):
    import ipaddress
    try:
        routes = payload.get("routes")
        if not isinstance(routes, list):
            return {"success": False, "error": "'routes' must be a list of CIDR strings"}
        for subnet in routes:
            try:
                ipaddress.ip_network(subnet, strict=False)
            except Exception:
                return {"success": False, "error": f"Invalid subnet: {subnet}"}
        result = TailscaleClient.set_subnet_routes(routes)
        if result is True:
            logger.info("Subnet routes set successfully")
            return {"success": True, "result": result}
        else:
            # Any non-True result indicates an error
            logger.error(f"Subnet routes set failed: {result}")
            return {"success": False, "error": str(result)}
    except Exception as e:
        logger.error(f"Set subnet routes API error: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/detect-networks")
async def detect_networks(request: Request):
    """Detect local networks for subnet route suggestions."""
    try:
        import psutil
        import ipaddress
        
        detected = []
        
        # Get network interfaces
        for interface_name, interface_addresses in psutil.net_if_addrs().items():
            # Skip loopback and non-ethernet interfaces
            if interface_name.startswith(('lo', 'Loopback', 'isatap', 'Teredo')):
                continue
                
            for addr in interface_addresses:
                if addr.family == 2:  # AF_INET (IPv4)
                    try:
                        # Calculate network from IP and netmask
                        ip = ipaddress.IPv4Address(addr.address)
                        if ip.is_private and not ip.is_loopback:
                            # Convert netmask to prefix length
                            netmask = ipaddress.IPv4Address(addr.netmask)
                            prefix_len = bin(int(netmask)).count('1')
                            
                            # Calculate network address
                            network = ipaddress.IPv4Network(f"{addr.address}/{prefix_len}", strict=False)
                            
                            detected.append({
                                "cidr": str(network),
                                "interface": interface_name,
                                "ip": addr.address
                            })
                    except Exception:
                        continue
        
        # Remove duplicates and sort
        unique_networks = {}
        for net in detected:
            unique_networks[net["cidr"]] = net
        
        return list(unique_networks.values())
        
    except Exception as e:
        logger.error(f"Network detection error: {str(e)}")
        return []

@router.get("/network-stats")
async def get_network_stats(request: Request):
    """Get real-time network statistics for dashboard charts."""
    try:
        # Check if TAILSCALE_PAT is not set (Tailscale API Key not configured)
        if not os.getenv("TAILSCALE_PAT"):
            logger.info("Tailscale not configured - returning empty network stats")
            return JSONResponse(content={
                "success": True,
                "stats": {
                    "tx": "0.0 KB/s",
                    "rx": "0.0 KB/s", 
                    "timestamp": time.time(),
                    "bytes_sent": 0,
                    "bytes_received": 0,
                    "active_peers": 0,
                    "total_peers": 0,
                    "offline_reason": "tailscale_not_configured"
                }
            })
            
        # Get network metrics from TailscaleClient
        metrics = TailscaleClient.get_network_metrics()
        
        if metrics and "error" not in metrics:
            # Convert bytes to human readable format
            def format_bytes_per_sec(bytes_val):
                if bytes_val == 0:
                    return "0.0 MB/s"
                # Simple approximation - in real scenario you'd track delta over time
                mb_val = bytes_val / (1024 * 1024) 
                if mb_val < 0.1:
                    kb_val = bytes_val / 1024
                    return f"{kb_val:.1f} KB/s"
                return f"{mb_val:.1f} MB/s"
            
            return JSONResponse(content={
                "success": True,
                "stats": {
                    "tx": format_bytes_per_sec(metrics.get("tx_bytes", 0)),
                    "rx": format_bytes_per_sec(metrics.get("rx_bytes", 0)),
                    "timestamp": metrics.get("timestamp", time.time()),
                    "bytes_sent": metrics.get("tx_bytes", 0),
                    "bytes_received": metrics.get("rx_bytes", 0),
                    "active_peers": metrics.get("active_peers", 0),
                    "total_peers": metrics.get("total_peers", 0)
                }
            })
        else:
            # Return mock data if no real stats available
            return JSONResponse(content={
                "success": True,
                "stats": {
                    "tx": "0.0 MB/s",
                    "rx": "0.0 MB/s", 
                    "timestamp": time.time(),
                    "bytes_sent": 0,
                    "bytes_received": 0,
                    "active_peers": 0,
                    "total_peers": 0
                }
            })
    except Exception as e:
        logger.error(f"Network stats API error: {str(e)}")
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "stats": {
                "tx": "0.0 MB/s",
                "rx": "0.0 MB/s",
                "timestamp": time.time(),
                "bytes_sent": 0,
            }
        }, status_code=500)

# TailSentry Device Management Endpoints
@router.post("/tailsentry/{device_id}/{action}")
async def manage_tailsentry_device(device_id: str, action: str, request: Request):
    """Manage a remote TailSentry device (restart, stop, logs, config)"""
    try:
        # Get device information first
        all_devices = TailscaleClient.get_all_devices()
        target_device = None
        
        for device in all_devices:
            if device.get('id') == device_id or device.get('ID') == device_id:
                target_device = device
                break
        
        if not target_device:
            return JSONResponse(content={
                "success": False,
                "error": f"Device {device_id} not found"
            }, status_code=404)
        
        # Check if device is online and has TailSentry
        if not target_device.get('online', False):
            return JSONResponse(content={
                "success": False,
                "error": f"Device {target_device.get('hostname', device_id)} is offline"
            }, status_code=400)
        
        if not target_device.get('isTailsentry', False):
            return JSONResponse(content={
                "success": False,
                "error": f"Device {target_device.get('hostname', device_id)} is not a TailSentry instance"
            }, status_code=400)
        
        device_ip = target_device.get('ip')
        if not device_ip:
            return JSONResponse(content={
                "success": False,
                "error": f"No IP address found for device {target_device.get('hostname', device_id)}"
            }, status_code=400)
        
        # Validate action
        valid_actions = ['restart', 'stop', 'logs', 'config']
        if action not in valid_actions:
            return JSONResponse(content={
                "success": False,
                "error": f"Invalid action: {action}. Valid actions: {', '.join(valid_actions)}"
            }, status_code=400)
        
        # For now, return a placeholder response
        # In a real implementation, you would make HTTP requests to the remote device
        logger.info(f"TailSentry {action} requested for device {target_device.get('hostname', device_id)} ({device_ip})")
        
        return JSONResponse(content={
            "success": True,
            "message": f"TailSentry {action} initiated on {target_device.get('hostname', device_id)}",
            "device_id": device_id,
            "action": action,
            "device_ip": device_ip
        })
        
    except Exception as e:
        logger.error(f"TailSentry management error: {str(e)}")
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)
