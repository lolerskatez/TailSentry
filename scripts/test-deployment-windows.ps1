# test-deployment-windows.ps1 - Simple deployment test for Windows
Write-Host "TailSentry Deployment Test (Windows)" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

$errors = 0

# Test Python
Write-Host ""
Write-Host "Testing Python environment..." -ForegroundColor Blue
try {
    $pythonVersion = python --version
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python not found" -ForegroundColor Red
    $errors++
}

# Test core dependencies
Write-Host ""
Write-Host "Testing core dependencies..." -ForegroundColor Blue
try {
    python -c "import fastapi, uvicorn, jinja2"
    Write-Host "✅ Core dependencies available" -ForegroundColor Green
}
catch {
    Write-Host "❌ Core dependencies missing" -ForegroundColor Red
    $errors++
}

# Test Tailscale
Write-Host ""
Write-Host "Testing Tailscale..." -ForegroundColor Blue
try {
    $tailscaleOutput = tailscale version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $version = ($tailscaleOutput | Select-Object -First 1) -replace '\s+', ' '
        Write-Host "✅ Tailscale found: $version" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Tailscale not authenticated" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Tailscale not found" -ForegroundColor Red
    $errors++
}

# Test TailSentry import
Write-Host ""
Write-Host "Testing TailSentry import..." -ForegroundColor Blue
try {
    python -c "import sys; sys.path.insert(0, '.'); import main"
    Write-Host "✅ TailSentry imports successfully" -ForegroundColor Green
}
catch {
    Write-Host "❌ TailSentry import failed" -ForegroundColor Red
    $errors++
}

# Test files
Write-Host ""
Write-Host "Testing file structure..." -ForegroundColor Blue
$requiredFiles = @("main.py", "tailscale_client.py", "helpers.py", "auth.py")
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        $errors++
    }
}

# Summary
Write-Host ""
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "============" -ForegroundColor Cyan
if ($errors -eq 0) {
    Write-Host "✅ All tests passed! TailSentry is ready." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Green
    Write-Host "1. Start TailSentry: python main.py"
    Write-Host "2. Open browser: http://localhost:8080"
    Write-Host "3. Test functionality"
    Write-Host "4. Deploy to spare computer"
}
else {
    Write-Host "❌ $errors test(s) failed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Common fixes:" -ForegroundColor Yellow
    Write-Host "1. Install dependencies: pip install fastapi uvicorn jinja2"
    Write-Host "2. Install Tailscale from tailscale.com"
    Write-Host "3. Check file structure"
}

Write-Host ""
exit $errors
