from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import logging
from auth import verify_password, create_session, logout, ADMIN_USERNAME, ADMIN_PASSWORD_HASH, SESSION_SECRET, is_rate_limited, record_login_attempt
from pathlib import Path

logger = logging.getLogger("tailsentry")

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login")
def login_get(request: Request):
    create_session(request, ADMIN_USERNAME)
    return RedirectResponse("/", status_code=302)

@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    create_session(request, ADMIN_USERNAME)
    return RedirectResponse("/", status_code=302)

@router.get("/change-password")
def change_password_get(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    if not request.session.get("force_password_change"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("change_password.html", {"request": request, "error": None})

@router.post("/change-password")
async def change_password_post(request: Request, new_password: str = Form(...), confirm_password: str = Form(...)):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=302)
    if not request.session.get("force_password_change"):
        return RedirectResponse("/", status_code=302)
    if new_password != confirm_password:
        return templates.TemplateResponse("change_password.html", {"request": request, "error": "Passwords do not match."})
    # Update .env file with new hash
    from auth import hash_password, ADMIN_USERNAME
    new_hash = hash_password(new_password)
    # Update .env file
    env_path = Path(".env")
    lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()
    # Remove old admin lines
    lines = [l for l in lines if not l.startswith("ADMIN_USERNAME=") and not l.startswith("ADMIN_PASSWORD_HASH=")]
    lines.append(f"ADMIN_USERNAME={ADMIN_USERNAME}\n")
    lines.append(f"ADMIN_PASSWORD_HASH={new_hash}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
    # Remove force_password_change flag
    request.session.pop("force_password_change", None)
    return templates.TemplateResponse("change_password.html", {"request": request, "success": True})
    
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.get("/logout")
def logout_route(request: Request):
    logout(request)
    return RedirectResponse("/login", status_code=302)

@router.get("/debug-auth")
def debug_auth(request: Request):
    """Debug endpoint to check auth state - REMOVE IN PRODUCTION!"""
    return {
        "admin_username": ADMIN_USERNAME,
        "password_hash_set": bool(ADMIN_PASSWORD_HASH),
        "password_hash_length": len(ADMIN_PASSWORD_HASH) if ADMIN_PASSWORD_HASH else 0,
        "session_secret_set": bool(SESSION_SECRET)
    }
