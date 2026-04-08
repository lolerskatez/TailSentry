# TailSentry 1.1.0 Deployment Guide

## Quick Start

### Step 1: Update Dependencies
```bash
cd /path/to/tailsentry

# Backup current requirements
cp requirements.txt requirements.txt.backup

# Install new dependencies
pip install -r requirements.txt

# Verify installations
python -c "import pyotp; import qrcode; print('✓ All dependencies installed')"
```

### Step 2: Environment Configuration
```bash
# Edit .env file
nano .env

# Add/update these variables:
DEVELOPMENT=false                    # Set to true for dev with /docs
AUDIT_RETENTION_DAYS=90             # Keep audit logs for 90 days
BACKUP_COMPRESS=true                # Compress backups with gzip
BACKUP_DIR=data/backups             # Backup storage location
SESSION_SECRET=your-random-secret   # Generate with: openssl rand -hex 32
SESSION_TIMEOUT_MINUTES=30          # Session timeout in minutes
```

### Step 3: Initialize Database
```bash
# The database schema will auto-initialize on first run
# But you can pre-create tables:
python -c "
from services.audit_logger import AuditLogger
from services.mfa_service import MFAService
from services.backup_service import BackupService

# Initialize all services (creates tables)
AuditLogger()
MFAService()
BackupService()
print('✓ Database tables initialized')
"
```

### Step 4: Start TailSentry
```bash
# Docker
docker-compose -f docker-compose.prod.yml up -d

# Or systemd
systemctl restart tailsentry

# Or direct
python main.py
```

### Step 5: Verify Installation
```bash
# Check health endpoint
curl http://localhost:8080/health

# Check API docs (if DEVELOPMENT=true)
curl http://localhost:8080/admin/api-docs

# Check audit logs are working
curl -X GET http://localhost:8080/admin/audit/search \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Feature-by-Feature Setup

### 1. API Documentation Setup

**For Development**
```bash
# Edit .env
DEVELOPMENT=true

# Restart service
systemctl restart tailsentry

# Access at http://localhost:8080/docs
```

**For Production**
```bash
# Edit .env
DEVELOPMENT=false

# API docs automatically hidden
# Use /admin/api-docs endpoint for authenticated access
```

### 2. Database Backups Setup

**Directory Permissions**
```bash
# Create backup directory
mkdir -p data/backups
chmod 700 data/backups

# (If running as systemd service)
sudo chown tailsentry:tailsentry data/backups
```

**Create Initial Backup**
```bash
# Via API
curl -X POST http://localhost:8080/admin/backups/create \
  -H "Cookie: tailsentry_session=YOUR_SESSION" \
  -d '{"description": "Initial backup"}'

# Or via Python
python -c "
from services.backup_service import BackupService
bs = BackupService()
result = bs.create_backup(description='Initial deployment backup')
print(f'Backup created: {result[\"filename\"]}')
"
```

**Automated Backup Scheduling**
```bash
# Create backup script
cat > /usr/local/bin/tailsentry-backup.sh << 'EOF'
#!/bin/bash
cd /var/www/tailsentry
python -c "
from services.backup_service import BackupService
bs = BackupService()
result = bs.create_backup(description='Automated daily backup')
if result['success']:
    print(f'✓ Backup created: {result[\"filename\"]}')
else:
    print(f'✗ Backup failed: {result[\"error\"]}')
"
EOF

chmod +x /usr/local/bin/tailsentry-backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/tailsentry-backup.sh") | crontab -

# Or add to systemd timer
sudo systemctl enable --now tailsentry-backup.timer
```

### 3. Audit Logging Setup

**Automatic Startup**
```bash
# No setup needed - audit tables created automatically
# Logging starts recording all qualified events
```

**Monitoring Audit Logs**
```bash
# View recent events
curl -X GET 'http://localhost:8080/admin/audit/search?limit=10' \
  -H "Cookie: tailsentry_session=YOUR_SESSION"

# Get statistics
curl -X GET 'http://localhost:8080/admin/audit/statistics?days=30' \
  -H "Cookie: tailsentry_session=YOUR_SESSION"

# Export logs monthly
curl -X GET 'http://localhost:8080/admin/audit/export?format=csv' \
  -H "Cookie: tailsentry_session=YOUR_SESSION" \
  -o audit_logs_$(date +%Y%m%d).csv
```

**Cleanup Old Logs**
```bash
# Via API (admin only)
curl -X POST 'http://localhost:8080/admin/audit/cleanup' \
  -H "Cookie: tailsentry_session=YOUR_SESSION" \
  -H 'Content-Type: application/json' \
  -d '{"retention_days": 90}'

