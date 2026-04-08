from fastapi import APIRouter, Request
 # from auth import login_required
from services.tailscale_service import TailscaleClient
from templates_manager import templates

router = APIRouter()

from routes.user import get_current_user

@router.get("/dashboard")
async def dashboard(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
    })

