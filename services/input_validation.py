"""
Input validation utilities for TailSentry Discord bot
Provides comprehensive validation for user inputs and commands
"""

import re
import logging
from typing import Optional, Union, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger("tailsentry.input_validation")

class InputValidator:
    """Comprehensive input validation for Discord bot commands"""
    
    def __init__(self):
        # Regex patterns for common validations
        self.patterns = {
            'safe_string': re.compile(r'^[a-zA-Z0-9\s\-_.,:;!?()]+$'),
            'log_level': re.compile(r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$', re.IGNORECASE),
            'ip_address': re.compile(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'),
            'hostname': re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]?$'),
            'tailscale_node': re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,63}$'),
            'file_path': re.compile(r'^[a-zA-Z0-9\s\-_./\\:]+$'),
            'discord_user_id': re.compile(r'^\d{17,20}$'),
            'discord_channel_id': re.compile(r'^\d{17,20}$')
        }
        
        # Maximum lengths for different input types
        self.max_lengths = {
            'command_arg': 100,
            'log_search': 500,
            'filename': 255,
            'hostname': 63,
            'user_input': 1000
        }
        
        # Dangerous patterns to reject
        self.dangerous_patterns = [
            re.compile(r'[<>"\'\\\x00-\x1f\x7f-\x9f]'),  # Control chars, quotes, brackets
            re.compile(r'\.\./'),  # Path traversal
            re.compile(r'[;&|`$]'),  # Shell injection chars
            re.compile(r'javascript:', re.IGNORECASE),  # Script injection
            re.compile(r'<script', re.IGNORECASE),  # HTML injection
            re.compile(r'union\s+select', re.IGNORECASE),  # SQL injection
            re.compile(r'drop\s+table', re.IGNORECASE)  # SQL injection
        ]
    
    def validate_safe_string(self, text: str, max_length: int = 1000) -> tuple[bool, str]:
        """Validate that string is safe for general use"""
        if not isinstance(text, str):
            return False, "Input must be a string"
        
        if len(text) == 0:
            return False, "Input cannot be empty"
        
        if len(text) > max_length:
            return False, f"Input too long (max {max_length} characters)"
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if pattern.search(text):
                return False, "Input contains potentially dangerous characters"
        
        return True, ""
    
    def validate_log_level(self, level: str) -> tuple[bool, str]:
        """Validate log level parameter"""
        if not self.patterns['log_level'].match(level):
            return False, "Invalid log level. Use: DEBUG, INFO, WARNING, ERROR, or CRITICAL"
        return True, ""
    
    def validate_hostname(self, hostname: str) -> tuple[bool, str]:
        """Validate hostname or node name"""
        is_valid, error = self.validate_safe_string(hostname, self.max_lengths['hostname'])
        if not is_valid:
            return False, error
        
        if not self.patterns['hostname'].match(hostname):
            return False, "Invalid hostname format"
        
        return True, ""
    
    def validate_file_path(self, path: str) -> tuple[bool, str]:
        """Validate file path (with extra security checks)"""
        is_valid, error = self.validate_safe_string(path, self.max_lengths['filename'])
        if not is_valid:
            return False, error
        
        # Additional path security checks
        if '..' in path:
            return False, "Path traversal not allowed"
        
        if path.startswith('/') or ':' in path[:3]:  # Unix absolute or Windows drive
            return False, "Absolute paths not allowed"
        
        return True, ""
    
    def validate_discord_id(self, user_id: Union[str, int], id_type: str = "user") -> tuple[bool, str]:
        """Validate Discord user/channel/guild ID"""
        user_id_str = str(user_id)
        
        pattern_key = f'discord_{id_type}_id'
        if pattern_key not in self.patterns:
            pattern_key = 'discord_user_id'  # Default to user ID pattern
        
        if not self.patterns[pattern_key].match(user_id_str):
            return False, f"Invalid Discord {id_type} ID format"
        
        return True, ""
    
    def validate_number_range(self, value: Union[str, int], min_val: int, max_val: int) -> tuple[bool, str]:
        """Validate number is within acceptable range"""
        try:
            num = int(value)
            if num < min_val or num > max_val:
                return False, f"Number must be between {min_val} and {max_val}"
            return True, ""
        except (ValueError, TypeError):
            return False, "Invalid number format"
    
    def validate_time_range(self, time_str: str) -> tuple[bool, str]:
        """Validate time range for log queries (e.g., '1h', '30m', '2d')"""
        pattern = re.compile(r'^(\d+)([hmd])$')
        match = pattern.match(time_str.lower())
        
        if not match:
            return False, "Invalid time format. Use format like '1h', '30m', or '2d'"
        
        value, unit = match.groups()
        value = int(value)
        
        # Set reasonable limits
        limits = {'m': 1440, 'h': 168, 'd': 7}  # 1 day in minutes, 1 week in hours, 1 week in days
        
        if value > limits[unit]:
            return False, f"Time range too large. Maximum: {limits[unit]}{unit}"
        
        return True, ""
    
    def sanitize_for_logging(self, text: str) -> str:
        """Sanitize text for safe logging (remove/escape problematic chars)"""
        # Remove control characters and non-printable chars
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Escape remaining problematic characters
        sanitized = sanitized.replace('\\', '\\\\').replace('"', '\\"')
        
        # Truncate if too long
        if len(sanitized) > 500:
            sanitized = sanitized[:497] + "..."
        
        return sanitized

# Validation decorators for bot commands
def validate_input(validation_func, *validation_args):
    """Decorator to validate bot command inputs"""
    def decorator(func):
        async def wrapper(interaction, *args, **kwargs):
            # Find the first string argument to validate
            for arg in args:
                if isinstance(arg, str):
                    is_valid, error_msg = validation_func(arg, *validation_args)
                    if not is_valid:
                        await interaction.response.send_message(
                            f"❌ Invalid input: {error_msg}", 
                            ephemeral=True
                        )
                        logger.warning(f"Input validation failed: {error_msg} (user: {interaction.user.id})")
                        return
                    break
            
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

# Example usage in discord_bot.py:
"""
from .input_validation import InputValidator, validate_input

validator = InputValidator()

@tree.command(name="logs", description="Get recent TailSentry logs")
@validate_input(validator.validate_safe_string, 500)
async def logs_command(interaction: discord.Interaction, filter_text: str = ""):
    # Command implementation here
    pass

@tree.command(name="status", description="Check TailSentry status")
@validate_input(validator.validate_hostname)
async def status_command(interaction: discord.Interaction, node_name: str = ""):
    # Command implementation here
    pass
"""
