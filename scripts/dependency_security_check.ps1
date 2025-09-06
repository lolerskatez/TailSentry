# Dependency Security Check Script
# Run this regularly to check for known vulnerabilities

# Install safety for vulnerability scanning
pip install safety

# Check for known vulnerabilities in installed packages
Write-Host "🔍 Scanning for known vulnerabilities in Python packages..." -ForegroundColor Yellow
pip list --format=freeze | python -m safety check --stdin

# Check for outdated packages
Write-Host "`n📦 Checking for outdated packages..." -ForegroundColor Yellow
pip list --outdated

# Audit Discord.py specifically (most critical dependency)
Write-Host "`n🤖 Discord.py security information:" -ForegroundColor Cyan
pip show discord.py | Select-String "Version|Author|Summary"

# Check requirements files for version pinning
Write-Host "`n📌 Checking version pinning in requirements..." -ForegroundColor Yellow
$requirements_files = @("requirements.txt", "requirements-frozen.txt", "requirements-dev.txt")

foreach ($file in $requirements_files) {
    if (Test-Path $file) {
        Write-Host "`nChecking ${file}:" -ForegroundColor White
        $unpinned = Select-String -Path $file -Pattern "^[^#]*[^=<>~!]$" | Select-Object -First 5
        if ($unpinned) {
            Write-Host "⚠️  Unpinned dependencies found:" -ForegroundColor Red
            $unpinned.Line
        } else {
            Write-Host "✅ All dependencies properly pinned" -ForegroundColor Green
        }
    }
}

# Check for development dependencies in production
Write-Host "`n🔍 Checking for development dependencies..." -ForegroundColor Yellow
$dev_patterns = @("test", "dev", "debug", "mock", "pytest", "coverage")
pip list | Select-String -Pattern ($dev_patterns -join "|") | ForEach-Object {
    Write-Host "⚠️  Development package detected: $($_.Line)" -ForegroundColor Red
}

Write-Host "`n✅ Dependency security scan complete!" -ForegroundColor Green
Write-Host "💡 Recommendations:" -ForegroundColor Cyan
Write-Host "   - Run 'pip-audit' for more detailed security scanning" -ForegroundColor White
Write-Host "   - Update packages regularly: pip install --upgrade -r requirements.txt" -ForegroundColor White
Write-Host "   - Consider using 'pip-tools' for better dependency management" -ForegroundColor White
