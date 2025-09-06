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
    async def notify_user_created(username: str, display_name: str, role: str, created_by: str):
        """Send user creation notification"""
        try:
            await notification_service.send_notification(
                "user_created",
                username=username,
                display_name=display_name,
                role=role,
                created_by=created_by,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send user creation notification: {e}")
    
    @staticmethod
    async def notify_user_login(username: str, ip_address: str):
        """Send user login notification"""
        try:
            await notification_service.send_notification(
                "user_login",
                username=username,
                ip_address=ip_address,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send user login notification: {e}")
    
    @staticmethod
    async def notify_user_login_failed(username: str, ip_address: str):
        """Send failed login notification"""
        try:
            await notification_service.send_notification(
                "user_login_failed",
                username=username,
                ip_address=ip_address,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send failed login notification: {e}")
    
    @staticmethod
    async def notify_user_password_changed(username: str):
        """Send password change notification"""
        try:
            await notification_service.send_notification(
                "user_password_changed",
                username=username,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send password change notification: {e}")
    
    @staticmethod
    async def notify_user_deleted(username: str, display_name: str, deleted_by: str):
        """Send user deletion notification"""
        try:
            await notification_service.send_notification(
                "user_deleted",
                username=username,
                display_name=display_name,
                deleted_by=deleted_by,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send user deletion notification: {e}")
    
    @staticmethod
    async def notify_user_role_changed(username: str, old_role: str, new_role: str, changed_by: str):
        """Send user role change notification"""
        try:
            await notification_service.send_notification(
                "user_role_changed",
                username=username,
                old_role=old_role,
                new_role=new_role,
                changed_by=changed_by,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send user role change notification: {e}")
    
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
    async def notify_new_device_detected(device_name: str, device_id: str, os: str, ip_address: str):
        """Send new device detected notification"""
        try:
            await notification_service.send_notification(
                "new_device_detected",
                device_name=device_name,
                device_id=device_id,
                os=os,
                ip_address=ip_address,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send new device notification: {e}")
    
    @staticmethod
    async def notify_high_cpu_usage(cpu_percentage: float, threshold: float, duration: str, hostname: str):
        """Send high CPU usage notification"""
        try:
            await notification_service.send_notification(
                "high_cpu_usage",
                cpu_percentage=cpu_percentage,
                threshold=threshold,
                duration=duration,
                hostname=hostname,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send high CPU usage notification: {e}")
    
    @staticmethod
    async def notify_high_memory_usage(memory_percentage: float, threshold: float, memory_used: str, memory_total: str, hostname: str):
        """Send high memory usage notification"""
        try:
            await notification_service.send_notification(
                "high_memory_usage",
                memory_percentage=memory_percentage,
                threshold=threshold,
                memory_used=memory_used,
                memory_total=memory_total,
                hostname=hostname,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send high memory usage notification: {e}")
    
    @staticmethod
    async def notify_disk_space_low(disk_path: str, disk_used: str, disk_total: str, disk_percentage: float, disk_free: str):
        """Send low disk space notification"""
        try:
            await notification_service.send_notification(
                "disk_space_low",
                disk_path=disk_path,
                disk_used=disk_used,
                disk_total=disk_total,
                disk_percentage=disk_percentage,
                disk_free=disk_free,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send disk space notification: {e}")
    
    @staticmethod
    async def notify_certificate_expiring(domain: str, days_remaining: int, expiry_date: str):
        """Send certificate expiring notification"""
        try:
            await notification_service.send_notification(
                "certificate_expiring",
                domain=domain,
                days_remaining=days_remaining,
                expiry_date=expiry_date,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send certificate expiring notification: {e}")
    
    @staticmethod
    async def notify_suspicious_activity(activity_type: str, source_ip: str, details: str):
        """Send suspicious activity notification"""
        try:
            await notification_service.send_notification(
                "suspicious_activity",
                activity_type=activity_type,
                source_ip=source_ip,
                details=details,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send suspicious activity notification: {e}")
    
    @staticmethod
    async def notify_multiple_failed_logins(username: str, source_ip: str, attempt_count: int, time_window: str):
        """Send multiple failed logins notification"""
        try:
            await notification_service.send_notification(
                "multiple_failed_logins",
                username=username,
                source_ip=source_ip,
                attempt_count=attempt_count,
                time_window=time_window,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send multiple failed logins notification: {e}")
    
    @staticmethod
    async def notify_service_failure(service_name: str, error_message: str, last_success: str, restart_attempts: int):
        """Send service failure notification"""
        try:
            await notification_service.send_notification(
                "service_failure",
                service_name=service_name,
                error_message=error_message,
                last_success=last_success,
                restart_attempts=restart_attempts,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send service failure notification: {e}")
    
    @staticmethod
    async def notify_discord_bot_connected(bot_name: str, guild_count: int, command_count: int):
        """Send Discord bot connected notification"""
        try:
            await notification_service.send_notification(
                "discord_bot_connected",
                bot_name=bot_name,
                guild_count=guild_count,
                command_count=command_count,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send Discord bot connected notification: {e}")
    
    @staticmethod
    async def notify_discord_bot_disconnected(bot_name: str, disconnect_reason: str, uptime: str, auto_reconnect: bool):
        """Send Discord bot disconnected notification"""
        try:
            await notification_service.send_notification(
                "discord_bot_disconnected",
                bot_name=bot_name,
                disconnect_reason=disconnect_reason,
                uptime=uptime,
                auto_reconnect=auto_reconnect,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send Discord bot disconnected notification: {e}")
    
    @staticmethod
    async def notify_device_key_expiring(device_name: str, days_remaining: int, expiry_date: str):
        """Send device key expiring notification"""
        try:
            await notification_service.send_notification(
                "device_key_expiring",
                device_name=device_name,
                days_remaining=days_remaining,
                expiry_date=expiry_date,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send device key expiring notification: {e}")
    
    @staticmethod
    async def notify_tailscale_update_available(new_version: str, current_version: str):
        """Send Tailscale update available notification"""
        try:
            await notification_service.send_notification(
                "tailscale_update_available",
                new_version=new_version,
                current_version=current_version,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send Tailscale update notification: {e}")
    
    @staticmethod
    async def notify_update_available(new_version: str, current_version: str, changelog_url: str):
        """Send TailSentry update available notification"""
        try:
            await notification_service.send_notification(
                "update_available",
                new_version=new_version,
                current_version=current_version,
                changelog_url=changelog_url,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send update available notification: {e}")
    
    @staticmethod
    async def notify_database_backup(backup_file: str, backup_size: str, duration: str):
        """Send database backup notification"""
        try:
            await notification_service.send_notification(
                "database_backup",
                backup_file=backup_file,
                backup_size=backup_size,
                duration=duration,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send database backup notification: {e}")
    
    @staticmethod
    async def notify_webhook_failure(webhook_url: str, status_code: int, error_message: str, retry_count: int):
        """Send webhook failure notification"""
        try:
            await notification_service.send_notification(
                "webhook_failure",
                webhook_url=webhook_url,
                status_code=status_code,
                error_message=error_message,
                retry_count=retry_count,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send webhook failure notification: {e}")
    
    @staticmethod
    async def notify_security_settings_changed(user: str):
        """Send security settings change notification"""
        try:
            await notification_service.send_notification(
                "security_settings_changed",
                user=user,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            logger.error(f"Failed to send security settings change notification: {e}")
    
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

async def notify_user_created(username: str, display_name: str, role: str, created_by: str):
    """Helper function for user creation notification"""
    await notifications.notify_user_created(username, display_name, role, created_by)

async def notify_user_login(username: str, ip_address: str):
    """Helper function for user login notification"""
    await notifications.notify_user_login(username, ip_address)

async def notify_user_login_failed(username: str, ip_address: str):
    """Helper function for failed login notification"""
    await notifications.notify_user_login_failed(username, ip_address)

async def notify_user_password_changed(username: str):
    """Helper function for password change notification"""
    await notifications.notify_user_password_changed(username)

async def notify_user_deleted(username: str, display_name: str, deleted_by: str):
    """Helper function for user deletion notification"""
    await notifications.notify_user_deleted(username, display_name, deleted_by)

async def notify_user_role_changed(username: str, old_role: str, new_role: str, changed_by: str):
    """Helper function for user role change notification"""
    await notifications.notify_user_role_changed(username, old_role, new_role, changed_by)

async def notify_security_settings_changed(user: str):
    """Helper function for security settings change notification"""
    await notifications.notify_security_settings_changed(user)
