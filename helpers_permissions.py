"""Helper functions for permission-based UI visibility in TailSentry."""
from functools import wraps
from fastapi import HTTPException, Request
from typing import List, Optional, Callable, Any


def get_user_role(request: Request) -> Optional[str]:
    """Get the current user's role from session.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User role (admin, operator, viewer) or None if not authenticated
    """
    try:
        user = request.session.get("user")
        if user:
            return user.get("role")
    except:
        pass
    return None


def get_user_id(request: Request) -> Optional[int]:
    """Get the current user's ID from session.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User ID or None if not authenticated
    """
    try:
        user = request.session.get("user")
        if user:
            return user.get("id")
    except:
        pass
    return None


def has_role(request: Request, required_roles: List[str]) -> bool:
    """Check if user has one of the required roles.
    
    Args:
        request: FastAPI Request object
        required_roles: List of roles to check (admin, operator, viewer)
        
    Returns:
        True if user has required role
    """
    user_role = get_user_role(request)
    if not user_role:
        return False
    
    # Admin can access everything
    if user_role == "admin":
        return True
    
    # Check specific role
    return user_role in required_roles


def require_role(*roles: str):
    """Decorator to require specific role for endpoint.
    
    Args:
        *roles: Required roles (admin, operator, viewer)
        
    Example:
        @app.get("/admin")
        @require_role("admin")
        async def admin_endpoint(request: Request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not has_role(request, list(roles)):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


class PermissionContext:
    """Context helper for permission checks in templates."""
    
    def __init__(self, request: Request):
        """Initialize permission context.
        
        Args:
            request: FastAPI Request object
        """
        self.request = request
        self.user_role = get_user_role(request)
        self.user_id = get_user_id(request)
    
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.user_role == "admin"
    
    def is_operator(self) -> bool:
        """Check if user is operator or admin."""
        return self.user_role in ["admin", "operator"]
    
    def is_viewer(self) -> bool:
        """Check if user is any role (viewer, operator, admin)."""
        return self.user_role is not None
    
    def can_edit_users(self) -> bool:
        """Check if user can edit other users."""
        return self.is_admin()
    
    def can_view_audit(self) -> bool:
        """Check if user can view audit logs."""
        return self.is_admin()
    
    def can_create_backup(self) -> bool:
        """Check if user can create database backups."""
        return self.is_admin()
    
    def can_restore_backup(self) -> bool:
        """Check if user can restore database backups."""
        return self.is_admin()
    
    def can_manage_mfa(self) -> bool:
        """Check if user can manage MFA settings."""
        return True  # Users can manage their own MFA
    
    def can_manage_other_mfa(self) -> bool:
        """Check if user can manage other users' MFA."""
        return self.is_admin()
    
    def can_view_device_details(self) -> bool:
        """Check if user can view detailed device information."""
        return self.is_operator()
    
    def can_modify_device(self) -> bool:
        """Check if user can modify device settings."""
        return self.is_operator()
    
    def can_remove_device(self) -> bool:
        """Check if user can remove devices."""
        return self.is_admin()
    
    def can_view_settings(self) -> bool:
        """Check if user can view system settings."""
        return self.is_operator()
    
    def can_modify_settings(self) -> bool:
        """Check if user can modify system settings."""
        return self.is_admin()
    
    def can_export_config(self) -> bool:
        """Check if user can export configuration."""
        return self.is_operator()
    
    def can_import_config(self) -> bool:
        """Check if user can import configuration."""
        return self.is_admin()
    
    def get_visible_actions(self) -> List[str]:
        """Get list of visible UI actions for this user.
        
        Returns:
            List of action names user can perform
        """
        actions = []
        
        # Viewer permissions
        if self.is_viewer():
            actions.extend(["view_dashboard", "view_logs"])
        
        # Operator permissions
        if self.is_operator():
            actions.extend([
                "view_devices",
                "modify_device",
                "view_network",
                "view_settings",
                "export_config"
            ])
        
        # Admin permissions
        if self.is_admin():
            actions.extend([
                "manage_users",
                "create_backup",
                "restore_backup",
                "view_audit",
                "modify_settings",
                "import_config",
                "manage_mfa"
            ])
        
        return actions


# Template context helper for Jinja2
def create_permission_context(request: Request) -> dict:
    """Create permission context for Jinja2 templates.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Dictionary with permission checks for templates
    """
    perm = PermissionContext(request)
    
    return {
        "is_admin": perm.is_admin(),
        "is_operator": perm.is_operator(),
        "is_viewer": perm.is_viewer(),
        "can_edit_users": perm.can_edit_users(),
        "can_view_audit": perm.can_view_audit(),
        "can_create_backup": perm.can_create_backup(),
        "can_restore_backup": perm.can_restore_backup(),
        "can_manage_mfa": perm.can_manage_mfa(),
        "can_view_device_details": perm.can_view_device_details(),
        "can_modify_device": perm.can_modify_device(),
        "can_remove_device": perm.can_remove_device(),
        "can_view_settings": perm.can_view_settings(),
        "can_modify_settings": perm.can_modify_settings(),
        "can_export_config": perm.can_export_config(),
        "can_import_config": perm.can_import_config(),
        "visible_actions": perm.get_visible_actions()
    }


# Example middleware to add to base template context
async def add_permissions_to_context(request: Request, call_next):
    """Middleware to add permissions to all template responses.
    
    Example:
        app.middleware("http")(add_permissions_to_context)
    """
    response = await call_next(request)
    request.state.permissions = create_permission_context(request)
    return response
