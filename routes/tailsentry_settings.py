"""
TailSentry Settings Management API
Handles application configuration, environment variables, and system settings
"""

import os
import json
import bcrypt
import secrets
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv, set_key, find_dotenv
from routes.user import get_current_user

logger = logging.getLogger("tailsentry.settings")

router = APIRouter()

# Load environment variables
load_dotenv()

class SecuritySettings(BaseModel):
    session_timeout_minutes: int = Field(default=30, ge=5, le=1440)
    session_secret: Optional[str] = None
    admin_username: str = Field(default="admin", min_length=3)
    admin_password: Optional[str] = None  # Will be hashed
    force_https: bool = False
    cors_origins: List[str] = ["*"]

class TailscaleSettings(BaseModel):
    tailscale_pat: Optional[str] = None
    tailscale_tailnet: str = "-"
    api_timeout: int = Field(default=10, ge=1, le=60)
    force_live_data: bool = True

class ApplicationSettings(BaseModel):
    development: bool = False
    data_dir: str = "/app/data"
    log_level: str = Field(default="INFO")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class MonitoringSettings(BaseModel):
    health_check_enabled: bool = True
    health_check_interval: int = Field(default=300, ge=60, le=3600)
    alert_email: Optional[str] = None
    webhook_url: Optional[str] = None

class BackupSettings(BaseModel):
    backup_enabled: bool = True
    backup_retention_days: int = Field(default=30, ge=1, le=365)

class TailSentryConfig(BaseModel):
    security: SecuritySettings = SecuritySettings()
    tailscale: TailscaleSettings = TailscaleSettings()
    application: ApplicationSettings = ApplicationSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    backup: BackupSettings = BackupSettings()

# Configuration file paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
ENV_FILE = Path(find_dotenv() or BASE_DIR / ".env")
CONFIG_FILE = CONFIG_DIR / "tailsentry_config.json"

def get_current_config() -> TailSentryConfig:
    """Load current configuration from environment and config files"""
    config = TailSentryConfig()
    
    # Load from environment variables
    config.security.session_timeout_minutes = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    config.security.session_secret = os.getenv("SESSION_SECRET")
    config.security.admin_username = os.getenv("ADMIN_USERNAME", "admin")
    config.security.force_https = os.getenv("DEVELOPMENT", "false").lower() == "false"
    
    cors_origins = os.getenv("ALLOWED_ORIGIN", "*")
    config.security.cors_origins = [cors_origins] if cors_origins != "*" else ["*"]
    
    config.tailscale.tailscale_pat = os.getenv("TAILSCALE_PAT")
    config.tailscale.tailscale_tailnet = os.getenv("TAILSCALE_TAILNET", "-")
    config.tailscale.api_timeout = int(os.getenv("TAILSCALE_API_TIMEOUT", "10"))
    config.tailscale.force_live_data = os.getenv("TAILSENTRY_FORCE_LIVE_DATA", "true").lower() == "true"
    
    config.application.development = os.getenv("DEVELOPMENT", "false").lower() == "true"
    config.application.data_dir = os.getenv("TAILSENTRY_DATA_DIR", "/app/data")
    config.application.log_level = os.getenv("LOG_LEVEL", "INFO")
    config.application.log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    config.monitoring.health_check_enabled = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
    config.monitoring.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "300"))
    config.monitoring.alert_email = os.getenv("ALERT_EMAIL")
    config.monitoring.webhook_url = os.getenv("WEBHOOK_URL")
    
    config.backup.backup_enabled = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
    config.backup.backup_retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    
    # Load additional config from JSON file if it exists
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                json_config = json.load(f)
                # Merge JSON config with environment config
                # Environment variables take precedence
                for section, values in json_config.items():
                    if hasattr(config, section):
                        section_obj = getattr(config, section)
                        for key, value in values.items():
                            if hasattr(section_obj, key) and not os.getenv(f"{section.upper()}_{key.upper()}"):
                                setattr(section_obj, key, value)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
    
    return config

