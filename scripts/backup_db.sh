#!/bin/bash
# TailSentry Database Backup Script
# Automated backup of SQLite database with integrity checking
# Usage: ./backup_db.sh [backup_dir] [retention_days]

set -e

# Configuration with defaults
DB_PATH="${DB_PATH:-$(pwd)/users.db}"
BACKUP_DIR="${1:-.}/backups"
RETENTION_DAYS="${2:-30}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure database exists
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}❌ ERROR: Database not found at $DB_PATH${NC}" >&2
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/users.db.backup-$TIMESTAMP"

echo -e "${YELLOW}📊 Starting TailSentry database backup...${NC}"
echo "Database: $DB_PATH"
echo "Backup location: $BACKUP_FILE"
echo ""

# Copy database
if ! cp "$DB_PATH" "$BACKUP_FILE" 2>/dev/null; then
    echo -e "${RED}❌ ERROR: Failed to create backup${NC}" >&2
    exit 1
fi

echo -e "${GREEN}✓ Backup file created${NC}"

# Verify backup integrity
echo -n "Verifying backup integrity... "
if ! sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
    echo -e "${RED}❌ FAILED${NC}"
    rm -f "$BACKUP_FILE"
    echo -e "${RED}❌ ERROR: Backup verification failed - backup deleted${NC}" >&2
    exit 1
fi
echo -e "${GREEN}✓ PASSED${NC}"

# Get backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup size: $BACKUP_SIZE"
echo ""

# Clean old backups
echo "Cleaning backups older than $RETENTION_DAYS days..."
OLD_COUNT=$(find "$BACKUP_DIR" -name "users.db.backup-*" -mtime +$RETENTION_DAYS | wc -l)

if [ $OLD_COUNT -gt 0 ]; then
    find "$BACKUP_DIR" -name "users.db.backup-*" -mtime +$RETENTION_DAYS -delete
    echo -e "${GREEN}✓ Deleted $OLD_COUNT old backup(s)${NC}"
else
    echo "No old backups to delete"
fi

# Count remaining backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "users.db.backup-*" | wc -l)
echo "Active backups: $BACKUP_COUNT"

echo ""
echo -e "${GREEN}✅ Backup completed successfully${NC}"
echo "Location: $BACKUP_FILE"
