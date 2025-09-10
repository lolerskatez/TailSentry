import os
import time
import secrets
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from middleware.security import SecurityHeadersMiddleware
from helpers import start_scheduler, shutdown_scheduler
from version import VERSION

# Set process title for proper identification by Tailscale
try:
    from setproctitle import setproctitle
    setproctitle("TailSentry")
except ImportError:
    # Fallback if setproctitle is not available
    pass

# Setup base directory
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


# Configure logging with rotation
from logging.handlers import RotatingFileHandler
log_file = LOG_DIR / "tailsentry.log"
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')  # 5MB per file, 5 backups
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
# Ensure UTF-8 encoding for console output on Windows
try:
    import os
    if os.name == 'nt':  # Windows
        import io
        stream_handler.stream = io.TextIOWrapper(stream_handler.stream.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass  # Fallback if encoding change fails
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler]
)

# Create logger
logger = logging.getLogger("tailsentry")

# Set the same format for all loggers
for name in ["apscheduler", "uvicorn", "fastapi"]:
    module_logger = logging.getLogger(name)
    module_logger.handlers = []  # Remove any existing handlers
    for handler in logging.root.handlers:
        module_logger.addHandler(handler)

# Load environment variables
load_dotenv()

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    # Startup
    logger.info(f"Starting TailSentry v1.0.0...")
    # Record startup time
    app.state.start_time = time.time()
    # Start background tasks
    start_scheduler()
    logger.info(f"TailSentry started successfully")
    
    # Send startup notification
    try:
        from notifications_manager import notify_system_startup
        await notify_system_startup()
    except Exception as e:
        logger.warning(f"Failed to send startup notification: {e}")
    
    # Start Discord bot if configured
    try:
        from services.discord_bot import start_discord_bot
        await start_discord_bot()
    except Exception as e:
        logger.warning(f"Failed to start Discord bot: {e}")
    
    # Initialize SSO providers
    try:
        from services.sso_auth import sso_auth
        sso_auth.initialize_providers()
        logger.info("SSO providers initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize SSO providers: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down TailSentry...")
    
    # Send shutdown notification
    try:
        from notifications_manager import notify_system_shutdown
        await notify_system_shutdown()
    except Exception as e:
        logger.warning(f"Failed to send shutdown notification: {e}")
    
    shutdown_scheduler()
    uptime = time.time() - app.state.start_time
    logger.info(f"TailSentry shutdown complete. Uptime: {uptime:.2f} seconds")

# Initialize FastAPI
app = FastAPI(
    title="TailSentry",
    description="Secure Tailscale Management Dashboard",
    version=VERSION,
    lifespan=lifespan,
    # Comment these out to enable OpenAPI docs in development
    docs_url=None if not os.getenv("DEVELOPMENT", "false").lower() == "true" else "/docs",
    redoc_url=None if not os.getenv("DEVELOPMENT", "false").lower() == "true" else "/redoc",
)


# Session config
from routes import user as user_routes

# Session configuration
SESSION_SECRET = os.getenv("SESSION_SECRET", "changeme")
if SESSION_SECRET == "changeme":
    logger.warning("SESSION_SECRET is using the default value 'changeme'. Set SESSION_SECRET in your .env for production!")
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT_MINUTES", 30)) * 60

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="tailsentry_session",
    max_age=SESSION_TIMEOUT,
    same_site="lax",  # Changed from "strict" to "lax" to fix redirect issues
    # Always set https_only=False for local network access
    https_only=False,
    # Add domain and path for better compatibility
    path="/",
)

# Include user authentication router
app.include_router(user_routes.router)

# Add security headers middleware with enhanced CSP
app.add_middleware(SecurityHeadersMiddleware, 
    csp={
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://cdn.jsdelivr.net"],  # For Alpine.js and Chart.js CDN
        'style-src': ["'self'", "'unsafe-inline'"],   # For Tailwind
        'img-src': ["'self'", "data:"],
        'connect-src': ["'self'", "ws:", "wss:"],     # For WebSocket
    }
)

# Add CSRF protection
from middleware.csrf import CSRFMiddleware
# Exempt /api/* endpoints, /health, and some others from CSRF protection
csrf_exempt_paths = {"/login", "/", "/api/*", "/health"}
app.add_middleware(CSRFMiddleware, exempt_paths=csrf_exempt_paths)

# Add rate limiting in production
# DISABLED for development/demo to avoid 429 errors
# if not os.getenv("DEVELOPMENT", "false").lower() == "true":
#     from middleware.rate_limit import RateLimitMiddleware
#     app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# Add compression for better performance
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add application monitoring
# from middleware.monitoring import MonitoringMiddleware
# app.add_middleware(MonitoringMiddleware)

