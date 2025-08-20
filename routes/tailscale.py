from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
 # from auth import login_required
from services.tailscale_service import TailscaleClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/subnets")
def subnets(request: Request):
    subnets = TailscaleClient.subnet_routes()
    return templates.TemplateResponse("subnets.html", {"request": request, "subnets": subnets})

@router.post("/subnets/toggle")
def toggle_subnet(request: Request, cidr: str = Form(...), enable: bool = Form(...)):
    result = TailscaleClient.set_subnet_routes([cidr] if enable else [])
    return RedirectResponse("/subnets", status_code=302)

@router.get("/exitnode")
def exitnode(request: Request):
    status = TailscaleClient.status_json()
    self_obj = status.get("Self", {}) if isinstance(status, dict) else {}
    # If Self is a list, use the first element, else use as dict
    if isinstance(self_obj, list) and self_obj:
        self_obj = self_obj[0]
    if not isinstance(self_obj, dict):
        self_obj = {}
    capabilities = self_obj.get("Capabilities", {}) if isinstance(self_obj, dict) else {}
    is_exit = capabilities.get("ExitNode", False) if isinstance(capabilities, dict) else False
    return templates.TemplateResponse("exitnode.html", {"request": request, "is_exit": is_exit})

@router.post("/exitnode/toggle")
def toggle_exitnode(request: Request, enable: bool = Form(...)):
    result = TailscaleClient.set_exit_node(enable)
    return RedirectResponse("/exitnode", status_code=302)

@router.get("/service")
def service(request: Request):
    status = TailscaleClient.service_status()
    logs = TailscaleClient.logs()
    return templates.TemplateResponse("service.html", {"request": request, "status": status, "logs": logs})

@router.post("/service/control")
def service_control(request: Request, action: str = Form(...)):
    result = TailscaleClient.service_control(action)
    return RedirectResponse("/service", status_code=302)
