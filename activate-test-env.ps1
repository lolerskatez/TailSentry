# activate-test-env.ps1 - Activate TailSentry testing environment
if (Test-Path "venv") {
    & "venv\Scripts\Activate.ps1"
    Write-Host "✅ TailSentry test environment activated" -ForegroundColor Green
    Write-Host "Python: $(python --version)"
    Write-Host "Location: $(Get-Command python | Select-Object -ExpandProperty Source)"
    Write-Host ""
    Write-Host "📋 To run TailSentry:"
    Write-Host "  python main.py"
    Write-Host ""
    Write-Host "🧪 To run tests:"
    Write-Host "  .\scripts\test-deployment-windows.ps1"
    Write-Host "  .\scripts\run-all-tests.ps1"
    Write-Host "  python scripts\performance_tester.py"
    Write-Host ""
    Write-Host "🌐 Once started, open: http://localhost:8080"
    Write-Host ""
    Write-Host "To deactivate: deactivate"
}
else {
    Write-Host "❌ Virtual environment not found." -ForegroundColor Red
    Write-Host "Create one with: python -m venv venv"
}
