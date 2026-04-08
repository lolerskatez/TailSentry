"""Database initialization and migration module."""
import os
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger("tailsentry.db")

# Database configuration
PROJECT_ROOT = Path(__file__).parent
DB_DIR = PROJECT_ROOT / "data"
DB_PATH = DB_DIR / "tailsentry.db"


def ensure_data_dir():
    """Ensure data directory exists."""
    DB_DIR.mkdir(exist_ok=True, mode=0o755)


def get_db_connection():
    """Get a database connection with row factory."""
    ensure_data_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database with schema if it doesn't exist."""
    ensure_data_dir()
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Check if users table exists with all columns
        c.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in c.fetchall()}
        
        # Create table if it doesn't exist
        if not columns:
            logger.info("Creating users table")
            c.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    email TEXT UNIQUE,
                    active INTEGER DEFAULT 1,
                    display_name TEXT,
                    activity_log TEXT
                )
            ''')
            
            # Create indexes
            c.execute('CREATE INDEX IF NOT EXISTS ix_users_username ON users(username)')
            c.execute('CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)')
            c.execute('CREATE INDEX IF NOT EXISTS ix_users_active ON users(active)')
            
            conn.commit()
            logger.info("Users table created successfully")
        else:
            # Add missing columns if upgrading from old schema
            required_columns = {
                'id', 'username', 'password_hash', 'role', 'created_at',
                'email', 'active', 'display_name', 'activity_log'
            }
            missing = required_columns - columns
            
            if missing:
                logger.info(f"Adding missing columns: {missing}")
                
                if 'email' not in columns:
                    c.execute('ALTER TABLE users ADD COLUMN email TEXT UNIQUE')
                if 'active' not in columns:
                    c.execute('ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1')
                if 'display_name' not in columns:
                    c.execute('ALTER TABLE users ADD COLUMN display_name TEXT')
                if 'activity_log' not in columns:
                    c.execute('ALTER TABLE users ADD COLUMN activity_log TEXT')
                
                conn.commit()
                logger.info("Schema updated successfully")
    
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        conn.close()


def get_database_url():
    """Get database URL for SQLAlchemy."""
    return f"sqlite:///{DB_PATH}"


if __name__ == "__main__":
    init_database()
    logger.info(f"Database initialized at {DB_PATH}")
