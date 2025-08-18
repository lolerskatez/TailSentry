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
    # Accept is_exit_node (frontend) or enable (legacy)
    enable = data.get("is_exit_node")
    if enable is None:
        enable = data.get("enable")
    if enable is None:
        return JSONResponse({"success": False, "error": "Missing 'is_exit_node' field."}, status_code=400)
    # Load all settings
    try:
        with open(SETTINGS_PATH, 'r') as f:
            settings = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read tailscale_settings.json: {e}")
        return JSONResponse({"success": False, "error": "Failed to read settings."}, status_code=500)
    # Update exit node setting
    settings["advertise_exit_node"] = bool(enable)
    # Optionally update hostname if provided
    if "hostname" in data:
        settings["hostname"] = data["hostname"]
    # Save settings
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write tailscale_settings.json: {e}")
        return JSONResponse({"success": False, "error": "Failed to write settings."}, status_code=500)
    # Call authenticate_tailscale with all settings
    fake_request = Request(request.scope, receive=request.receive)
    fake_request._json = settings
    resp = await authenticate_tailscale(fake_request)
    return resp
