# TailSentry Version Management
VERSION = "1.0.0"
BUILD_DATE = "2025-08-15"
GIT_COMMIT = "unknown"

def get_version_info():
    """Get comprehensive version information"""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "git_commit": GIT_COMMIT
    }
