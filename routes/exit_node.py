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
    enable = data.get("enable")
    auth_key = data.get("auth_key")
    if enable is None:
        return JSONResponse({"success": False, "error": "Missing 'enable' field."}, status_code=400)
    try:
        with open(SETTINGS_PATH, 'r') as f:
            settings = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read tailscale_settings.json: {e}")
        return JSONResponse({"success": False, "error": "Failed to read settings."}, status_code=500)
    settings["advertise_exit_node"] = bool(enable)
    try:
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write tailscale_settings.json: {e}")
        return JSONResponse({"success": False, "error": "Failed to write settings."}, status_code=500)
    # Use provided auth_key if present, else from settings
    fake_request = Request(request.scope, receive=request.receive)
    fake_request._json = {"auth_key": auth_key or settings.get("auth_key", "")}
    resp = await authenticate_tailscale(fake_request)
    return resp
