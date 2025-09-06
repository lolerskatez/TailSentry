"""
Enhanced access control for TailSentry Discord bot
Provides rate limiting, user validation, and audit logging
"""

import time
import json
import logging
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger("tailsentry.discord_access_control")

class DiscordAccessControl:
    """Enhanced access control for Discord bot with rate limiting and audit logging"""
    
    def __init__(self, allowed_user_ids: Optional[List[str]] = None, 
                 rate_limit_per_minute: int = 10,
                 max_failed_attempts: int = 5,
                 audit_log_path: str = "logs/discord_bot_audit.log"):
        """
        Initialize access control
        
        Args:
            allowed_user_ids: List of Discord user IDs allowed to use bot (None = allow all)
            rate_limit_per_minute: Maximum commands per minute per user
            max_failed_attempts: Max failed attempts before temporary block
            audit_log_path: Path to audit log file
        """
        # Only use user IDs, no usernames for security
        self.allowed_user_ids = set(allowed_user_ids or [])
        self.rate_limit_per_minute = rate_limit_per_minute
        self.max_failed_attempts = max_failed_attempts
        self.audit_log_path = Path(audit_log_path)
        
        # Rate limiting tracking
        self.user_requests = defaultdict(list)
        self.failed_attempts = defaultdict(int)
        self.blocked_until = defaultdict(float)
        
        # Ensure audit log directory exists
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Discord access control initialized: {len(self.allowed_user_ids)} allowed users, {rate_limit_per_minute}/min rate limit")
    
    def is_user_allowed(self, user_id: str) -> bool:
        """Check if user ID is in allowed list"""
        # If no restrictions set, allow all users
        if not self.allowed_user_ids:
            return True
        
        return user_id in self.allowed_user_ids
    
    def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests (older than 1 minute)
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id] 
            if req_time > minute_ago
        ]
        
        # Check if rate limit exceeded
        if len(self.user_requests[user_id]) >= self.rate_limit_per_minute:
            logger.warning(f"Rate limit exceeded for user {user_id}: {len(self.user_requests[user_id])}/{self.rate_limit_per_minute}")
            return False
        
        # Record this request
        self.user_requests[user_id].append(now)
        return True
    
    def is_user_blocked(self, user_id: str) -> bool:
        """Check if user is temporarily blocked due to failed attempts"""
        # Check if block has expired (blocks last 1 hour)
        if user_id in self.blocked_until:
            if time.time() < self.blocked_until[user_id]:
                return True
            else:
                # Block expired, remove it
                del self.blocked_until[user_id]
                self.failed_attempts[user_id] = 0
        
        return False
    
    def record_failed_attempt(self, user_id: str, reason: str = "unauthorized"):
        """Record failed authentication attempt"""
        self.failed_attempts[user_id] += 1
        
        logger.warning(f"Failed bot access attempt from user {user_id}: {reason} (total: {self.failed_attempts[user_id]})")
        
        # Block user if too many failed attempts
        if self.failed_attempts[user_id] >= self.max_failed_attempts:
            # Block for 1 hour
            self.blocked_until[user_id] = time.time() + 3600
            logger.warning(f"User {user_id} temporarily blocked for 1 hour due to {self.failed_attempts[user_id]} failed attempts")
        
        # Log to audit
        self._log_audit_event("failed_access", user_id, "unknown", success=False, error=reason)
    
    def record_successful_access(self, user_id: str, username: str, command: str, guild_id: Optional[str] = None, channel_id: Optional[str] = None):
        """Record successful command usage"""
        # Reset failed attempts on successful access
        if user_id in self.failed_attempts:
            self.failed_attempts[user_id] = 0
        
        logger.info(f"Discord bot command '{command}' used by {username} (ID: {user_id})")
        
        # Log to audit
        self._log_audit_event(command, user_id, username, guild_id=guild_id, channel_id=channel_id, success=True)
    
    def _log_audit_event(self, command: str, user_id: str, username: str, 
                        guild_id: Optional[str] = None, channel_id: Optional[str] = None, 
                        success: bool = True, error: Optional[str] = None, 
                        risk_level: str = "low", interaction=None):
        """Enhanced audit logging with comprehensive event details"""
        try:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "command": command,
                "user_id": user_id,
                "username": username,  # For readability, but don't use for auth
                "guild_id": guild_id,
                "channel_id": channel_id,
                "success": success,
                "error": error,
                "risk_level": risk_level,
                "user_hash": self._hash_user_info(user_id),
                "source": "discord_bot",
                "session_id": f"discord_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            }
            
            # Add interaction context if available
            if interaction:
                audit_entry.update({
                    "command_name": interaction.command.name if interaction.command else None,
                    "user_roles": [role.name for role in interaction.user.roles] if hasattr(interaction.user, 'roles') else [],
                    "interaction_type": type(interaction).__name__
                })
            
            # Store for in-memory analysis
            self._store_audit_event(audit_entry)
            
            # Write to file
            with open(self.audit_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_entry) + '\n')
            
            # Log with appropriate level based on risk and success
            if not success or risk_level in ['high', 'critical']:
                logger.warning(f"AUDIT_ALERT: {json.dumps(audit_entry)}")
            else:
                logger.info(f"AUDIT: {json.dumps(audit_entry)}")
                
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def _store_audit_event(self, event: dict):
        """Store audit event for later analysis"""
        if not hasattr(self, 'recent_events'):
            self.recent_events = []
        
        self.recent_events.append(event)
        
        # Keep only last 1000 events in memory
        if len(self.recent_events) > 1000:
            self.recent_events = self.recent_events[-1000:]
    
    def get_user_activity_summary(self, user_id: str, hours: int = 24) -> dict:
        """Get summary of user activity for security analysis"""
        if not hasattr(self, 'recent_events'):
            return {'error': 'No audit data available'}
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        user_events = [
            event for event in self.recent_events 
            if event['user_id'] == user_id and 
            datetime.fromisoformat(event['timestamp']) > cutoff_time
        ]
        
        return {
            'user_id': user_id,
            'period_hours': hours,
            'total_commands': len(user_events),
            'failed_commands': sum(1 for e in user_events if not e['success']),
            'high_risk_actions': sum(1 for e in user_events if e['risk_level'] in ['high', 'critical']),
            'unique_commands': list(set(e.get('command_name', 'unknown') for e in user_events)),
            'last_activity': max((e['timestamp'] for e in user_events), default=None)
        }
    
    def detect_suspicious_activity(self, user_id: Optional[str] = None) -> List[dict]:
        """Detect potentially suspicious activity patterns"""
        if not hasattr(self, 'recent_events'):
            return []
        
        alerts = []
        recent_time = datetime.utcnow() - timedelta(hours=1)
        
        # Filter events
        events = self.recent_events
        if user_id:
            events = [e for e in events if e['user_id'] == user_id]
        
        # Check for rapid-fire commands (potential bot)
        for uid in set(e['user_id'] for e in events):
            user_events = [e for e in events if e['user_id'] == uid 
                          and datetime.fromisoformat(e['timestamp']) > recent_time]
            
            if len(user_events) > 20:  # More than 20 commands in an hour
                alerts.append({
                    'type': 'rapid_commands',
                    'user_id': uid,
                    'command_count': len(user_events),
                    'severity': 'medium'
                })
        
        # Check for high failure rates
        for uid in set(e['user_id'] for e in events):
            user_events = [e for e in events if e['user_id'] == uid]
            failed = sum(1 for e in user_events if not e['success'])
            
            if len(user_events) > 5 and failed / len(user_events) > 0.5:
                alerts.append({
                    'type': 'high_failure_rate',
                    'user_id': uid,
                    'failure_rate': f"{failed}/{len(user_events)}",
                    'severity': 'high'
                })
        
        return alerts
    
    def _hash_user_info(self, user_id: str) -> str:
        """Create a privacy-preserving hash of user info for analytics"""
        # Combine user ID with current date for daily unique tracking
        daily_salt = datetime.utcnow().strftime("%Y-%m-%d")
        combined = f"user_{user_id}_{daily_salt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get usage statistics for a user"""
        return {
            "failed_attempts": self.failed_attempts.get(user_id, 0),
            "is_blocked": self.is_user_blocked(user_id),
            "recent_requests": len(self.user_requests.get(user_id, [])),
            "rate_limit": self.rate_limit_per_minute
        }
    
    def cleanup_old_data(self):
        """Clean up old tracking data to prevent memory leaks"""
        now = time.time()
        hour_ago = now - 3600
        
        # Clean old rate limit data
        for user_id in list(self.user_requests.keys()):
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id] 
                if req_time > hour_ago
            ]
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
        
        # Clean expired blocks
        for user_id in list(self.blocked_until.keys()):
            if now >= self.blocked_until[user_id]:
                del self.blocked_until[user_id]
                if user_id in self.failed_attempts:
                    del self.failed_attempts[user_id]
