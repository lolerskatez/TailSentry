"""
DEVELOPER WORKFLOW GUIDE
========================

How to develop features with TailSentry's test & migration infrastructure

TABLE OF CONTENTS
=================
1. Feature Development Workflow
2. Testing Best Practices
3. Database Changes
4. Troubleshooting
5. Code Review Checklist
"""

# Feature Development Workflow

## Standard Workflow: From Idea to Production

```
┌─────────────────────────────────────────────────────┐
│ 1. PLANNING & SETUP                                │
├─────────────────────────────────────────────────────┤
│ • Create feature branch: git checkout -b feat/name │
│ • Plan test cases                                   │
│ • Check if database changes needed                 │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ 2. WRITE TESTS FIRST (TDD)                         │
├─────────────────────────────────────────────────────┤
│ • Create test_*.py file in tests/                  │
│ • Import fixtures: monkeypatch_db, sample_user    │
│ • Write test code that demonstrates desired        │
│   behavior                                          │
│ • Run: pytest tests/test_*.py -v                   │
│ • Expect: FAILED (feature not implemented yet)    │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ 3. IMPLEMENT FEATURE                               │
├─────────────────────────────────────────────────────┤
│ • Write minimal code to pass the test             │
│ • Follow existing code patterns                    │
│ • Add docstrings                                   │
│ • Run: pytest tests/test_*.py -v                   │
│ • Expect: PASSED                                   │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ 4. DATABASE CHANGES (if needed)                    │
├─────────────────────────────────────────────────────┤
│ • If schema changed:                              │
│   - Run: alembic revision -m "Description"        │
│   - Edit migration file: alembic/versions/        │
│   - Test: alembic upgrade head                    │
│   - Test: alembic downgrade -1                    │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ 5. RUN FULL TEST SUITE                            │
├─────────────────────────────────────────────────────┤
│ • Run: pytest tests/ -v                            │
│ • Verify: All tests pass (14/14 for auth, etc.)   │
│ • Check: No regressions                            │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ 6. CODE REVIEW & COMMIT                            │
├─────────────────────────────────────────────────────┤
│ • Commit: git commit -m "feat: description"       │
│ • Push: git push origin feat/name                  │
│ • Create: Pull request                             │
│ • Provide: Test proof in PR                        │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ 7. MERGE & DEPLOY                                  │
├─────────────────────────────────────────────────────┤
│ • Approve: Code review passed                     │
│ • Run: pytest in CI/CD                             │
│ • Deploy: Run migrations on staging first          │
│ • Monitor: Application logs                        │
│ • Verify: Feature works end-to-end                 │
└─────────────────────────────────────────────────────┘
```

## Example: Adding "User Suspension" Feature

### Step 1: Plan Tests
```python
# tests/test_user_suspension.py
def test_suspend_user():
    """User can be suspended and cannot login"""

def test_suspend_user_via_admin():
    """Admin can suspend any user"""

def test_suspended_user_cannot_access_dashboard():
    """Suspended users get denied access"""
```

### Step 2: Write Failing Tests
```bash
$ cd e:\TailSentry
$ python -m pytest tests/test_user_suspension.py -v
# FAILED - functions don't exist yet
```

### Step 3: Implement Feature
```python
# In auth_user.py
def suspend_user(username: str) -> bool:
    """Suspend user account."""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET active = 0 WHERE username = ?', (username,))
    conn.commit()
    result = c.rowcount > 0
    conn.close()
    return result
```

### Step 4: Run Tests (Now Pass!)
```bash
$ python -m pytest tests/test_user_suspension.py -v
# PASSED ✓
```

### Step 5: Create Migration (if schema changed)
```bash
$ alembic revision -m "Add suspension reason column"
# Edit migration and test it works

$ alembic upgrade head
$ alembic downgrade -1  # Verify rollback works
```

### Step 6: Full Test Suite
```bash
$ pytest tests/ -v
# 14 passed (auth) + your new tests
```

### Step 7: Commit & Push
```bash
$ git add .
$ git commit -m "feat: add user suspension feature"
$ git push origin feat/user-suspension
```

---

# Testing Best Practices

## Use Fixtures

✅ **GOOD** - Uses fixtures
```python
def test_user_login(monkeypatch_db, sample_user):
    """Test user can login."""
    import auth_user
    auth_user.create_user(sample_user["username"], sample_user["password"])
    result = auth_user.verify_user(sample_user["username"], sample_user["password"])
    assert result is not None
```

❌ **BAD** - Manual setup
```python
def test_user_login():
    """Test user can login."""
    import sqlite3
    conn = sqlite3.connect("test.db")  # ← Creates new database
    c = conn.cursor()
    c.execute("CREATE TABLE...")       # ← Duplicates fixture setup
    # ... more setup code ...
```

## Test Isolation

✅ **GOOD** - Each test gets fresh database
```python
def test_one(monkeypatch_db, sample_user):
    auth_user.create_user(sample_user["username"], "pass1")
    # Uses fresh test database

def test_two(monkeypatch_db, sample_user):
    auth_user.create_user(sample_user["username"], "pass2")
    # Also gets fresh test database (separate from test_one)
    # No data from test_one leaks here
```

❌ **BAD** - Shared state between tests
```python
# Don't do this - tests will interfere with each other
db_path = "global_test.db"

def test_one():
    auth_user.create_user("user1", "pass1")

def test_two():
    auth_user.create_user("user1", "pass1")  # ← Might fail if user1 already exists
```

## Descriptive Test Names

✅ **GOOD** - Clear what is being tested
```python
def test_create_user_with_valid_credentials():
def test_verify_user_with_wrong_password():
def test_suspend_user_prevents_login():
```

❌ **BAD** - Vague names
```python
def test_1():
def test_user():
def test_works():
```

