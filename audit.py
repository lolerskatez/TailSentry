"""Audit logging for security-relevant events."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional
import json
import os
from pathlib import Path

# Configure audit logger
audit_logger = logging.getLogger("tailsentry.audit")
audit_logger.setLevel(logging.INFO)

# Set up audit log file
AUDIT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
AUDIT_LOG_DIR.mkdir(exist_ok=True)

audit_handler = logging.FileHandler(AUDIT_LOG_DIR / "audit.log")
audit_handler.setFormatter(
    logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
)
audit_logger.addHandler(audit_handler)

def log_audit_event(
    event_type: str,
    user: str,
    action: str,
    resource: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> None:
    """Log an audit event.
    
    Args:
        event_type: Type of event (auth, admin, system, etc.)
        user: Username or system identifier
        action: Action being performed
        resource: Resource being acted upon
        status: Outcome status (success, failure, error)
        details: Additional event details
        ip_address: Source IP address
    """
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "user": user,
        "action": action,
        "resource": resource,
        "status": status,
        "ip_address": ip_address,
        "details": details or {}
    }
    
    # Log the event
    audit_logger.info(json.dumps(event))

# Example usage:
# log_audit_event(
#     event_type="auth",
#     user="admin",
#     action="login",
#     resource="web_ui",
#     status="success",
#     ip_address="192.168.1.100"
# )
