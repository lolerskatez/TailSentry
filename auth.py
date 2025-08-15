import os
import bcrypt
from pathlib import Path
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from itsdangerous import Signer
from datetime import datetime, timedelta

# Create .env file if it doesn't exist
env_path = Path(".env")
if not env_path.exists():
    env_path.touch()

load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "changeme")
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT_MINUTES", 30))

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

signer = Signer(SESSION_SECRET)

# --- Auth helpers ---
def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

# Add rate limiting for failed login attempts
MAX_ATTEMPTS = 5  # Max failed attempts
ATTEMPT_WINDOW = 15 * 60  # 15 minutes in seconds
login_attempts = {}  # IP -> {count: int, first_attempt: datetime}

def is_rate_limited(ip: str) -> bool:
    now = datetime.utcnow()
    if ip not in login_attempts:
        return False
    
    # Reset if outside window
    if (now - login_attempts[ip]["first_attempt"]).total_seconds() > ATTEMPT_WINDOW:
        login_attempts[ip] = {"count": 0, "first_attempt": now}
        return False
    
    return login_attempts[ip]["count"] >= MAX_ATTEMPTS

def record_login_attempt(ip: str, success: bool):
    now = datetime.utcnow()
    if success:
        if ip in login_attempts:
            del login_attempts[ip]
        return
    
    if ip not in login_attempts:
        login_attempts[ip] = {"count": 1, "first_attempt": now}
    else:
        # Reset if outside window
        if (now - login_attempts[ip]["first_attempt"]).total_seconds() > ATTEMPT_WINDOW:
            login_attempts[ip] = {"count": 1, "first_attempt": now}
        else:
            login_attempts[ip]["count"] += 1

def login_required(func):
    async def wrapper(request: Request, *args, **kwargs):
        session = request.session
        if not session.get("user"):
            return RedirectResponse("/login", status_code=302)
        
        # Session expiry
        if session.get("expires_at"):
            try:
                expiry = datetime.fromisoformat(session["expires_at"])
                if datetime.utcnow() > expiry:
                    request.session.clear()
                    return RedirectResponse("/login", status_code=302)
            except (ValueError, TypeError):
                # Invalid expiry format, clear session
                request.session.clear()
                return RedirectResponse("/login", status_code=302)
                
        # Refresh session timeout on activity
        create_session(request, session["user"])
        
        # Call the original function, handling both sync and async
        import inspect
        if inspect.iscoroutinefunction(func):
            return await func(request)
        else:
            return func(request)
    return wrapper

def create_session(request: Request, username: str):
    expires_at = (datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT)).isoformat()
    request.session["user"] = username
    request.session["expires_at"] = expires_at

def logout(request: Request):
    request.session.clear()
