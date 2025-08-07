import os
import time
import secrets
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from helpers import SecurityHeadersMiddleware, start_scheduler, shutdown_scheduler

# Setup base directory
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "tailsentry.log"),
        logging.StreamHandler()
    ]
)

# Create logger
logger = logging.getLogger("tailsentry")

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="TailSentry",
    description="Secure Tailscale Management Dashboard",
    version="1.0.0",
    # Comment these out to enable OpenAPI docs in development
    docs_url=None if not os.getenv("DEVELOPMENT", "false").lower() == "true" else "/docs",
    redoc_url=None if not os.getenv("DEVELOPMENT", "false").lower() == "true" else "/redoc",
)

# Session config
SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET:
    # Generate a secure secret key if not provided
    SESSION_SECRET = secrets.token_hex(32)
    logger.warning("Generated random session secret. For persistent sessions, set SESSION_SECRET in .env")
    
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT_MINUTES", 30)) * 60
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="tailsentry_session",
    max_age=SESSION_TIMEOUT,
    same_site="strict",
    # Only set https_only=False during development
    https_only=not os.getenv("DEVELOPMENT", "false").lower() == "true",
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS - restrict to our own origin in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"] if os.getenv("DEVELOPMENT", "false").lower() == "true" else ["Content-Type", "X-Requested-With"],
)

# Application startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize app on startup"""
    logger.info(f"Starting TailSentry v1.0.0...")
    # Record startup time
    app.state.start_time = time.time()
    # Start background tasks
    start_scheduler()
    logger.info(f"TailSentry started successfully")
    
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down TailSentry...")
    shutdown_scheduler()
    uptime = time.time() - app.state.start_time
    logger.info(f"TailSentry shutdown complete. Uptime: {uptime:.2f} seconds")

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Import routes
from routes import auth, dashboard, tailscale, keys, api
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(tailscale.router)
app.include_router(keys.router)
app.include_router(api.router, prefix="/api")

# Global context processor for all templates
@app.middleware("http")
async def add_global_template_vars(request: Request, call_next):
    """Add global variables to all templates"""
    request.state.app_version = "1.0.0"
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
        "version": "1.0.0",
        "uptime": f"{uptime:.2f} seconds"
    }

# Root route
@app.get("/", include_in_schema=False)
async def root(request: Request):
    """Root endpoint, serves index page"""
    return templates.TemplateResponse("index.html", {"request": request})
