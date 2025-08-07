# TailSentry Role-Based Access Control (RBAC) Design

## 🔑 User Roles & Permissions

### Admin Role
- Full system access
- Tailscale key management
- Service control (start/stop/restart)
- Configuration management
- User management
- Audit log access

### Operator Role  
- Dashboard viewing
- Tailscale status monitoring
- Limited service controls (restart only)
- Key creation (with expiry limits)
- Read-only configuration access

### Viewer Role
- Dashboard viewing only
- Tailscale status (read-only)
- No administrative functions
- No sensitive data access

### Service Account
- API access only
- Specific endpoint permissions
- No interactive login
- Audit trail for all actions

## 🛡️ Permission Matrix

| Action | Admin | Operator | Viewer | Service |
|--------|-------|----------|--------|---------|
| View Dashboard | ✅ | ✅ | ✅ | ❌ |
| Tailscale Status | ✅ | ✅ | ✅ | ✅ |
| Create Keys | ✅ | ✅¹ | ❌ | ✅² |
| Revoke Keys | ✅ | ❌ | ❌ | ❌ |
| Service Control | ✅ | ✅³ | ❌ | ❌ |
| Config Edit | ✅ | ❌ | ❌ | ❌ |
| User Management | ✅ | ❌ | ❌ | ❌ |
| Audit Logs | ✅ | ❌ | ❌ | ❌ |

¹ Limited expiry (max 7 days)
² Specific scoped permissions only  
³ Restart only, no start/stop

## 🔐 Implementation Strategy

### Phase 1: Database Integration
```python
# User table schema
class User:
    id: int
    username: str
    password_hash: str
    role: str  # admin, operator, viewer
    is_active: bool
    created_at: datetime
    last_login: datetime
    
class UserSession:
    id: str
    user_id: int
    expires_at: datetime
    permissions: List[str]
```

### Phase 2: Permission Decorators
```python
@requires_permission("tailscale:key:create")
@login_required
def create_key(request: Request, ...):
    # Implementation
    
@requires_role("admin")
@login_required  
def manage_users(request: Request, ...):
    # Implementation
```

### Phase 3: API Key Management
```python
class APIKey:
    id: str
    user_id: int
    name: str
    permissions: List[str]
    expires_at: datetime
    is_active: bool
```

## 🔍 Audit Implementation

### Audit Event Types
- Authentication (login/logout/failed)
- Authorization (permission denied)
- Data access (view/create/modify/delete)
- System operations (service control)
- Configuration changes

### Audit Data Structure
```python
class AuditEvent:
    id: str
    timestamp: datetime
    user_id: int
    session_id: str
    event_type: str
    resource: str
    action: str
    result: str  # success/failure
    ip_address: str
    user_agent: str
    additional_data: dict
```

## 🌐 API Security

### Rate Limiting by Role
- Admin: 1000 requests/hour
- Operator: 500 requests/hour  
- Viewer: 100 requests/hour
- Service: 10000 requests/hour

### Endpoint Protection
```python
# Different rate limits per endpoint
@rate_limit("100/hour", per_user=True)
@requires_permission("tailscale:status:read")
def get_status():
    pass

@rate_limit("10/hour", per_user=True) 
@requires_permission("tailscale:key:create")
def create_key():
    pass
```

## 📋 Migration Path

### Step 1: Add User Management
- Extend current auth.py
- Add user database models
- Implement role checking

### Step 2: Granular Permissions
- Define permission system
- Add permission decorators
- Update all routes

### Step 3: Audit System
- Add audit logging
- Implement audit viewer
- Set up alerts

### Step 4: API Keys
- Add API key generation
- Implement API authentication
- Add key management UI

## 🔧 Configuration Management

### Environment-based Roles
```bash
# Development
RBAC_ENABLED=false
DEFAULT_ROLE=admin

# Production  
RBAC_ENABLED=true
DEFAULT_ROLE=viewer
REQUIRE_EMAIL_VERIFICATION=true
```

### Role Assignment
```bash
# CLI tool for user management
./manage.py create-user --username admin --role admin
./manage.py assign-role --username user1 --role operator
./manage.py list-permissions --role viewer
```
