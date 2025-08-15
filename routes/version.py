from fastapi import APIRouter
import subprocess
import os
from typing import Dict, Any
from version import get_version_info

router = APIRouter()

@router.get("/api/version")
async def get_version():
    """Get current version information"""
    version_info: Dict[str, Any] = get_version_info()
    
    # Try to get git info if available
    try:
        if os.path.exists('.git'):
            git_commit = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'], 
                stderr=subprocess.DEVNULL
            ).decode().strip()
            version_info['git_commit'] = git_commit
            
            # Check if there are uncommitted changes
            try:
                subprocess.check_output(
                    ['git', 'diff-index', '--quiet', 'HEAD', '--'],
                    stderr=subprocess.DEVNULL
                )
                version_info['git_dirty'] = False
            except subprocess.CalledProcessError:
                version_info['git_dirty'] = True
    except:
        pass
    
    return {"version_info": version_info}

@router.get("/api/update/check")
async def check_for_updates():
    """Check if updates are available (placeholder)"""
    # This would integrate with your CI/CD or release system
    return {
        "updates_available": False,
        "latest_version": "1.0.0",
        "current_version": get_version_info()["version"],
        "release_notes_url": "https://github.com/lolerskatez/TailSentry/releases"
    }
