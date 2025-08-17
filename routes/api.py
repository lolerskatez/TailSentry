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
@router.get("/status")
@login_required
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
@login_required
async def get_device(request: Request):
    """Get information about this device"""
    try:
        device_info = TailscaleClient.get_device_info()
        return device_info or {}
    except Exception as e:
        logger.error(f"Device API error: {str(e)}")
        return {"error": str(e)}

@router.get("/peers")
@login_required
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
@login_required
async def get_exit_node(request: Request):
    """Get current exit node"""
    try:
        return {"exit_node": TailscaleClient.get_active_exit_node()}
    except Exception as e:
        logger.error(f"Exit node API error: {str(e)}")
        return {"error": str(e)}

@router.get("/subnet-routes")
@login_required
async def get_subnet_routes(request: Request):
    """Get advertised subnet routes"""
    try:
        return {"routes": TailscaleClient.subnet_routes()}
    except Exception as e:
        logger.error(f"Subnet routes API error: {str(e)}")
        return {"error": str(e)}

@router.get("/local-subnets")
@login_required
async def get_local_subnets(request: Request):
    """Get detected local subnets"""
    try:
        return {"subnets": TailscaleClient.detect_local_subnets()}
    except Exception as e:
        logger.error(f"Local subnets API error: {str(e)}")
        return {"error": str(e)}
