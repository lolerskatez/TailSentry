"""Pytest configuration and shared fixtures for TailSentry tests."""
import os
import sys
import sqlite3
import tempfile
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Use a module-level temporary directory that persists for the entire session
_temp_db_dir = tempfile.TemporaryDirectory()


@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary test database path."""
    db_path = os.path.join(_temp_db_dir.name, "test.db")
    yield db_path
    # Cleanup handled by TemporaryDirectory context manager


@pytest.fixture
def test_db(test_db_path, monkeypatch):
    """Create and initialize test database with schema."""
    # Ensure database module uses test path
    import database
    monkeypatch.setattr(database, "DB_PATH", Path(test_db_path))
    
    # Create connection and schema
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    
    # Create users table with all columns
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
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
    conn.commit()
    
    yield conn
    
    conn.close()
    # Clean up the test database file
    try:
        os.unlink(test_db_path)
    except (OSError, FileNotFoundError):
        pass


@pytest.fixture
def monkeypatch_db(monkeypatch, test_db_path):
    """Monkeypatch auth_user and database to use test database."""
    import database
    import auth_user
    
    # Create a unique test database for this test to ensure isolation
    import tempfile
    test_dir = tempfile.mkdtemp()
    unique_db_path = os.path.join(test_dir, "test_isolated.db")
    
    # Patch database module
    monkeypatch.setattr(database, "DB_PATH", Path(unique_db_path))
    
    # Create test database with schema
    conn = sqlite3.connect(unique_db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
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
    conn.commit()
    conn.close()
    
    # Patch auth_user to use test database
    monkeypatch.setattr(auth_user, "DB_PATH", unique_db_path)
    
    yield monkeypatch
    
    # Cleanup
    try:
        os.unlink(unique_db_path)
        os.rmdir(test_dir)
    except (OSError, FileNotFoundError):
        pass


@pytest.fixture
def app_client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from main import app
    
    client = TestClient(app)
    return client


@pytest.fixture
def authenticated_session(app_client):
    """Create authenticated session."""
    # This would be used for route tests that require authentication
    response = app_client.post("/authenticate", data={
        "username": "testuser",
        "password": "testpass123"
    })
    return app_client.cookies


@pytest.fixture
def sample_user():
    """Sample user data for tests."""
    return {
        "username": "testuser",
        "password": "TestPassword123!",
        "role": "admin",
        "email": "test@example.com",
        "display_name": "Test User"
    }


@pytest.fixture
def sample_users():
    """Multiple sample users for tests."""
    return [
        {
            "username": "admin",
            "password": "AdminPass123!",
            "role": "admin",
            "email": "admin@example.com",
            "display_name": "Administrator"
        },
        {
            "username": "user1",
            "password": "UserPass123!",
            "role": "user",
            "email": "user1@example.com",
            "display_name": "User One"
        },
        {
            "username": "user2",
            "password": "UserPass456!",
            "role": "viewer",
            "email": "user2@example.com",
            "display_name": "User Two"
        }
    ]
