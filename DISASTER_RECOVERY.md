# 🚨 TailSentry Disaster Recovery Plan

Complete disaster recovery procedures for critical outages and data loss scenarios.

## 📋 Table of Contents

- [RTO/RPO Targets](#rtorpo-targets)
- [Recovery Procedures](#recovery-procedures)
- [Disaster Scenarios](#disaster-scenarios)
- [Runbooks](#runbooks)
- [Testing & Validation](#testing--validation)
- [Contact & Escalation](#contact--escalation)

---

## ⏱️ RTO/RPO Targets

| Metric | Target | Description |
|--------|--------|-------------|
| **RTO** (Recovery Time Objective) | 30 minutes | Maximum acceptable downtime |
| **RPO** (Recovery Point Objective) | 1 hour | Maximum acceptable data loss |
| **Backup Frequency** | Hourly | Database snapshots taken every hour |
| **Backup Retention** | 30 days | Minimum retention period |
| **Monthly Test** | Monthly | Recovery procedures tested monthly |

---

## 🔄 Recovery Procedures

### Full System Recovery Steps

#### Phase 1: Assessment (5 minutes)

```bash
# 1. Determine what's lost
systemctl status tailsentry

# 2. Check data integrity
/opt/tailsentry/scripts/validate_db.sh

# 3. Check backups available
ls -la /opt/tailsentry/backups/users.db.backup-* | head -5

# 4. Review logs for error details
tail -f /opt/tailsentry/logs/tailsentry.log | head -50
```

**Decision Tree**:
- ✅ Service running, data intact → Go to Phase 2
- ❌ Service running, data corrupted → Database Recovery (see DATABASE_RECOVERY.md)
- ❌ Service not running → Go to Phase 3
- ❌ Both service and data lost → Go to Phase 4

#### Phase 2: Critical Data Verification (5 minutes)

```bash
# Verify configuration files are intact
ls -la /opt/tailsentry/config/
cat /opt/tailsentry/.env | grep -E "^TAILSCALE_|^SMTP_|^DISCORD_" | head -10

# Test database connectivity
sqlite3 /opt/tailsentry/users.db "SELECT COUNT(*) FROM users;"

# Verify backups
ls -lt /opt/tailsentry/backups/ | head -5
```

**Success Criteria**:
- ✅ Configuration files present
- ✅ Environment variables configured
- ✅ Database queries return results
- ✅ Recent backups exist

#### Phase 3: Service Recovery (10-15 minutes)

```bash
# If service crashed but data intact

# 1. Stop service
sudo systemctl stop tailsentry

# 2. Wait for graceful shutdown
sleep 5

# 3. Check for locks
lsof | grep users.db
pkill -f "python main.py"

# 4. Validate database
/opt/tailsentry/scripts/validate_db.sh

# 5. Restart service
sudo systemctl start tailsentry

# 6. Verify service health
sleep 10
curl http://localhost:8080/health
```

#### Phase 4: Full System Rebuild (30-60 minutes)

See detailed procedures below under "Runbooks"

---

## 🎯 Disaster Scenarios

### Scenario A: Disk Full

**Symptoms**: Service hangs, database locked, high I/O wait  
**RTO**: 15 minutes  
**Data Loss**: Minimal (if backups on separate disk)

**Recovery**:
```bash
# 1. Check disk usage
df -h
du -h /opt/tailsentry/* | sort -rh

# 2. Stop service
systemctl stop tailsentry

# 3. Clean logs (safe to delete)
rm /opt/tailsentry/logs/tailsentry.log.*
truncate -s 0 /opt/tailsentry/logs/tailsentry.log

# 4. Verify free space is >5GB
df -h /opt/tailsentry

# 5. Restart service
systemctl start tailsentry

# 6. Implement log rotation if not present
# See /etc/logrotate.d/tailsentry
```

### Scenario B: Corrupted Database

**Symptoms**: Integrity check fails, users can't log in  
**RTO**: 10 minutes  
**Data Loss**: Up to 1 hour

See [DATABASE_RECOVERY.md](DATABASE_RECOVERY.md) for detailed procedures

### Scenario C: Lost Configuration Files

**Symptoms**: Service starts but can't connect to Tailscale/SMTP  
**RTO**: 20 minutes  
**Data Loss** Minimal (if .env backup exists)

**Recovery**:
```bash
# 1. Check for .env backup
ls -la /opt/tailsentry/.env* /opt/tailsentry/config/*.json

# 2. If backup exists, restore
cp /opt/tailsentry/.env.backup /opt/tailsentry/.env

# 3. If no backup, recreate from documentation
# Refer to .env.example or documentation

# 4. Verify configuration
grep "TAILSCALE_API_TOKEN" /opt/tailsentry/.env

# 5. Restart service
systemctl restart tailsentry
```

### Scenario D: Server Hardware Failure

**Symptoms**: Physical server down, no recovery possible  
**RTO**: 60+ minutes  
**Data Loss**: Up to 1 hour (if hourly backups to remote)

**Recovery**:
```bash
# 1. Provision new server
# 2. Install OS and dependencies
# 3. Deploy TailSentry fresh installation
sudo ./setup.sh install

# 4. Restore database from remote backup
scp backup@remote:/backups/tailsentry/users.db.backup-latest \
    /opt/tailsentry/users.db

# 5. Restore configuration files
scp -r backup@remote:/backups/tailsentry/config/ \
    /opt/tailsentry/

# 6. Restore .env file
scp backup@remote:/backups/tailsentry/.env \
    /opt/tailsentry/

# 7. Start service
systemctl start tailsentry
```

### Scenario E: Ransomware/Compromise

**Symptoms**: Files encrypted, service compromised, suspicious activity  
**RTO**: 120+ minutes  
**Data Loss**: Varies (depends on backup integrity)

**Recovery**:
```bash
# 1. IMMEDIATE: Isolate system from network
sudo iptables -A INPUT -j DROP
sudo iptables -A OUTPUT -j DROP

# 2. Power down immediately to preserve forensics
sudo poweroff

# 3. Boot from recovery media
# 4. Mount filesystem read-only
# 5. Capture forensic image
# 6. Clean wipe and fresh install on new server
# 7. Restore from verified clean backup

# 8. Change all credentials:
#    - Tailscale API tokens
#    - SMTP passwords
#    - SSO secrets
#    - Admin passwords
```

---

## 📖 Runbooks

### Runbook 1: Fresh Installation with Data Restore

**Scenario**: Complete server loss, need full rebuild  
**Duration**: 45 minutes  
**Prerequisites**: Remote backup available

```bash
#!/bin/bash
# Complete system recovery runbook

echo "=== TailSentry Full Recovery Runbook ==="
echo "Step 1: Fresh installation"
cd /tmp
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry
sudo ./setup.sh install

echo "Step 2: Stop service"
sudo systemctl stop tailsentry

echo "Step 3: Restore database from backup"
# Adjust source as needed
BACKUP_SOURCE="s3://company-backups/tailsentry/users.db.backup-latest"
aws s3 cp "$BACKUP_SOURCE" /opt/tailsentry/users.db

echo "Step 4: Verify backup integrity"
/opt/tailsentry/scripts/validate_db.sh || {
    echo "ERROR: Backup integrity check failed"
    exit 1
}

echo "Step 5: Restore configuration"
aws s3 cp s3://company-backups/tailsentry/.env /opt/tailsentry/.env
aws s3 cp s3://company-backups/tailsentry/config/ /opt/tailsentry/config/ --recursive

echo "Step 6: Set proper permissions"
sudo chown -R tailsentry:tailsentry /opt/tailsentry
sudo chmod 600 /opt/tailsentry/.env

echo "Step 7: Start service"
sudo systemctl start tailsentry

echo "Step 8: Verify service health"
sleep 5
curl http://localhost:8080/health || exit 1

echo "=== Recovery Complete ==="
```

### Runbook 2: Database-Only Restoration

**Scenario**: Service running but database corrupted  
**Duration**: 10 minutes

```bash
#!/bin/bash
# Database-only recovery runbook

echo "=== Database Recovery Runbook ==="

DB_PATH="/opt/tailsentry/users.db"
BACKUP_DIR="/opt/tailsentry/backups"

echo "Step 1: Validate corruption"
sqlite3 "$DB_PATH" "PRAGMA integrity_check;"

echo "Step 2: Stop TailSentry service"
sudo systemctl stop tailsentry

echo "Step 3: Backup corrupted database"
cp "$DB_PATH" "$DB_PATH.corrupted-$(date +%s)"

echo "Step 4: Find and restore best backup"
BEST_BACKUP=$(ls -t "$BACKUP_DIR"/users.db.backup-* | head -1)
echo "Using backup: $BEST_BACKUP"
cp "$BEST_BACKUP" "$DB_PATH"

echo "Step 5: Verify restored database"
sqlite3 "$DB_PATH" "PRAGMA integrity_check;" | grep -q "ok" || {
    echo "ERROR: Restored database failed integrity check"
    exit 1
}

echo "Step 6: Restart TailSentry"
sudo systemctl start tailsentry

echo "Step 7: Verify service"
sleep 3
curl http://localhost:8080/health

echo "=== Database Recovery Complete ==="
```

### Runbook 3: Rapid Failover

**Scenario**: Primary server down, failover to standby  
**Duration**: 5 minutes  
**Requirement**: Standby server configured and ready

```bash
#!/bin/bash
# Rapid failover runbook

echo "=== Failover Runbook ==="

STANDBY_SERVER="tailsentry-standby.company.com"
BACKUP_SOURCE="/mnt/nfs/tailsentry-backups"

echo "Step 1: Verify primary is truly down"
ping -c 1 tailsentry-primary.company.com && {
    echo "ERROR: Primary still responding"
    exit 1
}

echo "Step 2: Start service on standby"
ssh $STANDBY_SERVER "sudo systemctl start tailsentry"

echo "Step 3: Verify standby is responding"
curl http://$STANDBY_SERVER:8080/health

echo "Step 4: Update DNS (if applicable)"
# Update your DNS/load balancer here
# Example: Change CNAME to point to standby

echo "Step 5: Notify team"
echo "Failover complete to $STANDBY_SERVER" | mail -s "TailSentry Failover" ops@company.com

echo "=== Failover Complete ==="
```

---

## 🧪 Testing & Validation

### Monthly Recovery Test

**Schedule**: First Monday of each month, 10 AM UTC  
**Duration**: 2 hours  
**Participants**: Operations team

**Test Procedure**:

```bash
#!/bin/bash
# Monthly recovery test runbook

echo "=== Monthly Full Recovery Test ==="
echo "Date: $(date)"
echo ""

# 1. Document current state
echo "1. Initial state check"
sqlite3 /opt/tailsentry/users.db "SELECT COUNT(*) FROM users;" > /tmp/pre-test-count.txt
echo "User count before: $(cat /tmp/pre-test-count.txt)"

# 2. Simulate database corruption
echo "2. Simulating corruption"
sudo systemctl stop tailsentry
dd if=/dev/urandom bs=1 count=512 of=/opt/tailsentry/users.db.test conv=notrunc

# 3. Verify corruption (should fail)
echo "3. Verifying corruption created"
sqlite3 /opt/tailsentry/users.db.test "PRAGMA integrity_check;" 2>&1 | tee /tmp/corruption-check.txt

# 4. Restore database
echo "4. Attempting recovery"
cp /opt/tailsentry/backups/users.db.backup-* /opt/tailsentry/users.db 2>/dev/null || {
    echo "ERROR: No backups available"
    exit 1
}

# 5. Verify recovery
echo "5. Verifying recovery"
sqlite3 /opt/tailsentry/users.db "SELECT COUNT(*) FROM users;" > /tmp/post-test-count.txt
echo "User count after: $(cat /tmp/post-test-count.txt)"

# 6. Restart service
echo "6. Starting service"
sudo systemctl start tailsentry
sleep 5

# 7. Verify service health
echo "7. Verifying service"
curl -s http://localhost:8080/health > /tmp/health-check.txt
echo "Health check result: $(cat /tmp/health-check.txt)"

# 8. Generate test report
echo "8. Generating report"
echo "=== Monthly Recovery Test Report ===" > /tmp/recovery-test-report.txt
echo "Date: $(date)" >> /tmp/recovery-test-report.txt
echo "Success: YES" >> /tmp/recovery-test-report.txt
echo "Users before: $(cat /tmp/pre-test-count.txt)" >> /tmp/recovery-test-report.txt
echo "Users after: $(cat /tmp/post-test-count.txt)" >> /tmp/recovery-test-report.txt
echo "Service health: $(cat /tmp/health-check.txt)" >> /tmp/recovery-test-report.txt

# 9. Cleanup
echo "9. Cleaning up"
rm /opt/tailsentry/users.db.test

echo "=== Test Complete ==="
echo "Report saved to /tmp/recovery-test-report.txt"
```

### Quarterly Offsite Backup Test

**Schedule**: First quarter of each quarter  
**Duration**: 3 hours

```bash
# Test restoration from offsite backup
# 1. Download backup from remote location
# 2. Verify checksum matches
# 3. Perform integrity check
# 4. Test on isolated test server
# 5. Document results
```

---

## 📞 Contact & Escalation

### Escalation Procedures

| Level | Trigger | Action | Timeline |
|-------|---------|--------|----------|
| **L1** | Service unhealthy | Automated alert to Slack #operations | Immediate |
| **L2** | Service unresponsive >5 min | Page on-call engineer | 5 minutes |
| **L3** | Data loss suspected | Escalate to manager | 10 minutes |
| **L4** | Security breach detected | Executive notification | 15 minutes |

### Contact Information

```
On-Call Engineer: /var/spool/on-call.txt
Manager: ops-manager@company.com
Executive Team: security@company.com

Backup contact: See /etc/contact-list.txt
```

---

## 📋 Pre-Disaster Checklist

Before disasters happen...

- [ ] Automated hourly backups configured
- [ ] Remote backup copy stored off-site
- [ ] Recovery procedures documented (this file)
- [ ] Recovery scripts tested and working
- [ ] Team trained on recovery procedures
- [ ] Monitoring alerts configured
- [ ] RTO/RPO targets documented and agreed upon
- [ ] DNS failover configured (if applicable)
- [ ] Standby server ready (if applicable)
- [ ] Communication plan established

---

## 📊 Recovery Documentation

### Important Locations

- Database backups: `/opt/tailsentry/backups/`
- Configuration: `/opt/tailsentry/config/`
- Secrets file: `/opt/tailsentry/.env`
- Logs: `/opt/tailsentry/logs/`
- This document: `/opt/tailsentry/DISASTER_RECOVERY.md`

### Critical Credentials (Secure Location)

Store securely in a password manager:
- Tailscale API token
- SMTP password
- SSO client secret
- Initial admin password

---

## 🔗 Related Documentation

- [DATABASE_BACKUP.md](DATABASE_BACKUP.md) - Backup procedures
- [DATABASE_RECOVERY.md](DATABASE_RECOVERY.md) - Database-specific recovery
- [SECURITY.md](SECURITY.md) - Security best practices
- [MONITORING.md](MONITORING.md) *(Phase 3)* - Monitoring and alerting

---

**Last Updated**: April 2026  
**Next Review**: July 2026  
**Created By**: DevOps Team  
**Approved By**: [Manager Name]

---

**Critical Reminder**: This plan is only useful if tested regularly. Test quarterly. Document results. Update as needed.
