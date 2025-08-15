from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import logging
from audit import log_audit_event
from auth import (
    verify_password, create_session, logout, 
    ADMIN_USERNAME, ADMIN_PASSWORD_HASH, SESSION_SECRET,
    is_rate_limited, record_login_attempt,
    is_first_run, setup_admin_account
)

logger = logging.getLogger("tailsentry")

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login")
def login_get(request: Request):
    # Redirect to setup if this is the first run
    if is_first_run():
        return RedirectResponse("/setup", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.get("/setup")
def setup_get(request: Request):
    # Redirect to login if already set up
    if not is_first_run():
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("onboarding.html", {"request": request, "error": None})

@router.post("/setup")
async def setup_post(request: Request):
    # Get client IP
    client_ip = request.client.host if request.client else request.headers.get("X-Forwarded-For", "unknown")
    
    # Redirect to login if already set up
    if not is_first_run():
        log_audit_event(
            event_type="auth",
            user="unknown",
            action="setup_attempt",
            resource="onboarding",
            status="failure",
            details={"reason": "already_setup"},
            ip_address=client_ip
        )
        return JSONResponse({"success": False, "message": "Setup already completed"}, status_code=400)
    
    try:
        # Parse JSON body
        body = await request.json()
        hostname = body.get("hostname", "").strip()
        tailscale_pat = body.get("tailscale_pat", "").strip()
        password = body.get("admin_password", "").strip()
        
        # Validate required fields
        if not hostname or not tailscale_pat or not password:
            return JSONResponse({"success": False, "message": "All fields are required"}, status_code=400)
        
        # Validate password
        if len(password) < 8:
            log_audit_event(
                event_type="auth",
                user="admin",
                action="setup_attempt",
                resource="onboarding",
                status="failure",
                details={"reason": "password_too_short"},
                ip_address=client_ip
            )
            return JSONResponse({"success": False, "message": "Password must be at least 8 characters"}, status_code=400)
        
        # Set up the admin account
        setup_admin_account("admin", password)
        
        # Log successful setup
        log_audit_event(
            event_type="auth",
            user="admin",
            action="setup_complete",
            resource="onboarding",
            status="success",
            details={"hostname": hostname},
            ip_address=client_ip
        )
        
        return JSONResponse({"success": True, "message": "Setup completed successfully"})
        
    except Exception as e:
        logger.error(f"Setup error: {str(e)}", exc_info=True)
        return JSONResponse({"success": False, "message": "Internal server error"}, status_code=500)

@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    # Check if first run
    if is_first_run():
        return RedirectResponse("/setup", status_code=302)
        
    client_host = request.client.host if request.client else request.headers.get("X-Forwarded-For", "unknown")
    
    # Check for rate limiting
    if is_rate_limited(client_host):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Too many login attempts. Please try again later."
        })
    
    # Attempt login
    logger.info(f"Login attempt - Username received: '{username}', Expected: '{ADMIN_USERNAME}'")
    logger.info(f"Username match: {username == ADMIN_USERNAME}")
    logger.info(f"Password hash available: {'Yes' if ADMIN_PASSWORD_HASH else 'No'}")
    
    password_match = verify_password(password, ADMIN_PASSWORD_HASH)
    logger.info(f"Password verification result: {password_match}")
    
    success = username == ADMIN_USERNAME and password_match
    logger.info(f"Overall login success: {success}")
    
    record_login_attempt(client_host, success)
    
    if success:
        create_session(request, username)
        return RedirectResponse("/", status_code=302)
    
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
        "session_secret_set": bool(SESSION_SECRET),
        "is_first_run": is_first_run()
    }
