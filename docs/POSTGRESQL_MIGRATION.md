# PostgreSQL Migration Guide for TailSentry

## Overview

This guide provides step-by-step instructions for migrating TailSentry from SQLite to PostgreSQL. This migration is recommended for deployments with more than 100 concurrent users or when multi-instance deployment is needed.

## Why Migrate to PostgreSQL?

- **Scalability**: Handle more concurrent users
- **Performance**: Better query optimization for complex reports
- **Reliability**: ACID transactions, better crash recovery
- **Multi-instance**: Shared database for load-balanced deployments
- **Backup tools**: Enterprise backup solutions
- **Monitoring**: Better observability and query logging

## Prerequisites

1. PostgreSQL 12+ installed and running
2. `psycopg2` or `asyncpg` Python driver
3. Database admin credentials
4. Backup of your current SQLite database
5. TailSentry stopped during migration

## Step-by-Step Migration

### Step 1: Create PostgreSQL Database

```bash
# Connect to PostgreSQL as admin
sudo -u postgres psql

# Create database and user
CREATE DATABASE tailsentry;
CREATE USER tailsentry_user WITH PASSWORD 'secure_password_here';
ALTER ROLE tailsentry_user SET client_encoding TO 'utf8';
ALTER ROLE tailsentry_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE tailsentry_user SET default_transaction_deferrable TO on;
ALTER ROLE tailsentry_user SET default_transaction_read_committed TO off;

# Grant permissions
GRANT ALL PRIVILEGES ON DATABASE tailsentry TO tailsentry_user;
GRANT CREATE ON SCHEMA public TO tailsentry_user;

# Exit psql
\q
```

### Step 2: Update TailSentry Configuration

Update your `.env` file to use PostgreSQL instead of SQLite:

```bash
# Old SQLite configuration (comment out or remove)
# DATABASE_URL=sqlite:///./data/tailsentry.db

# New PostgreSQL configuration
DATABASE_URL=postgresql://tailsentry_user:secure_password_here@localhost:5432/tailsentry
DATABASE_DRIVER=psycopg2  # or asyncpg for async
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

### Step 3: Export Data from SQLite

Create an export script to migrate data:

```python
# migrate_sqlite_to_postgres.py
import sqlite3
import psycopg2
import json
from pathlib import Path

