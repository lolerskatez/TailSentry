

from fastapi import APIRouter, Request

from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/settings")
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@router.get("/settings/users")
async def manage_users(request: Request):
    from auth_user import list_users
    users = list_users()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})


@router.get("/settings/tailscale")
async def tailscale_settings_page(request: Request):
    return templates.TemplateResponse("tailscale_settings.html", {"request": request})
