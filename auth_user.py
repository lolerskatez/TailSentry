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
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
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
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                  (username, pwd_context.hash(password), role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username: str, password: str) -> Optional[dict]:
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    if user and pwd_context.verify(password, user['password_hash']):
        return dict(user)
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
    c.execute('SELECT id, username, role, created_at FROM users')
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

# Initialize DB and ensure admin user at module load
init_db()
add_email_column()
add_display_name_column()
add_active_column()
add_activity_log_column()
ensure_default_admin()
