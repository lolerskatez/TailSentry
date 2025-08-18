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
        from tailscale_client import TailscaleClient
        ts_status_raw = TailscaleClient.status_json()
        # Unpack if status_json returns a tuple (data, timestamp)
        if isinstance(ts_status_raw, tuple):
            ts_status = ts_status_raw[0]
        else:
            ts_status = ts_status_raw
        extra_args = []
        if isinstance(ts_status, dict):
            self_info = ts_status.get("Self")
            if isinstance(self_info, dict):
                # Add --hostname
                hostname = self_info.get("HostName")
                if hostname:
                    extra_args.append(f"--hostname={hostname}")
                # Add --accept-routes if present
                if self_info.get("Capabilities", {}).get("AcceptRoutes", False):
                    extra_args.append("--accept-routes")
                # Add --advertise-exit-node if present
                if self_info.get("Capabilities", {}).get("ExitNode", False):
                    extra_args.append("--advertise-exit-node")
                # Add --advertise-routes if present
                advertised_routes = self_info.get("AdvertisedRoutes", [])
                if advertised_routes:
                    extra_args.append(f"--advertise-routes={','.join(advertised_routes)}")
        # Compose the command
        cmd = ["tailscale", "up", f"--authkey={auth_key}"] + extra_args
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
