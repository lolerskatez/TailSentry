
import logging
import os
import subprocess
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette import status as http_status
from auth import login_required

router = APIRouter()
logger = logging.getLogger("tailsentry.authenticate")

# Simple test endpoint to verify router registration
@router.get("/api/test-save-key")
async def test_save_key():
    return {"success": True, "message": "/api/save-key endpoint is available."}

# Save only the auth_key to tailscale_settings.json (no tailscale up)
@router.post("/api/save-key")
@login_required
async def save_auth_key(request: Request):
    logger.info("/api/save-key called")
    try:
        data = await request.json()
        key = data.get("auth_key")
        if not key:
            return JSONResponse({"success": False, "error": "No authentication key provided."}, status_code=400)
        settings_path = os.path.join(os.path.dirname(__file__), '..', 'tailscale_settings.json')
        try:
            with open(settings_path, 'r') as f:
                ts_settings = json.load(f)
        except Exception:
            ts_settings = {}
        ts_settings["auth_key"] = key
        with open(settings_path, 'w') as f:
            json.dump(ts_settings, f, indent=2)
        logger.info("Auth key saved to tailscale_settings.json")
        return {"success": True}
    except Exception as e:
        logger.exception(f"Exception saving auth key: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

import logging
import os
import subprocess
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette import status as http_status
from auth import login_required


router = APIRouter()
logger = logging.getLogger("tailsentry.authenticate")



@router.post("/api/down")
@login_required
async def tailscale_down(request: Request):
    logger.info("/api/down called")
    try:
        cmd = ["tailscale", "down"]
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        logger.info(f"tailscale down finished. Return code: {result.returncode}")
        logger.info(f"stdout: {result.stdout}")
        logger.info(f"stderr: {result.stderr}")
        if result.returncode == 0:
            return {"success": True, "stdout": result.stdout}
        else:
            return JSONResponse({
                "success": False,
                "error": result.stderr or "Tailscale CLI error.",
                "stdout": result.stdout,
                "returncode": result.returncode
            }, status_code=400)
    except Exception as e:
        logger.exception(f"Exception during tailscale down: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


@router.get("/api/test")
async def test_authenticate_route():
    logger.info("/api/test endpoint hit!")
    return {"success": True, "message": "Test endpoint reached."}

@router.post("/api/authenticate")
@login_required
async def authenticate_tailscale(request: Request):
    logger.info("/api/authenticate called")
    try:
        import json
        settings_path = os.path.join(os.path.dirname(__file__), '..', 'tailscale_settings.json')
        data = await request.json()
        logger.info(f"Request JSON: {data}")
        # Update settings file with any provided values
        try:
            with open(settings_path, 'r') as f:
                ts_settings = json.load(f)
        except Exception:
            ts_settings = {}
        # Update settings with new values from request
        if "auth_key" in data and data["auth_key"]:
            ts_settings["auth_key"] = data["auth_key"]
        if "hostname" in data and data["hostname"]:
            ts_settings["hostname"] = data["hostname"]
        if "accept_routes" in data:
            ts_settings["accept_routes"] = data["accept_routes"]
        if "advertise_exit_node" in data:
            ts_settings["advertise_exit_node"] = data["advertise_exit_node"]
        if "advertise_routes" in data:
            ts_settings["advertise_routes"] = data["advertise_routes"]
        # Save updated settings
        with open(settings_path, 'w') as f:
            json.dump(ts_settings, f, indent=2)
        # Now build CLI command from file only
        with open(settings_path, 'r') as f:
            ts_settings = json.load(f)
        extra_args = []
        if ts_settings.get("hostname"):
            extra_args.append(f"--hostname={ts_settings['hostname']}")
        if ts_settings.get("accept_routes"):
            extra_args.append("--accept-routes")
        if ts_settings.get("advertise_exit_node"):
            extra_args.append("--advertise-exit-node")
        adv_routes = ts_settings.get("advertise_routes", [])
        if adv_routes:
            extra_args.append(f"--advertise-routes={','.join(adv_routes)}")
        cmd = ["tailscale", "up"]
        if ts_settings.get("auth_key"):
            cmd.append(f"--authkey={ts_settings['auth_key']}")
        else:
            logger.error("No auth key provided to /api/authenticate")
            return JSONResponse({"success": False, "error": "No auth key provided."}, status_code=http_status.HTTP_400_BAD_REQUEST)
        cmd += extra_args
        logger.error(f"tailscale up full command: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception as e:
            logger.exception(f"Exception running tailscale up: {e}")
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        logger.error(f"tailscale CLI finished running. Return code: {result.returncode}")
        logger.error(f"stdout: {result.stdout}")
        logger.error(f"stderr: {result.stderr}")
        if result.returncode == 0:
            logger.info("tailscale up succeeded")
            return {"success": True, "stdout": result.stdout}
        else:
            logger.error("tailscale up failed")
            return JSONResponse({
                "success": False,
                "error": result.stderr or "Tailscale CLI error.",
                "stdout": result.stdout,
                "returncode": result.returncode
            }, status_code=400)
    except Exception as e:
        logger.exception(f"Exception during tailscale authentication: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
