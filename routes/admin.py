"""Administrative and management routes for TailSentry."""
import os
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from services.backup_service import BackupService
from services.audit_logger import AuditLogger, AuditEventType
from services.mfa_service import MFAService
from routes.user import get_current_user, check_role

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger("tailsentry.admin")

# Initialize services
backup_service = BackupService()
audit_logger = AuditLogger()
mfa_service = MFAService()


# ==================== BACKUP & RESTORE ROUTES ====================

@router.get("/backups")
async def list_backups(request: Request):
    """List all available backups."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        audit_logger.log_event(
            AuditEventType.UNAUTHORIZED_ACCESS,
            username=user.get("username") if user else None,
            resource_type="backup",
            action="list",
            status="failure"
        )
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    backups = backup_service.list_backups()
    
    audit_logger.log_event(
        AuditEventType.API_CALL,
        username=user.get("username"),
        resource_type="backup",
        action="list",
        details={"count": len(backups)}
    )
    
    return JSONResponse(content={"success": True, "backups": backups})


@router.post("/backups/create")
async def create_backup(request: Request, description: str = ""):
    """Create a database backup."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        audit_logger.log_event(
            AuditEventType.UNAUTHORIZED_ACCESS,
            username=user.get("username") if user else None,
            resource_type="backup",
            action="create",
            status="failure"
        )
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    result = backup_service.create_backup(description=description)
    
    if result.get("success"):
        audit_logger.log_event(
            AuditEventType.BACKUP_CREATED,
            username=user.get("username"),
            resource_type="backup",
            action="create",
            details=result
        )
    else:
        audit_logger.log_event(
            AuditEventType.BACKUP_CREATED,
            username=user.get("username"),
            resource_type="backup",
            action="create",
            status="failure",
            error_message=result.get("error")
        )
    
    return JSONResponse(content=result)


@router.post("/backups/restore/{backup_filename}")
async def restore_backup(request: Request, backup_filename: str):
    """Restore database from a backup."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        audit_logger.log_event(
            AuditEventType.UNAUTHORIZED_ACCESS,
            username=user.get("username") if user else None,
            resource_type="backup",
            action="restore",
            status="failure"
        )
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    result = backup_service.restore_backup(backup_filename)
    
    if result.get("success"):
        audit_logger.log_event(
            AuditEventType.BACKUP_RESTORED,
            username=user.get("username"),
            resource_type="backup",
            action="restore",
            details={"backup_file": backup_filename}
        )
    else:
        audit_logger.log_event(
            AuditEventType.BACKUP_RESTORED,
            username=user.get("username"),
            resource_type="backup",
            action="restore",
            status="failure",
            error_message=result.get("error")
        )
    
    return JSONResponse(content=result)


@router.delete("/backups/{backup_filename}")
async def delete_backup(request: Request, backup_filename: str):
    """Delete a backup file."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    result = backup_service.delete_backup(backup_filename)
    
    audit_logger.log_event(
        AuditEventType.API_CALL,
        username=user.get("username"),
        resource_type="backup",
        action="delete",
        details={"backup_file": backup_filename}
    )
    
    return JSONResponse(content=result)


@router.post("/backups/cleanup")
async def cleanup_backups(request: Request, keep_count: int = 10):
    """Clean up old backups, keeping only recent ones."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    result = backup_service.cleanup_old_backups(keep_count=keep_count)
    
    audit_logger.log_event(
        AuditEventType.API_CALL,
        username=user.get("username"),
        resource_type="backup",
        action="cleanup",
        details=result
    )
    
    return JSONResponse(content=result)


@router.get("/backups/download/{backup_filename}")
async def download_backup(request: Request, backup_filename: str):
    """Download a backup file."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    backup_path = Path("data/backups") / backup_filename
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    
    audit_logger.log_event(
        AuditEventType.API_CALL,
        username=user.get("username"),
        resource_type="backup",
        action="download",
        details={"backup_file": backup_filename}
    )
    
    return FileResponse(
        path=backup_path,
        filename=backup_filename,
        media_type="application/octet-stream"
    )


# ==================== AUDIT LOG ROUTES ====================