# Automated cleanup (find your settings later)
# python -c "from services.audit_logger import AuditLogger; AuditLogger().cleanup_old_events(90)"
```

### 4. WebSocket Keepalive Configuration

**No Setup Required**
- Automatically enabled on all WebSocket connections
- Keepalive ping: every 30 seconds
- Idle timeout: 5 minutes
- Graceful cleanup on disconnect

**Monitoring**
```bash
# Check WebSocket connections in logs
grep -i websocket /var/log/tailsentry/tailsentry.log

# Monitor active connections
watch -n 5 'grep -c "WebSocket" /var/log/tailsentry/tailsentry.log'
```

### 5. MFA (Multi-Factor Authentication) Setup

**Enable MFA**
```bash
# User goes to /mfa-setup or settings page
# Follows 3-step wizard:
# 1. Generate TOTP secret and QR code
# 2. Scan with authenticator app
# 3. Verify with generated code

# Admin can enable for users via API
curl -X POST 'http://localhost:8080/admin/user/1/mfa/enable' \
  -H "Cookie: tailsentry_session=ADMIN_SESSION"
```

**Monitor MFA Adoption**
```bash
# Check which users have MFA enabled
python -c "
from services.mfa_service import MFAService
import sqlite3

mfa = MFAService()
conn = sqlite3.connect('data/tailsentry.db')
cursor = conn.cursor()
cursor.execute('SELECT user_id, mfa_enabled, mfa_method FROM mfa_settings')
for row in cursor.fetchall():
    print(f'User {row[0]}: {\"Enabled\" if row[1] else \"Disabled\"} ({row[2]})')
conn.close()
"
```

**Recovery Code Backup**
- Each user gets 10 recovery codes during MFA setup
- Users should store these securely
- Each code can be used once if authenticator is lost
- Admin can generate new codes if lost

### 6. Permission-Based UI Setup

**Verify Permissions**
```bash
# Test admin access
curl -X GET 'http://localhost:8080/admin/audit/search' \
  -H "Cookie: tailsentry_session=ADMIN_SESSION"

# Test non-admin access (should fail)
curl -X GET 'http://localhost:8080/admin/audit/search' \
  -H "Cookie: tailsentry_session=USER_SESSION"
```

**Update User Roles**
```python
# Grant admin role to user
from auth_user import get_user_by_id, update_user

user = get_user_by_id(1)
user['role'] = 'admin'
update_user(user)

# Roles available:
# - admin: Full access to all features
# - operator: Can manage devices and view settings
# - viewer: Read-only access to dashboard
```

### 7. PostgreSQL Migration (Optional - for scale)

**Plan Migration**
```bash
# Timeline: 1-2 weeks staging, then production

# Phase 1: Preparation
1. Size your SQLite database
2. Estimate PostgreSQL server needs
3. Plan backup windows

# Phase 2: Staging
1. Setup PostgreSQL instance
2. Test migration script
3. Performance testing
4. Rollback testing

# Phase 3: Production
1. Create production backup
2. Run migration
3. Verify data integrity
4. Monitor performance
```

**See docs/POSTGRESQL_MIGRATION.md for detailed steps**

---

## Post-Deployment Checklist

### Day 1
- [ ] Verify all endpoints are accessible
- [ ] Test backup/restore functionality
- [ ] Create first manual backup
- [ ] Check audit logs are recording
- [ ] Test MFA setup for one user
- [ ] Verify permission restrictions
- [ ] Review WebSocket connections in logs
- [ ] Check no errors in application logs

### Week 1
- [ ] Monitor audit log volume
- [ ] Test backup restore process
- [ ] Review MFA adoption
- [ ] Test permission-based access
- [ ] Setup automated backup scheduling
- [ ] Export first week of audit logs
- [ ] Performance baseline testing
- [ ] Security audit of admin endpoints

### Month 1
- [ ] Review audit statistics
- [ ] Verify backup retention policy
- [ ] Analyze MFA effectiveness
- [ ] Monitor WebSocket activity
- [ ] Plan PostgreSQL migration (if >100 users)
- [ ] Export monthly compliance report
- [ ] Review and update user permissions
- [ ] Capacity planning for next quarter

---

## Monitoring & Alerting

### Key Metrics to Monitor

**Backup Status**
```bash
# Error alert if no recent backup
* Last backup older than 24 hours

# Success if latest backup exists
* Latest backup size is reasonable
* Backup directory has space
```

**Audit Logs**
```bash
# Alert on suspicious patterns
* High number of failed logins from same IP
* Unauthorized access attempts
* Admin password changes
* Bulk user deletions

