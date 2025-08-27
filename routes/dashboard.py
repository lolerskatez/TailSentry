from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
 # from auth import login_required
from services.tailscale_service import TailscaleClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")

from routes.user import get_current_user

@router.get("/dashboard")
async def dashboard(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
    })

@router.get("/alt-dashboard")
async def alt_dashboard(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("alt_dashboard.html", {
        "request": request,
        "user": user,
    })

