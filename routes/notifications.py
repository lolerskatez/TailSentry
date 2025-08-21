"""
TailSentry Notifications System
Handles SMTP, Telegram, Discord notifications and configuration
"""

import os
import json
import logging
import smtplib
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr, validator
from dotenv import load_dotenv, set_key, find_dotenv
from routes.user import get_current_user
import httpx

try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
except ImportError:
    # Fallback for environments without email support
    MimeText = None
    MimeMultipart = None

logger = logging.getLogger("tailsentry.notifications")

router = APIRouter()

# Load environment variables
load_dotenv()

class SMTPSettings(BaseModel):
    enabled: bool = False
    smtp_server: str = Field(default="", max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    use_tls: bool = True
    use_ssl: bool = False
    username: str = Field(default="", max_length=255)
    password: Optional[str] = None
    from_email: EmailStr = Field(default="noreply@tailsentry.local")
    from_name: str = Field(default="TailSentry", max_length=100)
    
    @validator('smtp_port')
    def validate_port(cls, v):
        if v not in [25, 465, 587, 993, 995]:
            logger.warning(f"Non-standard SMTP port {v} specified")
        return v

class TelegramSettings(BaseModel):
    enabled: bool = False
    bot_token: Optional[str] = Field(default=None, min_length=10)
    chat_id: Optional[str] = Field(default=None, min_length=1)
    parse_mode: str = Field(default="HTML")
    disable_web_page_preview: bool = True
    
    @validator('bot_token')
    def validate_bot_token(cls, v):
        if v and not v.startswith(('bot', 'Bot')):
            if ':' in v:  # Valid token format
                return v
            raise ValueError('Invalid bot token format')
        return v
    
    @validator('parse_mode')
    def validate_parse_mode(cls, v):
        if v not in ['HTML', 'Markdown', 'MarkdownV2']:
            raise ValueError('parse_mode must be HTML, Markdown, or MarkdownV2')
        return v

class DiscordSettings(BaseModel):
    enabled: bool = False
    webhook_url: Optional[str] = Field(default=None, min_length=10)
    username: str = Field(default="TailSentry", max_length=80)
    avatar_url: Optional[str] = None
    embed_color: int = Field(default=0x3498db, ge=0, le=0xFFFFFF)
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        if v and not v.startswith('https://discord.com/api/webhooks/'):
            raise ValueError('Invalid Discord webhook URL')
        return v

class NotificationTemplate(BaseModel):
    event_type: str = Field(..., max_length=50)
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=2000)
    enabled: bool = True

class NotificationSettings(BaseModel):
    smtp: SMTPSettings = SMTPSettings()
    telegram: TelegramSettings = TelegramSettings()
    discord: DiscordSettings = DiscordSettings()
    global_enabled: bool = True
    retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_delay: int = Field(default=60, ge=10, le=3600)
    rate_limit_enabled: bool = True
    rate_limit_per_hour: int = Field(default=100, ge=1, le=1000)

# Configuration file paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
ENV_FILE = Path(find_dotenv() or BASE_DIR / ".env")
NOTIFICATIONS_CONFIG_FILE = CONFIG_DIR / "notifications_config.json"
TEMPLATES_FILE = CONFIG_DIR / "notification_templates.json"