# Monitor volume
* Events per hour baseline
* Storage usage of audit tables
```

**MFA Usage**
```bash
# Track adoption
* Percentage of users with MFA
* MFA-related errors
* Recovery code usage
```

**WebSocket Health**
```bash
# Check connection patterns
* Average connection lifetime
* Connection errors
* Keepalive effectiveness
```

### Setup Monitoring Alert

```bash
# Create monitoring script
cat > /usr/local/bin/tailsentry-monitor.sh << 'EOF'
#!/bin/bash

# Check backup age
LATEST_BACKUP=$(find data/backups -name "*.sql.gz" -type f -printf '%T@\n' | sort -rn | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "CRITICAL: No backup found"
    # Send alert
fi

# Check disk space
DISK_USAGE=$(df data/ | awk 'NR==2 {print $5}' | cut -d'%' -f1)
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "WARNING: Disk usage at ${DISK_USAGE}%"
fi

# Check service health
if ! curl -s http://localhost:8080/health > /dev/null; then
    echo "CRITICAL: Service not responding"
fi
EOF

chmod +x /usr/local/bin/tailsentry-monitor.sh

# Run every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/tailsentry-monitor.sh") | crontab -
```

---

## Troubleshooting

### Common Issues

**1. "MFA tables not found"**
```bash
# Solution: Recreate tables
python -c "from services.mfa_service import MFAService; MFAService()"
# Or restart the application
```

**2. "Backup directory permission denied"**
```bash
# Solution: Fix permissions
sudo chown -R tailsentry:tailsentry data/backups
sudo chmod 700 data/backups
```

**3. "Audit logs not showing"**
```bash
# Verify tables exist
sqlite3 data/tailsentry.db ".tables" | grep audit

# Check service is writing
tail -f logs/tailsentry.log | grep -i audit

# Manually log event to test
python -c "
from services.audit_logger import AuditLogger, AuditEventType
al = AuditLogger()
al.log_event(AuditEventType.LOGIN, username='test', status='success')
print('✓ Logged test event')
"
```

**4. "WebSocket connection drops"**
```bash
# Check network timeout settings
# Increase idle timeout in routes/api.py if needed
# Verify firewall allows WebSocket keep-alive
```

**5. "MFA QR code not displaying"**
```bash
# Verify Pillow is installed
pip list | grep Pillow

# If not, install
pip install Pillow>=10.0.0

# Test QR generation
python -c "from services.mfa_service import MFAService; m = MFAService(); print('✓ QR library working')"
```

---

## Performance Tuning

### Database Optimization
```bash
# Vacuum database (cleanup space)
sqlite3 data/tailsentry.db "VACUUM;"

# Analyze query performance
sqlite3 data/tailsentry.db "ANALYZE;"
```

### Backup Compression
```bash
# Default: gzip compression reduces size 60-80%
# To disable compression (not recommended):
# Modify services/backup_service.py and set compress=False
```

### Audit Log Retention
```bash
# Reduce retention to save space (default 90 days)
# In .env: AUDIT_RETENTION_DAYS=30

# Or manually cleanup
python -c "
from services.audit_logger import AuditLogger
al = AuditLogger()
deleted = al.cleanup_old_events(retention_days=30)
print(f'Deleted {deleted} events')
"
```

---

## Backup & Recovery

### Full System Backup
```bash
# Backup everything
tar -czf tailsentry_backup_$(date +%Y%m%d).tar.gz \
  data/tailsentry.db \
  data/backups \
  logs/ \
  config/

# Restore
tar -xzf tailsentry_backup_YYYYMMDD.tar.gz
```

### Database Recovery
```bash
# List recovery points
ls -lh data/backups/

# Restore from backup
curl -X POST 'http://localhost:8080/admin/backups/restore/tailsentry_backup_YYYYMMDD_HHMMSS.sql.gz' \
  -H "Cookie: tailsentry_session=ADMIN_SESSION"
```

---

## Documentation Links

- **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Integration Guide**: [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
- **PostgreSQL Migration**: [docs/POSTGRESQL_MIGRATION.md](docs/POSTGRESQL_MIGRATION.md)
- **API Documentation**: `/admin/api-docs` (when authenticated)
- **Test Examples**: [tests/test_integration.py](tests/test_integration.py)

---

## Support

- **GitHub Issues**: https://github.com/lolerskatez/TailSentry/issues
- **Documentation**: See docs/ directory
- **Tests**: Run `pytest tests/ -v` for examples
- **Logs**: Check `logs/tailsentry.log` for errors

---

**Deployment Date**: April 8, 2026
**Version**: 1.1.0
**Status**: Ready for Production ✅
