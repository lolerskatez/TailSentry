# 🔒 TailSentry Discord Bot Security Hardening

## 🚨 Critical Security Issues & Fixes

### 1. Log Data Filtering (HIGH PRIORITY)

**Problem**: Bot can expose sensitive data in logs (tokens, IPs, passwords)

**Solution**: Implement log sanitization before sending to Discord

```python
import re

class LogSanitizer:
    """Sanitize logs before sending to Discord"""
    
    def __init__(self):
        self.patterns = [
            # Tokens and API Keys
            (r'[A-Za-z0-9]{24}\.[A-Za-z0-9]{6}\.[A-Za-z0-9_-]{27}', '[DISCORD_TOKEN]'),
            (r'sk-[A-Za-z0-9]{48}', '[OPENAI_TOKEN]'),
            (r'xoxb-[A-Za-z0-9-]{50,}', '[SLACK_TOKEN]'),
            (r'ghp_[A-Za-z0-9]{36}', '[GITHUB_TOKEN]'),
            (r'Bearer [A-Za-z0-9_-]+', 'Bearer [REDACTED]'),
            
            # IP Addresses (optional - may be needed for debugging)
            # (r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '[IP_ADDRESS]'),
            
            # Passwords and secrets
            (r'password["\s]*[:=]["\s]*[^"\s,}]+', 'password="[REDACTED]"'),
            (r'secret["\s]*[:=]["\s]*[^"\s,}]+', 'secret="[REDACTED]"'),
            (r'token["\s]*[:=]["\s]*[^"\s,}]+', 'token="[REDACTED]"'),
            
            # Email addresses (optional)
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
            
            # Common sensitive environment variables
            (r'TAILSCALE_[A-Z_]*=[^\s]+', 'TAILSCALE_[REDACTED]'),
            (r'DISCORD_[A-Z_]*=[^\s]+', 'DISCORD_[REDACTED]'),
            (r'API_[A-Z_]*=[^\s]+', 'API_[REDACTED]'),
        ]
    
    def sanitize(self, log_content: str) -> str:
        """Remove sensitive data from log content"""
        sanitized = log_content
        
        for pattern, replacement in self.patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized

# Usage in discord_bot.py
async def _get_logs(self, lines: int = 50, level: Optional[str] = None) -> str:
    """Get recent logs from the log file"""
    try:
        # ... existing log reading code ...
        
        # Sanitize logs before returning
        sanitizer = LogSanitizer()
        sanitized_logs = sanitizer.sanitize(raw_logs)
        
        return sanitized_logs
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return f"Error reading logs: {str(e)}"
```

### 2. Enhanced Access Control

**Problem**: Username-based auth is insecure, no rate limiting

**Solution**: Implement robust access control

```python
import time
from collections import defaultdict

class DiscordAccessControl:
    """Enhanced access control for Discord bot"""
    
    def __init__(self, allowed_user_ids: List[str], rate_limit_per_minute: int = 10):
        self.allowed_user_ids = set(allowed_user_ids)
        self.rate_limit_per_minute = rate_limit_per_minute
        self.user_requests = defaultdict(list)
        self.failed_attempts = defaultdict(int)
        
    def is_user_allowed(self, user_id: str) -> bool:
        """Check if user is allowed (ID only, no usernames)"""
        return not self.allowed_user_ids or user_id in self.allowed_user_ids
    
    def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id] 
            if req_time > minute_ago
        ]
        
        # Check rate limit
        if len(self.user_requests[user_id]) >= self.rate_limit_per_minute:
            return False
        
        # Record this request
        self.user_requests[user_id].append(now)
        return True
    
    def record_failed_attempt(self, user_id: str):
        """Record failed authentication attempt"""
        self.failed_attempts[user_id] += 1
        logger.warning(f"Failed bot access attempt from user {user_id} (total: {self.failed_attempts[user_id]})")
    
    def is_user_blocked(self, user_id: str) -> bool:
        """Check if user is temporarily blocked due to failed attempts"""
        return self.failed_attempts[user_id] >= 5

# Usage in command handlers
access_control = DiscordAccessControl(allowed_user_ids=self.allowed_users)

async def logs_slash(interaction: discord.Interaction, lines: int = 50, level: Optional[str] = None):
    user_id = str(interaction.user.id)
    
    # Check if user is blocked
    if access_control.is_user_blocked(user_id):
        await interaction.response.send_message("❌ Access temporarily blocked due to repeated unauthorized attempts.", ephemeral=True)
        return
    
    # Check permissions
    if not access_control.is_user_allowed(user_id):
        access_control.record_failed_attempt(user_id)
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    # Check rate limit
    if not access_control.check_rate_limit(user_id):
        await interaction.response.send_message("❌ Rate limit exceeded. Please wait before using commands again.", ephemeral=True)
        return
    
    # Log access attempt
    logger.info(f"Discord bot command '/logs' used by {interaction.user} (ID: {user_id})")
    
    # ... rest of command logic ...
```

### 3. Audit Logging

**Problem**: No tracking of bot usage

