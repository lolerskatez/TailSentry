from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi import status as http_status, Depends
from auth import login_required
import subprocess
import logging
import os

router = APIRouter()
logger = logging.getLogger("tailsentry.authenticate")

@router.get("/api/test")
async def test_authenticate_route():
    logger.info("/api/test endpoint hit!")
    return {"success": True, "message": "Test endpoint reached."}

@router.post("/api/authenticate")
@login_required
async def authenticate_tailscale(request: Request):
    logger.info("/api/authenticate called")
    try:
        data = await request.json()
        logger.info(f"Request JSON: {data}")
        auth_key = data.get("auth_key")
        if not auth_key:
            logger.error("No auth key provided to /api/authenticate")
            return JSONResponse({"success": False, "error": "No auth key provided."}, status_code=http_status.HTTP_400_BAD_REQUEST)
        logger.info(f"Environment PATH: {os.environ.get('PATH')}")
        logger.info("About to run tailscale CLI")
        # Get current Tailscale status to extract non-default flags
        import json
        settings_path = os.path.join(os.path.dirname(__file__), '..', 'tailscale_settings.json')
        try:
            with open(settings_path, 'r') as f:
                ts_settings = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read tailscale_settings.json: {e}")
            return JSONResponse({"success": False, "error": "Failed to read Tailscale settings."}, status_code=500)

        extra_args = []
        # Build command from config
        if ts_settings.get("hostname"):
            extra_args.append(f"--hostname={ts_settings['hostname']}")
        if ts_settings.get("accept_routes"):
            extra_args.append("--accept-routes")
        if ts_settings.get("advertise_exit_node"):
            extra_args.append("--advertise-exit-node")
        adv_routes = ts_settings.get("advertise_routes", [])
        if adv_routes:
            extra_args.append(f"--advertise-routes={','.join(adv_routes)}")
        # Compose the command
        cmd = ["tailscale", "up"]
        if ts_settings.get("auth_key"):
            cmd.append(f"--authkey={ts_settings['auth_key']}")
        elif auth_key:
            cmd.append(f"--authkey={auth_key}")
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