## Test All States

✅ **GOOD** - Test success AND failure
```python
def test_verify_user_success(monkeypatch_db, sample_user):
    # ✓ Password correct
    
def test_verify_user_wrong_password(monkeypatch_db, sample_user):
    # ✓ Password wrong - should fail
    
def test_verify_nonexistent_user(monkeypatch_db):
    # ✓ User doesn't exist - should fail
    
def test_verify_inactive_user(monkeypatch_db, sample_user):
    # ✓ User inactive - should fail
```

---

# Database Changes

## When You Need a Migration

You need a migration if you:
- Add a column to a table
- Remove a column
- Change a column type
- Add an index
- Change constraints
- Create a new table

You DON'T need a migration if you:
- Change only Python code (routes, services)
- Update only templates or static files
- Modify environment variables

## Creating a Migration

```bash
# 1. Make database schema change (add column, etc.)

# 2. Create migration file
$ alembic revision -m "Add last_login_time column to users"

# 3. Edit alembic/versions/XXX_add_last_login_time_column.py
def upgrade() -> None:
    op.add_column('users', sa.Column('last_login_time', sa.DateTime()))

def downgrade() -> None:
    op.drop_column('users', 'last_login_time')

# 4. Test upgrade
$ alembic upgrade head

# 5. Test downgrade
$ alembic downgrade -1

# 6. Verify upgrade works again
$ alembic upgrade head
```

## Migration Checklist

Before committing a migration:
- [ ] Upgrade script works (`alembic upgrade head`)
- [ ] Downgrade script works (`alembic downgrade -1`)
- [ ] Upgrade works again (`alembic upgrade head`)
- [ ] No data loss during upgrade
- [ ] Indexes created for performance
- [ ] Column constraints match application requirements
- [ ] Migration file has descriptive name
- [ ] Both upgrade() and downgrade() are implemented

---

# Troubleshooting

## Test Fails: "no such table: users"

**Cause**: Database not initialized

**Solution**:
```bash
# Option 1: Use fixture (automatic)
def test_something(monkeypatch_db):  # ← monkeypatch_db initializes DB
    pass

# Option 2: Manual initialization
from database import init_database
init_database()
```

## Test Fails: "UNIQUE constraint failed: users.username"

**Cause**: User data not isolated between tests

**Solution**: Already fixed in conftest.py! Each test gets fresh DB.
```python
@pytest.fixture
def monkeypatch_db(monkeypatch, test_db_path):
    # Creates unique, fresh database for each test
    unique_db_path = os.path.join(test_dir, "test_isolated.db")
```

## Test Times Out

**Cause**: Infinite loop or blocking operation in test

**Solution**: Add timeout
```bash
$ pytest tests/test_file.py -v --timeout=5
```

## Migration Won't Apply

**Check Migration History**:
```bash
$ alembic history
# Shows all migrations

$ alembic current
# Shows current version

$ alembic downgrade -1
# Try reverting previous version

$ alembic upgrade head
# Try again
```

## "SQLite database is locked"

**Cause**: Multiple processes accessing database

**Solution**: Ensure database connections closed
```python
try:
    conn = get_db_connection()
    # Do work
finally:
    conn.close()  # ← Always close connection
```

---

# Code Review Checklist

When reviewing a PR with database changes:

```
✅ Tests
  □ Does the PR include tests?
  □ Do all tests pass?
  □ Is test coverage adequate?
  □ Are tests properly isolated?

✅ Database (if applicable)
  □ Is there a migration file?
  □ Does migration have upgrade/downgrade?
  □ Can you upgrade and downgrade?
  □ Is data preserved during upgrade?
  □ Are indexes created if needed?

✅ Code Quality
  □ Code follows existing patterns?
  □ Error handling adequate?
  □ Docstrings present?
  □ No hardcoded values?
  □ Logging appropriate?

✅ Backward Compatibility
  □ Existing features still work?
  □ Old data can still be accessed?
  □ No breaking changes?

✅ Documentation
  □ Tests document behavior?
  □ Complex code has comments?
  □ Migration has clear purpose?
  □ Docstrings are clear?
```

## Example Code Review Comment

```
✅ Looks good! The test properly isolates the new feature.

Minor suggestions:
1. Add a test for the error case (when user already suspended)
2. Consider adding an index on `suspended_at` for query performance
3. Update docstring to match parameter types

Ready to merge once these are addressed.
```

---

# Quick Command Reference

```bash
# Testing
pytest tests/ -v                     # Run all tests
pytest tests/test_auth.py -v        # Run specific test file
pytest -k test_create -v            # Run tests matching name
pytest tests/test_auth.py::TestUserCreation -v  # Run test class
pytest tests/test_auth.py::TestUserCreation::test_create_user_success -v

# Migrations  
alembic current                     # Show current version
alembic history                     # Show migration history
alembic revision -m "message"       # Create new migration
alembic upgrade head                # Apply all pending
alembic downgrade -1                # Revert previous
alembic downgrade 001_initial       # Revert to specific version

# Database
python -c "from database import init_database; init_database()"
python -c "from auth_user import list_users; print(list_users())"

# Git
git checkout -b feat/feature-name   # Create feature branch
git add .
git commit -m "feat: description"
git push origin feat/feature-name   # Push to GitHub
```

---

# Getting Help

1. **Check existing tests** - Look in `tests/` for similar tests
2. **Read documentation** - See `TESTING_AND_MIGRATIONS.md`
3. **Review fixtures** - Check `tests/conftest.py` for available fixtures
4. **Run with verbose** - `pytest -vv` for detailed output
5. **Check error trace** - pytest provides clear error messages
6. **Ask team** - Slack or GitHub discussions

---

**Good luck with development! The test infrastructure is here to help you ship code with confidence.**
