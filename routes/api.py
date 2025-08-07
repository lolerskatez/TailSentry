import time
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from auth import login_required
from tailscale_client import TailscaleClient
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
@router.get("/api/status")
@login_required
async def get_status(request: Request):
    """Get current Tailscale status"""
    status = TailscaleClient.status_json()
    return status

@router.get("/api/device")
@login_required
async def get_device(request: Request):
    """Get information about this device"""
    return TailscaleClient.get_device_info()

@router.get("/api/peers")
@login_required
async def get_peers(request: Request):
    """Get list of peers"""
    status = TailscaleClient.status_json()
    return {"peers": status.get("Peer", {})}

@router.get("/api/exit-node")
@login_required
async def get_exit_node(request: Request):
    """Get current exit node"""
    return {"exit_node": TailscaleClient.get_active_exit_node()}

@router.get("/api/subnet-routes")
@login_required
async def get_subnet_routes(request: Request):
    """Get advertised subnet routes"""
    return {"routes": TailscaleClient.subnet_routes()}

@router.get("/api/local-subnets")
@login_required
async def get_local_subnets(request: Request):
    """Get detected local subnets"""
    return {"subnets": TailscaleClient.detect_local_subnets()}
