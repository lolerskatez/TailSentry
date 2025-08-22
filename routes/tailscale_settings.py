from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi import status as http_status
import json
import os
import logging
from dotenv import set_key, find_dotenv
from services.tailscale_service import TailscaleClient

router = APIRouter()
tailscale_settings_router = router
logger = logging.getLogger("tailsentry.tailscale_settings")

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'tailscale_settings.json')

def load_settings():
    try:
        with open(SETTINGS_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(settings):
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=2)

@router.get("/api/tailscale-settings")
async def get_tailscale_settings():
    settings = load_settings()
    
    # Add PAT status (without exposing the actual value)
    settings['tailscale_pat'] = ''  # Don't expose actual PAT
    settings['has_pat'] = bool(os.getenv('TAILSCALE_PAT'))
    
    return JSONResponse(settings)

@router.post("/api/tailscale-settings")
async def apply_tailscale_settings(request: Request):
    data = await request.json()
    
    # Handle PAT separately - save to .env file
    if 'tailscale_pat' in data:
        pat_value = data.get('tailscale_pat', '').strip()
        try:
            env_file = find_dotenv()
            if not env_file:
                logger.error("No .env file found")
                return JSONResponse({"success": False, "error": ".env file not found"}, status_code=500)
                
            if pat_value:
                set_key(env_file, 'TAILSCALE_PAT', f"'{pat_value}'")
                logger.info("Tailscale PAT updated successfully")
            else:
                # Clear PAT if empty
                set_key(env_file, 'TAILSCALE_PAT', '')
                logger.info("Tailscale PAT cleared")
        except Exception as e:
            logger.error(f"Failed to update TAILSCALE_PAT in .env: {e}", exc_info=True)
            return JSONResponse({"success": False, "error": f"Failed to update PAT: {e}"}, status_code=500)
    
    # Remove PAT from data before saving to tailscale_settings.json
    settings_data = {k: v for k, v in data.items() if k != 'tailscale_pat'}
    
    try:
        save_settings(settings_data)
    except Exception as e:
        logger.error(f"Failed to write tailscale_settings.json: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": f"Failed to write settings: {e}"}, status_code=500)
    try:
        result = TailscaleClient.set_exit_node_advanced(
            advertised_routes=data.get("advertise_routes"),
            firewall=data.get("exit_node_firewall"),
            hostname=data.get("hostname")
        )
        logger.info(f"TailscaleClient.set_exit_node_advanced result: {result}")
        status = TailscaleClient.status_json()
        if result is not True:
            logger.error(f"Exit node operation failed: {result}")
            return JSONResponse({"success": False, "error": str(result), "status": status}, status_code=500)
        return JSONResponse({"success": True, "message": "Settings applied!", "status": status})
    except Exception as e:
        logger.error(f"Failed to apply settings via TailscaleClient: {e}", exc_info=True)
        status = TailscaleClient.status_json()
        return JSONResponse({"success": False, "error": f"Failed to apply settings: {e}", "status": status}, status_code=500)

@router.post("/api/subnet-routes")
async def set_subnet_routes(request: Request):
    """Set advertised subnet routes"""
    try:
        data = await request.json()
        routes = data.get("routes", [])
        
        result = TailscaleClient.set_subnet_routes(routes)
        if result is True:
            return JSONResponse({"success": True, "message": "Routes updated successfully"})
        else:
            return JSONResponse({"success": False, "error": str(result)}, status_code=500)
    except Exception as e:
        logger.error(f"Failed to set subnet routes: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.get("/api/local-subnets")
async def get_local_subnets():
    """Get detected local subnets"""
    try:
        subnets = TailscaleClient.detect_local_subnets()
        return JSONResponse(subnets)
    except Exception as e:
        logger.error(f"Failed to detect local subnets: {e}", exc_info=True)
        return JSONResponse([], status_code=500)

@router.post("/api/exit-node")
async def set_exit_node(request: Request):
    """Set or unset exit node"""
    try:
        data = await request.json()
        exit_node = data.get("exit_node")
        
        if exit_node:
            result = TailscaleClient.set_exit_node(True, {"exit_node": exit_node})
        else:
            result = TailscaleClient.set_exit_node(False)
            
        if result is True:
            return JSONResponse({"success": True, "message": "Exit node updated successfully"})
        else:
            return JSONResponse({"success": False, "error": str(result)}, status_code=500)
    except Exception as e:
        logger.error(f"Failed to set exit node: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/api/tailscale-service")
async def tailscale_service_control(request: Request):
    """Control Tailscale service (start, stop, restart, status)"""
    try:
        data = await request.json()
        action = data.get("action")
        
        if action == "status":
            status = TailscaleClient.service_status()
            return JSONResponse({"success": True, "status": status})
        elif action in ["start", "stop", "restart", "up", "down"]:
            if action == "up":
                result = TailscaleClient.up()
            elif action == "down":
                result = TailscaleClient.service_control("down")
            else:
                result = TailscaleClient.service_control(action)
                
            if result is True or "success" in str(result).lower():
                return JSONResponse({"success": True, "message": f"Service {action} completed"})
            else:
                return JSONResponse({"success": False, "error": str(result)}, status_code=500)
        else:
            return JSONResponse({"success": False, "error": "Invalid action"}, status_code=400)
    except Exception as e:
        logger.error(f"Failed to control service: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.get("/api/tailscale-logs")
async def get_tailscale_logs():
    """Get Tailscale logs"""
    try:
        logs = TailscaleClient.logs()
        return JSONResponse({"success": True, "logs": logs})
    except Exception as e:
        logger.error(f"Failed to get logs: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e), "logs": ""}, status_code=500)

@router.get("/api/network-metrics")
async def get_network_metrics():
    """Get network metrics"""
    try:
        metrics = TailscaleClient.get_network_metrics()
        return JSONResponse({"success": True, "metrics": metrics})
    except Exception as e:
        logger.error(f"Failed to get network metrics: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/api/clear-cache")
async def clear_cache():
    """Clear Tailscale status cache"""
    try:
        TailscaleClient.clear_cache()
        return JSONResponse({"success": True, "message": "Cache cleared successfully"})
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
