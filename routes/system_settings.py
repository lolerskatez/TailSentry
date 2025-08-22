from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import logging
from dotenv import load_dotenv, set_key, find_dotenv
from routes.user import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger("tailsentry.system_settings")

# Load environment variables
load_dotenv()

@router.get("/settings/system")
async def system_settings_page(request: Request):
    """Display system settings page"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)
    
    # Get current environment settings (without exposing sensitive values)
    settings = {
        "tailscale_pat_configured": bool(os.getenv("TAILSCALE_PAT")),
        "tailscale_tailnet": os.getenv("TAILSCALE_TAILNET", "-"),
        "development_mode": os.getenv("DEVELOPMENT", "false").lower() == "true",
        "force_live_data": os.getenv("TAILSENTRY_FORCE_LIVE_DATA", "true").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "session_timeout": os.getenv("SESSION_TIMEOUT_MINUTES", "30"),
    }
    
    return templates.TemplateResponse("system_settings.html", {
        "request": request,
        "current_user": current_user,
        "settings": settings
    })

@router.post("/api/system-settings")
async def update_system_settings(request: Request):
    """Update system settings via API"""
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    
    try:
        data = await request.json()
        env_file = find_dotenv()
        
        if not env_file:
            return JSONResponse({"error": ".env file not found"}, status_code=500)
        
        # Update environment variables
        updated_keys = []
        
        # Handle Tailscale PAT (only update if provided)
        if "tailscale_pat" in data and data["tailscale_pat"].strip():
            set_key(env_file, "TAILSCALE_PAT", f"'{data['tailscale_pat'].strip()}'")
            updated_keys.append("TAILSCALE_PAT")
            
        # Handle other settings
        if "tailscale_tailnet" in data:
            set_key(env_file, "TAILSCALE_TAILNET", f"'{data['tailscale_tailnet']}'")
            updated_keys.append("TAILSCALE_TAILNET")
            
        if "development_mode" in data:
            set_key(env_file, "DEVELOPMENT", f"'{str(data['development_mode']).lower()}'")
            updated_keys.append("DEVELOPMENT")
            
        if "force_live_data" in data:
            set_key(env_file, "TAILSENTRY_FORCE_LIVE_DATA", f"'{str(data['force_live_data']).lower()}'")
            updated_keys.append("TAILSENTRY_FORCE_LIVE_DATA")
            
        if "log_level" in data:
            set_key(env_file, "LOG_LEVEL", f"'{data['log_level']}'")
            updated_keys.append("LOG_LEVEL")
            
        if "session_timeout" in data:
            set_key(env_file, "SESSION_TIMEOUT_MINUTES", f"'{data['session_timeout']}'")
            updated_keys.append("SESSION_TIMEOUT_MINUTES")
        
        # Reload environment variables
        load_dotenv(override=True)
        
        logger.info(f"System settings updated by {current_user.get('username')}: {updated_keys}")
        
        return JSONResponse({
            "success": True,
            "message": f"Settings updated successfully. Updated: {', '.join(updated_keys)}",
            "restart_required": "TAILSCALE_PAT" in updated_keys or "LOG_LEVEL" in updated_keys
        })
        
    except Exception as e:
        logger.error(f"Failed to update system settings: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to update settings: {str(e)}"}, status_code=500)

@router.post("/api/clear-tailscale-pat")
async def clear_tailscale_pat(request: Request):
    """Clear the Tailscale PAT (useful for testing demo mode)"""
    current_user = get_current_user(request)
    if not current_user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    
    try:
        env_file = find_dotenv()
        if not env_file:
            return JSONResponse({"error": ".env file not found"}, status_code=500)
        
        # Comment out the TAILSCALE_PAT line
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        with open(env_file, 'w') as f:
            for line in lines:
                if line.strip().startswith('TAILSCALE_PAT='):
                    f.write(f"# {line}")
                else:
                    f.write(line)
        
        # Reload environment
        load_dotenv(override=True)
        
        logger.info(f"Tailscale PAT cleared by {current_user.get('username')}")
        
        return JSONResponse({
            "success": True,
            "message": "Tailscale PAT cleared. Application will use demo data."
        })
        
    except Exception as e:
        logger.error(f"Failed to clear Tailscale PAT: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to clear PAT: {str(e)}"}, status_code=500)
