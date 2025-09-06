"""
SMTP Security Middleware for TailSentry
Provides additional security layers for SMTP operations
"""

import logging
import time
import hashlib
from typing import Dict, Optional
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SMTPSecurityMiddleware:
    """Security middleware for SMTP operations"""
    
    # Rate limiting for configuration changes
    _config_change_attempts = {}
    _failed_auth_attempts = {}
    
    # Security settings
    MAX_CONFIG_CHANGES_PER_HOUR = 10
    MAX_FAILED_AUTH_PER_IP = 5
    AUTH_LOCKOUT_DURATION = 300  # 5 minutes
    
    @classmethod
    def get_client_identifier(cls, request) -> str:
        """Get unique identifier for client (IP + user agent hash)"""
        try:
            client_ip = request.client.host if hasattr(request, 'client') else 'unknown'
            user_agent = request.headers.get('user-agent', '')
            ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
            return f"{client_ip}_{ua_hash}"
        except:
            return "unknown_client"
    
    @classmethod
    def check_config_change_rate_limit(cls, client_id: str) -> bool:
        """Check if client can make configuration changes"""
        now = time.time()
        hour_key = f"{client_id}_{int(now // 3600)}"
        
        # Clean old entries
        old_keys = [k for k in cls._config_change_attempts.keys() 
                   if k.endswith(f"_{int(now // 3600) - 2}")]
        for key in old_keys:
            del cls._config_change_attempts[key]
        
        # Check current hour limit
        current_attempts = cls._config_change_attempts.get(hour_key, 0)
        if current_attempts >= cls.MAX_CONFIG_CHANGES_PER_HOUR:
            logger.warning(f"Config change rate limit exceeded for client: {client_id}")
            return False
        
        return True
    
    @classmethod
    def record_config_change(cls, client_id: str):
        """Record a configuration change attempt"""
        now = time.time()
        hour_key = f"{client_id}_{int(now // 3600)}"
        cls._config_change_attempts[hour_key] = cls._config_change_attempts.get(hour_key, 0) + 1
    
    @classmethod
    def check_auth_attempts(cls, client_id: str) -> bool:
        """Check if client is locked out due to failed auth attempts"""
        now = time.time()
        
        if client_id in cls._failed_auth_attempts:
            attempts, last_attempt = cls._failed_auth_attempts[client_id]
            
            # Reset if lockout period has passed
            if now - last_attempt > cls.AUTH_LOCKOUT_DURATION:
                del cls._failed_auth_attempts[client_id]
                return True
            
            # Check if locked out
            if attempts >= cls.MAX_FAILED_AUTH_PER_IP:
                logger.warning(f"Client {client_id} locked out due to failed auth attempts")
                return False
        
        return True
    
    @classmethod
    def record_failed_auth(cls, client_id: str):
        """Record a failed authentication attempt"""
        now = time.time()
        
        if client_id in cls._failed_auth_attempts:
            attempts, _ = cls._failed_auth_attempts[client_id]
            cls._failed_auth_attempts[client_id] = (attempts + 1, now)
        else:
            cls._failed_auth_attempts[client_id] = (1, now)
    
    @classmethod
    def clear_failed_auth(cls, client_id: str):
        """Clear failed authentication attempts for client"""
        if client_id in cls._failed_auth_attempts:
            del cls._failed_auth_attempts[client_id]
    
    @classmethod
    def validate_smtp_operation(cls, operation_type: str, client_id: str, user_data: dict) -> Dict[str, any]:
        """Validate SMTP operation with security checks"""
        
        # Check authentication lockout
        if not cls.check_auth_attempts(client_id):
            return {
                "allowed": False,
                "reason": "Client temporarily locked due to failed authentication attempts",
                "retry_after": cls.AUTH_LOCKOUT_DURATION
            }
        
        # Check configuration change rate limiting
        if operation_type in ['config_save', 'config_test']:
            if not cls.check_config_change_rate_limit(client_id):
                return {
                    "allowed": False,
                    "reason": "Configuration change rate limit exceeded",
                    "retry_after": 3600
                }
        
        # Check user permissions
        if not user_data or not user_data.get('is_admin', False):
            return {
                "allowed": False,
                "reason": "Administrative privileges required for SMTP operations"
            }
        
        return {"allowed": True}
    
    @classmethod
    def log_smtp_operation(cls, operation_type: str, client_id: str, user_data: dict, success: bool, details: str = ""):
        """Log SMTP operation for audit trail"""
        username = user_data.get('username', 'unknown') if user_data else 'unknown'
        status = "SUCCESS" if success else "FAILED"
        
        logger.info(f"SMTP Operation - Type: {operation_type}, Client: {client_id}, "
                   f"User: {username}, Status: {status}, Details: {details}")
        
        # Record configuration change
        if operation_type in ['config_save', 'config_test'] and success:
            cls.record_config_change(client_id)

def smtp_security_required(operation_type: str):
    """Decorator to add security checks to SMTP operations"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            try:
                # Get client identifier
                client_id = SMTPSecurityMiddleware.get_client_identifier(request)
                
                # Get user data (assume get_current_user function exists)
                from routes.user import get_current_user
                user = get_current_user(request)
                
                # Validate operation
                validation = SMTPSecurityMiddleware.validate_smtp_operation(
                    operation_type, client_id, user
                )
                
                if not validation["allowed"]:
                    SMTPSecurityMiddleware.log_smtp_operation(
                        operation_type, client_id, user, False, validation["reason"]
                    )
                    
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429 if "rate limit" in validation["reason"] else 403,
                        detail=validation["reason"],
                        headers={"Retry-After": str(validation.get("retry_after", 3600))}
                    )
                
                # Execute the function
                result = await func(request, *args, **kwargs)
                
                # Log successful operation
                SMTPSecurityMiddleware.log_smtp_operation(
                    operation_type, client_id, user, True
                )
                
                return result
                
            except Exception as e:
                # Log failed operation
                client_id = SMTPSecurityMiddleware.get_client_identifier(request)
                user = get_current_user(request) if 'get_current_user' in globals() else None
                
                SMTPSecurityMiddleware.log_smtp_operation(
                    operation_type, client_id, user, False, str(e)
                )
                
                raise
        
        return wrapper
    return decorator
