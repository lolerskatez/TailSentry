from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from auth import login_required
from tailscale_client import TailscaleClient
import logging

router = APIRouter()
logger = logging.getLogger("tailsentry.config")

class AuthKeyRequest(BaseModel):
    auth_key: str

class ExitNodeRequest(BaseModel):
    enabled: bool

@router.get("/api/config")
@login_required
async def get_config(request: Request):
    """Get current Tailscale configuration"""
    try:
        # Get device info and status
        device_info = TailscaleClient.get_device_info()
        status = TailscaleClient.status_json()
        
        # Extract configuration data
        config_data = {
            "auth_status": "authenticated" if status.get("BackendState") == "Running" else "unauthenticated",
            "exit_node_enabled": device_info.get("is_exit_node", False),
            "advertised_routes": device_info.get("advertised_routes", []),
            "tailnet": str(status.get("CurrentTailnet", "unknown")),
            "node_key": device_info.get("node_key", ""),
            "last_auth_time": device_info.get("created", ""),
            "hostname": device_info.get("hostname", ""),
            "tailscale_ip": device_info.get("tailscale_ip", ""),
            "online": status.get("BackendState") == "Running"
        }
        
        return {"config": config_data}
        
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")

@router.post("/api/config/reauth")
@login_required 
async def reauthenticate(request: Request, auth_request: AuthKeyRequest):
    """Re-authenticate device with new auth key"""
    try:
        auth_key = auth_request.auth_key.strip()
        
        if not auth_key:
            raise HTTPException(status_code=400, detail="Auth key is required")
            
        if not auth_key.startswith("tskey-"):
            raise HTTPException(status_code=400, detail="Invalid auth key format")
        
        # Use TailscaleClient to re-authenticate
        result = TailscaleClient.up(authkey=auth_key)
        
        if result is True:
            logger.info("Device re-authenticated successfully")
            return {"success": True, "message": "Device re-authenticated successfully"}
        else:
            # result is a string error message
            error_msg = str(result)
            logger.error(f"Re-authentication failed: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Re-authentication failed: {error_msg}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during re-authentication: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Re-authentication error: {str(e)}")

@router.post("/api/config/exit-node")
@login_required
async def configure_exit_node(request: Request, exit_request: ExitNodeRequest):
    """Enable or disable exit node functionality"""
    try:
        enabled = exit_request.enabled
        
        # Use TailscaleClient to configure exit node
        result = TailscaleClient.set_exit_node(enable=enabled)
        
        if result is True:
            action = "enabled" if enabled else "disabled"
            logger.info(f"Exit node {action} successfully")
            return {"success": True, "message": f"Exit node {action} successfully", "enabled": enabled}
        else:
            # result is a string error message
            error_msg = str(result)
            logger.error(f"Exit node configuration failed: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Exit node configuration failed: {error_msg}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring exit node: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Exit node configuration error: {str(e)}")

@router.get("/api/traffic")
@login_required
async def get_traffic_stats(request: Request):
    """Get current traffic statistics"""
    try:
        # Get traffic stats from TailscaleClient
        status = TailscaleClient.status_json()
        device_info = TailscaleClient.get_device_info()
        
        # Calculate traffic statistics (this would need real implementation)
        traffic_data = {
            "tx_rate": "0.0 MB/s",  # This would come from real monitoring
            "rx_rate": "0.0 MB/s",  # This would come from real monitoring
            "total_tx": "0.0 GB",   # This would come from accumulated stats
            "total_rx": "0.0 GB",   # This would come from accumulated stats
            "active_peers": len(status.get("Peer", {})),
            "uptime": device_info.get("uptime", "0s"),
            "last_activity": "now",
            "activity_level": 50
        }
        
        return {"traffic": traffic_data}
        
    except Exception as e:
        logger.error(f"Error getting traffic stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get traffic statistics: {str(e)}")
