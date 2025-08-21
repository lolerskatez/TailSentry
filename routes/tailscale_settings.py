from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi import status as http_status
import json
import os
import logging
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
    return JSONResponse(settings)

@router.post("/api/tailscale-settings")
async def apply_tailscale_settings(request: Request):
    data = await request.json()
    try:
        save_settings(data)
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
