# TailSentry Database Validation Script (Windows PowerShell)
# Performs integrity checks on main database and backups
# Usage: .\validate_db.ps1 [-DbPath "C:\path\to\users.db"] [-BackupDir "C:\path\to\backups"]

param(
    [string]$DbPath = "$(Get-Location)\users.db",
    [string]$BackupDir = "$(Get-Location)\backups"
)

Write-Host "🔍 TailSentry Database Validation Report" -ForegroundColor Cyan
Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "============================================"
Write-Host ""

$pass = $true

# Check main database
Write-Host "📊 Main Database: $DbPath" -ForegroundColor Yellow
if (Test-Path $DbPath) {
    $size = (Get-Item $DbPath).Length
    $sizeMB = [math]::Round($size / 1MB, 2)
    Write-Host "Size: $sizeMB MB"
    
    # Check integrity
    Write-Host -NoNewline "Integrity check: "
    $sqlite = "sqlite3.exe"
    $integrity = & $sqlite $DbPath "PRAGMA integrity_check;" 2>$null
    
    if ($integrity -eq "ok") {
        Write-Host "✅ PASS" -ForegroundColor Green
    } else {
        Write-Host "❌ FAIL" -ForegroundColor Red
        Write-Host "Details: $integrity"
        $pass = $false
    }
} else {
    Write-Host "❌ Database file not found!" -ForegroundColor Red
    $pass = $false
}

Write-Host ""

# Check backups
Write-Host "📂 Backups Directory: $BackupDir" -ForegroundColor Yellow
if (Test-Path $BackupDir) {
    $backups = @(Get-ChildItem $BackupDir -Name "users.db.backup-*" 2>/dev/null).Count
    Write-Host "Total backups: $backups"
    
    if ($backups -eq 0) {
        Write-Host "⚠️  NO BACKUPS FOUND" -ForegroundColor Red
        $pass = $false
    } else {
        # Display recent backups
        Write-Host ""
        Write-Host "📋 Recent Backups:" -ForegroundColor Yellow
        Get-ChildItem $BackupDir -Name "users.db.backup-*" 2>/dev/null |
            Sort-Object -Descending |
            Select-Object -First 5 |
            ForEach-Object {
                $file = Join-Path $BackupDir $_
                $item = Get-Item $file
                $sizeMB = [math]::Round($item.Length / 1MB, 2)
                Write-Host "  $sizeMB MB - $_"
                
                # Check integrity
                $integrity = & sqlite3.exe $file "PRAGMA integrity_check;" 2>$null
                if ($integrity -eq "ok") {
                    Write-Host "    └─ ✓ valid" -ForegroundColor Green
                } else {
                    Write-Host "    └─ ✗ CORRUPTED" -ForegroundColor Red
                }
            }
        
        # Check backup age
        Write-Host ""
        $oldest = Get-ChildItem $BackupDir -Name "users.db.backup-*" 2>/dev/null | 
            Sort-Object | 
            Select-Object -First 1
        
        if ($oldest) {
            $oldestPath = Join-Path $BackupDir $oldest
            $oldestTime = (Get-Item $oldestPath).CreationTime
            $age = [math]::Round(((Get-Date) - $oldestTime).TotalDays)
            
            if ($age -gt 7) {
                Write-Host "⚠️  Oldest backup age: $age days (>7 days)" -ForegroundColor Yellow
            } else {
                Write-Host "✓ Oldest backup age: $age days" -ForegroundColor Green
            }
        }
    }
} else {
    Write-Host "❌ Backup directory not found: $BackupDir" -ForegroundColor Red
    $pass = $false
}

Write-Host ""
Write-Host "============================================"
if ($pass) {
    Write-Host "✅ All checks PASSED" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Some checks FAILED" -ForegroundColor Red
    exit 1
}
