#!/usr/bin/env python3
"""
Add a test endpoint to debug the 400 error issue
"""

import sys
import os
sys.path.append('/opt/tailsentry')

# Test by adding a simple endpoint to see if the issue is with @login_required
test_route_code = '''
@router.get("/api/test")
async def test_endpoint(request: Request):
    """Simple test endpoint without @login_required"""
    return {"status": "ok", "message": "Test endpoint working"}

@router.get("/api/test-auth")
@login_required
async def test_endpoint_with_auth(request: Request):
    """Test endpoint with @login_required"""
    return {"status": "ok", "message": "Test endpoint with auth working"}
'''

print("🔧 Adding test endpoints to routes/config.py")
print("=" * 40)

# Read the current file
with open('/opt/tailsentry/routes/config.py', 'r') as f:
    content = f.read()

# Add test endpoints at the end, before the last line
if '@router.get("/api/test")' not in content:
    # Insert before the last line
    lines = content.split('\n')
    lines.insert(-1, test_route_code)
    new_content = '\n'.join(lines)
    
    with open('/opt/tailsentry/routes/config.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Test endpoints added to routes/config.py")
    print("📝 Added:")
    print("   - GET /api/test (no auth)")
    print("   - GET /api/test-auth (with auth)")
    
    print("\n🔄 Restart TailSentry to apply changes:")
    print("   sudo systemctl restart tailsentry.service")
    
    print("\n🧪 Then test with:")
    print("   curl http://localhost:8080/api/test")
    print("   # Should work without authentication")
    
else:
    print("⚠️  Test endpoints already exist")

print("\n💡 This will help us determine if the issue is:")
print("   - FastAPI request handling")
print("   - @login_required decorator")
print("   - Middleware interference")
