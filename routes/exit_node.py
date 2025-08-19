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

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'tailscale_settings.json')

@router.post("/api/exit-node")
@login_required
async def set_exit_node(request: Request):
    data = await request.json()
    # Accept advanced payload: advertised_routes (array), firewall (bool), hostname
    advertised_routes = data.get("advertised_routes")
    firewall = data.get("firewall")
    hostname = data.get("hostname")
    # Load all settings
    try:
        with open(SETTINGS_PATH, 'r') as f:
            settings = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read tailscale_settings.json: {e}")
        return JSONResponse({"success": False, "error": "Failed to read settings."}, status_code=500)
    # Update settings
    if advertised_routes is not None:
        settings["advertise_routes"] = advertised_routes
    if firewall is not None:
        settings["exit_node_firewall"] = bool(firewall)
    if hostname:
        settings["hostname"] = hostname
    # Save settings
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write tailscale_settings.json: {e}")
        return JSONResponse({"success": False, "error": "Failed to write settings."}, status_code=500)

    # Actually apply exit node settings at the Tailscale service level
    try:
        from tailscale_client import TailscaleClient
        # Use new set_exit_node_advanced for full control if implemented, else fallback
        if hasattr(TailscaleClient, 'set_exit_node_advanced'):
            result = TailscaleClient.set_exit_node_advanced(advertised_routes, firewall, hostname)
        else:
            # Fallback: use set_exit_node with IPv4/IPv6 detection
            enable = False
            if advertised_routes:
                enable = '0.0.0.0/0' in advertised_routes or '::/0' in advertised_routes
            result = TailscaleClient.set_exit_node(enable)
        logger.info(f"TailscaleClient.set_exit_node result: {result}")
    except Exception as e:
        logger.error(f"Failed to set exit node via TailscaleClient: {e}")
        return JSONResponse({"success": False, "error": f"Failed to set exit node: {e}"}, status_code=500)

    # Call authenticate_tailscale with all settings (to ensure settings are applied)
    fake_request = Request(request.scope, receive=request.receive)
    fake_request._json = settings
    resp = await authenticate_tailscale(fake_request)
    # Return new state for frontend sync
    try:
        with open(SETTINGS_PATH, 'r') as f:
            new_settings = json.load(f)
    except Exception:
        new_settings = settings
    return JSONResponse({"success": True, "settings": new_settings})