# Default notification templates
DEFAULT_TEMPLATES = {
    "system_startup": {
        "title": "🚀 TailSentry Started",
        "message": "TailSentry has started successfully at {timestamp}",
        "enabled": True
    },
    "system_shutdown": {
        "title": "🛑 TailSentry Stopped",
        "message": "TailSentry has been shut down at {timestamp}",
        "enabled": True
    },
    "tailscale_connection": {
        "title": "🌐 Tailscale Connected",
        "message": "Device {device_name} connected to Tailscale network",
        "enabled": True
    },
    "tailscale_disconnection": {
        "title": "⚠️ Tailscale Disconnected",
        "message": "Device {device_name} disconnected from Tailscale network",
        "enabled": True
    },
    "peer_online": {
        "title": "✅ Peer Online",
        "message": "Peer {peer_name} ({peer_ip}) is now online",
        "enabled": False
    },
    "peer_offline": {
        "title": "❌ Peer Offline",
        "message": "Peer {peer_name} ({peer_ip}) has gone offline",
        "enabled": False
    },
    "subnet_route_change": {
        "title": "🔄 Subnet Route Changed",
        "message": "Subnet route configuration changed: {routes}",
        "enabled": True
    },
    "exit_node_change": {
        "title": "🚪 Exit Node Changed",
        "message": "Exit node changed to: {exit_node}",
        "enabled": True
    },
    "health_check_failure": {
        "title": "⚠️ Health Check Failed",
        "message": "Health check failed: {error_message}",
        "enabled": True
    },
    "configuration_change": {
        "title": "⚙️ Configuration Updated",
        "message": "TailSentry configuration was updated by {user}",
        "enabled": True
    },
    "security_alert": {
        "title": "🔒 Security Alert",
        "message": "Security event detected: {details}",
        "enabled": True
    },
    "backup_completed": {
        "title": "💾 Backup Completed",
        "message": "Configuration backup completed successfully",
        "enabled": True
    },
    "backup_failed": {
        "title": "❌ Backup Failed",
        "message": "Configuration backup failed: {error}",
        "enabled": True
    }
}

def get_current_notification_settings() -> NotificationSettings:
    """Load current notification configuration"""
    config = NotificationSettings()
    
    # Load from environment variables
    config.global_enabled = os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true"
    config.retry_attempts = int(os.getenv("NOTIFICATION_RETRY_ATTEMPTS", "3"))
    config.retry_delay = int(os.getenv("NOTIFICATION_RETRY_DELAY", "60"))
    config.rate_limit_enabled = os.getenv("NOTIFICATION_RATE_LIMIT", "true").lower() == "true"
    config.rate_limit_per_hour = int(os.getenv("NOTIFICATION_RATE_LIMIT_PER_HOUR", "100"))
    
    # SMTP settings
    config.smtp.enabled = os.getenv("SMTP_ENABLED", "false").lower() == "true"
    config.smtp.smtp_server = os.getenv("SMTP_SERVER", "")
    config.smtp.smtp_port = int(os.getenv("SMTP_PORT", "587"))
    config.smtp.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    config.smtp.use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    config.smtp.username = os.getenv("SMTP_USERNAME", "")
    config.smtp.password = os.getenv("SMTP_PASSWORD")
    config.smtp.from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@tailsentry.local")
    config.smtp.from_name = os.getenv("SMTP_FROM_NAME", "TailSentry")
    
    # Telegram settings
    config.telegram.enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    config.telegram.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    config.telegram.chat_id = os.getenv("TELEGRAM_CHAT_ID")
    config.telegram.parse_mode = os.getenv("TELEGRAM_PARSE_MODE", "HTML")
    config.telegram.disable_web_page_preview = os.getenv("TELEGRAM_DISABLE_PREVIEW", "true").lower() == "true"
    
    # Discord settings
    config.discord.enabled = os.getenv("DISCORD_ENABLED", "false").lower() == "true"
    config.discord.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    config.discord.username = os.getenv("DISCORD_USERNAME", "TailSentry")
    config.discord.avatar_url = os.getenv("DISCORD_AVATAR_URL")
    config.discord.embed_color = int(os.getenv("DISCORD_EMBED_COLOR", "0x3498db"), 16)
    
    # Load additional config from JSON file if it exists
    if NOTIFICATIONS_CONFIG_FILE.exists():
        try:
            with open(NOTIFICATIONS_CONFIG_FILE, 'r') as f:
                json_config = json.load(f)
                # Override with JSON config where environment variables are not set
                for section, values in json_config.items():
                    if hasattr(config, section):
                        section_obj = getattr(config, section)
                        for key, value in values.items():
                            if hasattr(section_obj, key):
                                setattr(section_obj, key, value)
        except Exception as e:
            logger.warning(f"Failed to load notifications config file: {e}")
    
    return config

