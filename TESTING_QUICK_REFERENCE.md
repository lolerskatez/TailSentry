"""
Quick Reference: Testing & Migrations
======================================

TESTING
-------
pytest tests/                           # Run all tests
pytest tests/test_auth.py -v           # Run auth tests
pytest -k test_create_user             # Run specific test
pytest --tb=short                       # Short traceback format
pytest --cov=. --cov-report=html       # Coverage report

MIGRATIONS
----------
alembic current                         # Show current version
alembic history                         # Show all migrations
alembic revision -m "message"           # Create new migration
alembic upgrade head                    # Apply all pending
alembic downgrade -1                    # Rollback one
alembic downgrade 001_initial           # Rollback to specific

DATABASE
--------
python -c "from database import init_database; init_database()"
python -c "from auth_user import list_users; print(list_users())"

DEVELOPMENT WORKFLOW
--------------------
1. Write test
2. Run test (fails)
3. Implement feature
4. Run test (passes)
5. Commit changes
6. Create migration if schema changed
7. Test migration up/down
8. Merge to main

COMMON ISSUES
-------------
Test import error:
  → Install requirements-dev.txt
  → Check conftest.py fixtures

Database not found:
  → Call init_database() on startup ✓ (done in main.py)
  → Check data/ directory exists

Migration conflicts:
  → Check migration history: alembic history
  → Rebase migrations if needed

Fixture errors:
  → Review conftest.py fixtures
  → Check monkeypatch_db usage
  → Verify test_db_path fixture

HELPFUL COMMANDS
----------------
# Show test stats
pytest --collect-only

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run last failed tests
pytest --lf

# Run failed tests first
pytest --ff

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Profile slow tests
pytest --durations=10
"""
