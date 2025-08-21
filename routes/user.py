from fastapi import APIRouter, Request, Form, Depends, Response, status, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from auth_user import create_user, verify_user, get_user, list_users, delete_user, init_db, get_user_activity_log, append_user_activity
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import aiosmtplib
from email_validator import validate_email, EmailNotValidError
import os

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Initialize DB on startup
init_db()

SESSION_SECRET = os.environ.get("SESSION_SECRET", "changeme")
serializer = URLSafeTimedSerializer(SESSION_SECRET)

RESET_TOKEN_EXPIRY = 3600  # 1 hour

async def send_reset_email(to_email, token):
    reset_link = f"http://localhost:8080/reset-password?token={token}"
    message = f"""Subject: TailSentry Password Reset\n\nClick the link to reset your password: {reset_link}\nIf you did not request this, ignore this email."""
    await aiosmtplib.send(
        message,
        hostname=os.environ.get("SMTP_HOST", "localhost"),
        port=int(os.environ.get("SMTP_PORT", 25)),
        username=os.environ.get("SMTP_USER"),
        password=os.environ.get("SMTP_PASS"),
        sender=os.environ.get("SMTP_FROM", "noreply@localhost"),
        recipients=[to_email],
    )

def get_current_user(request: Request):
    username = request.session.get("user")
    if username:
        return get_user(username)
    return None

@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login")
def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...), remember_me: str = Form(None)):
    import logging
    logger = logging.getLogger("tailsentry")
    
    # First check if user exists and get their status
    from auth_user import get_user
    existing_user = get_user(username)
    
    user = verify_user(username, password)
    if user:
        logger.info(f"[LOGIN] Successful login for active user: {username}")
        request.session["user"] = user["username"]
        if remember_me:
            request.session["remember_me"] = True
            request.session["max_age"] = 60*60*24*30  # 30 days
        else:
            request.session["remember_me"] = False
            request.session["max_age"] = None
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    else:
        # Check if it's a disabled account vs invalid credentials
        if existing_user:
            # Convert Row to dict first
            existing_user_dict = dict(existing_user)
            # User exists, check if account is disabled
            if existing_user_dict.get('active', 1) == 0:
                logger.warning(f"[LOGIN] Login attempt for disabled account: {username}")
                return templates.TemplateResponse("login.html", {"request": request, "error": "Account is disabled. Please contact an administrator."})
            else:
                logger.warning(f"[LOGIN] Invalid password for user: {username}")
                return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
        else:
            logger.warning(f"[LOGIN] Login attempt for non-existent user: {username}")
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.get("/logout")
def logout(request: Request, response: Response):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@router.get("/register")
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})

@router.post("/register")
def register(request: Request, username: str = Form(...), password: str = Form(...)):
    if create_user(username, password):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"})

@router.get("/users")
def users(request: Request, user=Depends(get_current_user)):
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("users.html", {
        "request": request, 
        "users": list_users(), 
        "current_user": user
    })

@router.post("/users/delete")
def delete_user_route(request: Request, username: str = Form(...), user=Depends(get_current_user)):
    import logging
    logger = logging.getLogger("tailsentry")
    
    if not user or user["role"] != "admin":
        logger.warning(f"[DELETE USER] Access denied - user: {user}")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Prevent admin from deleting their own account
    if user["username"] == username:
        logger.warning(f"[DELETE USER] Admin {user['username']} attempted to delete their own account")
        # Return to users page with error message
        from auth_user import list_users
        return templates.TemplateResponse("users.html", {
            "request": request, 
            "users": list_users(), 
            "current_user": user,
            "error": "You cannot delete your own account. Use another admin account to delete this one if needed."
        })
    
    logger.info(f"[DELETE USER] Admin {user['username']} deleting user: {username}")
    delete_user(username)
    logger.info(f"[DELETE USER] Successfully deleted user: {username}")
    return RedirectResponse(url="/settings/users", status_code=status.HTTP_302_FOUND)

