"""
TailSentry Testing & Database Migration Guide

This document describes the new testing framework and database migration system
introduced to improve code quality, reliability, and maintainability.
"""

# Testing & Migration Infrastructure Guide

## Overview

TailSentry now includes:
- **Comprehensive Test Suite** with pytest fixtures and auth/API test coverage
- **Database Migration System** using Alembic for versioned schema management
- **Centralized Database Module** for consistent database access patterns

---

## Quick Start

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests with coverage
pytest tests/ -v --cov=. --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run with verbose output
pytest tests/ -vv --tb=short

# Run specific test class or function
pytest tests/test_auth.py::TestUserCreation::test_create_user_success -v
```

### Database Migrations

```bash
# Initialize database (done automatically on app startup)
python -c "from database import init_database; init_database()"

# Create a new migration after schema changes
alembic revision --autogenerate -m "Add new column to users table"

# Apply pending migrations
alembic upgrade head

# Rollback to previous migration
alembic downgrade -1

# Show current migration version
alembic current

# Show migration history
alembic history
```

---

## Directory Structure

```
TailSentry/
├── tests/                          # Test suite
│   ├── __init__.py                 # Package marker
│   ├── conftest.py                 # Pytest configuration & fixtures
│   ├── test_auth.py                # Authentication tests
│   ├── test_api_basic.py           # Basic API endpoint tests
│   └── fixtures.py                 # Shared test fixtures (future)
│
├── alembic/                        # Database migration system
│   ├── env.py                      # Alembic environment
│   ├── script.py.mako              # Migration script template
│   ├── versions/                   # Migration files
│   │   └── 001_initial_users_table.py
│   └── __init__.py
│
├── database.py                     # Centralized database module
├── auth_user.py                    # User authentication (now uses database.py)
├── alembic.ini                     # Alembic configuration
└── requirements-dev.txt            # Development dependencies
```

---

## Test Suite Details

### Fixtures (conftest.py)

**test_db_path**: Provides temporary database path for tests
```python
@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary test database."""
```

**test_db**: Creates initialized test database
```python
@pytest.fixture
def test_db(test_db_path):
    """Create and initialize test database with schema."""
```

**monkeypatch_db**: Monkeypatches auth_user to use test database
```python
@pytest.fixture
def monkeypatch_db(monkeypatch, test_db_path):
    """Monkeypatch auth_user.py to use test database."""
```

**app_client**: FastAPI test client for route testing
```python
@pytest.fixture
def app_client():
    """Create FastAPI test client."""
```

**sample_user**: Single test user data
```python
@pytest.fixture
def sample_user():
    """Sample user data for tests."""
```

**sample_users**: Multiple test users
```python
@pytest.fixture
def sample_users():
    """Multiple sample users for tests."""
```

### Test Coverage

#### test_auth.py - Authentication Tests

- **TestUserCreation**: Create user success, duplicate rejection, default role
- **TestUserVerification**: Verify with correct/wrong password, inactive users
- **TestUserRetrieval**: Get user, list users
- **TestUserDeletion**: Delete user success/failure
- **TestUserEmail**: Set email, get user by email

#### test_api_basic.py - API Endpoint Tests

- **TestHealthEndpoint**: Health check endpoints
- **TestRootEndpoint**: Root path behavior
- **TestApiBreadcrumbs**: API endpoints exist and don't 404

### Writing New Tests

```python
import pytest

class TestNewFeature:
    """Test new feature functionality."""
    
    def test_feature_works(self, monkeypatch_db, sample_user):
        """Test that feature works."""
        # Arrange
        import auth_user
        existing_user = auth_user.create_user(
            sample_user["username"],
            sample_user["password"]
        )
        assert existing_user is True
        
        # Act
        result = my_function(sample_user["username"])
        
        # Assert
        assert result is not None
```

### Tips for Testing

1. **Use fixtures** for database setup instead of manual initialization
2. **Keep tests isolated** - each test should be independent
3. **Use descriptive names** - test function names should describe what they test
4. **Mock external services** - don't call real Tailscale API in tests
5. **Test edge cases** - empty inputs, None values, invalid data

---

## Database Migrations

### Schema Management

Alembic provides version control for database schema:

```
001_initial_users_table (current)
├── users table
├── username unique constraint
├── email unique constraint
└── indexes on username, email, active
```

### Creating Migrations

**Auto-generate migrations** (for SQLAlchemy models):
```bash
alembic revision --autogenerate -m "Add last_login column"
```

**Manual migrations** (for custom SQL):
```bash
alembic revision -m "Add stored procedure"
```

Then edit `alembic/versions/XXX_description.py`:
```python
def upgrade() -> None:
    """Create index on created_at column."""
    op.create_index('ix_users_created_at', 'users', ['created_at'])

def downgrade() -> None:
    """Drop index on created_at column."""
    op.drop_index('ix_users_created_at', table_name='users')
```

### Migration Best Practices

1. **Always include downgrade** - makes rollbacks possible
2. **Use descriptive names** - `001_add_email_column` vs `001_update`
3. **Keep migrations small** - one logical change per migration
4. **Test downgrades** - verify `alembic downgrade` works
5. **Never modify old migrations** - create new ones instead

### Troubleshooting Migrations

**Migration won't apply:**
```bash
# Check current migration version
alembic current

# Check migration history
alembic history

# Manually set migration version (use cautiously)
alembic stamp <revision>
```

**Need to rollback:**
```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific migration
alembic downgrade 001_initial_users_table
```

---

## Database Module (database.py)

### Purpose
Centralized database connection and initialization logic.

### Key Functions

**ensure_data_dir()**: Ensures data directory exists
```python
from database import ensure_data_dir
ensure_data_dir()  # Creates data/ directory if needed
```

**get_db_connection()**: Gets database connection with row factory
```python
from database import get_db_connection
conn = get_db_connection()
c = conn.cursor()
c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
user = c.fetchone()  # Returns sqlite3.Row object
```

**init_database()**: Initializes database with schema
```python
from database import init_database
init_database()  # Runs startup checks, creates tables if needed
```

**get_database_url()**: Returns SQLAlchemy-compatible database URL
```python
from database import get_database_url
url = get_database_url()  # Returns "sqlite:///./data/tailsentry.db"
```

---

## Integration with Application

### Startup Sequence

1. **main.py starts**
   - Imports `from database import init_database`
   - Calls `init_database()` before creating FastAPI app

2. **Database initialized**
   - Creates data directory
   - Creates users table if doesn't exist
   - Adds missing columns if upgrading
   - Creates indexes

3. **auth_user imported**
   - Uses `database.get_db_connection()` via `get_db()`
   - Schema migration functions run with error handling

4. **App ready**
   - All routes can use auth_user functions
   - Database is properly initialized

---

## Continuous Improvement

### Next Steps

1. **Expand Test Coverage**
   - Add tests for route handlers
   - Add tests for service modules (tailscale_service, discord_bot, etc.)
   - Add integration tests for complete workflows

2. **Add More Migrations**
   - Consolidate notification service structure
   - Refactor activity_log from JSON to structured table
   - Add indexes for common queries

3. **Performance Testing**
   - Add performance benchmarks
   - Test query performance with large datasets
   - Identify slow database queries

4. **Documentation**
   - Add API response schema documentation
   - Create database schema documentation
   - Create troubleshooting guide

---

## Support

For issues or questions:
1. Check test output - pytest provides detailed error messages
2. Review migration logs - `alembic.ini` has logging configuration
3. Check database.py - centralized logic for debugging
4. Run tests in verbose mode - `pytest -vv`

---

## Example: Adding a New Feature with Tests

### 1. Write failing test first (TDD)
```python
# tests/test_new_feature.py
def test_new_feature(monkeypatch_db):
    import auth_user
    result = auth_user.new_function("test")
    assert result is True
```

### 2. Run test (fails as expected)
```bash
pytest tests/test_new_feature.py -v
# FAILED - function doesn't exist yet
```

### 3. Implement feature
```python
# auth_user.py
def new_function(param: str) -> bool:
    """Implement the new feature."""
    return True
```

### 4. Run test (passes)
```bash
pytest tests/test_new_feature.py -v
# PASSED
```

### 5. If schema change needed, create migration
```bash
alembic revision -m "Add new_column for new feature"
# Edit alembic/versions/XXX_add_new_column.py
alembic upgrade head
```

### 6. Verify backwards compatibility
```bash
alembic downgrade -1
alembic upgrade head
# Ensure no data loss
```

---

**Version**: 1.0.0
**Last Updated**: 2026-04-08
**Maintainer**: TailSentry Team
