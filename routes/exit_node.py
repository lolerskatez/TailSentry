from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi import status as http_status, Depends
 # from auth import login_required
import json
import os
import logging
from .authenticate import authenticate_tailscale

router = APIRouter()
logger = logging.getLogger("tailsentry.exit_node")

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'tailscale_settings.json')

@router.post("/api/exit-node")
 # @login_required
async def set_exit_node(request: Request):
    data = await request.json()
    # Accept advanced payload: advertised_routes (array), firewall (bool), hostname, exit_node_enable (bool)
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

    # Robustly handle exit node intent
    exit_node_enable = data.get("exit_node_enable")
    # If not explicitly set, infer from advertised_routes
    if exit_node_enable is None:
        adv_routes = merged["advertise_routes"]
        exit_node_enable = ("0.0.0.0/0" in adv_routes) or ("::/0" in adv_routes)

    # Ensure advertise_routes includes or excludes exit node routes as needed
    adv_routes = [r for r in merged["advertise_routes"] if r not in ("0.0.0.0/0", "::/0")]
    if exit_node_enable:
        # Add exit node routes if not present
        if "0.0.0.0/0" not in adv_routes:
            adv_routes.append("0.0.0.0/0")
        # Optionally add "::/0" for IPv6 exit node
        # if "::/0" not in adv_routes:
        #     adv_routes.append("::/0")
    # If disabling, ensure exit node routes are not present
    merged["advertise_routes"] = adv_routes

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
            result = TailscaleClient.set_exit_node(exit_node_enable, settings=merged)
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
