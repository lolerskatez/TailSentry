# Quick Integration Guide for New Features

## 1. Using Audit Logging in Your Routes

### Import the Audit Logger
```python
from services.audit_logger import AuditLogger, AuditEventType

# Initialize once (or use singleton pattern)
audit_logger = AuditLogger()
```

### Log User Actions
```python
# Log a login
audit_logger.log_event(
    event_type=AuditEventType.LOGIN,
    user_id=user.id,
    username=user.username,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    status="success"
)

# Log a failed login
audit_logger.log_event(
    event_type=AuditEventType.LOGIN_FAILED,
    username=username,
    ip_address=request.client.host,
    status="failure",
    error_message="Invalid password"
)

# Log user creation
audit_logger.log_event(
    event_type=AuditEventType.USER_CREATED,
    user_id=current_user.get("id"),
    username=current_user.get("username"),
    resource_type="user",
    resource_id=str(new_user.id),
    details={"new_username": new_user.username}
)

# Log device modification
audit_logger.log_event(
    event_type=AuditEventType.DEVICE_MODIFIED,
    user_id=user.id,
    username=user.username,
    resource_type="device",
    resource_id=device_name,
    action="enable",
    changes_to={"enabled": True}
)
```

### Available Event Types
- `AuditEventType.LOGIN` - User login
- `AuditEventType.LOGOUT` - User logout
- `AuditEventType.LOGIN_FAILED` - Failed login attempt
- `AuditEventType.USER_CREATED` - New user creation
- `AuditEventType.USER_DELETED` - User deletion
- `AuditEventType.USER_MODIFIED` - User updates
- `AuditEventType.ROLE_CHANGED` - Permission changes
- `AuditEventType.DEVICE_MODIFIED` - Device changes
- `AuditEventType.SETTINGS_CHANGED` - Settings updates
- `AuditEventType.BACKUP_CREATED` - Backup creation
- `AuditEventType.BACKUP_RESTORED` - Backup restore
- `AuditEventType.API_CALL` - API usage
- `AuditEventType.ERROR` - General errors
- `AuditEventType.UNAUTHORIZED_ACCESS` - Failed authorization
- `AuditEventType.MFA_ENABLED` - MFA activation
- `AuditEventType.MFA_DISABLED` - MFA deactivation

## 2. Using Permission Checks

### In Route Endpoints
```python
from fastapi import HTTPException, Request
from helpers_permissions import has_role, require_role, get_user_role

# Option 1: Using decorator
@router.get("/admin/users")
@require_role("admin")
async def list_users(request: Request):
    # Only admin can access
    pass

# Option 2: Manual check
@router.post("/user/settings")
async def update_settings(request: Request):
    user = get_current_user(request)
    if not user or not check_role(user, ["admin", "operator"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
    # Continue with update
    pass
```

### In Templates
```jinja2
{% if can_edit_users %}
  <button>Manage Users</button>
{% endif %}

{% if can_create_backup %}
  <button>Create Backup</button>
{% endif %}

{% if is_admin %}
  <div class="admin-section">
    Only admins see this
  </div>
{% endif %}
```

## 3. Implementing MFA in Login Flow

### Import MFA Service
```python
from services.mfa_service import MFAService

mfa_service = MFAService()
```

### Check if MFA is Enabled
```python
# After verifying username/password
if mfa_service.is_mfa_enabled(user.id):
    request.session["pending_mfa"] = True
    request.session["pending_user_id"] = user.id
    # Redirect to MFA verification page
    return RedirectResponse(url="/mfa-verify", status_code=302)
else:
    # Normal login - set session
    request.session["user"] = user.username
```

### Verify MFA Token
```python
# In MFA verification endpoint
@router.post("/mfa-verify")
async def verify_mfa(request: Request, token: str):
    user_id = request.session.get("pending_user_id")
    
    # Check rate limiting first
    if not mfa_service.check_mfa_rate_limit(user_id):
        return {"success": False, "error": "Too many failed attempts"}
    
    # Try recovery code
    if mfa_service.use_recovery_code(user_id, token):
        mfa_service.log_mfa_attempt(user_id, True, "recovery_code")
        request.session["user"] = username
        request.session.pop("pending_user_id")
        request.session.pop("pending_mfa")
        return RedirectResponse(url="/dashboard")
    
    # Try TOTP token
    status = mfa_service.get_mfa_status(user_id)
    if mfa_service.verify_totp(user_id, token, status["totp_secret"]):
        mfa_service.log_mfa_attempt(user_id, True, "totp")
        request.session["user"] = username
        return RedirectResponse(url="/dashboard")
    
    # Failed token
    mfa_service.log_mfa_attempt(user_id, False, "totp")
    return {"success": False, "error": "Invalid token"}
```

