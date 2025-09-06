# 🔒 TailSentry Security Hardening Script
# Run this script to fix file permissions and environment security

Write-Host "🔒 TailSentry Security Hardening" -ForegroundColor Cyan

# 1. Fix .env file permissions
if (Test-Path ".env") {
    Write-Host "Securing .env file permissions..." -ForegroundColor Yellow
    
    # Get current user
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    
    # Remove inheritance and set explicit permissions
    $acl = Get-Acl ".env"
    $acl.SetAccessRuleProtection($true, $false)  # Disable inheritance
    
    # Give full control to current user only
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule($currentUser, "FullControl", "Allow")
    $acl.SetAccessRule($accessRule)
    
    # Apply permissions
    Set-Acl -Path ".env" -AclObject $acl
    
    Write-Host "✅ .env file secured - only accessible by current user" -ForegroundColor Green
} else {
    Write-Host "⚠️  .env file not found" -ForegroundColor Yellow
}

# 2. Create secure logs directory
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# 3. Check for exposed secrets in git
Write-Host "Checking for secrets in git history..." -ForegroundColor Yellow
if (Test-Path ".git") {
    $secretCheck = git log --oneline --all | Select-String -Pattern "token|password|secret|key" -CaseSensitive:$false
    if ($secretCheck) {
        Write-Host "⚠️  Potential secrets found in git history:" -ForegroundColor Red
        $secretCheck | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        Write-Host "🔧 Consider using 'git filter-branch' or 'BFG Repo-Cleaner' to remove secrets" -ForegroundColor Yellow
    } else {
        Write-Host "✅ No obvious secrets found in git history" -ForegroundColor Green
    }
}

# 4. Create .gitignore if missing
if (!(Test-Path ".gitignore")) {
    Write-Host "Creating .gitignore file..." -ForegroundColor Yellow
    @"
# TailSentry Security
.env
*.log
logs/
data/
__pycache__/
*.pyc
.pytest_cache/

# Sensitive files
audit.log
discord_bot_audit.log
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8
    Write-Host "✅ .gitignore created" -ForegroundColor Green
}

# 5. Check Python dependencies for vulnerabilities
Write-Host "Checking Python dependencies for security vulnerabilities..." -ForegroundColor Yellow
try {
    pip install safety | Out-Null
    $safetyCheck = python -m safety check 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ No known vulnerabilities in Python dependencies" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Security vulnerabilities found:" -ForegroundColor Red
        Write-Host $safetyCheck -ForegroundColor Red
    }
} catch {
    Write-Host "⚠️  Could not check dependencies (install 'safety' package)" -ForegroundColor Yellow
}

Write-Host "`n🔒 Security hardening complete!" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor White
Write-Host "1. Regenerate your Discord bot token" -ForegroundColor White
Write-Host "2. Test bot commands with new security features" -ForegroundColor White
Write-Host "3. Monitor logs/discord_bot_audit.log for usage" -ForegroundColor White
