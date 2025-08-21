
# Diagnostics export endpoint: logs, Tailscale status, config
@router.get("/api/diagnostics/download")
async def download_diagnostics():
    # TODO: Restrict to authenticated/admin users only
    import tempfile
    from services.tailscale_service import TailscaleClient
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'tailscale_settings.json')
    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'tailsentry.log')
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write Tailscale status
        status_file = os.path.join(tmpdir, 'tailscale_status.json')
        try:
            status = TailscaleClient.status_json()
            with open(status_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(status, f, indent=2)
        except Exception as e:
            with open(status_file, 'w', encoding='utf-8') as f:
                f.write(f'Error getting status: {e}')
        # Prepare zip
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(log_path):
                zf.write(log_path, arcname="tailsentry.log")
            if os.path.exists(config_path):
                zf.write(config_path, arcname="tailscale_settings.json")
            zf.write(status_file, arcname="tailscale_status.json")
        mem_zip.seek(0)
        return StreamingResponse(mem_zip, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=diagnostics_bundle.zip"})
# Real-time log streaming via WebSocket
import asyncio
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws/logs")
async def logs_websocket(websocket: WebSocket):
    await websocket.accept()
    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'tailsentry.log')
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, 2)  # Move to end of file
            while True:
                line = f.readline()
                if line:
                    await websocket.send_text(line)
                else:
                    await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket log streaming error: {e}")
# Download full log file endpoint (for authenticated users)


# Download full log file endpoint (for authenticated users)
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
import zipfile
import io

# ...existing code...

# Place this endpoint after router is defined
@router.get("/api/logs/download")
async def download_logs_file(zip: bool = False):
    """Download the full current log file or a zipped archive."""
    # TODO: Add authentication check here
    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'tailsentry.log')
    if not os.path.exists(log_path):
        return JSONResponse(content={"error": "Log file not found."}, status_code=404)
    if zip:
        # Create a zip in memory
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(log_path, arcname="tailsentry.log")
        mem_zip.seek(0)
        return StreamingResponse(mem_zip, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=tailsentry_logs.zip"})
    else:
        return FileResponse(log_path, filename="tailsentry.log", media_type="text/plain")

import os
import logging
import os
import logging
import zipfile
import io
import asyncio
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse



router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger("tailsentry.logs")


# Page route
@router.get("/logs")
async def logs_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request})

# API endpoint for logs with server-side filtering


# Download full log file endpoint (for authenticated users)
@router.get("/api/logs/download")
async def download_logs_file(zip: bool = False):
    # TODO: Restrict to authenticated/admin users only
    # Example: if not request.session.get('user') or not request.session.get('is_admin'): return JSONResponse(status_code=403, content={"error": "Forbidden"})
    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'tailsentry.log')
    if not os.path.exists(log_path):
        return JSONResponse(content={"error": "Log file not found."}, status_code=404)
    if zip:
        # Create a zip in memory
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(log_path, arcname="tailsentry.log")
        mem_zip.seek(0)
        return StreamingResponse(mem_zip, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=tailsentry_logs.zip"})
    else:
        return FileResponse(log_path, filename="tailsentry.log", media_type="text/plain")

# Real-time log streaming via WebSocket
@router.websocket("/ws/logs")
async def logs_websocket(websocket: WebSocket):
    await websocket.accept()
    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'tailsentry.log')
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, 2)  # Move to end of file
            while True:
                line = f.readline()
                if line:
                    await websocket.send_text(line)
                else:
                    await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket log streaming error: {e}")

# API endpoint for logs with server-side filtering
@router.get("/api/logs")
async def get_logs(request: Request):
    """Return the last N lines of the main log file for diagnostics, with server-side filtering."""
    try:
        lines = int(request.query_params.get('lines', 100))
    except Exception:
        lines = 100
    level = request.query_params.get('level', '').upper()
    search = request.query_params.get('search', '').lower()
        log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'tailsentry.log')
        # TODO: Restrict to authenticated/admin users only
        # Example: if not request.session.get('user') or not request.session.get('is_admin'): return JSONResponse(status_code=403, content={"error": "Forbidden"})
    try:
        if not os.path.exists(log_path):
            return {"logs": "Log file not found."}
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if lines > 0 else all_lines
        # Server-side filtering
        filtered = []
        for line in last_lines:
            if level and f'- {level} -' not in line:
                continue
            if search and search not in line.lower():
                continue
            filtered.append(line)
        return {"logs": ''.join(filtered) if filtered else 'No logs found.'}
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return {"logs": f"Error reading logs: {e}"}

# Download full log file endpoint (for authenticated users)
@router.get("/api/logs/download")
async def download_logs(zip: bool = False):
    """Download the full current log file or a zipped archive."""
    # TODO: Add authentication check here
    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'tailsentry.log')
    if not os.path.exists(log_path):
        return JSONResponse(content={"error": "Log file not found."}, status_code=404)
    if zip:
        # Create a zip in memory
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(log_path, arcname="tailsentry.log")
        mem_zip.seek(0)
        return StreamingResponse(mem_zip, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=tailsentry_logs.zip"})
    else:
        return FileResponse(log_path, filename="tailsentry.log", media_type="text/plain")
