from fastapi import APIRouter, Request, Form, Depends, Response, status
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
    user = verify_user(username, password)
    if user:
        request.session["user"] = user["username"]
        if remember_me:
            request.session["remember_me"] = True
            request.session["max_age"] = 60*60*24*30  # 30 days
        else:
            request.session["remember_me"] = False
            request.session["max_age"] = None
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
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
    return templates.TemplateResponse("users.html", {"request": request, "users": list_users()})

@router.post("/users/delete")
def delete_user_route(request: Request, username: str = Form(...), user=Depends(get_current_user)):
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    delete_user(username)
    return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)

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
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": None, "success": None})

@router.post("/profile")
def profile_update(request: Request, email: str = Form(...), display_name: str = Form(""), current_password: str = Form(""), new_password: str = Form(""), user=Depends(get_current_user)):
    from auth_user import set_user_email, set_user_display_name, verify_user, get_db, pwd_context
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    error = None
    success = None
    # Update email
    if email and email != user.get("email"):
        if not current_password or not verify_user(user["username"], current_password):
            error = "Current password required to change email."
        else:
            set_user_email(user["username"], email)
            append_user_activity(user["username"], f"Changed email to {email}")
            success = "Email updated. "
    # Update display name
    if display_name != user.get("display_name"):
        set_user_display_name(user["username"], display_name)
        append_user_activity(user["username"], f"Changed display name to {display_name}")
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
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "error": error, "success": success})

@router.post("/users/role")
def set_role(request: Request, username: str = Form(...), role: str = Form(...), user=Depends(get_current_user)):
    from auth_user import set_user_role
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    set_user_role(username, role)
    return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)

@router.post("/users/active")
def set_active(request: Request, username: str = Form(...), active: int = Form(...), user=Depends(get_current_user)):
    from auth_user import set_user_active
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    set_user_active(username, bool(active))
    return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)