**Solution**: Comprehensive audit logging

```python
import json
from datetime import datetime

class BotAuditLogger:
    """Audit logging for Discord bot usage"""
    
    def __init__(self, audit_log_path: str = "logs/discord_bot_audit.log"):
        self.audit_log_path = audit_log_path
        
    def log_command_usage(self, command: str, user_id: str, username: str, 
                         guild_id: str, channel_id: str, success: bool, 
                         error: str = None):
        """Log bot command usage"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "command": command,
            "user_id": user_id,
            "username": username,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "success": success,
            "error": error,
            "ip_hash": self._hash_user_ip(user_id)  # For tracking without storing IPs
        }
        
        with open(self.audit_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(audit_entry) + '\n')
    
    def _hash_user_ip(self, user_id: str) -> str:
        """Create a hash of user info for tracking without storing sensitive data"""
        import hashlib
        return hashlib.sha256(f"user_{user_id}_{datetime.utcnow().date()}".encode()).hexdigest()[:16]

# Usage in commands
audit_logger = BotAuditLogger()

async def logs_slash(interaction: discord.Interaction, lines: int = 50, level: Optional[str] = None):
    try:
        # ... permission checks ...
        
        # Get logs
        logs = await self._get_logs(lines, level)
        
        # Send response
        await interaction.response.send_message(f"📄 Logs:\n```\n{logs}\n```")
        
        # Log successful usage
        audit_logger.log_command_usage(
            command="logs",
            user_id=str(interaction.user.id),
            username=str(interaction.user),
            guild_id=str(interaction.guild_id),
            channel_id=str(interaction.channel_id),
            success=True
        )
        
    except Exception as e:
        # Log failed usage
        audit_logger.log_command_usage(
            command="logs",
            user_id=str(interaction.user.id),
            username=str(interaction.user),
            guild_id=str(interaction.guild_id),
            channel_id=str(interaction.channel_id),
            success=False,
            error=str(e)
        )
        
        await interaction.response.send_message("❌ Command failed.", ephemeral=True)
```

### 4. Environment Security

**Problem**: Bot token stored in plain text

**Solution**: Enhanced environment security

```bash
# Set proper file permissions for .env
chmod 600 .env
chown tailsentry:tailsentry .env

# Use systemd service with limited permissions
[Unit]
Description=TailSentry Discord Bot
After=network.target

[Service]
Type=simple
User=tailsentry
Group=tailsentry
WorkingDirectory=/opt/tailsentry
Environment=PYTHONPATH=/opt/tailsentry
EnvironmentFile=/opt/tailsentry/.env
ExecStart=/opt/tailsentry/venv/bin/python main.py
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/tailsentry/logs /opt/tailsentry/data

[Install]
WantedBy=multi-user.target
```

### 5. Network Security

**Problem**: Bot has unnecessary network access

**Solution**: Implement network restrictions

```python
# In discord_bot.py - limit outbound connections
import socket
import ssl

class SecureDiscordBot(TailSentryDiscordBot):
    """Security-hardened Discord bot"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configure secure SSL context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        # Allowed Discord endpoints only
        self.allowed_hosts = [
            'discord.com',
            'discordapp.com',
            'gateway.discord.gg'
        ]
```

## 🚨 Security Checklist

### Before Deployment:
- [ ] Regenerate bot token (if exposed)
- [ ] Implement log sanitization
- [ ] Enable User ID-only access control
- [ ] Set up audit logging
- [ ] Configure rate limiting
- [ ] Set proper file permissions (chmod 600 .env)
- [ ] Use dedicated service user
- [ ] Restrict network access

### Ongoing Security:
- [ ] Regular bot token rotation (quarterly)
- [ ] Monitor audit logs for suspicious activity
- [ ] Review user access list monthly
- [ ] Update Discord bot permissions as needed
- [ ] Monitor for failed authentication attempts
- [ ] Keep discord.py library updated

### In Case of Compromise:
1. **Immediately** regenerate bot token
2. Remove bot from all Discord servers
3. Review audit logs for unauthorized access
4. Change all related passwords/tokens
5. Check logs for data exfiltration
6. Notify users if sensitive data was exposed

## 📊 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|---------|------------|
| Token exposure | Medium | High | Token rotation, env security |
| Log data leakage | High | Medium | Log sanitization |
| Unauthorized access | Medium | Medium | Strong access control |
| Rate limit abuse | Low | Low | Rate limiting |
| Server compromise | Low | High | Network restrictions |

## 🎯 Security Maturity Levels

**Current Level: 2/5 (Basic)**
- ✅ Basic access control
- ✅ Minimal permissions
- ❌ No log filtering
- ❌ No audit logging
- ❌ No rate limiting

**Target Level: 4/5 (Secure)**
- ✅ All current features
- ✅ Log sanitization
- ✅ Comprehensive audit logging
- ✅ Rate limiting & blocking
- ✅ Enhanced access control
- ✅ Environment hardening

---

*Security is a process, not a destination. Regular reviews and updates are essential.*
