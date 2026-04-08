"""Audit logging service for tracking user actions and system events."""
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger("tailsentry.audit")


class AuditEventType(str, Enum):
    """Types of audit events."""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    USER_MODIFIED = "user_modified"
    ROLE_CHANGED = "role_changed"
    DEVICE_MODIFIED = "device_modified"
    SETTINGS_CHANGED = "settings_changed"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"
    API_CALL = "api_call"
    ERROR = "error"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"


class AuditLogger:
    """Handle audit logging to SQLite database."""
    
    def __init__(self, db_path: str = "data/tailsentry.db"):
        """Initialize audit logger.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = Path(db_path)
        self._init_audit_tables()
    
    def _init_audit_tables(self):
        """Initialize audit logging tables."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create audit_events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    user_id INTEGER,
                    username TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    action TEXT,
                    changes_from TEXT,
                    changes_to TEXT,
                    status TEXT,
                    error_message TEXT,
                    details TEXT
                )
            ''')
            
            # Create indexes for audit queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS ix_audit_timestamp 
                ON audit_events(timestamp DESC)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS ix_audit_event_type 
                ON audit_events(event_type)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS ix_audit_user_id 
                ON audit_events(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS ix_audit_username 
                ON audit_events(username)
            ''')
            
            # Create audit_settings table for audit configuration
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_settings (
                    id INTEGER PRIMARY KEY,
                    retention_days INTEGER DEFAULT 90,
                    enable_detailed_logging INTEGER DEFAULT 1,
                    log_api_calls INTEGER DEFAULT 1,
                    log_failed_auth INTEGER DEFAULT 1,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert default audit settings if not exists
            cursor.execute('SELECT COUNT(*) FROM audit_settings')
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO audit_settings 
                    (retention_days, enable_detailed_logging, log_api_calls, log_failed_auth)
                    VALUES (90, 1, 1, 1)
                ''')
            
            conn.commit()
            conn.close()
            logger.info("Audit tables initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize audit tables: {e}", exc_info=True)
    
    def log_event(self, event_type: AuditEventType, user_id: Optional[int] = None,
                  username: Optional[str] = None, ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None, resource_type: Optional[str] = None,
                  resource_id: Optional[str] = None, action: Optional[str] = None,
                  changes_from: Optional[Dict] = None, changes_to: Optional[Dict] = None,
                  status: str = "success", error_message: Optional[str] = None,
                  details: Optional[Dict] = None) -> bool:
        """Log an audit event.
        
        Args:
            event_type: Type of event
            user_id: ID of the user performing the action
            username: Username of the user
            ip_address: IP address of the request
            user_agent: User agent string
            resource_type: Type of resource being modified
            resource_id: ID of the resource
            action: Specific action performed
            changes_from: Previous values (for modifications)
            changes_to: New values (for modifications)
            status: Status of the action (success/failure)
            error_message: Error message if applicable
            details: Additional details as dict
            
        Returns:
            True if logged successfully
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_events
                (event_type, user_id, username, ip_address, user_agent, 
                 resource_type, resource_id, action, changes_from, changes_to, 
                 status, error_message, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_type.value,
                user_id,
                username,
                ip_address,
                user_agent,
                resource_type,
                resource_id,
                action,
                json.dumps(changes_from) if changes_from else None,
                json.dumps(changes_to) if changes_to else None,
                status,
                error_message,
                json.dumps(details) if details else None
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}", exc_info=True)
            return False
    
    def search_events(self, event_type: Optional[str] = None, username: Optional[str] = None,
                     user_id: Optional[int] = None, resource_type: Optional[str] = None,
                     start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                     limit: int = 100, offset: int = 0, order_by: str = "timestamp DESC") -> List[Dict]:
        """Search audit events with filters.
        
        Args:
            event_type: Filter by event type
            username: Filter by username
            user_id: Filter by user ID
            resource_type: Filter by resource type
            start_date: Filter events from this date onwards
            end_date: Filter events up to this date
            limit: Maximum number of results
            offset: Offset for pagination
            order_by: Order by clause
            
        Returns:
            List of matching audit events
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            if username:
                query += " AND username LIKE ?"
                params.append(f"%{username}%")
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if resource_type:
                query += " AND resource_type = ?"
                params.append(resource_type)
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            events = []
            for row in rows:
                event = dict(row)
                # Parse JSON fields
                if event.get('changes_from'):
                    try:
                        event['changes_from'] = json.loads(event['changes_from'])
                    except:
                        pass
                if event.get('changes_to'):
                    try:
                        event['changes_to'] = json.loads(event['changes_to'])
                    except:
                        pass
                if event.get('details'):
                    try:
                        event['details'] = json.loads(event['details'])
                    except:
                        pass
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to search audit events: {e}", exc_info=True)
            return []
    
    def get_user_activity(self, username: str, days: int = 30) -> List[Dict]:
        """Get activity log for a specific user.
        
        Args:
            username: Username to get activity for
            days: Number of days to look back
            
        Returns:
            List of user activities
        """
        start_date = datetime.now() - timedelta(days=days)
        return self.search_events(username=username, start_date=start_date)
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent audit events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        return self.search_events(limit=limit)
    
    def cleanup_old_events(self, retention_days: int = 90) -> int:
        """Delete audit events older than retention period.
        
        Args:
            retention_days: Number of days to retain
            
        Returns:
            Number of events deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute(
                'DELETE FROM audit_events WHERE timestamp < ?',
                (cutoff_date.isoformat(),)
            )
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted} audit events older than {retention_days} days")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup audit events: {e}", exc_info=True)
            return 0
    
    def export_events(self, filename: str, start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None, format: str = "csv") -> bool:
        """Export audit events to file.
        
        Args:
            filename: Output filename
            start_date: Filter events from this date onwards
            end_date: Filter events up to this date
            format: Export format (csv or json)
            
        Returns:
            True if exported successfully
        """
        try:
            events = self.search_events(start_date=start_date, end_date=end_date, limit=10000)
            
            if format == "json":
                import json
                with open(filename, 'w') as f:
                    json.dump(events, f, indent=2, default=str)
            else:  # CSV
                import csv
                if not events:
                    return True
                
                with open(filename, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=events[0].keys())
                    writer.writeheader()
                    writer.writerows(events)
            
            logger.info(f"Exported {len(events)} audit events to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export audit events: {e}", exc_info=True)
            return False
    
    def get_statistics(self, days: int = 30) -> Dict:
        """Get audit statistics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with statistics
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Total events
            cursor.execute(
                'SELECT COUNT(*) FROM audit_events WHERE timestamp >= ?',
                (start_date.isoformat(),)
            )
            total_events = cursor.fetchone()[0]
            
            # Events by type
            cursor.execute('''
                SELECT event_type, COUNT(*) as count
                FROM audit_events
                WHERE timestamp >= ?
                GROUP BY event_type
            ''', (start_date.isoformat(),))
            events_by_type = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Failed events
            cursor.execute(
                'SELECT COUNT(*) FROM audit_events WHERE timestamp >= ? AND status = ?',
                (start_date.isoformat(), 'failure')
            )
            failed_events = cursor.fetchone()[0]
            
            # Active users
            cursor.execute(
                'SELECT COUNT(DISTINCT username) FROM audit_events WHERE timestamp >= ?',
                (start_date.isoformat(),)
            )
            active_users = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "days_analyzed": days,
                "total_events": total_events,
                "failed_events": failed_events,
                "active_users": active_users,
                "events_by_type": events_by_type
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}", exc_info=True)
            return {}
