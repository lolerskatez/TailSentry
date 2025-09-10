def add_activity_log_column():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE users ADD COLUMN activity_log TEXT')
    except Exception:
        pass  # Ignore if already exists
    conn.commit()
    conn.close()

import json

def append_user_activity(username: str, activity: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT activity_log FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    if row and row[0]:
        try:
            log = json.loads(row[0])
        except Exception:
            log = []
    else:
        log = []
    log.append(activity)
    # Keep only last 20 entries
    log = log[-20:]
    c.execute('UPDATE users SET activity_log = ? WHERE username = ?', (json.dumps(log), username))
    conn.commit()
    conn.close()

def get_user_activity_log(username: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT activity_log FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except Exception:
            return []
    return []
def add_active_column():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1')
    except Exception:
        pass  # Ignore if already exists
    conn.commit()
    conn.close()
import os
import sqlite3
from passlib.context import CryptContext
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'users.db')
print(f"[DEBUG] Using DB_PATH: {DB_PATH}")

# Ensure data directory exists
data_dir = os.path.dirname(DB_PATH)
if not os.path.exists(data_dir):
    os.makedirs(data_dir, mode=0o755, exist_ok=True)
    print(f"[DEBUG] Created data directory: {data_dir}")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    # Ensure data directory exists before connecting
    data_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, mode=0o755, exist_ok=True)
        print(f"[DEBUG] Created data directory: {data_dir}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def create_user(username: str, password: str, role: str = 'user') -> bool:
    import logging
    logger = logging.getLogger("tailsentry")
    logger.info(f"[CREATE USER] Starting creation - username: {username} | role: {role} | password_len: {len(password) if password else 0}")
    
    conn = get_db()
    c = conn.cursor()
    try:
        logger.info(f"[CREATE USER] Executing INSERT for {username}")
        c.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                  (username, pwd_context.hash(password), role))
        conn.commit()
        logger.info(f"[CREATE USER] Success - user {username} created")
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"[CREATE USER] IntegrityError for {username}: {e}")
        return False
    except Exception as e:
        logger.error(f"[CREATE USER] General Exception for {username}: {type(e).__name__}: {e}")
        return False
    finally:
        conn.close()

def verify_user(username: str, password: str) -> Optional[dict]:
    import logging
    logger = logging.getLogger("tailsentry")
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    if user and pwd_context.verify(password, user['password_hash']):
        # Check if user is active
        # Convert Row to dict first, then check active status
        user_dict = dict(user)
        if user_dict.get('active', 1) == 1:  # Default to active if column doesn't exist
            logger.info(f"[VERIFY USER] Authentication successful for active user: {username}")
            return user_dict
        else:
            # User exists and password is correct, but account is disabled
            logger.warning(f"[VERIFY USER] Authentication denied for disabled user: {username}")
            return None
    else:
        if user:
            logger.warning(f"[VERIFY USER] Invalid password for user: {username}")
        else:
            logger.warning(f"[VERIFY USER] User not found: {username}")
        return None

def get_user(username: str) -> Optional[dict]:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def list_users() -> list:
    conn = get_db()
    c = conn.cursor()
    # Include active and display_name for UI
    try:
        c.execute('ALTER TABLE users ADD COLUMN display_name TEXT')
    except Exception:
        pass
    try:
        c.execute('ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1')
    except Exception:
        pass
    c.execute('SELECT id, username, role, created_at, COALESCE(active,1) AS active, COALESCE(display_name, "") AS name FROM users')
    users = c.fetchall()
    conn.close()
    return [dict(u) for u in users]

