"""Database backup and restore service for TailSentry."""
import os
import json
import gzip
import logging
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger("tailsentry.backup")


class BackupService:
    """Handle database backups and restores."""
    
    def __init__(self, db_path: str = "data/tailsentry.db", backup_dir: str = "data/backups"):
        """Initialize backup service.
        
        Args:
            db_path: Path to the SQLite database
            backup_dir: Directory to store backups
        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(self, description: str = "", compress: bool = True) -> Dict:
        """Create a database backup.
        
        Args:
            description: Optional description of the backup
            compress: Whether to gzip compress the backup
            
        Returns:
            Dict with backup metadata
        """
        try:
            if not self.db_path.exists():
                logger.error(f"Database file not found: {self.db_path}")
                return {"success": False, "error": "Database file not found"}
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"tailsentry_backup_{timestamp}.sql"
            if compress:
                backup_filename += ".gz"
            
            backup_path = self.backup_dir / backup_filename
            
            # Create SQL dump
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Export all data
            sql_dump = ""
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                # Get create statement
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                create_stmt = cursor.fetchone()
                if create_stmt and create_stmt[0]:
                    sql_dump += create_stmt[0] + ";\n"
                
                # Get all rows
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                if rows:
                    # Get column names
                    column_names = [description[0] for description in cursor.description]
                    
                    for row in rows:
                        values = ", ".join(
                            f"'{str(val).replace(chr(39), chr(39)+chr(39))}'" 
                            if val is not None else "NULL" 
                            for val in row
                        )
                        sql_dump += f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({values});\n"
            
            conn.close()
            
            # Write backup file
            if compress:
                with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                    f.write(sql_dump)
            else:
                backup_path.write_text(sql_dump, encoding='utf-8')
            
            backup_info = {
                "success": True,
                "filename": backup_filename,
                "path": str(backup_path),
                "size": backup_path.stat().st_size,
                "timestamp": timestamp,
                "description": description,
                "compressed": compress
            }
            
            logger.info(f"Backup created: {backup_filename} ({backup_info['size']} bytes)")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def restore_backup(self, backup_filename: str) -> Dict:
        """Restore database from a backup.
        
        Args:
            backup_filename: Filename of the backup to restore
            
        Returns:
            Dict with restore status
        """
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return {"success": False, "error": "Backup file not found"}
            
            # Read SQL dump
            if backup_filename.endswith(".gz"):
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    sql_dump = f.read()
            else:
                sql_dump = backup_path.read_text(encoding='utf-8')
            
            # Create backup of current database before restore
            current_backup = self.create_backup(
                description="Auto-backup before restore",
                compress=True
            )
            
            # Restore to database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Execute SQL dump
            cursor.executescript(sql_dump)
            conn.commit()
            conn.close()
            
            logger.info(f"Database restored from: {backup_filename}")
            return {
                "success": True,
                "message": "Database restored successfully",
                "previous_backup": current_backup.get("filename")
            }
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def list_backups(self) -> List[Dict]:
        """List all available backups.
        
        Returns:
            List of backup metadata
        """
        try:
            backups = []
            for backup_file in sorted(self.backup_dir.glob("tailsentry_backup_*.sql*"), reverse=True):
                stat = backup_file.stat()
                backups.append({
                    "filename": backup_file.name,
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "compressed": backup_file.name.endswith(".gz")
                })
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}", exc_info=True)
            return []
    
    def delete_backup(self, backup_filename: str) -> Dict:
        """Delete a backup file.
        
        Args:
            backup_filename: Filename of the backup to delete
            
        Returns:
            Dict with delete status
        """
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                return {"success": False, "error": "Backup file not found"}
            
            # Prevent deletion of the only backup
            backups = self.list_backups()
            if len(backups) <= 1:
                return {"success": False, "error": "Cannot delete the last backup"}
            
            backup_path.unlink()
            logger.info(f"Backup deleted: {backup_filename}")
            return {"success": True, "message": "Backup deleted successfully"}
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def cleanup_old_backups(self, keep_count: int = 10) -> Dict:
        """Delete old backups, keeping only the most recent.
        
        Args:
            keep_count: Number of backups to keep
            
        Returns:
            Dict with cleanup status
        """
        try:
            backups = self.list_backups()
            if len(backups) <= keep_count:
                return {"success": True, "deleted": 0, "message": "No old backups to delete"}
            
            deleted_count = 0
            for backup in backups[keep_count:]:
                backup_path = self.backup_dir / backup["filename"]
                backup_path.unlink()
                deleted_count += 1
            
            logger.info(f"Cleanup: Deleted {deleted_count} old backups")
            return {
                "success": True,
                "deleted": deleted_count,
                "message": f"Deleted {deleted_count} old backups"
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