def save_notification_settings(config: NotificationSettings) -> bool:
    """Save notification configuration to .env file"""
    try:
        # Create .env file if it doesn't exist
        if not ENV_FILE.exists():
            ENV_FILE.touch()
        
        # Update environment variables
        env_vars = {
            "NOTIFICATIONS_ENABLED": str(config.global_enabled).lower(),
            "NOTIFICATION_RETRY_ATTEMPTS": str(config.retry_attempts),
            "NOTIFICATION_RETRY_DELAY": str(config.retry_delay),
            "NOTIFICATION_RATE_LIMIT": str(config.rate_limit_enabled).lower(),
            "NOTIFICATION_RATE_LIMIT_PER_HOUR": str(config.rate_limit_per_hour),
            
            # SMTP
            "SMTP_ENABLED": str(config.smtp.enabled).lower(),
            "SMTP_SERVER": config.smtp.smtp_server,
            "SMTP_PORT": str(config.smtp.smtp_port),
            "SMTP_USE_TLS": str(config.smtp.use_tls).lower(),
            "SMTP_USE_SSL": str(config.smtp.use_ssl).lower(),
            "SMTP_USERNAME": config.smtp.username,
            "SMTP_FROM_EMAIL": config.smtp.from_email,
            "SMTP_FROM_NAME": config.smtp.from_name,
            
            # Telegram
            "TELEGRAM_ENABLED": str(config.telegram.enabled).lower(),
            "TELEGRAM_PARSE_MODE": config.telegram.parse_mode,
            "TELEGRAM_DISABLE_PREVIEW": str(config.telegram.disable_web_page_preview).lower(),
            
            # Discord
            "DISCORD_ENABLED": str(config.discord.enabled).lower(),
            "DISCORD_USERNAME": config.discord.username,
            "DISCORD_EMBED_COLOR": hex(config.discord.embed_color),
        }
        
        # Add sensitive values if they exist
        if config.smtp.password:
            env_vars["SMTP_PASSWORD"] = config.smtp.password
        if config.telegram.bot_token:
            env_vars["TELEGRAM_BOT_TOKEN"] = config.telegram.bot_token
        if config.telegram.chat_id:
            env_vars["TELEGRAM_CHAT_ID"] = config.telegram.chat_id
        if config.discord.webhook_url:
            env_vars["DISCORD_WEBHOOK_URL"] = config.discord.webhook_url
        if config.discord.avatar_url:
            env_vars["DISCORD_AVATAR_URL"] = config.discord.avatar_url
        
        # Write to .env file
        for key, value in env_vars.items():
            set_key(ENV_FILE, key, value)
        
        return True
    except Exception as e:
        logger.error(f"Failed to save notification settings to .env: {e}")
        return False

