# 📊 TailSentry Database Backup Guide

Comprehensive guide for automating SQLite database backups, verification, and retention policies for TailSentry.

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Backup Strategies](#backup-strategies)
- [Automated Backups](#automated-backups)
- [Backup Verification](#backup-verification)
- [Retention Policy](#retention-policy)
- [Restoration](#restoration)
- [Disaster Recovery Integration](#disaster-recovery-integration)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

TailSentry uses **SQLite** (`users.db`) to store:
- User credentials and authentication data
- Session tokens
- Audit logs
- Configuration settings

This database is **critical to operations** and must be protected with automated backups.

### Backup Objectives

| Objective | Target |
|-----------|--------|
| **Recovery Time Objective (RTO)** | < 15 minutes |
| **Recovery Point Objective (RPO)** | < 1 hour |
| **Retention Period** | Minimum 7 days, recommended 30 days |
| **Backup Frequency** | Hourly (adjustable) |
| **Verification** | Automatic daily checks |

---

## 🚀 Quick Start

### 1. Manual Backup (Linux)
```bash
# Create immediate backup
cp /path/to/tailsentry/users.db /path/to/backup/users.db.backup-$(date +%Y%m%d-%H%M%S)

# Verify backup
sqlite3 /path/to/backup/users.db.backup-* "SELECT COUNT(*) FROM users;"
```

### 2. Manual Backup (Windows)
```powershell
# Create immediate backup
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item "C:\TailSentry\users.db" "C:\TailSentry\backups\users.db.backup-$timestamp"

# Verify backup
.\scripts\backup_db.ps1 -Verify
```

### 3. Schedule Automated Backup (Linux - Cron)
```bash
# Edit crontab
crontab -e

# Add hourly backup (runs at minute 0 of each hour)
0 * * * * /path/to/tailsentry/scripts/backup_db.sh

# Add daily verification (runs at 2 AM daily)
0 2 * * * /path/to/tailsentry/scripts/validate_db.sh
```

### 4. Schedule Automated Backup (Windows - Task Scheduler)
```powershell
# Run as administrator
PS> .\scripts\schedule_backup.ps1

# This creates a task that runs hourly
```

---

## 💾 Backup Strategies

### Strategy 1: Local File-Based Backup (Simple)

**Best for**: Single-instance deployments, small teams

**Pros**:
- Simple to implement
- No external dependencies
- Fast restore
- Works offline

**Cons**:
- No geographic redundancy
- Vulnerable to local disk failure
- Requires separate monitoring

**Implementation**:
```bash
#!/bin/bash
# scripts/backup_db.sh

DB_PATH="/path/to/tailsentry/users.db"
BACKUP_DIR="/path/to/tailsentry/backups"
RETENTION_DAYS=30

# Create backup
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
cp "$DB_PATH" "$BACKUP_DIR/users.db.backup-$TIMESTAMP"

# Delete old backups (older than RETENTION_DAYS)
find "$BACKUP_DIR" -name "users.db.backup-*" -mtime +$RETENTION_DAYS -delete

echo "Backup created: $BACKUP_DIR/users.db.backup-$TIMESTAMP"
```

### Strategy 2: Remote Backup (Enterprise)

**Best for**: Production deployments, compliance requirements

**Pros**:
- Geographic redundancy
- Off-site protection
- Compliance-friendly
- Immutable backup storage

**Cons**:
- Network overhead
- Potential latency
- Additional infrastructure

**Implementation**:
```bash
#!/bin/bash
# scripts/backup_db_remote.sh

DB_PATH="/path/to/tailsentry/users.db"
BACKUP_DIR="/path/to/tailsentry/backups"
REMOTE_SERVER="backup.company.com"
REMOTE_PATH="/backups/tailsentry"
RETENTION_DAYS=30

# Create local backup
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="users.db.backup-$TIMESTAMP"
cp "$DB_PATH" "$BACKUP_DIR/$BACKUP_FILE"

# Verify backup integrity
if ! sqlite3 "$BACKUP_DIR/$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
  echo "ERROR: Backup integrity check failed!"
  exit 1
fi

# Send to remote server (using rsync or scp)
rsync -av "$BACKUP_DIR/$BACKUP_FILE" "$REMOTE_SERVER:$REMOTE_PATH/"

# Clean up old backups locally
find "$BACKUP_DIR" -name "users.db.backup-*" -mtime +$RETENTION_DAYS -delete

# Clean up old backups on remote
ssh "$REMOTE_SERVER" "find $REMOTE_PATH -name 'users.db.backup-*' -mtime +$RETENTION_DAYS -delete"

echo "Backup synced to remote: $REMOTE_SERVER:$REMOTE_PATH/$BACKUP_FILE"
```

### Strategy 3: Docker Volume Backup

**Best for**: Docker deployments

**Pros**:
- Container-native approach
- Works with compose
- Easy to automate in docker-compose

**Cons**:
- Requires volume management tools
- May need container restart

**Implementation** (`docker-compose.backup.yml`):
```yaml
version: '3.8'

services:
  tailsentry:
    image: tailsentry:latest
    volumes:
      - tailsentry-data:/app/data
    # existing config...

  backup:
    image: alpine:latest
    volumes:
      - tailsentry-data:/data
      - ./backups:/backup
    command: |
      sh -c '
        while true; do
          TIMESTAMP=$$(date +%Y%m%d-%H%M%S)
          cp /data/users.db /backup/users.db.backup-$$TIMESTAMP
          find /backup -name "users.db.backup-*" -mtime +30 -delete
          sleep 3600
        done
      '
    depends_on:
      - tailsentry

volumes:
  tailsentry-data:
```

---

## 🤖 Automated Backups

### Linux: Cron-Based Automation

1. **Create backup script** (`scripts/backup_db.sh`):
```bash
#!/bin/bash
set -e

DB_PATH="${DB_PATH:-/opt/tailsentry/users.db}"
BACKUP_DIR="${BACKUP_DIR:-/opt/tailsentry/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Create backup with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/users.db.backup-$TIMESTAMP"
cp "$DB_PATH" "$BACKUP_FILE"

# Verify backup
if ! sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "ERROR: Backup verification failed for $BACKUP_FILE" >&2
    exit 1
fi

# Clean old backups
find "$BACKUP_DIR" -name "users.db.backup-*" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup successful: $BACKUP_FILE"
```

2. **Make script executable**:
```bash
chmod +x scripts/backup_db.sh
```

3. **Add to crontab**:
```bash
# Run every hour
0 * * * * /opt/tailsentry/scripts/backup_db.sh >> /var/log/tailsentry-backup.log 2>&1

# Run daily verification
0 2 * * * /opt/tailsentry/scripts/validate_db.sh >> /var/log/tailsentry-backup.log 2>&1
```

### Linux: Systemd Timer Automation (Modern Alternative)

**Create service** (`/etc/systemd/system/tailsentry-backup.service`):
```ini
[Unit]
Description=TailSentry Database Backup
After=tailsentry.service

[Service]
Type=oneshot
User=tailsentry
ExecStart=/opt/tailsentry/scripts/backup_db.sh
StandardOutput=journal
StandardError=journal
```

**Create timer** (`/etc/systemd/system/tailsentry-backup.timer`):
```ini
[Unit]
Description=TailSentry Backup Timer
Requires=tailsentry-backup.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
AccuracySec=1min
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable timer**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tailsentry-backup.timer
sudo systemctl start tailsentry-backup.timer

# Check status
sudo systemctl list-timers tailsentry-backup.timer
```

### Windows: Task Scheduler Automation

**Create script** (`scripts/schedule_backup.ps1`):
```powershell
# Run as Administrator
$TaskName = "TailSentry Database Backup"
$TaskPath = "\TailSentry\"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File 'C:\TailSentry\scripts\backup_db.ps1'"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Trigger = New-ScheduledTaskTrigger -Hourly -At 00
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
Write-Host "✅ Backup task scheduled: $TaskName"
```

**Create backup script** (`scripts/backup_db.ps1`):
```powershell
param(
    [string]$DbPath = "C:\TailSentry\users.db",
    [string]$BackupDir = "C:\TailSentry\backups",
    [int]$RetentionDays = 30,
    [switch]$Verify
)

# Create backup directory
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $BackupDir "users.db.backup-$timestamp"

# Create backup
Copy-Item -Path $DbPath -Destination $backupFile -Force

# Verify backup
$sqlite = "sqlite3.exe"
$query = "PRAGMA integrity_check;"
$output = & $sqlite $backupFile $query

if ($output -match "ok") {
    Write-Host "✅ Backup successful: $backupFile"
} else {
    Write-Host "❌ Backup verification failed for $backupFile"
    exit 1
}

# Clean old backups
$oldBackups = Get-ChildItem $BackupDir -Name "users.db.backup-*" | 
    ForEach-Object { [pscustomobject]@{ Name=$_; Time=(Get-Item (Join-Path $BackupDir $_)).CreationTime } } |
    Where-Object { $_.Time -lt (Get-Date).AddDays(-$RetentionDays) }

$oldBackups | ForEach-Object {
    Remove-Item (Join-Path $BackupDir $_.Name)
    Write-Host "🗑️  Deleted old backup: $($_.Name)"
}
```

---

## ✅ Backup Verification

### Automated Verification Script

**Linux** (`scripts/validate_db.sh`):
```bash
#!/bin/bash

DB_PATH="${DB_PATH:-/opt/tailsentry/users.db}"
BACKUP_DIR="${BACKUP_DIR:-/opt/tailsentry/backups}"

echo "🔍 Database Verification Report - $(date)"
echo "============================================"

# Check main database
echo ""
echo "📊 Main Database: $DB_PATH"
if [ -f "$DB_PATH" ]; then
    SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo "Size: $SIZE"
    INTEGRITY=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;")
    if [ "$INTEGRITY" = "ok" ]; then
        echo "✅ Integrity: PASS"
    else
        echo "❌ Integrity: FAIL - $INTEGRITY"
    fi
else
    echo "❌ Database file not found!"
fi

# Check backups
echo ""
echo "📂 Backups Directory: $BACKUP_DIR"
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "users.db.backup-*" | wc -l)
echo "Backup count: $BACKUP_COUNT"

echo ""
echo "📋 Recent Backups:"
ls -lh "$BACKUP_DIR"/users.db.backup-* | tail -5

# Check oldest backup age
if [ $BACKUP_COUNT -gt 0 ]; then
    OLDEST=$(find "$BACKUP_DIR" -name "users.db.backup-*" -printf '%T@ %p\n' | sort -n | head -1 | cut -d' ' -f2-)
    OLDEST_AGE=$(( ($(date +%s) - $(date -r "$OLDEST" +%s)) / 86400 ))
    echo ""
    echo "📅 Oldest backup age: $OLDEST_AGE days"
fi
```

**Windows** (`scripts/validate_db.ps1`):
```powershell
param(
    [string]$DbPath = "C:\TailSentry\users.db",
    [string]$BackupDir = "C:\TailSentry\backups"
)

Write-Host "🔍 Database Verification Report - $(Get-Date)" -ForegroundColor Cyan
Write-Host "============================================"

# Check main database
Write-Host ""
Write-Host "📊 Main Database: $DbPath" -ForegroundColor Yellow
if (Test-Path $DbPath) {
    $size = (Get-Item $DbPath).Length
    Write-Host "Size: $([math]::Round($size/1MB, 2)) MB"
    
    $integrity = & sqlite3.exe $DbPath "PRAGMA integrity_check;"
    if ($integrity -eq "ok") {
        Write-Host "✅ Integrity: PASS" -ForegroundColor Green
    } else {
        Write-Host "❌ Integrity: FAIL - $integrity" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Database file not found!" -ForegroundColor Red
}

# Check backups
Write-Host ""
Write-Host "📂 Backups Directory: $BackupDir" -ForegroundColor Yellow
$backups = Get-ChildItem $BackupDir -Name "users.db.backup-*" 2>/dev/null
$backupCount = $backups.Count
Write-Host "Backup count: $backupCount"

Write-Host ""
Write-Host "📋 Recent Backups:" -ForegroundColor Yellow
Get-ChildItem $BackupDir -Name "users.db.backup-*" 2>/dev/null | 
    ForEach-Object { Get-Item (Join-Path $BackupDir $_) } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 5 |
    Format-Table Name, @{Name="Size (MB)"; Expression={[math]::Round($_.Length/1MB, 2)}}, LastWriteTime
```

---

## 🔄 Retention Policy

### Recommended Retention Schedule

```
Backup Frequency: Hourly
Retention Period:
  - Last 24 hours:  Keep all hourly backups (24 backups)
  - Days 2-7:       Keep 1 daily backup per day (6 backups)
  - Days 8-30:      Keep 1 weekly backup (3 backups)
  
Total: ~33 backups maximum (~500MB-1GB disk usage)
```

### Tiered Retention Script

```bash
#!/bin/bash
# scripts/retention_policy.sh

BACKUP_DIR="/opt/tailsentry/backups"

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "users.db.backup-*" -mtime +30 -delete

# For the last 7 days, keep only one backup per day (01:00 if possible)
# This is more complex and typically handled by backup software
```

---

## 🔄 Restoration

### Restore from Latest Backup

**Linux**:
```bash
#!/bin/bash
# scripts/restore_db.sh [backup_file]

DB_PATH="/opt/tailsentry/users.db"
BACKUP_DIR="/opt/tailsentry/backups"

if [ -z "$1" ]; then
    # Find latest backup
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/users.db.backup-* | head -1)
    echo "Using latest backup: $BACKUP_FILE"
else
    BACKUP_FILE="$1"
fi

# Verify backup
if ! sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "ERROR: Backup integrity check failed!"
    exit 1
fi

# Create safety copy
cp "$DB_PATH" "$DB_PATH.pre-restore-$(date +%Y%m%d-%H%M%S)"

# Restore
cp "$BACKUP_FILE" "$DB_PATH"

# Verify restored database
if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "✅ Successfully restored from $BACKUP_FILE"
else
    echo "❌ Restoration failed or database corrupted"
    exit 1
fi
```

**Windows**:
```powershell
param(
    [string]$BackupFile,
    [string]$DbPath = "C:\TailSentry\users.db",
    [string]$BackupDir = "C:\TailSentry\backups"
)

if (-not $BackupFile) {
    # Find latest backup
    $BackupFile = Get-ChildItem $BackupDir -Name "users.db.backup-*" | 
        Sort-Object -Descending | 
        Select-Object -First 1
    $BackupFile = Join-Path $BackupDir $BackupFile
    Write-Host "Using latest backup: $BackupFile"
}

# Verify backup
$integrity = & sqlite3.exe $BackupFile "PRAGMA integrity_check;"
if ($integrity -ne "ok") {
    Write-Host "❌ Backup integrity check failed!"
    exit 1
}

# Create safety copy
$safetyBackup = "$DbPath.pre-restore-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $DbPath $safetyBackup
Write-Host "Created safety copy: $safetyBackup"

# Restore
Copy-Item $BackupFile $DbPath -Force
Write-Host "✅ Restored from backup"

# Verify restored database
$integrity = & sqlite3.exe $DbPath "PRAGMA integrity_check;"
if ($integrity -eq "ok") {
    Write-Host "✅ Restoration successful and verified"
} else {
    Write-Host "❌ Restoration failed - restoring safety copy"
    Copy-Item $safetyBackup $DbPath -Force
    exit 1
}
```

---

## 🆘 Disaster Recovery Integration

**See also**: [DATABASE_RECOVERY.md](DATABASE_RECOVERY.md) and [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)

Key integration points:
- Automated backups are prerequisite for recovery
- Verify `users.db` is backed up at least daily
- Test restoration quarterly
- Document backup location and access procedures
- Include backup location in DR manual

---

## 🔧 Troubleshooting

### Problem: Backup Script Fails

**Solution**:
1. Check disk space: `df -h`
2. Verify permissions: `ls -la /opt/tailsentry/`
3. Check database is not locked: `lsof | grep users.db`
4. Review logs: `tail -f /var/log/tailsentry-backup.log`

### Problem: Backups Taking Too Long

**Solution**:
1. Check database size: `du -h /opt/tailsentry/users.db`
2. Consider incremental backups
3. Run during off-peak hours
4. Check for heavy I/O

### Problem: Restore Fails

**Solution**:
1. Verify backup integrity first
2. Check target database permissions
3. Ensure TailSentry service is stopped
4. Verify no open connections: `lsof | grep users.db`

---

## ✨ Summary

Database backup automation is **critical** for TailSentry reliability. Recommended setup:
- ✅ Automated hourly backups
- ✅ Daily integrity verification
- ✅ 30-day retention policy
- ✅ Monthly restoration testing
- ✅ Remote backup copy for production

**Next Steps**:
1. Set up automated backup script appropriate for your platform
2. Schedule daily verification
3. Test restoration procedure quarterly
4. Document backup location and procedures
5. Refer to [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) for full recovery procedures