@router.get("/audit/search")
async def search_audit_logs(
    request: Request,
    event_type: str = None,
    username: str = None,
    resource_type: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100,
    offset: int = 0
):
    """Search audit logs with filters."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Parse dates
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except:
            pass
    
    events = audit_logger.search_events(
        event_type=event_type,
        username=username,
        resource_type=resource_type,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit,
        offset=offset
    )
    
    return JSONResponse(content={"success": True, "events": events})


@router.get("/audit/statistics")
async def get_audit_statistics(request: Request, days: int = 30):
    """Get audit log statistics."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    stats = audit_logger.get_statistics(days=days)
    
    return JSONResponse(content={"success": True, "statistics": stats})


@router.get("/audit/user-activity/{username}")
async def get_user_activity(request: Request, username: str, days: int = 30):
    """Get activity log for a specific user."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    activities = audit_logger.get_user_activity(username=username, days=days)
    
    return JSONResponse(content={"success": True, "activities": activities})


@router.get("/audit/export")
async def export_audit_logs(
    request: Request,
    format: str = "csv",
    start_date: str = None,
    end_date: str = None
):
    """Export audit logs to CSV or JSON."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Parse dates
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except:
            pass
    
    # Create temporary export file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_file = Path("data") / f"audit_export_{timestamp}.{format}"
    
    success = audit_logger.export_events(
        filename=str(export_file),
        start_date=start_dt,
        end_date=end_dt,
        format=format
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to export audit logs")
    
    audit_logger.log_event(
        AuditEventType.API_CALL,
        username=user.get("username"),
        resource_type="audit",
        action="export",
        details={"format": format}
    )
    
    return FileResponse(
        path=export_file,
        filename=f"audit_export_{timestamp}.{format}",
        media_type="application/octet-stream"
    )


@router.post("/audit/cleanup")
async def cleanup_audit_logs(request: Request, retention_days: int = 90):
    """Clean up old audit logs."""
    user = get_current_user(request)
    if not user or not check_role(user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    deleted = audit_logger.cleanup_old_events(retention_days=retention_days)
    
    audit_logger.log_event(
        AuditEventType.API_CALL,
        username=user.get("username"),
        resource_type="audit",
        action="cleanup",
        details={"deleted": deleted, "retention_days": retention_days}
    )
    
    return JSONResponse(content={
        "success": True,
        "deleted": deleted,
        "message": f"Deleted {deleted} old audit events"
    })


# ==================== MFA MANAGEMENT ROUTES ====================

@router.post("/user/{user_id}/mfa/enable")
async def enable_mfa(request: Request, user_id: int):
    """Enable MFA for a user."""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Users can only enable for themselves, admins can enable for anyone
    if user_id != current_user.get("id") and not check_role(current_user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    result = mfa_service.enable_totp(user_id, current_user.get("username"))
    
    if result.get("success"):
        audit_logger.log_event(
            AuditEventType.MFA_ENABLED,
            user_id=user_id,
            username=current_user.get("username")
        )
    
    return JSONResponse(content=result)


@router.post("/user/{user_id}/mfa/verify")
async def verify_mfa(request: Request, user_id: int):
    """Verify and activate MFA for a user."""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user_id != current_user.get("id") and not check_role(current_user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    data = await request.json()
    totp_token = data.get("token")
    totp_secret = data.get("secret")
    backup_codes = data.get("backup_codes")
    
    if not totp_token or not totp_secret:
        return JSONResponse(
            content={"success": False, "error": "Missing token or secret"},
            status_code=400
        )
    
    # Verify the token
    if not mfa_service.verify_totp(user_id, totp_token, totp_secret):
        mfa_service.log_mfa_attempt(user_id, False, "totp")
        return JSONResponse(
            content={"success": False, "error": "Invalid token"},
            status_code=400
        )
    
    # Activate MFA
    success = mfa_service.activate_mfa(
        user_id=user_id,
        mfa_method="totp",
        totp_secret=totp_secret,
        backup_codes=backup_codes
    )
    
    if success:
        mfa_service.log_mfa_attempt(user_id, True, "totp")
        audit_logger.log_event(
            AuditEventType.MFA_ENABLED,
            user_id=user_id,
            username=current_user.get("username")
        )
    
    return JSONResponse(content={"success": success})


@router.post("/user/{user_id}/mfa/disable")
async def disable_mfa(request: Request, user_id: int):
    """Disable MFA for a user."""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user_id != current_user.get("id") and not check_role(current_user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    success = mfa_service.disable_mfa(user_id)
    
    if success:
        audit_logger.log_event(
            AuditEventType.MFA_DISABLED,
            user_id=user_id,
            username=current_user.get("username")
        )
    
    return JSONResponse(content={"success": success})


@router.get("/user/{user_id}/mfa/status")
async def get_mfa_status(request: Request, user_id: int):
    """Get MFA status for a user."""
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user_id != current_user.get("id") and not check_role(current_user, ["admin"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    status = mfa_service.get_mfa_status(user_id)
    
    return JSONResponse(content={
        "success": True,
        "mfa_enabled": status.get("mfa_enabled") == 1 if status else False,
        "mfa_method": status.get("mfa_method") if status else None
    })


@router.post("/user/{user_id}/mfa/verify-token")
async def verify_mfa_token(request: Request, user_id: int):
    """Verify an MFA token during login."""
    data = await request.json()
    token = data.get("token")
    
    status = mfa_service.get_mfa_status(user_id)
    if not status or not status.get("mfa_enabled"):
        return JSONResponse(
            content={"success": False, "error": "MFA not enabled"},
            status_code=400
        )
    
    # Check rate limiting
    if not mfa_service.check_mfa_rate_limit(user_id):
        return JSONResponse(
            content={"success": False, "error": "Too many failed attempts. Try again later."},
            status_code=429
        )
    
    # Try recovery code first
    if mfa_service.use_recovery_code(user_id, token):
        mfa_service.log_mfa_attempt(user_id, True, "recovery_code")
        return JSONResponse(content={"success": True})
    
    # Try TOTP token
    if mfa_service.verify_totp(user_id, token, status.get("totp_secret")):
        mfa_service.log_mfa_attempt(user_id, True, "totp")
        return JSONResponse(content={"success": True})
    
    mfa_service.log_mfa_attempt(user_id, False, "totp")
    return JSONResponse(
        content={"success": False, "error": "Invalid token"},
        status_code=400
    )


# ==================== API DOCUMENTATION ROUTES ====================

@router.get("/api-docs")
async def api_documentation(request: Request):
    """Get API documentation."""
    user = get_current_user(request)
    
    docs = {
        "title": "TailSentry API Documentation",
        "version": os.getenv("VERSION", "1.0.0"),
        "base_url": str(request.base_url).rstrip("/"),
        "endpoints": {
            "backup": {
                "description": "Database backup and restore operations",
                "routes": [
                    {"method": "GET", "path": "/admin/backups", "description": "List all backups"},
                    {"method": "POST", "path": "/admin/backups/create", "description": "Create new backup"},
                    {"method": "POST", "path": "/admin/backups/restore/{filename}", "description": "Restore from backup"},
                    {"method": "DELETE", "path": "/admin/backups/{filename}", "description": "Delete backup"},
                    {"method": "GET", "path": "/admin/backups/download/{filename}", "description": "Download backup"},
                ]
            },
            "audit": {
                "description": "Audit logging and search",
                "routes": [
                    {"method": "GET", "path": "/admin/audit/search", "description": "Search audit logs"},
                    {"method": "GET", "path": "/admin/audit/statistics", "description": "Get audit statistics"},
                    {"method": "GET", "path": "/admin/audit/user-activity/{username}", "description": "Get user activity"},
                    {"method": "GET", "path": "/admin/audit/export", "description": "Export audit logs"},
                ]
            },
            "mfa": {
                "description": "Multi-factor authentication management",
                "routes": [
                    {"method": "POST", "path": "/admin/user/{user_id}/mfa/enable", "description": "Enable MFA"},
                    {"method": "POST", "path": "/admin/user/{user_id}/mfa/verify", "description": "Verify MFA setup"},
                    {"method": "POST", "path": "/admin/user/{user_id}/mfa/disable", "description": "Disable MFA"},
                    {"method": "GET", "path": "/admin/user/{user_id}/mfa/status", "description": "Get MFA status"},
                ]
            }
        }
    }
    
    if not user:
        # Only basic docs for unauthenticated users
        return JSONResponse(content={
            "title": "TailSentry API",
            "message": "Authenticate to access full documentation",
            "version": os.getenv("VERSION", "1.0.0")
        })
    
    return JSONResponse(content=docs)