# Change password endpoints
@router.get("/change-password")
def change_password_form(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("change_password.html", {"request": request, "error": None, "success": None})

@router.post("/change-password")
def change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...), user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    from auth_user import verify_user, get_db, pwd_context
    # Verify old password
    if not verify_user(user["username"], old_password):
        return templates.TemplateResponse("change_password.html", {"request": request, "error": "Current password is incorrect.", "success": None})
    # Update password
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET password_hash = ? WHERE username = ?', (pwd_context.hash(new_password), user["username"]))
    conn.commit()
    conn.close()
    return templates.TemplateResponse("change_password.html", {"request": request, "error": None, "success": "Password changed successfully."})

@router.get("/reset-password-request")
def reset_password_request_form(request: Request):
    return templates.TemplateResponse("reset_password_request.html", {"request": request, "error": None, "success": None})

@router.post("/reset-password-request")
async def reset_password_request(request: Request, email: str = Form(...)):
    from auth_user import get_user_by_email
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError:
        return templates.TemplateResponse("reset_password_request.html", {"request": request, "error": "Invalid email address.", "success": None})
    user = get_user_by_email(email)
    if not user:
        return templates.TemplateResponse("reset_password_request.html", {"request": request, "error": "No user with that email.", "success": None})
    token = serializer.dumps(email, salt="reset-password")
    await send_reset_email(email, token)
    return templates.TemplateResponse("reset_password_request.html", {"request": request, "error": None, "success": "Password reset link sent!"})

@router.get("/reset-password")
def reset_password_form(request: Request, token: str = ""):
    return templates.TemplateResponse("reset_password.html", {"request": request, "error": None, "success": None, "token": token})

@router.post("/reset-password")
def reset_password(request: Request, new_password: str = Form(...), token: str = Form(...)):
    from auth_user import get_user_by_email, get_db, pwd_context
    try:
        email = serializer.loads(token, salt="reset-password", max_age=RESET_TOKEN_EXPIRY)
    except SignatureExpired:
        return templates.TemplateResponse("reset_password.html", {"request": request, "error": "Token expired.", "success": None, "token": token})
    except BadSignature:
        return templates.TemplateResponse("reset_password.html", {"request": request, "error": "Invalid token.", "success": None, "token": token})
    user = get_user_by_email(email)
    if not user:
        return templates.TemplateResponse("reset_password.html", {"request": request, "error": "User not found.", "success": None, "token": token})
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET password_hash = ? WHERE email = ?', (pwd_context.hash(new_password), email))
    conn.commit()
    conn.close()
    return templates.TemplateResponse("reset_password.html", {"request": request, "error": None, "success": "Password updated!", "token": token})

@router.get("/profile")
def profile_form(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    # Attach activity log
    user = dict(user)
    user["activity_log"] = get_user_activity_log(user["username"])
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": None, "success": None, "active_nav": "profile"})

@router.post("/profile")
def profile_update(request: Request, email: str = Form(...), display_name: str = Form(""), current_password: str = Form(""), new_password: str = Form(""), user=Depends(get_current_user)):
    from auth_user import set_user_email, set_user_display_name, verify_user, get_db, pwd_context
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    error = None
    success = None
    # Convert user Row to dict for safe attribute access
    user_dict = dict(user)
    # Update email
    if email and email != user_dict.get("email"):
        if not current_password or not verify_user(user_dict["username"], current_password):
            error = "Current password required to change email."
        else:
            set_user_email(user_dict["username"], email)
            append_user_activity(user_dict["username"], f"Changed email to {email}")
            success = "Email updated. "
    # Update display name
    if display_name != user_dict.get("display_name"):
        set_user_display_name(user_dict["username"], display_name)
        append_user_activity(user_dict["username"], f"Changed display name to {display_name}")
        success = (success or "") + "Display name updated. "
    # Update password
    if new_password:
        if not current_password or not verify_user(user["username"], current_password):
            error = (error or "") + "Current password required to change password."
        else:
            conn = get_db()
            c = conn.cursor()
            c.execute('UPDATE users SET password_hash = ? WHERE username = ?', (pwd_context.hash(new_password), user["username"]))
            conn.commit()
            conn.close()
            append_user_activity(user["username"], "Changed password")
            success = (success or "") + "Password updated."
    # Reload user
    from auth_user import get_user
    user = get_user(user["username"])
    if user:
        user = dict(user)
        user["activity_log"] = get_user_activity_log(str(user["username"]))
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": error, "success": success, "active_nav": "profile"})

@router.post("/users/role")
def set_role(request: Request, username: str = Form(...), role: str = Form(...), user=Depends(get_current_user)):
    from auth_user import set_user_role
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    set_user_role(username, role)
    return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)

