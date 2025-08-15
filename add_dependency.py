#!/usr/bin/env python3
"""
Create a FastAPI dependency for authentication instead of a decorator
"""

dependency_code = '''
from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

async def require_auth(request: Request):
    """FastAPI dependency for requiring authentication"""
    session = request.session
    if not session.get("user"):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Session expiry
    if session.get("expires_at"):
        try:
            from datetime import datetime
            expiry = datetime.fromisoformat(session["expires_at"])
            if datetime.utcnow() > expiry:
                request.session.clear()
                raise HTTPException(status_code=401, detail="Session expired")
        except (ValueError, TypeError):
            # Invalid expiry format, clear session
            request.session.clear()
            raise HTTPException(status_code=401, detail="Invalid session")
            
    # Refresh session timeout on activity
    from auth import create_session
    create_session(request, session["user"])
    
    return session["user"]
'''

print("🔧 Creating FastAPI dependency approach")
print("=" * 40)

# Read current routes/config.py
with open('/opt/tailsentry/routes/config.py', 'r') as f:
    content = f.read()

# Add the dependency code at the top after imports
if 'async def require_auth' not in content:
    lines = content.split('\n')
    
    # Find where to insert (after imports, before first route)
    insert_line = 0
    for i, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            insert_line = i + 1
        elif line.startswith('@router.') or line.startswith('class '):
            break
    
    # Insert dependency code
    lines.insert(insert_line, '')
    lines.insert(insert_line + 1, dependency_code)
    lines.insert(insert_line + 2, '')
    
    new_content = '\n'.join(lines)
    
    with open('/opt/tailsentry/routes/config.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Added FastAPI dependency function")
else:
    print("⚠️  Dependency already exists")

print("\n📝 Next: Replace @login_required with Depends(require_auth)")
print("   This is more compatible with FastAPI")

replacement_code = '''
# Example of how to use the dependency:
# Instead of:
#   @login_required
#   async def get_config(request: Request):
# 
# Use:
#   async def get_config(request: Request, user: str = Depends(require_auth)):
'''

print(replacement_code)
