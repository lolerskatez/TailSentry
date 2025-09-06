# Package Update Script
# IMPORTANT: Test in development environment first!

Write-Host "🔄 Updating critical security packages..." -ForegroundColor Yellow

# Update Discord.py first (most critical for bot)
Write-Host "`n📦 Updating Discord.py..." -ForegroundColor Cyan
pip install --upgrade discord.py==2.6.3

# Update cryptography (security library)
Write-Host "`n🔐 Updating cryptography..." -ForegroundColor Cyan  
pip install --upgrade cryptography==45.0.7

# Update web framework
Write-Host "`n🌐 Updating FastAPI..." -ForegroundColor Cyan
pip install --upgrade fastapi==0.116.1

# Update other security-related packages
Write-Host "`n🔧 Updating other security packages..." -ForegroundColor Cyan
pip install --upgrade certifi requests urllib3

# Check for breaking changes
Write-Host "`n⚠️  IMPORTANT: Test all functionality after updates!" -ForegroundColor Red
Write-Host "   - Test Discord bot commands" -ForegroundColor White
Write-Host "   - Test web dashboard" -ForegroundColor White  
Write-Host "   - Check for deprecation warnings" -ForegroundColor White

# Regenerate requirements file
Write-Host "`n📝 Regenerating requirements-frozen.txt..." -ForegroundColor Cyan
pip freeze > requirements-frozen.txt

Write-Host "`n✅ Package updates complete!" -ForegroundColor Green
