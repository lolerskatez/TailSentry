"""
Log sanitization utilities for TailSentry Discord bot
Removes sensitive data from logs before sending to Discord
"""

import re
import logging

logger = logging.getLogger("tailsentry.log_sanitizer")

class LogSanitizer:
    """Sanitize logs before sending to Discord to prevent data leakage"""
    
    def __init__(self):
        self.patterns = [
            # Discord Bot Tokens
            (r'[A-Za-z0-9]{24}\.[A-Za-z0-9]{6}\.[A-Za-z0-9_-]{27}', '[DISCORD_TOKEN]'),
            
            # API Keys and Tokens
            (r'sk-[A-Za-z0-9]{48}', '[OPENAI_TOKEN]'),
            (r'xoxb-[A-Za-z0-9-]{50,}', '[SLACK_TOKEN]'),
            (r'ghp_[A-Za-z0-9]{36}', '[GITHUB_TOKEN]'),
            (r'Bearer [A-Za-z0-9_.-]+', 'Bearer [REDACTED]'),
            (r'token["\s]*[:=]["\s]*[^"\s,}]+', 'token="[REDACTED]"'),
            
            # Tailscale specific
            (r'tskey-[A-Za-z0-9]{32}', '[TAILSCALE_KEY]'),
            (r'ts-[A-Za-z0-9]{40,}', '[TAILSCALE_TOKEN]'),
            
            # Generic secrets
            (r'password["\s]*[:=]["\s]*[^"\s,}]+', 'password="[REDACTED]"'),
            (r'secret["\s]*[:=]["\s]*[^"\s,}]+', 'secret="[REDACTED]"'),
            (r'key["\s]*[:=]["\s]*[^"\s,}]+', 'key="[REDACTED]"'),
            
            # Environment variables with sensitive data
            (r'TAILSCALE_[A-Z_]*=[^\s]+', 'TAILSCALE_[VAR]=[REDACTED]'),
            (r'DISCORD_[A-Z_]*TOKEN=[^\s]+', 'DISCORD_[VAR]=[REDACTED]'),
            (r'API_[A-Z_]*=[^\s]+', 'API_[VAR]=[REDACTED]'),
            (r'SECRET_[A-Z_]*=[^\s]+', 'SECRET_[VAR]=[REDACTED]'),
            
            # Email addresses (optional - remove if you need emails for debugging)
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
            
            # IP addresses (be careful - these might be needed for network debugging)
            # Uncomment if you want to hide IPs:
            # (r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '[IP_ADDRESS]'),
            
            # URLs with tokens/keys
            (r'https?://[^\s]*[?&](?:token|key|secret|auth)=[A-Za-z0-9_.-]+', 'https://[REDACTED_URL]'),
            
            # File paths that might contain sensitive info
            (r'/home/[^/\s]+/\.ssh/[^\s]+', '[SSH_PATH]'),
            (r'/root/[^\s]+', '[ROOT_PATH]'),
        ]
    
    def sanitize(self, log_content: str) -> str:
        """Remove sensitive data from log content"""
        if not log_content:
            return log_content
            
        sanitized = log_content
        
        try:
            for pattern, replacement in self.patterns:
                sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        except Exception as e:
            logger.warning(f"Error sanitizing logs: {e}")
            # Return a safe fallback if sanitization fails
            return "[LOG_SANITIZATION_ERROR - Content hidden for security]"
        
        return sanitized
    
    def sanitize_for_audit(self, log_content: str) -> str:
        """More aggressive sanitization for audit logs"""
        sanitized = self.sanitize(log_content)
        
        # Additional patterns for audit logs
        audit_patterns = [
            # Hide all file paths
            (r'/[a-zA-Z0-9_./\-]+', '[FILE_PATH]'),
            # Hide process IDs
            (r'process \[?\d+\]?', 'process [PID]'),
            # Hide session IDs
            (r'session["\s]*[:=]["\s]*[A-Za-z0-9-]+', 'session="[SESSION_ID]"'),
        ]
        
        for pattern, replacement in audit_patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