def migrate_data():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('data/tailsentry.db')
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(
        dbname="tailsentry",
        user="tailsentry_user",
        password="secure_password_here",
        host="localhost"
    )
    pg_cursor = pg_conn.cursor()
    
    # Migrate users table
    sqlite_cursor.execute("SELECT * FROM users")
    users = sqlite_cursor.fetchall()
    
    for user in users:
        pg_cursor.execute('''
            INSERT INTO users 
            (id, username, password_hash, role, created_at, email, active, display_name, activity_log)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', tuple(user))
    
    # Migrate other tables similarly...
    # audit_events, mfa_settings, recovery_codes, etc.
    
    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()
    
    print("Migration complete!")

if __name__ == "__main__":
    migrate_data()
```

Run the migration script:

```bash
python migrate_sqlite_to_postgres.py
```

### Step 4: Update Database Module

Modify `database.py` to support PostgreSQL:

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/tailsentry.db")
DATABASE_DRIVER = os.getenv("DATABASE_DRIVER", "sqlite")

if DATABASE_DRIVER == "postgresql":
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", 20)),
        max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", 40)),
        pool_pre_ping=True,  # Test connections before use
        echo=False
    )
else:
    # SQLite fallback
    engine = create_engine(
        DATABASE_URL,
        connect_args={"timeout": 15},
        check_same_thread=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Step 5: Run Database Migrations with Alembic

```bash
# Initialize alembic if not already done
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial PostgreSQL schema"

# Apply migrations
alembic upgrade head
```

### Step 6: Update requirements.txt

```bash
# Add PostgreSQL drivers
pip install psycopg2-binary  # Or asyncpg if using async
pip install sqlalchemy>=2.0
pip install alembic>=1.13
```

### Step 7: Test Connection

```bash
python -c "from database import get_db; db = next(get_db()); print('Connected to PostgreSQL successfully')"
```

### Step 8: Start TailSentry

```bash
# Restart TailSentry
systemctl restart tailsentry

# Or with Docker
docker-compose -f docker-compose.prod.yml up -d
```

## Verification

After migration, verify everything works:

1. **Check data integrity**:
```sql
-- Connect to PostgreSQL as tailsentry_user
psql -U tailsentry_user -d tailsentry

-- Verify user count
SELECT COUNT(*) FROM users;

-- Verify audit events
SELECT COUNT(*) FROM audit_events;

-- Verify MFA settings
SELECT COUNT(*) FROM mfa_settings;
```

2. **Monitor logs for errors**:
```bash
docker logs tailsentry  # If using Docker
journalctl -u tailsentry -f  # If using systemd
tail -f logs/tailsentry.log  # If bare metal
```

3. **Test key features**:
   - Login
   - Create user
   - View dashboard
   - Export/restore backups
   - Check audit logs
   - Enable MFA

## Performance Tuning (PostgreSQL)

### Connection Pooling

Configure PgBouncer for better connection management:

```bash
# Install PgBouncer
sudo apt-get install pgbouncer

# Edit /etc/pgbouncer/pgbouncer.ini
[databases]
tailsentry = host=localhost port=5432 dbname=tailsentry user=tailsentry_user password=secure_password

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 10

# Start PgBouncer
sudo systemctl start pgbouncer
```

### Index Optimization

Create indexes for better query performance:

```sql
-- Audit log queries
CREATE INDEX idx_audit_timestamp_desc ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_event_type_status ON audit_events(event_type, status);
CREATE INDEX idx_audit_user_timestamp ON audit_events(user_id, timestamp DESC);

-- User queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(active);
CREATE INDEX idx_users_role ON users(role);

-- MFA queries
CREATE INDEX idx_mfa_settings_user_id ON mfa_settings(user_id);
CREATE INDEX idx_mfa_attempts_timestamp ON mfa_attempts(user_id, attempt_timestamp DESC);

-- Recovery codes
CREATE INDEX idx_recovery_codes_user_used ON recovery_codes(user_id, used);
```

### Query Logging

Enable slow query logging:

```sql
-- Edit postgresql.conf
log_min_duration_statement = 1000  -- Log queries slower than 1 second
log_connections = on
log_disconnections = on
log_line_prefix = '%t [%p] %u@%d '

-- Restart PostgreSQL
sudo systemctl restart postgresql
```

### Backup Strategy

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR=/backups/postgres
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

pg_dump -U tailsentry_user -h localhost tailsentry | gzip > $BACKUP_DIR/tailsentry_$TIMESTAMP.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "tailsentry_*.sql.gz" -mtime +30 -delete

# Add to crontab
# 0 2 * * * /path/to/backup_postgres.sh
```

## Rollback Plan

If the migration fails, you can rollback:

1. **Restore SQLite database**:
```bash
# Stop TailSentry
systemctl stop tailsentry

# Restore from backup
cp data/tailsentry.db.backup data/tailsentry.db

# Edit .env to point back to SQLite
DATABASE_URL=sqlite:///./data/tailsentry.db

# Restart
systemctl start tailsentry
```

2. **Keep PostgreSQL database for retry**:
```sql
-- Keep PostgreSQL data intact for next attempt
-- Don't drop database unless migration is successful
```

## Monitoring

Monitor PostgreSQL performance:

```bash
# Check active connections
sudo -u postgres psql -d tailsentry -c "SELECT count(*) FROM pg_stat_activity;"

# Check cache hit ratio
sudo -u postgres psql -d tailsentry -c "
SELECT
    sum(heap_blks_read) as heap_read,
    sum(heap_blks_hit)  as heap_hit,
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
FROM pg_statio_user_tables;"

# Check index usage
sudo -u postgres psql -d tailsentry -c "
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as number_of_scans
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;"
```

## Multi-Instance Deployment

Once on PostgreSQL, you can deploy multiple TailSentry instances:

```yaml
# docker-compose.prod-multi.yml
version: '3.8'

services:
  tailsentry-1:
    image: tailsentry:latest
    environment:
      DATABASE_URL: postgresql://tailsentry_user:password@postgres:5432/tailsentry
      ENVIRONMENT: production
    ports:
      - "8080:8080"
    depends_on:
      - postgres

  tailsentry-2:
    image: tailsentry:latest
    environment:
      DATABASE_URL: postgresql://tailsentry_user:password@postgres:5432/tailsentry
      ENVIRONMENT: production
    ports:
      - "8081:8080"
    depends_on:
      - postgres

  nginx:
    image: nginx:latest
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - tailsentry-1
      - tailsentry-2

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: tailsentry
      POSTGRES_USER: tailsentry_user
      POSTGRES_PASSWORD: secure_password_here
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

## Troubleshooting

### Connection Refused
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check firewall
sudo ufw allow 5432/tcp

# Test connection manually
psql -U tailsentry_user -h localhost -d tailsentry
```

### Performance Issues
```sql
-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM audit_events LIMIT 100;

-- Vacuum database
VACUUM ANALYZE;
```

### Data Integrity
```sql
-- Check for missing data
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM audit_events;
SELECT COUNT(*) FROM mfa_settings;

-- Verify foreign keys
SELECT constraint_name, table_name FROM information_schema.table_constraints
WHERE constraint_type = 'FOREIGN KEY' AND table_name IN ('users', 'mfa_settings', 'recovery_codes');
```

## Support & Resources

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/
- Alembic Migrations: https://alembic.sqlalchemy.org/
- TailSentry GitHub: https://github.com/lolerskatez/TailSentry
