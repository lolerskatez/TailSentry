from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from auth import (
    verify_password, create_session, logout, 
    ADMIN_USERNAME, ADMIN_PASSWORD_HASH,
    is_rate_limited, record_login_attempt
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login")
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    client_host = request.client.host
    
    # Check for rate limiting
    if is_rate_limited(client_host):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Too many login attempts. Please try again later."
        })
    
    # Attempt login
    success = username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD_HASH)
    record_login_attempt(client_host, success)
    
    if success:
        create_session(request, username)
        return RedirectResponse("/dashboard", status_code=302)
    
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.get("/logout")
def logout_route(request: Request):
    logout(request)
    return RedirectResponse("/login", status_code=302)
