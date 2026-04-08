"""
Enhanced Device Notifications Service
Separate module for monitoring Tailscale devices and sending Discord notifications
Can be imported independently from the Discord bot service
"""

import asyncio
import logging
import time
from typing import Dict, Set, Optional
from datetime import datetime

logger = logging.getLogger("tailsentry.device_notifications")

class DeviceNotificationService:
    """
    Service to monitor for new devices on the Tailnet and send Discord notifications
    This is a standalone service that can work independently or be integrated with the main app
    """
    
    def __init__(self, discord_bot=None, check_interval: int = 300):
        """
        Initialize the device notification service
        
        Args:
            discord_bot: Optional TailSentryDiscordBot instance for sending notifications
            check_interval: How often to check for new devices (seconds, default 5 minutes)
        """
        self.discord_bot = discord_bot
        self.check_interval = check_interval
        self.known_devices = set()
        self.running = False
        self._task = None
        logger.info(f"Device notification service initialized (check interval: {check_interval}s)")

    async def start_monitoring(self):
        """Start monitoring for new devices"""
        if self.running:
            logger.warning("Device monitoring already running")
            return
            
        self.running = True
        logger.info("Starting device notification monitoring...")
        
        # Initialize with current devices
        await self._initialize_known_devices()
        
        # Start monitoring loop
        self._task = asyncio.create_task(self._monitoring_loop())
        
    async def stop_monitoring(self):
        """Stop device monitoring"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Device monitoring stopped")

    async def _initialize_known_devices(self):
        """Initialize the set of known devices"""
        try:
            devices = await self._get_tailscale_devices()
            if devices:
                self.known_devices = set(device.get('id') for device in devices if device.get('id'))
                logger.info(f"Initialized with {len(self.known_devices)} known devices")
            else:
                logger.warning("Could not initialize known devices - no devices found")
        except Exception as e:
            logger.error(f"Failed to initialize known devices: {e}")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_for_new_devices()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait a bit before retrying

    async def _check_for_new_devices(self):
        """Check for new devices and send notifications"""
        try:
            current_devices = await self._get_tailscale_devices()
            if not current_devices:
                logger.debug("No devices found during check")
                return

            current_device_ids = set(device.get('id') for device in current_devices if device.get('id'))
            new_device_ids = current_device_ids - self.known_devices

            for new_device_id in new_device_ids:
                # Find the full device info
                device = next((d for d in current_devices if d.get('id') == new_device_id), None)
                if device:
                    logger.info(f"New device detected: {device.get('name', 'Unknown')} ({new_device_id})")
                    await self._send_new_device_notification(device)

            # Update known devices
            self.known_devices = current_device_ids

        except Exception as e:
            logger.error(f"Error checking for new devices: {e}")

    async def _get_tailscale_devices(self):
        """Get current Tailscale devices (with fallback handling)"""
        try:
            # Try to import TailscaleService
            from services.tailscale_service import TailscaleService
            
            service = TailscaleService()
            devices = await service.get_devices()
            return devices if devices else []
            
        except ImportError:
            logger.warning("TailscaleService not available - using mock data for testing")
            # Return mock data for testing when TailscaleService isn't available
            return [
                {
                    'id': 'mock_device_1',
                    'name': 'test-device-1',
                    'addresses': ['100.64.0.1'],
                    'os': 'linux',
                    'created': datetime.utcnow().isoformat(),
                    'lastSeen': datetime.utcnow().isoformat()
                }
            ]
        except Exception as e:
            logger.error(f"Failed to get Tailscale devices: {e}")
            return []

    async def _send_new_device_notification(self, device: dict):
        """Send Discord notification for new device"""
        if not self.discord_bot:
            logger.info(f"No Discord bot configured - would notify about new device: {device.get('name')}")
            return

        try:
            # Try to import Discord for embedding
            try:
                import discord
                DISCORD_AVAILABLE = True
            except ImportError:
                DISCORD_AVAILABLE = False
                logger.warning("Discord.py not available - sending text notification")

            if DISCORD_AVAILABLE:
                # Create rich embed
                embed = discord.Embed(
                    title="🖥️ New Device Joined Tailnet",
                    color=0x00ff00,  # Green color
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(name="Device Name", value=device.get('name', 'Unknown'), inline=True)
                embed.add_field(name="Device ID", value=device.get('id', 'Unknown'), inline=True)
                embed.add_field(name="OS", value=device.get('os', 'Unknown'), inline=True)
                
                if device.get('addresses'):
                    embed.add_field(name="IP Address", value=', '.join(device.get('addresses')), inline=False)
                
                if device.get('created'):
                    embed.add_field(name="First Seen", value=device.get('created'), inline=True)
                
                embed.set_footer(text="TailSentry Device Monitor")
                
                await self._send_discord_embed(embed)
            else:
                # Send text message
                message = f"🖥️ **New Device Joined Tailnet**\n"
                message += f"**Name:** {device.get('name', 'Unknown')}\n"
                message += f"**ID:** {device.get('id', 'Unknown')}\n"
                message += f"**OS:** {device.get('os', 'Unknown')}\n"
                if device.get('addresses'):
                    message += f"**IP:** {', '.join(device.get('addresses'))}\n"
                
                await self._send_discord_message(message)
                
        except Exception as e:
            logger.error(f"Failed to send new device notification: {e}")

    async def _send_discord_embed(self, embed):
        """Send Discord embed to appropriate channels"""
        try:
            if hasattr(self.discord_bot, 'log_channel_id') and self.discord_bot.log_channel_id:
                # Send to specific channel
                try:
                    channel = self.discord_bot.bot.get_channel(int(self.discord_bot.log_channel_id))
                    if channel:
                        await channel.send(embed=embed)
                        logger.info(f"Sent new device notification to channel {self.discord_bot.log_channel_id}")
                    else:
                        logger.warning(f"Could not find channel {self.discord_bot.log_channel_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to specific channel: {e}")
            else:
                # Send to all channels where bot has permission
                await self._broadcast_to_available_channels(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to send Discord embed: {e}")

    async def _send_discord_message(self, message: str):
        """Send Discord text message to appropriate channels"""
        try:
            if hasattr(self.discord_bot, 'log_channel_id') and self.discord_bot.log_channel_id:
                # Send to specific channel
                try:
                    channel = self.discord_bot.bot.get_channel(int(self.discord_bot.log_channel_id))
                    if channel:
                        await channel.send(message)
                        logger.info(f"Sent new device message to channel {self.discord_bot.log_channel_id}")
                    else:
                        logger.warning(f"Could not find channel {self.discord_bot.log_channel_id}")
                except Exception as e:
                    logger.error(f"Failed to send message to specific channel: {e}")
            else:
                # Send to all channels where bot has permission
                await self._broadcast_to_available_channels(content=message)
            
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")

    async def _broadcast_to_available_channels(self, embed=None, content=None):
        """Broadcast message to all available channels"""
        try:
            if not hasattr(self.discord_bot, 'bot'):
                logger.error("Discord bot not properly initialized")
                return

            sent_count = 0
            for guild in self.discord_bot.bot.guilds:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        try:
                            if embed:
                                await channel.send(embed=embed)
                            elif content:
                                await channel.send(content)
                            
                            logger.info(f"Sent notification to {guild.name}#{channel.name}")
                            sent_count += 1
                            break  # Only send to first available channel per guild
                        except Exception as e:
                            logger.debug(f"Could not send to {guild.name}#{channel.name}: {e}")
                            continue

            if sent_count == 0:
                logger.warning("Could not send notification to any channels")
            else:
                logger.info(f"Sent notifications to {sent_count} channels")
                
        except Exception as e:
            logger.error(f"Failed to broadcast to channels: {e}")

    async def check_device_now(self):
        """Manually trigger a device check (useful for testing)"""
        logger.info("Manual device check triggered")
        await self._check_for_new_devices()

    def get_status(self) -> dict:
        """Get service status"""
        return {
            "running": self.running,
            "known_devices_count": len(self.known_devices),
            "check_interval": self.check_interval,
            "discord_configured": self.discord_bot is not None
        }

# Standalone function to create and start the service
async def start_device_monitoring(discord_bot=None, check_interval: int = 300):
    """
    Convenience function to start device monitoring
    
    Args:
        discord_bot: Optional Discord bot instance
        check_interval: Check interval in seconds
        
    Returns:
        DeviceNotificationService instance
    """
    service = DeviceNotificationService(discord_bot, check_interval)
    await service.start_monitoring()
    return service
