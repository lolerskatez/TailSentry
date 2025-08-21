import os
import sqlite3
from passlib.context import CryptContext
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.db')
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