# Add metrics collection if enabled
if os.getenv("METRICS_ENABLED", "false").lower() == "true":
    from middleware.metrics import metrics_middleware
    app.middleware("http")(metrics_middleware)

# Configure CORS - restrict to our own origin in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"] if os.getenv("DEVELOPMENT", "false").lower() == "true" else ["Content-Type", "X-Requested-With", "X-CSRF-Token"],
)

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Custom error handlers
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
import uuid

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 error handler"""
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    """Custom 403 error handler with detailed logging"""
    import traceback
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"403 Forbidden {error_id}: {str(exc)} | Path: {request.url.path} | Method: {request.method} | User-Agent: {request.headers.get('user-agent')} | Remote: {request.client.host if request.client else 'unknown'}\nTraceback:\n{traceback.format_exc()}")
    return templates.TemplateResponse("403.html", {"request": request, "error_id": error_id, "detail": str(exc)}, status_code=403)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Custom 500 error handler with detailed logging"""
    import traceback
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"Internal server error {error_id}: {str(exc)} | Path: {request.url.path} | Method: {request.method} | User-Agent: {request.headers.get('user-agent')} | Remote: {request.client.host if request.client else 'unknown'}\nTraceback:\n{traceback.format_exc()}")
    return templates.TemplateResponse("500.html", {
        "request": request, 
        "error_id": error_id,
        "detail": str(exc)
    }, status_code=500)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed logging and proper error page"""
    import traceback
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"Validation error {error_id}: {str(exc)} | Path: {request.url.path} | Method: {request.method} | User-Agent: {request.headers.get('user-agent')} | Remote: {request.client.host if request.client else 'unknown'}\nValidation details: {exc.errors()}\nTraceback:\n{traceback.format_exc()}")
    return templates.TemplateResponse("error.html", {
        "request": request,
        "status_code": 400,
        "title": "Invalid Request",
        "message": "The request contains invalid data. Please check your input and try again.",
        "error_id": error_id,
        "detail": str(exc)
    }, status_code=400)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler"""
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"Unhandled exception {error_id}: {str(exc)}", exc_info=True)
    return templates.TemplateResponse("error.html", {
        "request": request,
        "status_code": 500,
        "title": "Unexpected Error",
        "message": "An unexpected error occurred. We've been notified and are working to fix it."
    }, status_code=500)

# Import all routers (including settings) in a single line

# Import all routers (including settings) in a single line
from routes import tailscale, keys, api, config, version, dashboard, settings, authenticate, exit_node, logs, tailscale_settings, sso
app.include_router(tailscale.router)
app.include_router(keys.router)
app.include_router(api.router, prefix="/api")
app.include_router(config.router)
app.include_router(version.router)
app.include_router(dashboard.router)
from routes import down
app.include_router(down.router, prefix="/api")
# Import authenticate router
try:
    from routes import authenticate
    app.include_router(authenticate.router, prefix="/api")
except Exception as e:
    logger.error(f'Failed to import/register authenticate router: {e}')
app.include_router(settings.router)
app.include_router(exit_node.router)
app.include_router(logs.router)
# app.include_router(monitoring.router, prefix="/system", tags=["monitoring"])  # temporarily disabled

# Register the new Tailscale settings API
app.include_router(tailscale_settings.tailscale_settings_router)

# Register TailSentry settings API
from routes import tailsentry_settings
app.include_router(tailsentry_settings.router)

# Register SSO router
app.include_router(sso.router)

# Register Notifications API
from routes import notifications
app.include_router(notifications.router)

# Global context processor for all templates
@app.middleware("http")
async def add_global_template_vars(request: Request, call_next):
    """Add global variables to all templates"""
    request.state.app_version = VERSION
    request.state.app_name = "TailSentry"
    response = await call_next(request)
    return response

# Health check endpoint
@app.get("/health", include_in_schema=True)
async def health_check():
    """Health check endpoint for monitoring"""
    uptime = time.time() - app.state.start_time
    return {
        "status": "ok", 
        "version": VERSION,
        "uptime": f"{uptime:.2f} seconds"
    }

# Favicon route
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve favicon"""
    return FileResponse("static/favicon.ico")

# Root route

from routes.user import get_current_user

@app.get("/", include_in_schema=False)
async def root(request: Request):
    """Root endpoint, requires login to access dashboard"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

# Test route for debugging
@app.get("/test", include_in_schema=False)
async def test_route():
    """Simple test route that returns basic HTML"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Route</title>
        <style>
            body { 
                background: green; 
                color: white; 
                font-size: 24px; 
                padding: 20px; 
                font-family: Arial, sans-serif;
            }
        </style>
    </head>
    <body>
        <h1>Test Route Working!</h1>
        <p>If you can see this, the server is working correctly.</p>
        <p>This means the issue is with template rendering or static file loading.</p>
    </body>
    </html>
    """)

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )
