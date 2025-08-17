from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from auth import login_required
from tailscale_client import TailscaleClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard")
@login_required
async def dashboard(request: Request):
    status = TailscaleClient.status_json()
    hostname = TailscaleClient.get_hostname()
    ip = TailscaleClient.get_ip()
    role = []
    self_obj = status.get("Self", {})
    if isinstance(self_obj, dict):
        if self_obj.get("Capabilities", {}).get("ExitNode", False):
            role.append("Exit Node")
        if self_obj.get("Capabilities", {}).get("SubnetRouter", False):
            role.append("Subnet Router")
    peers = status.get("Peer", {})
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "hostname": hostname,
        "ip": ip,
        "role": ", ".join(role) if role else "None",
        "status": status,
        "peers": peers,
    })

# New alternative dashboard route
@router.get("/alt-dashboard")
async def alt_dashboard(request: Request):
    return templates.TemplateResponse("alt_dashboard.html", {
        "request": request,
    })