def load_notification_templates() -> Dict[str, Dict]:
    """Load notification templates"""
    if TEMPLATES_FILE.exists():
        try:
            with open(TEMPLATES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load notification templates: {e}")
    
    # Return default templates
    return DEFAULT_TEMPLATES.copy()

def save_notification_templates(templates: Dict[str, Dict]) -> bool:
    """Save notification templates"""
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(templates, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save notification templates: {e}")
        return False

class NotificationService:
    def __init__(self):
        self.rate_limit_cache = {}
        
    async def send_notification(self, event_type: str, **kwargs) -> Dict[str, Any]:
        """Send notification for a specific event"""
        config = get_current_notification_settings()
        
        if not config.global_enabled:
            return {"success": False, "message": "Notifications globally disabled"}
        
        # Check rate limiting
        if config.rate_limit_enabled and self._is_rate_limited():
            return {"success": False, "message": "Rate limit exceeded"}
        
        # Load templates
        templates = load_notification_templates()
        
        if event_type not in templates:
            return {"success": False, "message": f"Unknown event type: {event_type}"}
        
        template = templates[event_type]
        if not template.get("enabled", True):
            return {"success": False, "message": f"Notifications disabled for {event_type}"}
        
        # Format message
        title = template["title"].format(**kwargs)
        message = template["message"].format(**kwargs)
        
        results = {}
        
        # Send via enabled channels
        if config.smtp.enabled:
            results["smtp"] = await self._send_smtp(config.smtp, title, message)
        
        if config.telegram.enabled:
            results["telegram"] = await self._send_telegram(config.telegram, title, message)
        
        if config.discord.enabled:
            results["discord"] = await self._send_discord(config.discord, title, message)
        
        # Update rate limit
        if config.rate_limit_enabled:
            self._update_rate_limit()
        
        return {"success": True, "results": results}
    
    async def _send_smtp(self, smtp_config: SMTPSettings, title: str, message: str) -> Dict[str, Any]:
        """Send email notification"""
        try:
            if not MimeText or not MimeMultipart:
                return {"success": False, "error": "Email modules not available"}
            
            # Get admin emails from database
            from auth_user import get_admin_emails
            admin_emails = get_admin_emails()
            
            # Fallback to environment variable if no admin emails in database
            if not admin_emails:
                fallback_email = os.getenv("ALERT_EMAIL", smtp_config.from_email)
                admin_emails = [fallback_email] if fallback_email else []
            
            if not admin_emails:
                return {"success": False, "error": "No recipient emails configured"}
            
            results = []
            for recipient_email in admin_emails:
                # Create message for each recipient
                msg = MimeMultipart('alternative')
                msg['Subject'] = title
                msg['From'] = f"{smtp_config.from_name} <{smtp_config.from_email}>"
                msg['To'] = recipient_email
                
                # Create HTML and text versions
                text_part = MimeText(message, 'plain')
                html_part = MimeText(f"<html><body><h3>{title}</h3><p>{message}</p></body></html>", 'html')
                
                msg.attach(text_part)
                msg.attach(html_part)
                
                # Send email to this recipient
                try:
                    if smtp_config.use_ssl:
                        server = smtplib.SMTP_SSL(smtp_config.smtp_server, smtp_config.smtp_port)
                    else:
                        server = smtplib.SMTP(smtp_config.smtp_server, smtp_config.smtp_port)
                        if smtp_config.use_tls:
                            server.starttls()
                    
                    if smtp_config.username and smtp_config.password:
                        server.login(smtp_config.username, smtp_config.password)
                    
                    server.send_message(msg)
                    server.quit()
                    
                    results.append(f"Email sent to {recipient_email}")
                except Exception as email_error:
                    logger.error(f"Failed to send email to {recipient_email}: {email_error}")
                    results.append(f"Failed to send to {recipient_email}: {str(email_error)}")
            
            success_count = len([r for r in results if "sent to" in r])
            total_count = len(admin_emails)
            
            if success_count > 0:
                return {"success": True, "message": f"Email sent to {success_count}/{total_count} recipients", "details": results}
            else:
                return {"success": False, "error": f"Failed to send to all {total_count} recipients", "details": results}
        except Exception as e:
            logger.error(f"SMTP notification failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_telegram(self, tg_config: TelegramSettings, title: str, message: str) -> Dict[str, Any]:
        """Send Telegram notification"""
        try:
            url = f"https://api.telegram.org/bot{tg_config.bot_token}/sendMessage"
            
            # Format message
            if tg_config.parse_mode == "HTML":
                formatted_message = f"<b>{title}</b>\n\n{message}"
            elif tg_config.parse_mode in ["Markdown", "MarkdownV2"]:
                formatted_message = f"*{title}*\n\n{message}"
            else:
                formatted_message = f"{title}\n\n{message}"
            
            payload = {
                "chat_id": tg_config.chat_id,
                "text": formatted_message,
                "parse_mode": tg_config.parse_mode,
                "disable_web_page_preview": tg_config.disable_web_page_preview
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    return {"success": True, "message": "Telegram message sent successfully"}
                else:
                    return {"success": False, "error": f"Telegram API error: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_discord(self, discord_config: DiscordSettings, title: str, message: str) -> Dict[str, Any]:
        """Send Discord notification"""
        try:
            if not discord_config.webhook_url:
                return {"success": False, "error": "Discord webhook URL not configured"}
                
            embed = {
                "title": title,
                "description": message,
                "color": discord_config.embed_color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "TailSentry Notification System"
                }
            }
            
            payload = {
                "username": discord_config.username,
                "embeds": [embed]
            }
            
            if discord_config.avatar_url:
                payload["avatar_url"] = discord_config.avatar_url
            
            async with httpx.AsyncClient() as client:
                response = await client.post(discord_config.webhook_url, json=payload, timeout=30)
                
                if response.status_code in [200, 204]:
                    return {"success": True, "message": "Discord message sent successfully"}
                else:
                    return {"success": False, "error": f"Discord webhook error: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _is_rate_limited(self) -> bool:
        """Check if rate limit is exceeded"""
        current_hour = datetime.now().hour
        if current_hour not in self.rate_limit_cache:
            self.rate_limit_cache = {current_hour: 0}  # Reset cache
        
        config = get_current_notification_settings()
        return self.rate_limit_cache.get(current_hour, 0) >= config.rate_limit_per_hour
    
    def _update_rate_limit(self):
        """Update rate limit counter"""
        current_hour = datetime.now().hour
        if current_hour not in self.rate_limit_cache:
            self.rate_limit_cache = {current_hour: 1}
        else:
            self.rate_limit_cache[current_hour] += 1

# Global notification service instance
notification_service = NotificationService()

@router.get("/api/notification-settings")
async def get_notification_settings(request: Request):
    """Get current notification configuration"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        config = get_current_notification_settings()
        
        # Return sanitized config (no sensitive data)
        return {
            "global_enabled": config.global_enabled,
            "retry_attempts": config.retry_attempts,
            "retry_delay": config.retry_delay,
            "rate_limit_enabled": config.rate_limit_enabled,
            "rate_limit_per_hour": config.rate_limit_per_hour,
            "smtp": {
                "enabled": config.smtp.enabled,
                "smtp_server": config.smtp.smtp_server,
                "smtp_port": config.smtp.smtp_port,
                "use_tls": config.smtp.use_tls,
                "use_ssl": config.smtp.use_ssl,
                "username": config.smtp.username,
                "from_email": config.smtp.from_email,
                "from_name": config.smtp.from_name,
                "has_password": bool(config.smtp.password)
            },
            "telegram": {
                "enabled": config.telegram.enabled,
                "parse_mode": config.telegram.parse_mode,
                "disable_web_page_preview": config.telegram.disable_web_page_preview,
                "has_bot_token": bool(config.telegram.bot_token),
                "has_chat_id": bool(config.telegram.chat_id)
            },
            "discord": {
                "enabled": config.discord.enabled,
                "username": config.discord.username,
                "embed_color": config.discord.embed_color,
                "avatar_url": config.discord.avatar_url,
                "has_webhook_url": bool(config.discord.webhook_url)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get notification settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to load notification settings")

@router.post("/api/notification-settings")
async def update_notification_settings(request: Request, config: NotificationSettings):
    """Update notification configuration"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Save configuration
        if save_notification_settings(config):
            logger.info(f"Notification settings updated by user: {user.get('username', 'unknown')}")
            return {
                "success": True,
                "message": "Notification settings updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save notification settings")
            
    except Exception as e:
        logger.error(f"Failed to update notification settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

@router.get("/api/notification-templates")
async def get_notification_templates(request: Request):
    """Get notification templates"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        templates = load_notification_templates()
        return {"templates": templates}
    except Exception as e:
        logger.error(f"Failed to get notification templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to load notification templates")

@router.post("/api/notification-templates")
async def update_notification_templates(request: Request, templates_data: dict):
    """Update notification templates"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        templates = templates_data.get("templates", {})
        
        if save_notification_templates(templates):
            logger.info(f"Notification templates updated by user: {user.get('username', 'unknown')}")
            return {
                "success": True,
                "message": "Notification templates updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save notification templates")
            
    except Exception as e:
        logger.error(f"Failed to update notification templates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update templates: {str(e)}")

@router.post("/api/test-notification")
async def test_notification(request: Request, test_data: dict):
    """Test notification delivery"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        channel = test_data.get("channel", "all")
        
        # Send test notification
        result = await notification_service.send_notification(
            "system_startup",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            device_name="test-device"
        )
        
        return {
            "success": result["success"],
            "message": "Test notification sent",
            "results": result.get("results", {})
        }
        
    except Exception as e:
        logger.error(f"Failed to send test notification: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {str(e)}")

@router.post("/api/send-notification")
async def send_notification_endpoint(request: Request, notification_data: dict):
    """Send a custom notification"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        event_type = notification_data.get("event_type")
        kwargs = notification_data.get("data", {})
        
        if not event_type:
            raise HTTPException(status_code=400, detail="event_type is required")
        
        result = await notification_service.send_notification(event_type, **kwargs)
        
        return {
            "success": result["success"],
            "message": "Notification sent",
            "results": result.get("results", {})
        }
        
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")
