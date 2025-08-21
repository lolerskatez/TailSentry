
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/settings")
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@router.get("/tailscale-settings")
async def tailscale_settings(request: Request):
    return templates.TemplateResponse("tailscale_settings.html", {"request": request})
