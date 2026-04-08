# 🔧 TailSentry Database Recovery Guide

Comprehensive guide for detecting, validating, and recovering from SQLite database corruption and failures.

## 📋 Table of Contents

- [Overview](#overview)
- [Corruption Detection](#corruption-detection)
- [Recovery Procedures](#recovery-procedures)
- [Partial Recovery](#partial-recovery)
- [Prevention](#prevention)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

Database corruption can occur due to:
- Unexpected power loss or system crash
- Corrupted backups
- Filesystem errors
- Hardware failures
- Software conflicts

This guide covers how to detect and recover from these scenarios.

### Recovery Options

| Scenario | Solution | RTO | Data Loss |
|----------|----------|-----|-----------|
| **Corrupted main DB** | Restore from backup | 5-10 min | < 1 hour |
| **All backups corrupted** | Partial recovery + rebuild | 30 min | Variable |
| **Backup unavailable** | Manual recreation | 60+ min | High |

---

## 🔍 Corruption Detection

### 1. Automatic Validation

**Run the validation script**:

```bash
# Linux
./scripts/validate_db.sh

# Windows (PowerShell)
.\scripts\validate_db.ps1
```

**Expected Output** (pass):
```
✅ All checks PASSED
```

**Failed Output** (corruption detected):
```
❌ FAIL
Details: database disk image is malformed
```

### 2. Manual Integrity Check

**SQL Integrity Pragma**:
```bash
sqlite3 /path/to/users.db "PRAGMA integrity_check;"
```

**Output**:
- **`ok`** = Database is healthy
- **`corruption`** = Database is corrupt
- **Specific errors** = Indicates type of corruption

**Examples**:
```
# Good
$ sqlite3 users.db "PRAGMA integrity_check;"
ok

# Bad - Image is malformed
$ sqlite3 users.db "PRAGMA integrity_check;"
database disk image is malformed

# Bad - Corruption details
$ sqlite3 users.db "PRAGMA integrity_check;"
wrong page type
duplicate table definitions
```

### 3. Quick Health Check

```bash
# Test basic connectivity
sqlite3 users.db "SELECT COUNT(*) FROM users;"

# If this fails or hangs, corruption is likely present
```

### 4. Backup Health Check

```bash
# Check all backups for corruption
for backup in backups/users.db.backup-*; do
    echo "Checking $backup..."
    sqlite3 "$backup" "PRAGMA integrity_check;" | grep -q "ok" && echo "✓ OK" || echo "✗ CORRUPT"
done
```

---

## 🔄 Recovery Procedures

### Scenario 1: Main Database Corrupted (Backups Healthy)

**Duration**: 5-10 minutes

**Steps**:

1. **Stop TailSentry service**:
   ```bash
   # Linux systemd
   sudo systemctl stop tailsentry
   
   # Linux manual
   pkill -f "python main.py"
   
   # Windows
   Stop-Service TailSentry
   ```

2. **Verify corruption**:
   ```bash
   sqlite3 /path/to/users.db "PRAGMA integrity_check;"
   # Should show corruption
   ```

3. **Identify good backup**:
   ```bash
   # Find most recent backup
   ls -lt backups/users.db.backup-* | head -1
   
   # Test backup
   sqlite3 backups/users.db.backup-20250408-143022 "PRAGMA integrity_check;"
   # Should show "ok"
   ```

4. **Create safety copy**:
   ```bash
   cp /path/to/users.db /path/to/users.db.corrupted-$(date +%s)
   ```

5. **Restore from backup**:
   ```bash
   # Linux
   cp backups/users.db.backup-20250408-143022 /path/to/users.db
   
   # Windows PowerShell
   Copy-Item "backups\users.db.backup-20250408-143022" "users.db" -Force
   ```

6. **Verify restored database**:
   ```bash
   sqlite3 /path/to/users.db "PRAGMA integrity_check;"
   # Should show "ok"
   ```

7. **Restart TailSentry**:
   ```bash
   # Linux systemd
   sudo systemctl start tailsentry
   
   # Windows
   Start-Service TailSentry
   ```

8. **Verify service is healthy**:
   ```bash
   curl http://localhost:8080/health
   # Should return 200 OK
   ```

### Scenario 2: Multiple Backups Corrupted

**Duration**: 30 minutes

**Steps**:

1. **Stop TailSentry service** (see Scenario 1, step 1)

2. **Find oldest good backup**:
   ```bash
   # Test all backups for integrity
   for backup in backups/users.db.backup-*; do
       RESULT=$(sqlite3 "$backup" "PRAGMA integrity_check;" 2>&1)
       if [ "$RESULT" == "ok" ]; then
           echo "Good backup: $backup"
           break
       fi
   done
   ```

3. **If no good backups found**:
   
   Proceed to **Scenario 3** (Partial Recovery)

4. **If good backup found**:
   
   Follow Scenario 1, steps 4-8

### Scenario 3: All Backups Corrupted (Partial Recovery)

**Duration**: 30-60 minutes  
**Data Loss**: All data since last healthy backup

**Steps**:

1. **Stop TailSentry service**

2. **Dump database contents** (if possible):
   ```bash
   sqlite3 /path/to/users.db ".dump" > db_dump.sql 2>&1
   ```

3. **Create new database from dump**:
   ```bash
   rm /path/to/users.db
   sqlite3 /path/to/users.db < db_dump.sql
   ```

4. **Verify new database**:
   ```bash
   sqlite3 /path/to/users.db "PRAGMA integrity_check;"
   sqlite3 /path/to/users.db "SELECT COUNT(*) FROM users;"
   ```

5. **If dump fails** → Proceed to Scenario 4

### Scenario 4: Complete Data Loss (Rebuild from Scratch)

**Duration**: 60+ minutes  
**Data Loss**: Complete - requires password reset for all users  

**Steps**:

1. **Stop TailSentry service**

2. **Backup corrupted database**:
   ```bash
   cp /path/to/users.db /path/to/users.db.lost-$(date +%s)
   ```

3. **Delete corrupted database**:
   ```bash
   rm /path/to/users.db
   ```

4. **Start TailSentry** - This will create a fresh database:
   ```bash
   systemctl start tailsentry
   
   # Or manually
   python main.py
   ```

5. **Create new admin user** via the setup wizard

6. **Restore data manually**:
   - Re-add users
   - Re-configure settings
   - Check that configuration files are intact (they should be)

---

## 🔚 Partial Recovery

### Using WAL Files (Write-Ahead Logging)

SQLite may have transaction data in `.db-wal` and `.db-shm` files:

```bash
# These files may contain recent changes
ls -la users.db*

# If WAL files exist, they contain unwritten transactions
# SQLite should recover them automatically on next start
```

### Using Raw Recovery Tools

For severe corruption, consider:

1. **sqlite3 recovery module** (if available):
   ```bash
   # Some systems have recovery extensions
   sqlite3 users.db ".recover" | sqlite3 recovered.db
   ```

2. **Third-party recovery tools**:
   - [DBRecovery](https://www.dbsoftwares.com/dbrecovery/sqlite.html)
   - [SQLiteDoctor](https://www.sqlitedoctor.com/)

3. **Manual table recovery**:
   ```sql
   -- Export individual tables
   .mode insert
   .output users_export.sql
   SELECT * FROM users;
   ```

---

## 🛡️ Prevention

### 1. Regular Validation

**Automated daily checks**:

```bash
# Add to crontab
0 2 * * * /opt/tailsentry/scripts/validate_db.sh >> /var/log/tailsentry-backup.log 2>&1
```

### 2. Backup Verification

**Before relying on a backup**, verify it works:

```bash
# Test backup restoration quarterly
TEST_BACKUP="backups/users.db.backup-20250408-143022"
TEST_DIR="/tmp/test_restore"

mkdir -p "$TEST_DIR"
cp "$TEST_BACKUP" "$TEST_DIR/users.db"
sqlite3 "$TEST_DIR/users.db" "PRAGMA integrity_check;"
sqlite3 "$TEST_DIR/users.db" "SELECT COUNT(*) FROM users;"
rm -rf "$TEST_DIR"
```

### 3. Filesystem Health

**Monitor filesystem for errors**:

```bash
# Linux - check filesystem health
fsck -n /dev/sdXX  # Read-only check

# Monitor logs for I/O errors
tail -f /var/log/syslog | grep "I/O error"
```

### 4. Graceful Shutdowns

**Always stop TailSentry properly**:

```bash
# Proper shutdown
systemctl stop tailsentry

# Wait for it to finish
sleep 2

# Verify it stopped
systemctl status tailsentry
```

### 5. UPS Protection

For critical deployments, use UPS (Uninterruptible Power Supply) to prevent power-loss corruption.

---

## 🔧 Troubleshooting

### Problem: "database disk image is malformed"

**Troubleshooting**:
1. Check disk space: `df -h`
2. Check file permissions: `ls -la users.db`
3. Try immediate restart (sometimes temporary)
4. If persists, attempt recovery procedures above

### Problem: "database is locked"

**Troubleshooting**:
1. Check for running processes: `lsof | grep users.db`
2. Ensure TailSentry service is stopped: `systemctl stop tailsentry`
3. Kill orphaned processes: `pkill -f "sqlite3.*users"`
4. Wait 30 seconds and try again

### Problem: Backup restoration fails

**Troubleshooting**:
1. Verify backup is valid: `sqlite3 backup.db "PRAGMA integrity_check;"`
2. Check target permissions: `chmod 644 users.db`
3. Ensure TailSentry is stopped: `systemctl stop tailsentry`
4. Try manual restore: `cp backup.db users.db`
5. Try a different backup

### Problem: WAL file issues

**Troubleshooting**:
```bash
# Clean up WAL files
rm users.db-wal users.db-shm

# Restart service
systemctl restart tailsentry
```

---

## ✅ Verification Checklist

After recovery, verify:

- [ ] Database passes integrity check: `sqlite3 users.db "PRAGMA integrity_check;"`
- [ ] No errors in TailSentry logs: `tail -f logs/tailsentry.log`
- [ ] Dashboard loads: `curl http://localhost:8080/`
- [ ] Users can log in
- [ ] Expected data is present: `sqlite3 users.db "SELECT COUNT(*) FROM users;"`
- [ ] Audit logs show recent activity
- [ ] No I/O errors in system logs

---

## 📞 When to Call Support

If recovery procedures fail:

1. ✅ Have already attempted all recovery procedures
2. ✅ Have backup of corrupted database (`users.db.corrupted-*`)
3. ✅ Have validation results showing corruption
4. ✅ Have attempted restoration from multiple backups

---

## 🔗 Related Documentation

- [DATABASE_BACKUP.md](DATABASE_BACKUP.md) - Backup procedures
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) - Full disaster recovery plan
- [scripts/validate_db.sh](scripts/validate_db.sh) - Validation script
- [scripts/backup_db.sh](scripts/backup_db.sh) - Backup script

---

**Remember**: Prevention is easier than recovery. Maintain automated backups and regular validation!
