from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi import status, Depends
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
            return JSONResponse({"success": False, "error": "No auth key provided."}, status_code=status.HTTP_400_BAD_REQUEST)
        logger.info(f"Environment PATH: {os.environ.get('PATH')}")
        logger.info("About to run tailscale CLI")
        result = subprocess.run([
            "tailscale", "up", f"--authkey={auth_key}"
        ], capture_output=True, text=True, timeout=30)
        logger.info("tailscale CLI finished running")
        logger.info(f"tailscale up returned code {result.returncode}")
        logger.info(f"stdout: {result.stdout}")
        logger.info(f"stderr: {result.stderr}")
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
