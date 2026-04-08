#!/bin/bash
# TailSentry Database Validation Script
# Performs integrity checks on main database and backups
# Usage: ./validate_db.sh [db_path] [backup_dir]

# Configuration with defaults
DB_PATH="${1:-.}/users.db"
BACKUP_DIR="${2:-.}/backups"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 TailSentry Database Validation Report${NC}"
echo "$(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# Flag for overall status
PASS=true

# Check main database
echo -e "${YELLOW}📊 Main Database: $DB_PATH${NC}"
if [ -f "$DB_PATH" ]; then
    SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo "Size: $SIZE"
    
    # Check integrity
    echo -n "Integrity check: "
    INTEGRITY=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>/dev/null || echo "ERROR")
    
    if [ "$INTEGRITY" = "ok" ]; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "Details: $INTEGRITY"
        PASS=false
    fi
    
    # Get record counts
    echo -n "Database structure: "
    TABLES=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
    echo "$TABLES tables"
else
    echo -e "${RED}❌ Database file not found!${NC}"
    PASS=false
fi

echo ""

# Check backups
echo -e "${YELLOW}📂 Backups Directory: $BACKUP_DIR${NC}"
if [ -d "$BACKUP_DIR" ]; then
    BACKUP_COUNT=$(find "$BACKUP_DIR" -name "users.db.backup-*" | wc -l)
    echo "Total backups: $BACKUP_COUNT"
    
    if [ $BACKUP_COUNT -eq 0 ]; then
        echo -e "${RED}⚠️  NO BACKUPS FOUND${NC}"
        PASS=false
    else
        # Display recent backups
        echo ""
        echo -e "${YELLOW}📋 Recent Backups:${NC}"
        ls -lh "$BACKUP_DIR"/users.db.backup-* 2>/dev/null | awk '{print $5, $9}' | tail -5 | while read size file; do
            # Extract filename for display
            filename=$(basename "$file")
            echo "  $size - $filename"
            
            # Check integrity of backup
            INTEGRITY=$(sqlite3 "$file" "PRAGMA integrity_check;" 2>/dev/null || echo "ERROR")
            if [ "$INTEGRITY" = "ok" ]; then
                echo "    └─ ${GREEN}✓ valid${NC}"
            else
                echo "    └─ ${RED}✗ CORRUPTED${NC}"
            fi
        done
        
        # Check backup age
        echo ""
        OLDEST=$(find "$BACKUP_DIR" -name "users.db.backup-*" -printf '%T@ %p\n' 2>/dev/null | sort -n | head -1 | cut -d' ' -f2-)
        if [ -n "$OLDEST" ]; then
            OLDEST_TIME=$(stat -c %Y "$OLDEST")
            NOW=$(date +%s)
            OLDEST_AGE=$(( ($NOW - $OLDEST_TIME) / 86400 ))
            
            if [ $OLDEST_AGE -gt 7 ]; then
                echo -e "${YELLOW}⚠️  Oldest backup age: $OLDEST_AGE days (>7 days)${NC}"
            else
                echo -e "${GREEN}✓ Oldest backup age: $OLDEST_AGE days${NC}"
            fi
        fi
    fi
else
    echo -e "${RED}❌ Backup directory not found: $BACKUP_DIR${NC}"
    PASS=false
fi

echo ""

# Summary
echo "============================================"
if [ "$PASS" = true ]; then
    echo -e "${GREEN}✅ All checks PASSED${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks FAILED${NC}"
    exit 1
fi
