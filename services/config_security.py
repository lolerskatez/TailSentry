"""
Configuration security manager for TailSentry
Handles secure loading and validation of configuration files
"""

import json
import os
import stat
import logging
import platform
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("tailsentry.config_security")

class SecureConfigManager:
    """Cross-platform secure configuration file manager"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.is_windows = platform.system() == "Windows"
        
        # Set secure permissions based on OS
        if self.is_windows:
            # Windows: Remove inheritance, grant full control to owner only
            self.required_permissions = None  # Will use Windows ACLs
        else:
            # Unix/Linux: Owner read/write only
            self.required_permissions = 0o600
    
    def validate_file_permissions(self, file_path: Path) -> bool:
        """Check if config file has secure permissions (cross-platform)"""
        try:
            if self.is_windows:
                return self._check_windows_permissions(file_path)
            else:
                return self._check_unix_permissions(file_path)
        except OSError as e:
            logger.error(f"Cannot check permissions for {file_path}: {e}")
            return False
    
    def _check_unix_permissions(self, file_path: Path) -> bool:
        """Check Unix/Linux file permissions"""
        if self.required_permissions is None:
            return True  # Windows fallback
            
        file_stat = file_path.stat()
        current_perms = file_stat.st_mode & 0o777
        
        if current_perms != self.required_permissions:
            logger.warning(
                f"Insecure permissions on {file_path}: {oct(current_perms)} "
                f"(should be {oct(self.required_permissions)})"
            )
            return False
        return True
    
    def _check_windows_permissions(self, file_path: Path) -> bool:
        """Check Windows file permissions (basic check)"""
        # Basic Windows check - ensure file is not world-readable
        file_stat = file_path.stat()
        
        # Check if file is readable by others (basic heuristic)
        # On Windows, this is a simplified check
        if file_stat.st_mode & stat.S_IROTH:
            logger.warning(f"File {file_path} may be readable by others")
            return False
        
        return True
    
    def secure_file_permissions(self, file_path: Path) -> bool:
        """Set secure permissions on config file (cross-platform)"""
        try:
            if self.is_windows:
                return self._secure_windows_permissions(file_path)
            else:
                return self._secure_unix_permissions(file_path)
        except OSError as e:
            logger.error(f"Cannot set permissions on {file_path}: {e}")
            return False
    
    def _secure_unix_permissions(self, file_path: Path) -> bool:
        """Set secure Unix/Linux permissions"""
        if self.required_permissions is None:
            logger.warning("No Unix permissions set for Windows system")
            return False
            
        file_path.chmod(self.required_permissions)
        logger.info(f"Set secure permissions on {file_path}")
        return True
    
    def _secure_windows_permissions(self, file_path: Path) -> bool:
        """Set secure Windows permissions"""
        try:
            import subprocess
            # Use icacls to set Windows permissions
            # Remove inheritance and grant full control to current user only
            current_user = os.environ.get('USERNAME', 'user')
            
            commands = [
                ['icacls', str(file_path), '/inheritance:r'],
                ['icacls', str(file_path), f'/grant:r', f'{current_user}:F']
            ]
            
            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to set Windows permissions: {result.stderr}")
                    return False
            
            logger.info(f"Set secure Windows permissions on {file_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Could not set Windows permissions: {e}")
            # Fallback to basic chmod
            file_path.chmod(0o600)
            return True
    
    def load_config(self, filename: str, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """Securely load and validate configuration file"""
        file_path = self.config_dir / filename
        
        # Check file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Validate permissions
        if not self.validate_file_permissions(file_path):
            logger.warning(f"Config file {file_path} has insecure permissions")
            # Optionally fix permissions automatically
            # self.secure_file_permissions(file_path)
        
        # Load and validate JSON
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Schema validation if provided
            if schema:
                self.validate_config_schema(config, schema, filename)
            
            logger.info(f"Successfully loaded config: {filename}")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filename}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            raise
    
    def validate_config_schema(self, config: Dict, schema: Dict, filename: str):
        """Validate configuration against expected schema"""
        for key, expected_type in schema.items():
            if key not in config:
                logger.warning(f"Missing required config key '{key}' in {filename}")
                continue
                
            if not isinstance(config[key], expected_type):
                logger.warning(
                    f"Invalid type for '{key}' in {filename}: "
                    f"expected {expected_type.__name__}, got {type(config[key]).__name__}"
                )
    
    def mask_sensitive_values(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a copy of config with sensitive values masked for logging"""
        sensitive_keys = {
            'token', 'password', 'secret', 'key', 'api_key', 
            'discord_token', 'webhook_url', 'auth_key'
        }
        
        masked_config = {}
        for key, value in config.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 8:
                    masked_config[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    masked_config[key] = "[MASKED]"
            else:
                masked_config[key] = value
        
        return masked_config

# Configuration schemas for validation
DISCORD_CONFIG_SCHEMA = {
    'token': str,
    'channel_id': (str, int),
    'guild_id': (str, int),
    'log_level': str,
    'max_message_length': int,
    'rate_limit_per_minute': int
}

TAILSENTRY_CONFIG_SCHEMA = {
    'debug': bool,
    'host': str,
    'port': int,
    'secret_key': str,
    'database_path': str,
    'log_level': str
}

# Example usage:
"""
config_manager = SecureConfigManager()

# Load Discord bot config with validation
discord_config = config_manager.load_config('discord_config.json', DISCORD_CONFIG_SCHEMA)

# Log config (with sensitive values masked)
masked_config = config_manager.mask_sensitive_values(discord_config)
logger.info(f"Discord config loaded: {masked_config}")
"""
