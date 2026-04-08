# TailSentry Database Backup Script (Windows PowerShell)
# Automated backup of SQLite database with integrity checking
# Usage: .\backup_db.ps1 [-DbPath "C:\path\to\users.db"] [-BackupDir "C:\path\to\backups"] [-RetentionDays 30]

param(
    [string]$DbPath = "$(Get-Location)\users.db",
    [string]$BackupDir = "$(Get-Location)\backups",
    [int]$RetentionDays = 30,
    [switch]$Verify
)

# Verify database exists
if (-not (Test-Path $DbPath)) {
    Write-Host "❌ ERROR: Database not found at $DbPath" -ForegroundColor Red
    exit 1
}

# Create backup directory
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $BackupDir "users.db.backup-$timestamp"

Write-Host "📊 Starting TailSentry database backup..." -ForegroundColor Yellow
Write-Host "Database: $DbPath"
Write-Host "Backup location: $backupFile"
Write-Host ""

# Create backup
try {
    Copy-Item -Path $DbPath -Destination $backupFile -Force
} catch {
    Write-Host "❌ ERROR: Failed to create backup - $_" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Backup file created" -ForegroundColor Green

# Verify backup integrity
Write-Host -NoNewline "Verifying backup integrity... "
$sqlite = "sqlite3.exe"

# Check if sqlite3 is available
if (-not (Get-Command $sqlite -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  WARNING: sqlite3.exe not found in PATH" -ForegroundColor Yellow
    Write-Host "Integrity check skipped. Deploy sqlite3.exe to PATH for verification."
} else {
    $output = & $sqlite $backupFile "PRAGMA integrity_check;" 2>$null
    if ($output -match "ok") {
        Write-Host "✓ PASSED" -ForegroundColor Green
    } else {
        Write-Host "❌ FAILED" -ForegroundColor Red
        Remove-Item $backupFile
        Write-Host "❌ ERROR: Backup verification failed - backup deleted" -ForegroundColor Red
        exit 1
    }
}

# Get backup size
$backupSize = (Get-Item $backupFile).Length
$backupSizeMB = [math]::Round($backupSize / 1MB, 2)
Write-Host "Backup size: $backupSizeMB MB"
Write-Host ""

# Clean old backups
Write-Host "Cleaning backups older than $RetentionDays days..."
$oldBackups = Get-ChildItem $BackupDir -Name "users.db.backup-*" 2>/dev/null | 
    ForEach-Object { [pscustomobject]@{ Name=$_; Path=(Join-Path $BackupDir $_); Time=(Get-Item (Join-Path $BackupDir $_)).CreationTime } } |
    Where-Object { $_.Time -lt (Get-Date).AddDays(-$RetentionDays) }

if ($oldBackups.Count -gt 0) {
    $oldBackups | ForEach-Object {
        Remove-Item $_.Path
        Write-Host "  Deleted: $($_.Name)" -ForegroundColor Green
    }
    Write-Host "✓ Deleted $($oldBackups.Count) old backup(s)" -ForegroundColor Green
} else {
    Write-Host "No old backups to delete"
}

# Count remaining backups
$backupCount = @(Get-ChildItem $BackupDir -Name "users.db.backup-*" 2>/dev/null).Count
Write-Host "Active backups: $backupCount"

Write-Host ""
Write-Host "✅ Backup completed successfully" -ForegroundColor Green
Write-Host "Location: $backupFile"
