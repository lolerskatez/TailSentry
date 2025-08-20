import logging
import subprocess
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
 # from auth import login_required

router = APIRouter()
logger = logging.getLogger("tailsentry.down")

@router.post("/down")
 # @login_required
async def tailscale_down(request: Request):
    logger.info("/api/down called")
    try:
        cmd = ["tailscale", "down"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        logger.info(f"tailscale down return code: {result.returncode}")
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
        logger.exception(f"Exception running tailscale down: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
