
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
        # Get peer information from local daemon (works without API token)
        status = TailscaleClient.status_json()
        if isinstance(status, dict) and "Peer" in status:
            peers_data = {"peers": status["Peer"]}
            
            # Add mode indicator
            has_api_key = bool(os.getenv("TAILSCALE_API_KEY"))
            peers_data["_tailsentry_mode"] = "api" if has_api_key else "cli_only"
            
            if not has_api_key:
                logger.info("Peers API running in CLI-only mode - using local daemon data")
            
            return peers_data
        else:
            logger.warning("No peer data available from local daemon")
            return {"peers": {}, "_tailsentry_mode": "cli_only"}
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
        if isinstance(result, str) and result.lower().startswith("invalid"):
            logger.error(f"Subnet routes set error: {result}")
            return {"success": False, "error": result}
        return {"success": True, "result": result}
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
                "bytes_received": 0,
                "active_peers": 0,
                "total_peers": 0
            }
        }, status_code=500)
