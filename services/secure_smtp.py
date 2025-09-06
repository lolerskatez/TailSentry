"""
Enhanced SMTP Security Module for TailSentry
Provides secure SMTP functionality with improved validation, sanitization and security controls
"""

import smtplib
import ssl
import logging
import re
import html
import asyncio
from typing import Dict, List, Optional, Any
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.utils import formataddr, parseaddr
from email.header import Header
import socket
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SMTPSecurityError(Exception):
    """Custom exception for SMTP security-related errors"""
    pass

class SecureSMTPClient:
    """Enhanced SMTP client with security controls"""
    
    # Rate limiting
    _last_email_time = {}
    _email_count = {}
    
    # Security constants
    MAX_EMAILS_PER_HOUR = 50
    MIN_EMAIL_INTERVAL = 60  # seconds
    CONNECTION_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 5
    
    # Dangerous ports that should be blocked
    BLOCKED_PORTS = {21, 22, 23, 53, 80, 110, 143, 443, 993, 995}
    
    # Safe SMTP ports
    SAFE_PORTS = {25, 465, 587, 2525}
    
    @classmethod
    def validate_email_address(cls, email: str) -> bool:
        """Validate email address format and detect potential header injection"""
        if not email or not isinstance(email, str):
            return False
        
        # Check for header injection attempts
        if any(char in email for char in ['\n', '\r', '\0']):
            raise SMTPSecurityError("Email address contains invalid characters")
        
        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email.strip()):
            return False
        
        # Additional security checks
        if len(email) > 320:  # RFC 5321 limit
            return False
        
        local, domain = email.rsplit('@', 1)
        if len(local) > 64 or len(domain) > 253:
            return False
        
        return True
    
    @classmethod
    def sanitize_email_content(cls, content: str) -> str:
        """Sanitize email content to prevent injection attacks"""
        if not content:
            return ""
        
        # Remove potentially dangerous characters
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Escape HTML to prevent HTML injection
        content = html.escape(content)
        
        # Remove null bytes and other control characters
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        return content
    
    @classmethod
    def validate_smtp_config(cls, config) -> List[str]:
        """Validate SMTP configuration for security issues"""
        errors = []
        
        # Validate server hostname
        if not config.smtp_server or not isinstance(config.smtp_server, str):
            errors.append("SMTP server is required")
        elif not re.match(r'^[a-zA-Z0-9.-]+$', config.smtp_server):
            errors.append("SMTP server contains invalid characters")
        
        # Validate port
        if not isinstance(config.smtp_port, int) or config.smtp_port < 1 or config.smtp_port > 65535:
            errors.append("Invalid SMTP port number")
        elif config.smtp_port in cls.BLOCKED_PORTS:
            errors.append(f"Port {config.smtp_port} is not allowed for security reasons")
        elif config.smtp_port not in cls.SAFE_PORTS:
            logger.warning(f"Using non-standard SMTP port {config.smtp_port}")
        
        # Validate email addresses
        if config.from_email and not cls.validate_email_address(config.from_email):
            errors.append("Invalid 'from' email address format")
        
        # Validate username format (should be email-like)
        if config.username and not cls.validate_email_address(config.username):
            errors.append("Invalid username format")
        
        # Validate SSL/TLS configuration
        if config.use_ssl and config.use_tls:
            errors.append("Cannot use both SSL and TLS simultaneously")
        
        # Validate from_name for header injection
        if config.from_name:
            if any(char in config.from_name for char in ['\n', '\r', '\0']):
                errors.append("From name contains invalid characters")
            if len(config.from_name) > 78:  # RFC 2822 recommendation
                errors.append("From name is too long")
        
        return errors
    
    @classmethod
    def check_rate_limit(cls, identifier: str = "default") -> bool:
        """Check if rate limit allows sending email"""
        now = time.time()
        
        # Clean old entries
        cls._cleanup_rate_limit_data(now)
        
        # Check hourly limit
        hour_key = f"{identifier}_{int(now // 3600)}"
        if cls._email_count.get(hour_key, 0) >= cls.MAX_EMAILS_PER_HOUR:
            return False
        
        # Check minimum interval
        if identifier in cls._last_email_time:
            if now - cls._last_email_time[identifier] < cls.MIN_EMAIL_INTERVAL:
                return False
        
        return True
    
    @classmethod
    def update_rate_limit(cls, identifier: str = "default"):
        """Update rate limiting counters"""
        now = time.time()
        hour_key = f"{identifier}_{int(now // 3600)}"
        
        cls._last_email_time[identifier] = now
        cls._email_count[hour_key] = cls._email_count.get(hour_key, 0) + 1
    
    @classmethod
    def _cleanup_rate_limit_data(cls, current_time: float):
        """Clean up old rate limiting data"""
        current_hour = int(current_time // 3600)
        
        # Remove old hour entries
        old_keys = [k for k in cls._email_count.keys() if k.endswith(f"_{current_hour - 2}")]
        for key in old_keys:
            del cls._email_count[key]
        
        # Remove old last_email_time entries (older than 1 hour)
        old_identifiers = [k for k, v in cls._last_email_time.items() 
                          if current_time - v > 3600]
        for identifier in old_identifiers:
            del cls._last_email_time[identifier]
    
    @classmethod
    async def send_secure_email(cls, config, title: str, message: str, recipients: List[str]) -> Dict[str, Any]:
        """Send email with enhanced security measures"""
        try:
            # Validate configuration
            config_errors = cls.validate_smtp_config(config)
            if config_errors:
                return {"success": False, "error": f"Configuration errors: {'; '.join(config_errors)}"}
            
            # Check rate limiting
            if not cls.check_rate_limit():
                return {"success": False, "error": "Rate limit exceeded. Please wait before sending more emails."}
            
            # Validate and sanitize inputs
            title = cls.sanitize_email_content(title)[:200]  # Limit subject length
            message = cls.sanitize_email_content(message)[:10000]  # Limit message length
            
            if not title or not message:
                return {"success": False, "error": "Email title and message are required"}
            
            # Validate recipients
            valid_recipients = []
            for recipient in recipients:
                if cls.validate_email_address(recipient):
                    valid_recipients.append(recipient)
                else:
                    logger.warning(f"Invalid recipient email address: {recipient}")
            
            if not valid_recipients:
                return {"success": False, "error": "No valid recipient email addresses"}
            
            # Create secure SSL context
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            results = []
            successful_sends = 0
            
            for recipient in valid_recipients:
                try:
                    # Create message for each recipient (prevents header injection)
                    msg = MimeMultipart('alternative')
                    msg['Subject'] = Header(title, 'utf-8')
                    msg['From'] = formataddr((config.from_name, config.from_email))
                    msg['To'] = recipient
                    msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
                    msg['Message-ID'] = f"<{int(time.time())}.{hash(recipient)%10000}@tailsentry>"
                    
                    # Create both text and HTML versions
                    text_part = MimeText(message, 'plain', 'utf-8')
                    html_content = f"""
                    <html>
                        <head><title>{html.escape(title)}</title></head>
                        <body>
                            <h2>{html.escape(title)}</h2>
                            <p>{html.escape(message).replace(chr(10), '<br>')}</p>
                            <hr>
                            <p><small>This email was sent by TailSentry monitoring system.</small></p>
                        </body>
                    </html>
                    """
                    html_part = MimeText(html_content, 'html', 'utf-8')
                    
                    msg.attach(text_part)
                    msg.attach(html_part)
                    
                    # Send with retry logic
                    send_success = await cls._send_with_retry(config, msg, recipient, context)
                    
                    if send_success:
                        successful_sends += 1
                        results.append(f"Email sent successfully to {recipient}")
                    else:
                        results.append(f"Failed to send email to {recipient}")
                        
                except Exception as email_error:
                    logger.error(f"Failed to send email to {recipient}: {email_error}")
                    results.append(f"Failed to send to {recipient}: {str(email_error)}")
            
            # Update rate limiting
            if successful_sends > 0:
                cls.update_rate_limit()
            
            if successful_sends > 0:
                return {
                    "success": True, 
                    "message": f"Email sent to {successful_sends}/{len(valid_recipients)} recipients",
                    "details": results
                }
            else:
                return {
                    "success": False, 
                    "error": f"Failed to send to all {len(valid_recipients)} recipients",
                    "details": results
                }
                
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return {"success": False, "error": "Email sending failed due to security restrictions"}
    
    @classmethod
    async def _send_with_retry(cls, config, message, recipient: str, ssl_context) -> bool:
        """Send email with retry logic and proper error handling"""
        for attempt in range(cls.MAX_RETRIES):
            try:
                # Create connection with timeout
                if config.use_ssl:
                    server = smtplib.SMTP_SSL(
                        config.smtp_server, 
                        config.smtp_port, 
                        timeout=cls.CONNECTION_TIMEOUT,
                        context=ssl_context
                    )
                else:
                    server = smtplib.SMTP(
                        config.smtp_server, 
                        config.smtp_port, 
                        timeout=cls.CONNECTION_TIMEOUT
                    )
                    
                    if config.use_tls:
                        server.starttls(context=ssl_context)
                
                # Authenticate if credentials provided
                if config.username and config.password:
                    server.login(config.username, config.password)
                
                # Send message
                server.send_message(message)
                server.quit()
                
                logger.info(f"Email sent successfully to {recipient} on attempt {attempt + 1}")
                return True
                
            except (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused) as auth_error:
                logger.error(f"Authentication/recipient error for {recipient}: {auth_error}")
                return False  # Don't retry auth errors
                
            except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, socket.timeout) as conn_error:
                logger.warning(f"Connection error for {recipient} on attempt {attempt + 1}: {conn_error}")
                if attempt < cls.MAX_RETRIES - 1:
                    await asyncio.sleep(cls.RETRY_DELAY * (attempt + 1))  # Exponential backoff
                    continue
                return False
                
            except Exception as e:
                logger.error(f"Unexpected error sending to {recipient} on attempt {attempt + 1}: {e}")
                if attempt < cls.MAX_RETRIES - 1:
                    await asyncio.sleep(cls.RETRY_DELAY)
                    continue
                return False
        
        return False
    
    @classmethod
    async def test_connection(cls, config) -> Dict[str, Any]:
        """Test SMTP connection with security validation"""
        try:
            # Validate configuration first
            config_errors = cls.validate_smtp_config(config)
            if config_errors:
                return {"success": False, "error": f"Configuration errors: {'; '.join(config_errors)}"}
            
            # Create secure SSL context
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            # Test connection
            if config.use_ssl:
                server = smtplib.SMTP_SSL(
                    config.smtp_server, 
                    config.smtp_port, 
                    timeout=cls.CONNECTION_TIMEOUT,
                    context=context
                )
            else:
                server = smtplib.SMTP(
                    config.smtp_server, 
                    config.smtp_port, 
                    timeout=cls.CONNECTION_TIMEOUT
                )
                
                if config.use_tls:
                    server.starttls(context=context)
            
            # Test authentication if credentials provided
            if config.username and config.password:
                server.login(config.username, config.password)
            
            server.quit()
            
            return {"success": True, "message": "SMTP connection test successful"}
            
        except smtplib.SMTPAuthenticationError as auth_error:
            return {"success": False, "error": "SMTP authentication failed. Please check your credentials."}
        except smtplib.SMTPConnectError as conn_error:
            return {"success": False, "error": "Failed to connect to SMTP server. Please check server and port."}
        except ssl.SSLError as ssl_error:
            return {"success": False, "error": "SSL/TLS connection failed. Please check encryption settings."}
        except socket.timeout:
            return {"success": False, "error": "Connection timeout. Please check server address and firewall settings."}
        except Exception as e:
            logger.error(f"SMTP test failed: {e}")
            return {"success": False, "error": "SMTP test failed due to configuration issues"}
