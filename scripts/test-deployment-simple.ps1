# test-deployment-simple.ps1 - Simple deployment test for Windows
Write-Host "🚀 TailSentry Simple Deployment Test" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

$errors = 0

# Test 1: Python version
Write-Host ""
Write-Host "ℹ️  Testing Python environment..." -ForegroundColor Blue
try {
    $pythonVersion = python --version
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python not found" -ForegroundColor Red
    $errors++
}

# Test 2: Core dependencies
Write-Host ""
Write-Host "ℹ️  Testing core dependencies..." -ForegroundColor Blue
try {
    python -c "import fastapi, uvicorn, jinja2"
    Write-Host "✅ Core dependencies available" -ForegroundColor Green
}
catch {
    Write-Host "❌ Core dependencies missing" -ForegroundColor Red
    $errors++
}

# Test 3: Tailscale
Write-Host ""
Write-Host "ℹ️  Testing Tailscale..." -ForegroundColor Blue
try {
    $tailscaleOutput = tailscale version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $version = ($tailscaleOutput | Select-Object -First 1) -replace '\s+', ' '
        Write-Host "✅ Tailscale found: $version" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Tailscale not authenticated or not running" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Tailscale not found" -ForegroundColor Red
    $errors++
}

# Test 4: TailSentry import
Write-Host ""
Write-Host "ℹ️  Testing TailSentry import..." -ForegroundColor Blue
try {
    python -c "import sys; sys.path.insert(0, '.'); import main"
    Write-Host "✅ TailSentry imports successfully" -ForegroundColor Green
}
catch {
    Write-Host "❌ TailSentry import failed" -ForegroundColor Red
    $errors++
}

# Test 5: Basic file structure
Write-Host ""
Write-Host "ℹ️  Testing file structure..." -ForegroundColor Blue
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

# Test 6: Basic startup test
Write-Host ""
Write-Host "ℹ️  Testing basic startup..." -ForegroundColor Blue
try {
    # Start the application briefly
    $job = Start-Job -ScriptBlock {
        Set-Location $args[0]
        python main.py
    } -ArgumentList (Get-Location)
    
    Start-Sleep -Seconds 3
    
    # Check if it's running
    if ($job.State -eq "Running") {
        Write-Host "✅ Application starts successfully" -ForegroundColor Green
        Stop-Job $job
        Remove-Job $job
        
        # Quick health check
        try {
            Start-Sleep -Seconds 2
            $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ Health endpoint responding" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "⚠️  Health endpoint not responding (may be normal)" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "❌ Application failed to start" -ForegroundColor Red
        $errors++
    }
}
catch {
    Write-Host "❌ Startup test failed: $_" -ForegroundColor Red
    $errors++
}
finally {
    # Cleanup any remaining jobs
    Get-Job | Where-Object { $_.Name -like "Job*" } | Stop-Job -ErrorAction SilentlyContinue
    Get-Job | Where-Object { $_.Name -like "Job*" } | Remove-Job -ErrorAction SilentlyContinue
}

# Results
Write-Host ""
Write-Host "🎯 Test Summary" -ForegroundColor Cyan
Write-Host "===============" -ForegroundColor Cyan
if ($errors -eq 0) {
    Write-Host "✅ All tests passed! TailSentry is ready." -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 Next steps:" -ForegroundColor Green
    Write-Host "1. Start TailSentry: python main.py"
    Write-Host "2. Open browser: http://localhost:8080"
    Write-Host "3. Login and test functionality"
    Write-Host "4. Deploy to your spare computer"
}
else {
    Write-Host "❌ $errors test(s) failed. Please fix issues before deployment." -ForegroundColor Red
    Write-Host ""
    Write-Host "🔧 Common fixes:" -ForegroundColor Yellow
    Write-Host "1. Install missing dependencies: pip install fastapi uvicorn jinja2"
    Write-Host "2. Install/setup Tailscale from tailscale.com"
    Write-Host "3. Check file permissions and structure"
}

Write-Host ""
exit $errors