def save_config_to_env(config: TailSentryConfig) -> bool:
    """Save configuration to .env file"""
    try:
        # Create .env file if it doesn't exist
        if not ENV_FILE.exists():
            ENV_FILE.touch()
        
        # Update environment variables
        env_vars = {
            "SESSION_TIMEOUT_MINUTES": str(config.security.session_timeout_minutes),
            "ADMIN_USERNAME": config.security.admin_username,
            "DEVELOPMENT": str(config.application.development).lower(),
            "TAILSCALE_TAILNET": config.tailscale.tailscale_tailnet,
            "TAILSCALE_API_TIMEOUT": str(config.tailscale.api_timeout),
            "TAILSENTRY_FORCE_LIVE_DATA": str(config.tailscale.force_live_data).lower(),
            "TAILSENTRY_DATA_DIR": config.application.data_dir,
            "LOG_LEVEL": config.application.log_level,
            "LOG_FORMAT": config.application.log_format,
            "HEALTH_CHECK_ENABLED": str(config.monitoring.health_check_enabled).lower(),
            "HEALTH_CHECK_INTERVAL": str(config.monitoring.health_check_interval),
            "BACKUP_ENABLED": str(config.backup.backup_enabled).lower(),
            "BACKUP_RETENTION_DAYS": str(config.backup.backup_retention_days),
        }
        
        # Add optional values if they exist
        if config.security.session_secret:
            env_vars["SESSION_SECRET"] = config.security.session_secret
        if config.tailscale.tailscale_pat:
            env_vars["TAILSCALE_PAT"] = config.tailscale.tailscale_pat
        if config.monitoring.alert_email:
            env_vars["ALERT_EMAIL"] = config.monitoring.alert_email
        if config.monitoring.webhook_url:
            env_vars["WEBHOOK_URL"] = config.monitoring.webhook_url
        
        # Handle CORS origins
        if config.security.cors_origins and config.security.cors_origins != ["*"]:
            env_vars["ALLOWED_ORIGIN"] = config.security.cors_origins[0]
        else:
            env_vars["ALLOWED_ORIGIN"] = "*"
        
        # Write to .env file
        for key, value in env_vars.items():
            set_key(ENV_FILE, key, value)
        
        return True
    except Exception as e:
        logger.error(f"Failed to save config to .env: {e}")
        return False

