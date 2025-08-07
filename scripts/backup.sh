#!/bin/bash
# Automated backup script for TailSentry

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/tailsentry/backups}"
TAILSENTRY_DIR="${TAILSENTRY_DIR:-/opt/tailsentry}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"
LOG_FILE="${LOG_FILE:-/var/log/tailsentry-backup.log}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

create_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="tailsentry-backup-$timestamp"
    local backup_path="$BACKUP_DIR/$backup_name.tar.gz"
    
    log "📦 Creating backup: $backup_name"
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Create compressed backup
    tar -czf "$backup_path" \
        -C "$TAILSENTRY_DIR" \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='logs/*.log' \
        . || {
        log "❌ Failed to create backup"
        return 1
    }
    
    log "✅ Backup created: $backup_path"
    log "📊 Backup size: $(du -h "$backup_path" | cut -f1)"
    
    echo "$backup_path"
}

upload_to_s3() {
    local backup_path="$1"
    local backup_name=$(basename "$backup_path")
    
    if [ -z "$S3_BUCKET" ]; then
        log "ℹ️  S3_BUCKET not configured, skipping upload"
        return 0
    fi
    
    if ! command -v aws >/dev/null 2>&1; then
        log "⚠️  AWS CLI not installed, skipping S3 upload"
        return 0
    fi
    
    log "☁️  Uploading backup to S3: s3://$S3_BUCKET/$backup_name"
    
    if aws s3 cp "$backup_path" "s3://$S3_BUCKET/$backup_name"; then
        log "✅ Backup uploaded to S3 successfully"
    else
        log "❌ Failed to upload backup to S3"
        return 1
    fi
}

cleanup_old_backups() {
    log "🧹 Cleaning up backups older than $RETENTION_DAYS days"
    
    # Remove local backups older than retention period
    find "$BACKUP_DIR" -name "tailsentry-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete
    
    # Clean up S3 backups if configured
    if [ -n "$S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
        local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
        
        aws s3 ls "s3://$S3_BUCKET/" | grep "tailsentry-backup-" | while read -r line; do
            local file_date=$(echo "$line" | grep -o '[0-9]\{8\}_[0-9]\{6\}' | cut -d'_' -f1)
            if [ "$file_date" -lt "$cutoff_date" ]; then
                local file_name=$(echo "$line" | awk '{print $4}')
                log "🗑️  Removing old S3 backup: $file_name"
                aws s3 rm "s3://$S3_BUCKET/$file_name"
            fi
        done
    fi
    
    log "✅ Cleanup completed"
}

verify_backup() {
    local backup_path="$1"
    
    log "🔍 Verifying backup integrity"
    
    if tar -tzf "$backup_path" >/dev/null 2>&1; then
        log "✅ Backup integrity verified"
        return 0
    else
        log "❌ Backup verification failed"
        return 1
    fi
}

main() {
    log "🚀 Starting TailSentry backup process"
    
    # Create backup
    if backup_path=$(create_backup); then
        # Verify backup
        if verify_backup "$backup_path"; then
            # Upload to S3 if configured
            upload_to_s3 "$backup_path"
            
            # Cleanup old backups
            cleanup_old_backups
            
            log "✅ Backup process completed successfully"
        else
            log "❌ Backup verification failed, removing corrupt backup"
            rm -f "$backup_path"
            exit 1
        fi
    else
        log "❌ Backup creation failed"
        exit 1
    fi
}

# Run main function
main "$@"
