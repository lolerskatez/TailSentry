from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
 # from auth import login_required
from services.tailscale_service import TailscaleClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
    })