def save_config_to_json(config: TailSentryConfig) -> bool:
    """Save configuration to JSON file (excluding sensitive data)"""
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        
        # Create sanitized config (no sensitive data)
        safe_config = {
            "security": {
                "session_timeout_minutes": config.security.session_timeout_minutes,
                "admin_username": config.security.admin_username,
                "force_https": config.security.force_https,
                "cors_origins": config.security.cors_origins
            },
            "tailscale": {
                "tailscale_tailnet": config.tailscale.tailscale_tailnet,
                "api_timeout": config.tailscale.api_timeout,
                "force_live_data": config.tailscale.force_live_data
            },
            "application": {
                "development": config.application.development,
                "data_dir": config.application.data_dir,
                "log_level": config.application.log_level,
                "log_format": config.application.log_format
            },
            "monitoring": {
                "health_check_enabled": config.monitoring.health_check_enabled,
                "health_check_interval": config.monitoring.health_check_interval,
                "alert_email": config.monitoring.alert_email
            },
            "backup": {
                "backup_enabled": config.backup.backup_enabled,
                "backup_retention_days": config.backup.backup_retention_days
            }
        }
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(safe_config, f, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Failed to save config to JSON: {e}")
        return False

@router.get("/api/tailsentry-settings")
async def get_tailsentry_settings(request: Request):
    """Get current TailSentry configuration"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        config = get_current_config()
        
        # Return sanitized config (no sensitive data)
        return {
            "security": {
                "session_timeout_minutes": config.security.session_timeout_minutes,
                "admin_username": config.security.admin_username,
                "force_https": config.security.force_https,
                "cors_origins": config.security.cors_origins,
                "has_session_secret": bool(config.security.session_secret)
            },
            "tailscale": {
                "tailscale_tailnet": config.tailscale.tailscale_tailnet,
                "api_timeout": config.tailscale.api_timeout,
                "force_live_data": config.tailscale.force_live_data,
                "has_pat": bool(config.tailscale.tailscale_pat)
            },
            "application": {
                "development": config.application.development,
                "data_dir": config.application.data_dir,
                "log_level": config.application.log_level,
                "log_format": config.application.log_format
            },
            "monitoring": {
                "health_check_enabled": config.monitoring.health_check_enabled,
                "health_check_interval": config.monitoring.health_check_interval,
                "alert_email": config.monitoring.alert_email,
                "has_webhook_url": bool(config.monitoring.webhook_url)
            },
            "backup": {
                "backup_enabled": config.backup.backup_enabled,
                "backup_retention_days": config.backup.backup_retention_days
            }
        }
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to load settings")

@router.post("/api/tailsentry-settings")
async def update_tailsentry_settings(request: Request, config: TailSentryConfig):
    """Update TailSentry configuration"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Validate configuration
        if config.security.admin_password:
            # Hash the password if provided
            hashed = bcrypt.hashpw(config.security.admin_password.encode(), bcrypt.gensalt())
            # Save hashed password to env
            set_key(ENV_FILE, "ADMIN_PASSWORD_HASH", hashed.decode())
        
        # Generate session secret if not provided
        if not config.security.session_secret:
            config.security.session_secret = secrets.token_hex(32)
        
        # Save configuration
        env_success = save_config_to_env(config)
        json_success = save_config_to_json(config)
        
        if env_success:
            logger.info(f"TailSentry settings updated by user: {user.get('username', 'unknown')}")
            
            # Send configuration change notification
            try:
                from notifications_manager import notify_configuration_change
                await notify_configuration_change(user.get('username', 'unknown'))
            except Exception as notify_error:
                logger.warning(f"Failed to send configuration change notification: {notify_error}")
            
            return {
                "success": True,
                "message": "Settings updated successfully",
                "restart_required": True  # Most config changes require restart
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save settings")
            
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

@router.post("/api/tailsentry-settings/generate-secret")
async def generate_session_secret(request: Request):
    """Generate a new session secret"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        new_secret = secrets.token_hex(32)
        set_key(ENV_FILE, "SESSION_SECRET", new_secret)
        
        return {
            "success": True,
            "secret": new_secret,
            "message": "New session secret generated"
        }
    except Exception as e:
        logger.error(f"Failed to generate session secret: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate session secret")

@router.post("/api/tailsentry-settings/test-webhook")
async def test_webhook(request: Request):
    """Test webhook configuration"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        import httpx
        config = get_current_config()
        
        if not config.monitoring.webhook_url:
            raise HTTPException(status_code=400, detail="No webhook URL configured")
        
        # Send test message
        test_payload = {
            "text": "🧪 TailSentry webhook test",
            "username": "TailSentry",
            "timestamp": str(time.time()),
            "source": "settings_test"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config.monitoring.webhook_url,
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Webhook test successful"}
            else:
                return {
                    "success": False, 
                    "message": f"Webhook test failed: {response.status_code}"
                }
                
    except Exception as e:
        logger.error(f"Webhook test failed: {e}")
        return {"success": False, "message": f"Webhook test failed: {str(e)}"}

@router.get("/api/tailsentry-settings/system-info")
async def get_system_info(request: Request):
    """Get system information for diagnostics"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        import platform
        import psutil
        
        # Get disk usage for data directory
        data_dir = Path(os.getenv("TAILSENTRY_DATA_DIR", "/app/data"))
        disk_usage = {}
        if data_dir.exists():
            try:
                import shutil
                total, used, free = shutil.disk_usage(data_dir)
                disk_usage = {
                    "total": total,
                    "free": free,
                    "used": used
                }
            except Exception:
                disk_usage = {"error": "Unable to get disk usage"}
        
        return {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version()
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk": disk_usage,
            "env_file": {
                "exists": ENV_FILE.exists(),
                "path": str(ENV_FILE),
                "size": ENV_FILE.stat().st_size if ENV_FILE.exists() else 0
            },
            "config_file": {
                "exists": CONFIG_FILE.exists(),
                "path": str(CONFIG_FILE),
                "size": CONFIG_FILE.stat().st_size if CONFIG_FILE.exists() else 0
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system information")

@router.post("/api/tailsentry-settings/backup-config")
async def backup_config(request: Request):
    """Create a backup of current configuration"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from datetime import datetime
        import shutil
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = CONFIG_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        # Backup .env file
        if ENV_FILE.exists():
            env_backup = backup_dir / f"env_backup_{timestamp}.txt"
            shutil.copy2(ENV_FILE, env_backup)
        
        # Backup config file
        if CONFIG_FILE.exists():
            config_backup = backup_dir / f"config_backup_{timestamp}.json"
            shutil.copy2(CONFIG_FILE, config_backup)
        
        return {
            "success": True,
            "message": f"Configuration backed up with timestamp {timestamp}",
            "backup_dir": str(backup_dir)
        }
    except Exception as e:
        logger.error(f"Failed to backup config: {e}")
        raise HTTPException(status_code=500, detail="Failed to backup configuration")

@router.get("/api/tailsentry-settings/export")
async def export_settings(request: Request):
    """Export settings for backup/sharing (sanitized)"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        config = get_current_config()
        
        # Export sanitized settings
        export_data = {
            "version": "1.0",
            "exported_at": str(datetime.now()),
            "exported_by": user.get("username", "unknown"),
            "settings": {
                "security": {
                    "session_timeout_minutes": config.security.session_timeout_minutes,
                    "admin_username": config.security.admin_username,
                    "force_https": config.security.force_https,
                    "cors_origins": config.security.cors_origins
                },
                "tailscale": {
                    "tailscale_tailnet": config.tailscale.tailscale_tailnet,
                    "api_timeout": config.tailscale.api_timeout,
                    "force_live_data": config.tailscale.force_live_data
                },
                "application": {
                    "development": config.application.development,
                    "data_dir": config.application.data_dir,
                    "log_level": config.application.log_level,
                    "log_format": config.application.log_format
                },
                "monitoring": {
                    "health_check_enabled": config.monitoring.health_check_enabled,
                    "health_check_interval": config.monitoring.health_check_interval,
                    "alert_email": config.monitoring.alert_email
                },
                "backup": {
                    "backup_enabled": config.backup.backup_enabled,
                    "backup_retention_days": config.backup.backup_retention_days
                }
            }
        }
        
        return export_data
    except Exception as e:
        logger.error(f"Failed to export settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to export settings")

@router.post("/api/tailsentry-settings/import")
async def import_settings(request: Request, settings_data: dict):
    """Import settings from backup/export"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Validate import data
        if "settings" not in settings_data:
            raise HTTPException(status_code=400, detail="Invalid settings format")
        
        # Create config from imported data
        settings = settings_data["settings"]
        config = TailSentryConfig()
        
        # Apply imported settings
        if "security" in settings:
            sec = settings["security"]
            config.security.session_timeout_minutes = sec.get("session_timeout_minutes", 30)
            config.security.admin_username = sec.get("admin_username", "admin")
            config.security.force_https = sec.get("force_https", False)
            config.security.cors_origins = sec.get("cors_origins", ["*"])
        
        if "tailscale" in settings:
            ts = settings["tailscale"]
            config.tailscale.tailscale_tailnet = ts.get("tailscale_tailnet", "-")
            config.tailscale.api_timeout = ts.get("api_timeout", 10)
            config.tailscale.force_live_data = ts.get("force_live_data", True)
        
        if "application" in settings:
            app = settings["application"]
            config.application.development = app.get("development", False)
            config.application.data_dir = app.get("data_dir", "/app/data")
            config.application.log_level = app.get("log_level", "INFO")
            config.application.log_format = app.get("log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        if "monitoring" in settings:
            mon = settings["monitoring"]
            config.monitoring.health_check_enabled = mon.get("health_check_enabled", True)
            config.monitoring.health_check_interval = mon.get("health_check_interval", 300)
            config.monitoring.alert_email = mon.get("alert_email")
        
        if "backup" in settings:
            bak = settings["backup"]
            config.backup.backup_enabled = bak.get("backup_enabled", True)
            config.backup.backup_retention_days = bak.get("backup_retention_days", 30)
        
        # Save imported configuration
        if save_config_to_env(config) and save_config_to_json(config):
            logger.info(f"Settings imported by user: {user.get('username', 'unknown')}")
            return {
                "success": True,
                "message": "Settings imported successfully",
                "restart_required": True
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save imported settings")
            
    except Exception as e:
        logger.error(f"Failed to import settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import settings: {str(e)}")
