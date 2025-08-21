import os
import time
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
# from auth import login_required
from services.tailscale_service import TailscaleClient
import asyncio
import json
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger("tailsentry.ws")

# ...existing code...

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

import os
import time
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
 # from auth import login_required
from services.tailscale_service import TailscaleClient
import asyncio
import json
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger("tailsentry.ws")

# Store active websocket connections
active_connections = []

# Logs & Diagnostics API endpoint (after all imports and router definition)
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
import time
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from auth import login_required
from services.tailscale_service import TailscaleClient
import asyncio
import json
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger("tailsentry.ws")

# Store active websocket connections
active_connections = []

# WebSocket for real-time updates
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Get current status data
            status_data = {
                "type": "status_update",
                "timestamp": int(time.time()),
                "device_info": TailscaleClient.get_device_info(),
                "peers_count": len(TailscaleClient.status_json().get("Peer", {}))
            }
            
            # Send data to client
            await websocket.send_text(json.dumps(status_data))
            
            # Wait before next update
            await asyncio.sleep(5)  # Update every 5 seconds
            
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Remove from active connections
        if websocket in active_connections:
            active_connections.remove(websocket)

# API endpoints for status data
@router.get("/status")
async def get_status(request: Request):
    """Get current Tailscale status"""
    try:
        status = TailscaleClient.status_json()
        
        # Add debug logging
        logger.info(f"API /status called, returning data type: {type(status)}")
        
        if isinstance(status, dict) and "error" not in status:
            return status
        else:
            error_msg = status.get("error", "Unknown error") if isinstance(status, dict) else "Invalid data format"
            logger.error(f"Status API error: {error_msg}")
            return {"error": f"Failed to get Tailscale status: {error_msg}"}
    except Exception as e:
        logger.error(f"Status API exception: {str(e)}")
        return {"error": f"Internal server error: {str(e)}"}

@router.get("/device")
async def get_device(request: Request):
    """Get information about this device"""
    try:
        device_info = TailscaleClient.get_device_info()
        return device_info or {}
    except Exception as e:
        logger.error(f"Device API error: {str(e)}")
        return {"error": str(e)}

@router.get("/peers")
async def get_peers(request: Request):
    """Get list of peers"""
    try:
        status = TailscaleClient.status_json()
        if isinstance(status, dict) and "Peer" in status:
            return {"peers": status["Peer"]}
        else:
            return {"peers": {}}
    except Exception as e:
        logger.error(f"Peers API error: {str(e)}")
        return {"error": str(e)}

@router.get("/exit-node")
async def get_exit_node(request: Request):
    """Get current exit node"""
    try:
        return {"exit_node": TailscaleClient.get_active_exit_node()}
    except Exception as e:
        logger.error(f"Exit node API error: {str(e)}")
        return {"error": str(e)}

@router.get("/subnet-routes")
async def get_subnet_routes(request: Request):
    """Get advertised subnet routes"""
    try:
        return {"routes": TailscaleClient.subnet_routes()}
    except Exception as e:
        logger.error(f"Subnet routes API error: {str(e)}")
        return {"error": str(e)}

@router.get("/local-subnets")
async def get_local_subnets(request: Request):
    """Get detected local subnets"""
    try:
        return {"subnets": TailscaleClient.detect_local_subnets()}
    except Exception as e:
        logger.error(f"Local subnets API error: {str(e)}")
        return {"error": str(e)}


# Robust POST endpoint to set advertised subnet routes
from fastapi import Body

@router.post("/subnet-routes")
async def set_subnet_routes(request: Request, payload: dict = Body(...)):
    """Set advertised subnet routes"""
    import ipaddress
    try:
        routes = payload.get("routes")
        if not isinstance(routes, list):
            return {"success": False, "error": "'routes' must be a list of CIDR strings"}
        # Strictly validate each subnet as a valid CIDR
        for subnet in routes:
            try:
                ipaddress.ip_network(subnet, strict=False)
            except Exception:
                return {"success": False, "error": f"Invalid subnet: {subnet}"}
        result = TailscaleClient.set_subnet_routes(routes)
        # If set_subnet_routes returns a string, it's an error
        if isinstance(result, str) and result.lower().startswith("invalid"):
            logger.error(f"Subnet routes set error: {result}")
            return {"success": False, "error": result}
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Set subnet routes API error: {str(e)}")
        return {"success": False, "error": str(e)}
