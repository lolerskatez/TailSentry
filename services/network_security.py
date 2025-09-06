"""
Cross-platform network security configuration for TailSentry Discord bot
Restricts outbound connections to Discord endpoints only
"""

import socket
import ssl
import logging
import platform
import subprocess
from typing import List

logger = logging.getLogger("tailsentry.network_security")

class SecureNetworkConfig:
    """Cross-platform network security configuration for Discord bot"""
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        
        # Allowed Discord endpoints
        self.allowed_hosts = [
            'discord.com',
            'discordapp.com', 
            'gateway.discord.gg',
            'cdn.discordapp.com',
            'media.discordapp.net'
        ]
        
        # Blocked ports (everything except HTTPS)
        self.blocked_ports = list(range(1, 443)) + list(range(444, 65536))
        self.allowed_ports = [443, 80]  # HTTPS and HTTP for Discord
        
    def is_connection_allowed(self, host: str, port: int) -> bool:
        """Check if connection to host:port is allowed"""
        
        # Check if host is in allowed list
        host_allowed = any(
            host.endswith(allowed_host) or host == allowed_host 
            for allowed_host in self.allowed_hosts
        )
        
        # Check if port is allowed
        port_allowed = port in self.allowed_ports
        
        if not host_allowed:
            logger.warning(f"Blocked connection to unauthorized host: {host}")
            return False
            
        if not port_allowed:
            logger.warning(f"Blocked connection to unauthorized port: {port}")
            return False
            
        return True
    
    def create_secure_ssl_context(self) -> ssl.SSLContext:
        """Create a secure SSL context with proper verification"""
        context = ssl.create_default_context()
        
        # Enforce strong security settings
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # Disable weak ciphers
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        return context
    
    def setup_firewall_rules(self) -> bool:
        """Set up OS-specific firewall rules to restrict Discord bot network access"""
        try:
            if self.is_windows:
                return self._setup_windows_firewall()
            elif self.is_linux:
                return self._setup_linux_firewall()
            else:
                logger.warning("Unsupported OS for automatic firewall setup")
                return False
        except Exception as e:
            logger.error(f"Failed to set up firewall rules: {e}")
            return False
    
    def _setup_windows_firewall(self) -> bool:
        """Set up Windows firewall rules"""
        try:
            # Create outbound rule to block all traffic except Discord domains
            # This requires admin privileges
            commands = [
                # Block all outbound traffic for TailSentry process
                ['netsh', 'advfirewall', 'firewall', 'add', 'rule', 
                 'name=TailSentry_Block_All', 'dir=out', 'action=block', 
                 'program=python.exe'],
                
                # Allow Discord domains
                ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                 'name=TailSentry_Allow_Discord', 'dir=out', 'action=allow',
                 'remoteip=discord.com,discordapp.com', 'protocol=tcp',
                 'localport=443']
            ]
            
            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Windows firewall command failed: {result.stderr}")
                    return False
            
            logger.info("Windows firewall rules set up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up Windows firewall: {e}")
            return False
    
    def _setup_linux_firewall(self) -> bool:
        """Set up Linux firewall rules using iptables"""
        try:
            # Note: This requires root privileges
            # In production, these rules should be set up by system administrator
            
            firewall_rules = [
                # Allow outbound HTTPS to Discord domains
                "iptables -A OUTPUT -p tcp --dport 443 -d discord.com -j ACCEPT",
                "iptables -A OUTPUT -p tcp --dport 443 -d discordapp.com -j ACCEPT", 
                "iptables -A OUTPUT -p tcp --dport 443 -d gateway.discord.gg -j ACCEPT",
                "iptables -A OUTPUT -p tcp --dport 443 -d cdn.discordapp.com -j ACCEPT",
                
                # Block all other outbound traffic from TailSentry user
                # "iptables -A OUTPUT -m owner --uid-owner tailsentry -j REJECT"
            ]
            
            logger.info("Linux firewall rules prepared (requires manual setup with root privileges)")
            logger.info("To apply rules, run as root:")
            for rule in firewall_rules:
                logger.info(f"  {rule}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare Linux firewall rules: {e}")
            return False
    
    def generate_firewall_script(self) -> str:
        """Generate OS-specific firewall setup script"""
        if self.is_windows:
            return self._generate_windows_firewall_script()
        elif self.is_linux:
            return self._generate_linux_firewall_script()
        else:
            return "# Unsupported OS for firewall script generation"
    
    def _generate_windows_firewall_script(self) -> str:
        """Generate Windows PowerShell firewall script"""
        return '''
# Windows Firewall Configuration for TailSentry
# Run as Administrator

Write-Host "🔥 Setting up Windows Firewall for TailSentry..." -ForegroundColor Yellow

# Remove any existing TailSentry rules
Get-NetFirewallRule -DisplayName "TailSentry*" | Remove-NetFirewallRule -ErrorAction SilentlyContinue

# Allow outbound HTTPS to Discord domains
New-NetFirewallRule -DisplayName "TailSentry - Allow Discord HTTPS" -Direction Outbound -Protocol TCP -RemotePort 443 -RemoteAddress @("discord.com", "discordapp.com", "gateway.discord.gg", "cdn.discordapp.com") -Action Allow

# Block all other outbound traffic for Python (optional - may be too restrictive)
# New-NetFirewallRule -DisplayName "TailSentry - Block Python Outbound" -Direction Outbound -Program "%SystemRoot%\\System32\\python.exe" -Action Block

Write-Host "✅ Windows Firewall rules configured for TailSentry" -ForegroundColor Green
Write-Host "⚠️  Test Discord bot functionality after applying rules" -ForegroundColor Yellow
'''
    
    def _generate_linux_firewall_script(self) -> str:
        """Generate Linux iptables firewall script"""
        return '''#!/bin/bash
# Linux Firewall Configuration for TailSentry
# Run as root: sudo ./setup_firewall.sh

echo "🔥 Setting up Linux Firewall for TailSentry..."

# Create new chain for TailSentry
iptables -N TAILSENTRY_OUT 2>/dev/null || iptables -F TAILSENTRY_OUT

# Allow outbound HTTPS to Discord domains
iptables -A TAILSENTRY_OUT -p tcp --dport 443 -d discord.com -j ACCEPT
iptables -A TAILSENTRY_OUT -p tcp --dport 443 -d discordapp.com -j ACCEPT
iptables -A TAILSENTRY_OUT -p tcp --dport 443 -d gateway.discord.gg -j ACCEPT  
iptables -A TAILSENTRY_OUT -p tcp --dport 443 -d cdn.discordapp.com -j ACCEPT
iptables -A TAILSENTRY_OUT -p tcp --dport 443 -d media.discordapp.net -j ACCEPT

# Allow DNS lookups (required for domain resolution)
iptables -A TAILSENTRY_OUT -p udp --dport 53 -j ACCEPT
iptables -A TAILSENTRY_OUT -p tcp --dport 53 -j ACCEPT

# Allow loopback
iptables -A TAILSENTRY_OUT -o lo -j ACCEPT

# Drop all other outbound traffic from tailsentry user
iptables -A TAILSENTRY_OUT -j DROP

# Apply rules to tailsentry user
iptables -A OUTPUT -m owner --uid-owner tailsentry -j TAILSENTRY_OUT

# Save rules (Ubuntu/Debian)
if command -v iptables-save > /dev/null; then
    iptables-save > /etc/iptables/rules.v4
fi

echo "✅ Linux Firewall rules configured for TailSentry"
echo "⚠️  Test Discord bot functionality after applying rules"
echo "📝 To remove rules: iptables -D OUTPUT -m owner --uid-owner tailsentry -j TAILSENTRY_OUT"
'''

# Network monitoring decorator
def monitor_network_access(func):
    """Decorator to monitor and log network access attempts"""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Network access: {func.__name__} succeeded")
            return result
        except Exception as e:
            logger.warning(f"Network access: {func.__name__} failed - {e}")
            raise
    return wrapper
