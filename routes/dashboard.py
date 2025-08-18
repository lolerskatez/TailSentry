from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from auth import login_required
from tailscale_client import TailscaleClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard")
@login_required
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
    })

