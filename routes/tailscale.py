from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from auth import login_required
from tailscale_client import TailscaleClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/subnets")
@login_required
def subnets(request: Request):
    subnets = TailscaleClient.subnet_routes()
    return templates.TemplateResponse("subnets.html", {"request": request, "subnets": subnets})

@router.post("/subnets/toggle")
@login_required
def toggle_subnet(request: Request, cidr: str = Form(...), enable: bool = Form(...)):
    result = TailscaleClient.set_subnet_routes([cidr] if enable else [])
    return RedirectResponse("/subnets", status_code=302)

@router.get("/exitnode")
@login_required
def exitnode(request: Request):
    status = TailscaleClient.status_json()
    is_exit = status.get("Self", {}).get("Capabilities", {}).get("ExitNode", False)
    return templates.TemplateResponse("exitnode.html", {"request": request, "is_exit": is_exit})

@router.post("/exitnode/toggle")
@login_required
def toggle_exitnode(request: Request, enable: bool = Form(...)):
    result = TailscaleClient.set_exit_node(enable)
    return RedirectResponse("/exitnode", status_code=302)

@router.get("/service")
@login_required
def service(request: Request):
    status = TailscaleClient.service_status()
    logs = TailscaleClient.logs()
    return templates.TemplateResponse("service.html", {"request": request, "status": status, "logs": logs})

@router.post("/service/control")
@login_required
def service_control(request: Request, action: str = Form(...)):
    result = TailscaleClient.service_control(action)
    return RedirectResponse("/service", status_code=302)