@router.post("/users/active")
def set_active(request: Request, username: str = Form(...), active: int = Form(None), user=Depends(get_current_user)):
    from auth_user import set_user_active, is_user_active
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    if active is None:
        # Toggle when not provided by the form
        current = is_user_active(username)
        set_user_active(username, not current)
    else:
        set_user_active(username, bool(active))
    return RedirectResponse(url="/settings/users", status_code=status.HTTP_302_FOUND)

# Add user
@router.post("/users/add")
def add_user(request: Request, name: str = Form(""), username: str = Form(...), role: str = Form("user"), password: str = Form(...), user=Depends(get_current_user)):
    import logging
    logger = logging.getLogger("tailsentry")
    logger.info(f"[ADD USER] Request from {request.client.host if request.client else 'unknown'} | name: {name} | username: {username} | role: {role} | password_len: {len(password) if password else 0}")
    
    if not user or user["role"] != "admin":
        logger.warning(f"[ADD USER] Access denied - user: {user}")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    from auth_user import create_user, get_db
    try:
        logger.info(f"[ADD USER] Attempting to create user: {username}")
        created = create_user(username, password, role)
        logger.info(f"[ADD USER] User creation result: {created}")
        if created and name:
            # Set display name if provided
            conn = get_db()
            c = conn.cursor()
            c.execute('UPDATE users SET display_name = ? WHERE username = ?', (name, username))
            conn.commit()
            conn.close()
            logger.info(f"[ADD USER] Display name set for {username}: {name}")
        logger.info(f"[ADD USER] Success - redirecting to /settings/users")
        return RedirectResponse(url="/settings/users", status_code=status.HTTP_302_FOUND)
    except HTTPException as e:
        # If CSRF or other error, show in modal
        logger.error(f"[ADD USER] HTTPException: {e}")
        error = e.detail if hasattr(e, 'detail') else str(e)
        return templates.TemplateResponse("users.html", {"request": request, "users": list_users(), "current_user": user, "error": error})
    except Exception as e:
        logger.error(f"[ADD USER] General Exception: {type(e).__name__}: {e}")
        error = f"User creation failed: {str(e)}"
        return templates.TemplateResponse("users.html", {"request": request, "users": list_users(), "current_user": user, "error": error})

# Edit user
@router.post("/users/edit")
def edit_user(request: Request,
              original_username: str = Form(...),
              name: str = Form(""),
              username: str = Form(...),
              role: str = Form("user"),
              password: str = Form(""),
              user=Depends(get_current_user)):
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    from auth_user import get_db, pwd_context
    import sqlite3
    conn = get_db()
    try:
        c = conn.cursor()
        # Update core fields
        c.execute('UPDATE users SET username = ?, role = ? WHERE username = ?', (username, role, original_username))
        # Optionally update password
        if password:
            c.execute('UPDATE users SET password_hash = ? WHERE username = ?', (pwd_context.hash(password), username))
        # Update display name
        c.execute('UPDATE users SET display_name = ? WHERE username = ?', (name, username))
        conn.commit()
    except sqlite3.IntegrityError:
        # Username conflict; ignore and continue
        conn.rollback()
    finally:
        conn.close()
    return RedirectResponse(url="/settings/users", status_code=status.HTTP_302_FOUND)