def delete_user(username: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE username = ?', (username,))
    conn.commit()
    deleted = c.rowcount > 0
    conn.close()
    return deleted

def set_user_email(username: str, email: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET email = ? WHERE username = ?', (email, username))
        conn.commit()
        return True
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def get_admin_emails() -> list:
    """Get email addresses of all active admin users for notifications"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT email FROM users WHERE role = ? AND COALESCE(active, 1) = 1 AND email IS NOT NULL AND email != ""', ("admin",))
    emails = c.fetchall()
    conn.close()
    return [email[0] for email in emails if email[0]]

def set_user_display_name(username: str, display_name: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET display_name = ? WHERE username = ?', (display_name, username))
        conn.commit()
        return True
    finally:
        conn.close()

def get_user_display_name(username: str) -> str:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT display_name FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""

def add_email_column():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE users ADD COLUMN email TEXT')
    except Exception:
        pass  # Ignore if already exists
    conn.commit()
    conn.close()

def add_discord_username_column():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE users ADD COLUMN discord_username TEXT')
    except Exception:
        pass  # Ignore if already exists
    conn.commit()
    conn.close()

def add_notification_preferences_column():
    conn = get_db()
    c = conn.cursor()
    try:
        # JSON column to store notification preferences like {"email": true, "system_alerts": true, "maintenance": false}
        c.execute('ALTER TABLE users ADD COLUMN notification_preferences TEXT DEFAULT \'{"email": true, "system_alerts": true, "maintenance": true}\'')
    except Exception:
        pass  # Ignore if already exists
    conn.commit()
    conn.close()

def get_user_notification_preferences(username: str) -> dict:
    """Get user notification preferences, returns default if not set"""
    import json
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT notification_preferences FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    
    if row and row[0]:
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Return default preferences
    return {"email": True, "system_alerts": True, "maintenance": True}

def set_user_notification_preferences(username: str, preferences: dict) -> bool:
    """Set user notification preferences"""
    import json
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET notification_preferences = ? WHERE username = ?', 
                 (json.dumps(preferences), username))
        conn.commit()
        return True
    finally:
        conn.close()

def get_admin_emails_with_preferences(notification_type: str = "email") -> list:
    """Get email addresses of admin users who have opted in to receive the specified notification type"""
    import json
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT email, notification_preferences FROM users WHERE role = ? AND COALESCE(active, 1) = 1 AND email IS NOT NULL AND email != ""', ("admin",))
    users = c.fetchall()
    conn.close()
    
    opted_in_emails = []
    for email, prefs_json in users:
        if email:
            try:
                prefs = json.loads(prefs_json) if prefs_json else {"email": True, "system_alerts": True, "maintenance": True}
                # Check if user has opted in to this notification type
                if prefs.get(notification_type, True):  # Default to True if preference not set
                    opted_in_emails.append(email)
            except (json.JSONDecodeError, TypeError):
                # If preferences are corrupted, default to opt-in for backward compatibility
                opted_in_emails.append(email)
    
    return opted_in_emails

def add_display_name_column():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE users ADD COLUMN display_name TEXT')
    except Exception:
        pass  # Ignore if already exists
    conn.commit()
    conn.close()

def set_user_role(username: str, role: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET role = ? WHERE username = ?', (role, username))
        conn.commit()
        return True
    finally:
        conn.close()

def set_user_active(username: str, active: bool) -> bool:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1')
    except Exception:
        pass  # Ignore if already exists
    c.execute('UPDATE users SET active = ? WHERE username = ?', (1 if active else 0, username))
    conn.commit()
    conn.close()
    return True

def is_user_active(username: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT active FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0])

def ensure_default_admin():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', ("admin",))
    if not c.fetchone():
        c.execute('INSERT INTO users (username, password_hash, role, email, active, display_name) VALUES (?, ?, ?, ?, ?, ?)', ("admin", pwd_context.hash("admin123"), "admin", "admin@localhost", 1, "Administrator"))
        conn.commit()
    conn.close()

def create_or_update_sso_user(sso_provider: str, sso_user_id: str, email: str, display_name: str, username: Optional[str] = None, sso_metadata: Optional[dict] = None) -> Optional[dict]:
    """Create or update a user from SSO login"""
    import json
    import logging
    from datetime import datetime
    
    logger = logging.getLogger("tailsentry")
    conn = get_db()
    c = conn.cursor()
    
    # Check if user already exists by SSO provider and user ID
    c.execute('SELECT * FROM users WHERE sso_provider = ? AND sso_user_id = ?', (sso_provider, sso_user_id))
    existing_user = c.fetchone()
    
    if existing_user:
        # Update existing SSO user
        logger.info(f"[SSO] Updating existing SSO user: {sso_provider}:{sso_user_id}")
        c.execute('''UPDATE users SET 
                     email = ?, display_name = ?, last_sso_login = ?, sso_metadata = ?
                     WHERE sso_provider = ? AND sso_user_id = ?''', 
                  (email, display_name, datetime.now(), json.dumps(sso_metadata or {}), sso_provider, sso_user_id))
        conn.commit()
        conn.close()
        return dict(existing_user)
    
    # Create new SSO user
    if not username:
        # Generate username from email or use sso_user_id
        username = email.split('@')[0] if email and '@' in email else f"{sso_provider}_{sso_user_id}"
        
    # Ensure username is unique
    original_username = username
    counter = 1
    while True:
        c.execute('SELECT id FROM users WHERE username = ?', (username,))
        if not c.fetchone():
            break
        username = f"{original_username}_{counter}"
        counter += 1
    
    logger.info(f"[SSO] Creating new SSO user: {username} ({sso_provider}:{sso_user_id})")
    
    try:
        c.execute('''INSERT INTO users 
                     (username, password_hash, role, email, display_name, active, 
                      sso_provider, sso_user_id, sso_metadata, last_sso_login) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (username, '', 'user', email, display_name, 1, 
                   sso_provider, sso_user_id, json.dumps(sso_metadata or {}), datetime.now()))
        
        user_id = c.lastrowid
        conn.commit()
        
        # Get the created user
        c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        new_user = c.fetchone()
        conn.close()
        
        logger.info(f"[SSO] Successfully created SSO user: {username}")
        return dict(new_user)
        
    except Exception as e:
        logger.error(f"[SSO] Failed to create SSO user: {e}")
        conn.close()
        return None

def get_user_by_sso(sso_provider: str, sso_user_id: str) -> Optional[dict]:
    """Get user by SSO provider and user ID"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE sso_provider = ? AND sso_user_id = ?', (sso_provider, sso_user_id))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def link_sso_to_existing_user(username: str, sso_provider: str, sso_user_id: str, sso_metadata: Optional[dict] = None) -> bool:
    """Link SSO provider to an existing local user account"""
    import json
    import logging
    from datetime import datetime
    
    logger = logging.getLogger("tailsentry")
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''UPDATE users SET 
                     sso_provider = ?, sso_user_id = ?, sso_metadata = ?, last_sso_login = ?
                     WHERE username = ?''',
                  (sso_provider, sso_user_id, json.dumps(sso_metadata or {}), datetime.now(), username))
        
        if c.rowcount > 0:
            conn.commit()
            logger.info(f"[SSO] Successfully linked {sso_provider} to user: {username}")
            conn.close()
            return True
        else:
            logger.warning(f"[SSO] User not found for linking: {username}")
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"[SSO] Failed to link SSO to user {username}: {e}")
        conn.close()
        return False

def add_sso_columns():
    """Add SSO-related columns to users table"""
    conn = get_db()
    c = conn.cursor()
    try:
        # Add SSO provider column (e.g., 'google', 'microsoft', 'github', 'local')
        c.execute('ALTER TABLE users ADD COLUMN sso_provider TEXT DEFAULT "local"')
    except Exception:
        pass  # Ignore if already exists
    
    try:
        # Add SSO user ID (the unique ID from the SSO provider)
        c.execute('ALTER TABLE users ADD COLUMN sso_user_id TEXT')
    except Exception:
        pass  # Ignore if already exists
    
    try:
        # Add SSO metadata (JSON field for additional provider data)
        c.execute('ALTER TABLE users ADD COLUMN sso_metadata TEXT')
    except Exception:
        pass  # Ignore if already exists
    
    try:
        # Add last SSO login timestamp
        c.execute('ALTER TABLE users ADD COLUMN last_sso_login TIMESTAMP')
    except Exception:
        pass  # Ignore if already exists
    
    conn.commit()
    conn.close()

# Initialize DB and ensure admin user at module load
init_db()
add_email_column()
add_discord_username_column()
add_display_name_column()
add_active_column()
add_activity_log_column()
add_notification_preferences_column()
add_sso_columns()
ensure_default_admin()
