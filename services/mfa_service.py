"""Multi-Factor Authentication (MFA) service for TailSentry."""
import sqlite3
import logging
import pyotp
import secrets
import qrcode
from io import BytesIO
from base64 import b64encode
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger("tailsentry.mfa")


class MFAService:
    """Handle Multi-Factor Authentication for users."""
    
    def __init__(self, db_path: str = "data/tailsentry.db"):
        """Initialize MFA service.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = Path(db_path)
        self._init_mfa_tables()
    
    def _init_mfa_tables(self):
        """Initialize MFA-related tables."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create mfa_settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mfa_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    mfa_enabled INTEGER DEFAULT 0,
                    mfa_method TEXT,
                    totp_secret TEXT,
                    totp_backup_codes TEXT,
                    sms_phone TEXT,
                    sms_verified INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_verified DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Create mfa_attempts table for rate limiting
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mfa_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    attempt_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success INTEGER,
                    method TEXT,
                    ip_address TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Create recovery_codes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recovery_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    used INTEGER DEFAULT 0,
                    used_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_mfa_settings_user_id ON mfa_settings(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_mfa_attempts_user_id ON mfa_attempts(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS ix_recovery_codes_user_id ON recovery_codes(user_id)')
            
            conn.commit()
            conn.close()
            logger.info("MFA tables initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize MFA tables: {e}", exc_info=True)
    
    def enable_totp(self, user_id: int, username: str, issuer: str = "TailSentry") -> Dict:
        """Generate TOTP secret and QR code for user.
        
        Args:
            user_id: ID of the user
            username: Username of the user
            issuer: Issuer name for TOTP
            
        Returns:
            Dict with secret and QR code
        """
        try:
            # Generate TOTP secret
            totp = pyotp.TOTP(pyotp.random_base32())
            secret = totp.secret
            
            # Generate QR code
            provisioning_uri = totp.provisioning_uri(
                name=username,
                issuer_name=issuer
            )
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            
            qr_code_b64 = b64encode(img_buffer.getvalue()).decode()
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4) for _ in range(10)]
            
            return {
                "success": True,
                "secret": secret,
                "qr_code": f"data:image/png;base64,{qr_code_b64}",
                "provisioning_uri": provisioning_uri,
                "backup_codes": backup_codes
            }
            
        except Exception as e:
            logger.error(f"Failed to enable TOTP for user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def verify_totp(self, user_id: int, token: str, secret: str) -> bool:
        """Verify a TOTP token.
        
        Args:
            user_id: ID of the user
            token: TOTP token to verify
            secret: TOTP secret
            
        Returns:
            True if token is valid
        """
        try:
            totp = pyotp.TOTP(secret)
            # Allow for time drift of +/- 1 window (30 seconds)
            is_valid = totp.verify(token, window=1)
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to verify TOTP for user {user_id}: {e}", exc_info=True)
            return False
    
    def activate_mfa(self, user_id: int, mfa_method: str, totp_secret: Optional[str] = None,
                     backup_codes: Optional[List[str]] = None) -> bool:
        """Activate MFA for a user.
        
        Args:
            user_id: ID of the user
            mfa_method: MFA method (totp, sms, backup)
            totp_secret: TOTP secret if using TOTP
            backup_codes: List of backup codes
            
        Returns:
            True if MFA activated successfully
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Check if MFA settings exist
            cursor.execute('SELECT id FROM mfa_settings WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                # Update existing settings
                cursor.execute('''
                    UPDATE mfa_settings
                    SET mfa_enabled = 1, mfa_method = ?, totp_secret = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (mfa_method, totp_secret, user_id))
            else:
                # Create new settings
                cursor.execute('''
                    INSERT INTO mfa_settings
                    (user_id, mfa_enabled, mfa_method, totp_secret)
                    VALUES (?, 1, ?, ?)
                ''', (user_id, mfa_method, totp_secret))
            
            # Add backup codes if provided
            if backup_codes:
                # Delete old backup codes
                cursor.execute('DELETE FROM recovery_codes WHERE user_id = ?', (user_id,))
                
                # Insert new backup codes
                for code in backup_codes:
                    cursor.execute('''
                        INSERT INTO recovery_codes (user_id, code)
                        VALUES (?, ?)
                    ''', (user_id, code))
            
            conn.commit()
            conn.close()
            
            logger.info(f"MFA activated for user {user_id} using {mfa_method}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate MFA for user {user_id}: {e}", exc_info=True)
            return False
    
    def disable_mfa(self, user_id: int) -> bool:
        """Disable MFA for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            True if MFA disabled successfully
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE mfa_settings
                SET mfa_enabled = 0, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"MFA disabled for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable MFA for user {user_id}: {e}", exc_info=True)
            return False
    
    def is_mfa_enabled(self, user_id: int) -> bool:
        """Check if MFA is enabled for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            True if MFA is enabled
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('SELECT mfa_enabled FROM mfa_settings WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            return result and result[0] == 1 if result else False
            
        except Exception as e:
            logger.error(f"Failed to check MFA status for user {user_id}: {e}", exc_info=True)
            return False
    
    def get_mfa_status(self, user_id: int) -> Optional[Dict]:
        """Get MFA status for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dict with MFA status or None
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM mfa_settings WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get MFA status for user {user_id}: {e}", exc_info=True)
            return None
    
    def log_mfa_attempt(self, user_id: int, success: bool, method: str,
                       ip_address: Optional[str] = None) -> bool:
        """Log an MFA attempt.
        
        Args:
            user_id: ID of the user
            success: Whether the attempt was successful
            method: MFA method used
            ip_address: IP address of the attempt
            
        Returns:
            True if logged successfully
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO mfa_attempts
                (user_id, success, method, ip_address)
                VALUES (?, ?, ?, ?)
            ''', (user_id, 1 if success else 0, method, ip_address))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log MFA attempt: {e}", exc_info=True)
            return False
    
    def check_mfa_rate_limit(self, user_id: int, max_attempts: int = 5,
                            window_minutes: int = 15) -> bool:
        """Check if user is rate limited on MFA attempts.
        
        Args:
            user_id: ID of the user
            max_attempts: Maximum failed attempts allowed
            window_minutes: Time window in minutes
            
        Returns:
            True if under limit, False if rate limited
        """
        try:
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM mfa_attempts
                WHERE user_id = ? AND success = 0
                AND attempt_timestamp >= ?
            ''', (user_id, cutoff_time.isoformat()))
            
            failed_attempts = cursor.fetchone()[0]
            conn.close()
            
            return failed_attempts < max_attempts
            
        except Exception as e:
            logger.error(f"Failed to check MFA rate limit: {e}", exc_info=True)
            return True
    
    def use_recovery_code(self, user_id: int, code: str) -> bool:
        """Use a recovery code.
        
        Args:
            user_id: ID of the user
            code: Recovery code to use
            
        Returns:
            True if code is valid and unused
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Check if code exists and is unused
            cursor.execute('''
                SELECT id FROM recovery_codes
                WHERE user_id = ? AND code = ? AND used = 0
            ''', (user_id, code))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            
            # Mark code as used
            cursor.execute('''
                UPDATE recovery_codes
                SET used = 1, used_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND code = ?
            ''', (user_id, code))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recovery code used for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to use recovery code: {e}", exc_info=True)
            return False
