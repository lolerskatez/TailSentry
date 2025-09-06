"""
Device Notification Service for TailSentry
Monitors Tailscale network for new devices and sends Discord notifications
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set
import discord

logger = logging.getLogger("tailsentry.device_notifications")

class DeviceNotificationService:
    """Service to monitor for new devices and send Discord notifications"""
    
    def __init__(self, discord_bot, check_interval: int = 300):
        self.discord_bot = discord_bot
        self.check_interval = check_interval  # Check every 5 minutes by default
        self.known_devices: Set[str] = set()
        self.running = False
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
        while self.running:
            try:
                await self._check_for_new_devices()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in device monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _initialize_known_devices(self):
        """Initialize the set of known devices"""
        try:
            devices = await self._get_tailscale_devices()
            self.known_devices = {device.get('nodeId') for device in devices if device.get('nodeId')}
            logger.info(f"Initialized with {len(self.known_devices)} known devices")
        except Exception as e:
            logger.error(f"Failed to initialize known devices: {e}")

    async def _get_tailscale_devices(self):
        """Get Tailscale devices using the TailscaleService"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            
            from services.tailscale_service import TailscaleService
            
            service = TailscaleService()
            # Use the existing method to get devices
            devices_data = service.get_devices()
            return devices_data if devices_data else []
        except Exception as e:
            logger.error(f"Failed to get Tailscale devices: {e}")
            return []

    async def _check_for_new_devices(self):
        """Check for new devices and send notifications"""
        try:
            current_devices = await self._get_tailscale_devices()
            current_device_ids = {device.get('nodeId') for device in current_devices if device.get('nodeId')}
            
            # Find new devices
            new_device_ids = current_device_ids - self.known_devices
            
            if new_device_ids:
                logger.info(f"Found {len(new_device_ids)} new devices")
                
                # Send notification for each new device
                for device_id in new_device_ids:
                    device = next((d for d in current_devices if d.get('nodeId') == device_id), None)
                    if device:
                        await self._send_new_device_notification(device)
                
                # Update known devices
                self.known_devices = current_device_ids
                
        except Exception as e:
            logger.error(f"Error checking for new devices: {e}")

    async def _send_new_device_notification(self, device: Dict):
        """Send Discord notification for new device"""
        try:
            # Create notification embed
            embed = discord.Embed(
                title="🆕 New Device Detected!",
                description=f"A new device has joined your Tailscale network",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            # Device details
            embed.add_field(name="Device Name", value=device.get('name', 'Unknown'), inline=True)
            embed.add_field(name="Operating System", value=device.get('os', 'Unknown'), inline=True)
            embed.add_field(name="Status", value="🟢 Online" if device.get('online', False) else "🔴 Offline", inline=True)
            
            # Network info
            addresses = device.get('addresses', [])
            if addresses:
                embed.add_field(name="IP Address", value=addresses[0], inline=True)
            
            embed.add_field(name="Node ID", value=device.get('nodeId', 'Unknown'), inline=True)
            embed.add_field(name="First Seen", value=device.get('created', 'Unknown'), inline=True)
            
            # Tags if any
            if device.get('tags'):
                embed.add_field(name="Tags", value=", ".join(device['tags']), inline=False)
            
            embed.set_footer(text="TailSentry Device Monitor")
            
            # Send notification to configured channel or all channels
            if hasattr(self.discord_bot, 'log_channel_id') and self.discord_bot.log_channel_id:
                try:
                    channel = self.discord_bot.bot.get_channel(int(self.discord_bot.log_channel_id))
                    if channel:
                        await channel.send(embed=embed)
                        logger.info(f"Sent new device notification for {device.get('name')} to channel {self.discord_bot.log_channel_id}")
                    else:
                        logger.warning(f"Could not find channel {self.discord_bot.log_channel_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to specific channel: {e}")
            else:
                # Send to all channels where bot has permission
                for guild in self.discord_bot.bot.guilds:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            try:
                                await channel.send(embed=embed)
                                logger.info(f"Sent new device notification for {device.get('name')} to {guild.name}#{channel.name}")
                                break  # Only send to first available channel per guild
                            except Exception as e:
                                logger.debug(f"Could not send to {guild.name}#{channel.name}: {e}")
                                continue
            
        except Exception as e:
            logger.error(f"Failed to send new device notification: {e}")

    def stop_monitoring(self):
        """Stop device monitoring"""
        self.running = False
        logger.info("Device monitoring stopped")
