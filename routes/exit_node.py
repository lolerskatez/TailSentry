from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi import status as http_status, Depends
from auth import login_required
import json
import os
import logging
from .authenticate import authenticate_tailscale

router = APIRouter()
logger = logging.getLogger("tailsentry.exit_node")

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'tailscale_settings.json')

@router.post("/api/exit-node")
@login_required
async def set_exit_node(request: Request):
    data = await request.json()
    # Accept advanced payload: advertised_routes (array), firewall (bool), hostname
    # Load current settings
    try:
        with open(SETTINGS_PATH, 'r') as f:
            current_settings = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read tailscale_settings.json: {e}")
        current_settings = {}

    # Define robust defaults
    defaults = {
        "accept_routes": True,
        "advertise_routes": [],
        "exit_node_firewall": False,
        "hostname": None
    }

    # Merge: defaults < current_settings < payload
    merged = {**defaults, **current_settings, **data}
    # Clean up: ensure advertise_routes is a list
    if not isinstance(merged["advertise_routes"], list):
        merged["advertise_routes"] = []
    # Save merged settings
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(merged, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write tailscale_settings.json: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": f"Failed to write settings: {e}"}, status_code=500)

    # Actually apply exit node settings at the Tailscale service level
    from services.tailscale_service import TailscaleClient
    try:
        # Use new set_exit_node_advanced for full control if implemented, else fallback
        if hasattr(TailscaleClient, 'set_exit_node_advanced'):
            result = TailscaleClient.set_exit_node_advanced(
                merged.get("advertise_routes"),
                merged.get("exit_node_firewall"),
                merged.get("hostname")
            )
        else:
            # Fallback: use set_exit_node with merged settings
            enable = False
            adv_routes = merged.get("advertise_routes", [])
            if adv_routes:
                enable = '0.0.0.0/0' in adv_routes or '::/0' in adv_routes
            result = TailscaleClient.set_exit_node(enable, settings=merged)
        logger.info(f"TailscaleClient.set_exit_node result: {result}")
        # Always return the latest status and any error
        status = TailscaleClient.status_json()
        if result is not True:
            logger.error(f"Exit node operation failed: {result}")
            return JSONResponse({"success": False, "error": str(result), "status": status}, status_code=500)
        # Success: return updated status
        return JSONResponse({"success": True, "message": "Exit node setting applied!", "status": status})
    except Exception as e:
        logger.error(f"Failed to set exit node via TailscaleClient: {e}", exc_info=True)
        status = TailscaleClient.status_json()
        return JSONResponse({"success": False, "error": f"Failed to set exit node: {e}", "status": status}, status_code=500)
