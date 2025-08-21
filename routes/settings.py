from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
 # from auth import login_required

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/tailscale-settings")
async def tailscale_settings(request: Request):
    return templates.TemplateResponse("tailscale_settings.html", {"request": request})