## 4. Creating Backups Programmatically

### Import Backup Service
```python
from services.backup_service import BackupService

backup_service = BackupService()
```

### Create Manual Backup
```python
# Create backup before major operation
result = backup_service.create_backup(
    description="Before database migration"
)

if result["success"]:
    logger.info(f"Backup created: {result['filename']}")
    # Proceed with risky operation
else:
    logger.error(f"Backup failed: {result['error']}")
    # Cancel operation
```

### List and Clean Up
```python
# List all backups
backups = backup_service.list_backups()

# Keep only last 10 backups
result = backup_service.cleanup_old_backups(keep_count=10)
```

## 5. Audit Log Integration Template

### Add to base.html Navigation
```jinja2
{% if can_view_audit %}
  <a href="/admin/audit">Audit Logs</a>
{% endif %}

{% if can_create_backup %}
  <a href="/admin/backups">Database Backups</a>
{% endif %}
```

### Add to User Settings
```jinja2
{% if can_manage_mfa %}
  <section>
    <h3>Multi-Factor Authentication</h3>
    {% if mfa_enabled %}
      <p>MFA is enabled</p>
      <a href="/mfa-setup">Disable MFA</a>
    {% else %}
      <p>MFA is disabled</p>
      <a href="/mfa-setup">Enable MFA</a>
    {% endif %}
  </section>
{% endif %}
```

## 6. Testing Integration

### Run Integration Tests
```bash
# Run all integration tests
pytest tests/test_integration.py -v

# Run specific test
pytest tests/test_integration.py::TestAuditLogger::test_search_events -v

# Run with coverage
pytest tests/test_integration.py --cov=services
```

### Test Individual Features
```python
# Test audit logging
from services.audit_logger import AuditLogger, AuditEventType

audit = AuditLogger()
audit.log_event(AuditEventType.LOGIN, username="testuser")
events = audit.get_recent_events(limit=1)
print(events)

# Test backup
from services.backup_service import BackupService

backup = BackupService()
result = backup.create_backup(description="Test")
print(f"Backup created: {result['filename']}")

# Test MFA
from services.mfa_service import MFAService
import pyotp

mfa = MFAService()
result = mfa.enable_totp(user_id=1, username="testuser")
totp = pyotp.TOTP(result["secret"])
token = totp.now()
is_valid = mfa.verify_totp(1, token, result["secret"])
print(f"TOTP verification: {is_valid}")
```

## 7. Environment Variables

Add to `.env`:
```bash
# API Documentation (development only)
DEVELOPMENT=true

# Audit Settings
AUDIT_RETENTION_DAYS=90

# Backup Settings
BACKUP_COMPRESS=true
BACKUP_DIR=data/backups

# Session Security
SESSION_SECRET=your-secure-secret-here
SESSION_TIMEOUT_MINUTES=30

# DevelopmentURLs
ALLOWED_ORIGIN=*
```

## 8. Database Schema

The following tables are automatically created on first run:

- `audit_events` - Audit log entries
- `audit_settings` - Audit configuration
- `mfa_settings` - User MFA configuration
- `mfa_attempts` - MFA attempt tracking
- `recovery_codes` - MFA backup codes

## 9. Monitoring & Maintenance

### Daily Tasks
```bash
# Check backup status
cd /var/www/tailsentry
python -c "from services.backup_service import BackupService; print(BackupService().list_backups())"

# View recent audit events
python -c "from services.audit_logger import AuditLogger; print(AuditLogger().get_recent_events(10))"
```

### Weekly Tasks
- Review audit statistics
- Check MFA adoption
- Verify backup success

### Monthly Tasks
- Export audit logs for compliance
- Review and update permission policies
- Plan backup retention cleanup

## 10. Troubleshooting

### MFA Issues
- **"Invalid TOTP secret"**: Regenerate QR code on /mfa-setup
- **"Too many attempts"**: Wait 15 minutes for rate limit reset
- **"Lost authenticator"**: Use recovery codes from backup

### Backup Issues
- **"Cannot delete last backup"**: Create another backup first
- **"Backup file not found"**: Check backup_dir is correct
- **"Restore failed"**: Verify disk space and permissions

### Audit Issues
- **"Search returns no results"**: Adjust date range or filters
- **"Export fails"**: Check disk space in data/ directory
- **"Statistics empty"**: Events are logged automatically, may take time

---

## Support

- **Documentation**: See IMPLEMENTATION_SUMMARY.md
- **Tests**: Review tests/test_integration.py for usage examples
- **Code**: Check services/ directory for implementation details
- **Help**: Review docstrings in each service module
