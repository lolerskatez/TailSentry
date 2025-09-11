

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Import get_current_user from user routes for session checking
from routes.user import get_current_user


# Note: The `/settings` landing page (General) was removed per UX consolidation.
# Keep individual settings routes (appearance, users, tailscale, tailsentry, notifications)
# If a landing page is needed in future, recreate a new endpoint that points to
# an appropriate consolidated template.

@router.get("/settings/notifications")
async def notifications_settings(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("notifications.html", {
        "request": request, 
        "active_nav": "settings", 
        "user": user,
        "current_user": user
    })

@router.get("/settings/appearance")
async def appearance_settings(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("appearance.html", {
        "request": request, 
        "active_nav": "settings", 
        "user": user,
        "current_user": user
    })

@router.get("/settings/users")
async def manage_users(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    from auth_user import list_users
    users = list_users()
    return templates.TemplateResponse("users.html", {
        "request": request, 
        "users": users, 
        "active_nav": "settings", 
        "user": user, 
        "current_user": user
    })


@router.get("/settings/security")
async def security_settings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("security_settings.html", {
        "request": request, 
        "active_nav": "settings", 
        "user": user,
        "current_user": user
    })

@router.get("/settings/tailscale")
async def tailscale_settings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("tailscale_settings.html", {
        "request": request, 
        "active_nav": "settings", 
        "user": user,
        "current_user": user
    })

@router.get("/settings/tailsentry")
async def tailsentry_settings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("tailsentry_settings.html", {
        "request": request, 
        "active_nav": "settings", 
        "user": user,
        "current_user": user
    })
