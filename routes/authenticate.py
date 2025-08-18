from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi import status, Depends
from auth import login_required
import subprocess
import logging

router = APIRouter()
logger = logging.getLogger("tailsentry.authenticate")

@router.post("/api/authenticate")
@login_required
async def authenticate_tailscale(request: Request):
    data = await request.json()
    auth_key = data.get("auth_key")
    if not auth_key:
        logger.error("No auth key provided to /api/authenticate")
        return JSONResponse({"success": False, "error": "No auth key provided."}, status_code=status.HTTP_400_BAD_REQUEST)
    try:
        # Run the Tailscale CLI command
        result = subprocess.run([
            "tailscale", "up", f"--authkey={auth_key}"
        ], capture_output=True, text=True, timeout=30)
        logger.info(f"tailscale up returned code {result.returncode}")
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
        logger.exception("Exception during tailscale authentication")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
