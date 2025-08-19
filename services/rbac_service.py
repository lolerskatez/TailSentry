"""Role-Based Access Control (RBAC) implementation."""
from functools import wraps
from typing import Callable, List, Optional
from fastapi import Request, HTTPException
from audit import log_audit_event

def requires_permission(permission: str) -> Callable:
    """Decorator to check if user has required permission."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = request.session.get("user")
            if not user:
                log_audit_event(
                    event_type="auth",
                    user="anonymous",
                    action="access_denied",
                    resource=request.url.path,
                    status="failure",
                    details={"required_permission": permission},
                    ip_address=request.client.host if request.client else None
                )
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            # Get user's role and permissions
            role = user.get("role", "viewer")  # Default to viewer role
            if not has_permission(role, permission):
                log_audit_event(
                    event_type="auth",
                    user=user.get("username"),
                    action="access_denied",
                    resource=request.url.path,
                    status="failure",
                    details={
                        "required_permission": permission,
                        "user_role": role
                    },
                    ip_address=request.client.host if request.client else None
                )
                raise HTTPException(status_code=403, detail="Permission denied")
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    role_permissions = {
        "admin": [
            "tailscale:key:create",
            "tailscale:key:revoke",
            "tailscale:config:edit",
            "tailscale:service:control",
            "user:manage",
            "audit:view"
        ],
        "operator": [
            "tailscale:key:create",  # With expiry limits
            "tailscale:service:restart",
            "tailscale:status:view"
        ],
        "viewer": [
            "tailscale:status:view"
        ]
    }
    
    return permission in role_permissions.get(role, [])
