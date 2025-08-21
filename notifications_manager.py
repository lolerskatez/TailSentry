"""
TailSentry Notification Integration
Provides easy integration of the notification system throughout the application
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from routes.notifications import notification_service

logger = logging.getLogger("tailsentry.notification_integration")

class NotificationManager:
    """
    Centralized notification manager for sending notifications from anywhere in the application
    """
    
    @staticmethod
    async def notify_system_startup():
        """Send system startup notification"""
        try:
            await notification_service.send_notification(
                "system_startup",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    @staticmethod
    async def notify_system_shutdown():
        """Send system shutdown notification"""
        try:
            await notification_service.send_notification(
                "system_shutdown",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send shutdown notification: {e}")
    
    @staticmethod
    async def notify_tailscale_connection(device_name: str):
        """Send Tailscale connection notification"""
        try:
            await notification_service.send_notification(
                "tailscale_connection",
                device_name=device_name,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send Tailscale connection notification: {e}")
    
    @staticmethod
    async def notify_tailscale_disconnection(device_name: str):
        """Send Tailscale disconnection notification"""
        try:
            await notification_service.send_notification(
                "tailscale_disconnection",
                device_name=device_name,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send Tailscale disconnection notification: {e}")
    
    @staticmethod
    async def notify_peer_online(peer_name: str, peer_ip: str):
        """Send peer online notification"""
        try:
            await notification_service.send_notification(
                "peer_online",
                peer_name=peer_name,
                peer_ip=peer_ip,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send peer online notification: {e}")
    
    @staticmethod
    async def notify_peer_offline(peer_name: str, peer_ip: str):
        """Send peer offline notification"""
        try:
            await notification_service.send_notification(
                "peer_offline",
                peer_name=peer_name,
                peer_ip=peer_ip,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send peer offline notification: {e}")
    
    @staticmethod
    async def notify_subnet_route_change(routes: str):
        """Send subnet route change notification"""
        try:
            await notification_service.send_notification(
                "subnet_route_change",
                routes=routes,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send subnet route change notification: {e}")
    
    @staticmethod
    async def notify_exit_node_change(exit_node: str):
        """Send exit node change notification"""
        try:
            await notification_service.send_notification(
                "exit_node_change",
                exit_node=exit_node,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send exit node change notification: {e}")
    
    @staticmethod
    async def notify_health_check_failure(error_message: str):
        """Send health check failure notification"""
        try:
            await notification_service.send_notification(
                "health_check_failure",
                error_message=error_message,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send health check failure notification: {e}")
    
    @staticmethod
    async def notify_configuration_change(user: str):
        """Send configuration change notification"""
        try:
            await notification_service.send_notification(
                "configuration_change",
                user=user,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send configuration change notification: {e}")
    
    @staticmethod
    async def notify_security_alert(details: str):
        """Send security alert notification"""
        try:
            await notification_service.send_notification(
                "security_alert",
                details=details,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send security alert notification: {e}")
    
    @staticmethod
    async def notify_backup_completed():
        """Send backup completed notification"""
        try:
            await notification_service.send_notification(
                "backup_completed",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send backup completed notification: {e}")
    
    @staticmethod
    async def notify_backup_failed(error: str):
        """Send backup failed notification"""
        try:
            await notification_service.send_notification(
                "backup_failed",
                error=error,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send backup failed notification: {e}")
    
    @staticmethod
    async def notify_custom(event_type: str, **kwargs):
        """Send a custom notification with arbitrary data"""
        try:
            kwargs["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await notification_service.send_notification(event_type, **kwargs)
        except Exception as e:
            logger.error(f"Failed to send custom notification {event_type}: {e}")

# Global notification manager instance
notifications = NotificationManager()

# Helper functions for easy imports
async def notify_system_startup():
    """Helper function for system startup notification"""
    await notifications.notify_system_startup()

async def notify_system_shutdown():
    """Helper function for system shutdown notification"""
    await notifications.notify_system_shutdown()

async def notify_tailscale_connection(device_name: str):
    """Helper function for Tailscale connection notification"""
    await notifications.notify_tailscale_connection(device_name)

async def notify_tailscale_disconnection(device_name: str):
    """Helper function for Tailscale disconnection notification"""
    await notifications.notify_tailscale_disconnection(device_name)

async def notify_configuration_change(user: str):
    """Helper function for configuration change notification"""
    await notifications.notify_configuration_change(user)

async def notify_security_alert(details: str):
    """Helper function for security alert notification"""
    await notifications.notify_security_alert(details)

async def notify_backup_completed():
    """Helper function for backup completed notification"""
    await notifications.notify_backup_completed()

async def notify_backup_failed(error: str):
    """Helper function for backup failed notification"""
    await notifications.notify_backup_failed(error)
