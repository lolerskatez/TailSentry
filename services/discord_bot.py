"""
TailSentry Discord Bot Service
Handles Discord bot integration for interactive commands and log retrieval
Enhanced with security features: log sanitization, access control, and audit logging
"""

import logging
import os
import asyncio
import time
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import re

logger = logging.getLogger("tailsentry.discord_bot")

try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    logger.warning("Discord.py not available - Discord bot features disabled")

# Import security modules
from .log_sanitizer import LogSanitizer
from .discord_access_control import DiscordAccessControl

class TailSentryDiscordBot:
    """
    Discord bot for TailSentry that can receive commands and provide logs
    """

    def __init__(self, token: str, log_file_path: str, allowed_users: Optional[List[str]] = None, 
                 command_prefix: str = "!", log_channel_id: Optional[str] = None, 
                 status_channel_id: Optional[str] = None):
        """
        Initialize the Discord bot

        Args:
            token: Discord bot token
            log_file_path: Path to the log file
            allowed_users: List of Discord usernames/user IDs allowed to use commands (None = allow all)
            command_prefix: Command prefix for the bot
            log_channel_id: Channel ID for log notifications
            status_channel_id: Channel ID for status updates
        """
        self.token = token
        self.log_file_path = log_file_path
        self.allowed_users = allowed_users or []
        self.command_prefix = command_prefix
        self.log_channel_id = log_channel_id
        self.status_channel_id = status_channel_id
        
        # Initialize security components
        self.log_sanitizer = LogSanitizer()
        self.access_control = DiscordAccessControl(
            allowed_user_ids=allowed_users,
            rate_limit_per_minute=10,  # 10 commands per minute per user
            max_failed_attempts=5      # Block after 5 failed attempts
        )

        # Create bot with minimal intents to avoid privileged intent requirements
        intents = discord.Intents.none()
        intents.messages = True
        intents.guilds = True
        # Note: message_content intent is now privileged and requires special approval
        # We'll use slash commands instead which don't require message content access
        
        # Set default permissions for the bot
        default_permissions = discord.Permissions(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )
        
        self.bot = commands.Bot(
            command_prefix=command_prefix, 
            intents=intents, 
            help_command=None,
            default_permissions=default_permissions
        )

        # Register slash commands
        self._register_slash_commands()
        self._register_events()

    def _register_events(self):
        """Register bot events"""

        @self.bot.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {self.bot.user}")
            logger.info(f"Bot ID: {self.bot.user.id}")
            logger.info(f"Connected to {len(self.bot.guilds)} guilds")
            await self.bot.change_presence(activity=discord.Game(name="Monitoring TailSentry"))
            # Sync slash commands
            try:
                logger.info("Attempting to sync slash commands...")
                synced = await self.bot.tree.sync()
                logger.info(f"Synced {len(synced)} slash commands")
                for cmd in synced:
                    logger.info(f"Registered command: /{cmd.name} - {cmd.description}")
                
                # Start cleanup task for access control
                self.bot.loop.create_task(self._cleanup_task())
                
            except Exception as e:
                logger.error(f"Failed to sync slash commands: {e}")
                logger.error(f"Error details: {type(e).__name__}: {str(e)}")

    async def _cleanup_task(self):
        """Background task to clean up old access control data"""
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(3600)  # Run every hour
                self.access_control.cleanup_old_data()
                logger.debug("Access control cleanup completed")
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    def _register_commands(self):
        """Register bot commands (prefix commands - legacy)"""

        @self.bot.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.CommandNotFound):
                await ctx.send("❌ Unknown command. Use `!help` to see available commands.")
            elif isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ You don't have permission to use this command.")
            else:
                logger.error(f"Discord command error: {error}")
                await ctx.send(f"❌ An error occurred: {str(error)}")

        @self.bot.command(name='logs', help='Get recent logs from TailSentry')
        async def get_logs(ctx, lines: int = 50, level: Optional[str] = None):
            """Get recent logs from TailSentry"""
            try:
                # Check permissions
                if self.allowed_users and str(ctx.author.id) not in self.allowed_users and str(ctx.author) not in self.allowed_users:
                    await ctx.send("❌ You don't have permission to view logs.")
                    return

                # Validate parameters
                if lines < 1 or lines > 1000:
                    await ctx.send("❌ Number of lines must be between 1 and 1000.")
                    return

                if level and level.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                    await ctx.send("❌ Invalid log level. Use: DEBUG, INFO, WARNING, ERROR, or CRITICAL.")
                    return

                # Read logs
                logs = await self._get_logs(lines, level)

                if not logs:
                    await ctx.send("📄 No logs found.")
                    return

                # Format and send logs
                log_content = f"```\n{logs}\n```"

                # Discord has a 2000 character limit per message
                if len(log_content) > 2000:
                    # Split into multiple messages
                    chunks = [log_content[i:i+1990] for i in range(0, len(log_content), 1990)]
                    for i, chunk in enumerate(chunks[:5]):  # Limit to 5 messages
                        if i == 0:
                            await ctx.send(f"📄 **TailSentry Logs** (Last {lines} lines{f', Level: {level}' if level else ''}):\n{chunk}")
                        else:
                            await ctx.send(chunk)
                    if len(chunks) > 5:
                        await ctx.send("⚠️ Log output truncated due to length.")
                else:
                    await ctx.send(f"📄 **TailSentry Logs** (Last {lines} lines{f', Level: {level}' if level else ''}):\n{log_content}")

            except Exception as e:
                logger.error(f"Error in logs command: {e}")
                await ctx.send("❌ Failed to retrieve logs.")

        @self.bot.command(name='status', help='Get TailSentry status')
        async def get_status(ctx):
            """Get basic TailSentry status"""
            try:
                # Check permissions
                if self.allowed_users and str(ctx.author.id) not in self.allowed_users and str(ctx.author) not in self.allowed_users:
                    await ctx.send("❌ You don't have permission to view status.")
                    return

                # Get basic status info
                status_info = await self._get_status()

                embed = discord.Embed(
                    title="🖥️ TailSentry Status",
                    color=0x3498db,
                    timestamp=datetime.utcnow()
                )

                for key, value in status_info.items():
                    embed.add_field(name=key, value=value, inline=True)

                await ctx.send(embed=embed)

            except Exception as e:
                logger.error(f"Error in status command: {e}")
                await ctx.send("❌ Failed to get status.")

        @self.bot.command(name='help', help='Show available commands')
        async def show_help(ctx):
            """Show help information"""
            embed = discord.Embed(
                title="🤖 TailSentry Discord Bot",
                description="Available commands:",
                color=0x3498db
            )

            embed.add_field(
                name="!logs [lines] [level]",
                value="Get recent logs (default: 50 lines)\nExample: `!logs 100 ERROR`",
                inline=False
            )

            embed.add_field(
                name="!status",
                value="Get TailSentry status information",
                inline=False
            )

            embed.add_field(
                name="!help",
                value="Show this help message",
                inline=False
            )

            embed.set_footer(text="TailSentry Monitoring System")
            await ctx.send(embed=embed)

    def _register_slash_commands(self):
        """Register slash commands for the bot"""

        @self.bot.tree.command(name="logs", description="Get recent logs from TailSentry")
        @discord.app_commands.describe(lines="Number of lines to retrieve", level="Log level filter")
        @discord.app_commands.choices(level=[
            discord.app_commands.Choice(name="DEBUG", value="DEBUG"),
            discord.app_commands.Choice(name="INFO", value="INFO"),
            discord.app_commands.Choice(name="WARNING", value="WARNING"),
            discord.app_commands.Choice(name="ERROR", value="ERROR"),
            discord.app_commands.Choice(name="CRITICAL", value="CRITICAL")
        ])
        async def logs_slash(
            interaction: discord.Interaction,
            lines: int = 50,
            level: Optional[str] = None
        ):
            """Get recent logs from TailSentry via slash command"""
            user_id = str(interaction.user.id)
            username = str(interaction.user)
            
            try:
                # Security checks
                if self.access_control.is_user_blocked(user_id):
                    await interaction.response.send_message("❌ Access temporarily blocked due to repeated unauthorized attempts.", ephemeral=True)
                    return
                
                if not self.access_control.is_user_allowed(user_id):
                    self.access_control.record_failed_attempt(user_id, "user_not_authorized")
                    await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                    return
                
                if not self.access_control.check_rate_limit(user_id):
                    await interaction.response.send_message("❌ Rate limit exceeded. Please wait before using commands again.", ephemeral=True)
                    return
                
                # Validate parameters
                if lines < 1 or lines > 1000:
                    await interaction.response.send_message("❌ Number of lines must be between 1 and 1000.", ephemeral=True)
                    return
                
                if level and level.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                    await interaction.response.send_message("❌ Invalid log level. Use: DEBUG, INFO, WARNING, ERROR, or CRITICAL.", ephemeral=True)
                    return

                # Read logs
                raw_logs = await self._get_logs(lines, level)

                if not raw_logs:
                    await interaction.response.send_message("📄 No logs found.", ephemeral=True)
                    return

                # SECURITY: Sanitize logs before sending
                sanitized_logs = self.log_sanitizer.sanitize(raw_logs)
                log_content = f"```\n{sanitized_logs}\n```"

                # Discord has a 2000 character limit per message
                if len(log_content) > 2000:
                    # Split into multiple messages
                    chunks = [log_content[i:i+1990] for i in range(0, len(log_content), 1990)]
                    await interaction.response.send_message(f"📄 **TailSentry Logs** (Last {lines} lines{f', Level: {level}' if level else ''}):")
                    for i, chunk in enumerate(chunks[:5]):  # Limit to 5 messages
                        if i > 0:
                            await interaction.followup.send(chunk)
                    if len(chunks) > 5:
                        await interaction.followup.send("⚠️ Log output truncated due to length.")
                else:
                    await interaction.response.send_message(f"📄 **TailSentry Logs** (Last {lines} lines{f', Level: {level}' if level else ''}):\n{log_content}")

                # Record successful access
                self.access_control.record_successful_access(
                    user_id=user_id,
                    username=username,
                    command="logs",
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id) if interaction.channel_id else None
                )

            except Exception as e:
                logger.error(f"Error in logs slash command: {e}")
                await interaction.response.send_message("❌ Failed to retrieve logs.", ephemeral=True)

        @self.bot.tree.command(name="status", description="Get TailSentry status")
        async def status_slash(interaction: discord.Interaction):
            """Get basic TailSentry status via slash command"""
            user_id = str(interaction.user.id)
            username = str(interaction.user)
            
            try:
                # Security checks
                if self.access_control.is_user_blocked(user_id):
                    await interaction.response.send_message("❌ Access temporarily blocked due to repeated unauthorized attempts.", ephemeral=True)
                    return
                
                if not self.access_control.is_user_allowed(user_id):
                    self.access_control.record_failed_attempt(user_id, "user_not_authorized")
                    await interaction.response.send_message("❌ You don't have permission to view status.", ephemeral=True)
                    return
                
                if not self.access_control.check_rate_limit(user_id):
                    await interaction.response.send_message("❌ Rate limit exceeded. Please wait before using commands again.", ephemeral=True)
                    return

                # Get basic status info
                status_info = await self._get_status()

                embed = discord.Embed(
                    title="🖥️ TailSentry Status",
                    color=0x3498db,
                    timestamp=datetime.utcnow()
                )

                for key, value in status_info.items():
                    embed.add_field(name=key, value=value, inline=True)

                await interaction.response.send_message(embed=embed)

                # Record successful access
                self.access_control.record_successful_access(
                    user_id=user_id,
                    username=username,
                    command="status",
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id) if interaction.channel_id else None
                )

            except Exception as e:
                logger.error(f"Error in status slash command: {e}")
                await interaction.response.send_message("❌ Failed to get status.", ephemeral=True)

        @self.bot.tree.command(name="help", description="Show available commands")
        async def help_slash(interaction: discord.Interaction):
            """Show help information via slash command"""
            user_id = str(interaction.user.id)
            username = str(interaction.user)
            
            try:
                # Basic rate limiting for help command (less strict)
                if self.access_control.is_user_blocked(user_id):
                    await interaction.response.send_message("❌ Access temporarily blocked.", ephemeral=True)
                    return
                
                if not self.access_control.check_rate_limit(user_id):
                    await interaction.response.send_message("❌ Rate limit exceeded.", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title="🤖 TailSentry Discord Bot",
                    description="Available slash commands:",
                    color=0x3498db
                )

                embed.add_field(
                    name="/logs [lines] [level]",
                    value="Get recent logs (default: 50 lines)\nExample: `/logs lines:100 level:ERROR`",
                    inline=False
                )

                embed.add_field(
                    name="/status",
                    value="Get TailSentry status information",
                    inline=False
                )

                embed.add_field(
                    name="/help",
                    value="Show this help message",
                    inline=False
                )

                embed.set_footer(text="TailSentry Monitoring System | Security Enhanced")
                await interaction.response.send_message(embed=embed)

                # Record successful access (help is less sensitive)
                self.access_control.record_successful_access(
                    user_id=user_id,
                    username=username,
                    command="help",
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id) if interaction.channel_id else None
                )
                
            except Exception as e:
                logger.error(f"Error in help slash command: {e}")
                await interaction.response.send_message("❌ Command failed.", ephemeral=True)

        # NEW EXPANDED COMMANDS
        @self.bot.tree.command(name="devices", description="List all Tailscale devices")
        async def devices_slash(interaction: discord.Interaction):
            """List all Tailscale devices"""
            user_id = str(interaction.user.id)
            username = str(interaction.user)
            
            try:
                # Security checks
                if not await self._security_check(interaction, user_id, "devices"):
                    return

                # Get devices from Tailscale
                devices = await self._get_tailscale_devices()
                
                if not devices:
                    await interaction.response.send_message("📱 No devices found in tailnet.", ephemeral=True)
                    return

                # Create embedded response
                embed = discord.Embed(
                    title="🌐 Tailscale Devices",
                    description=f"Found {len(devices)} devices in tailnet",
                    color=0x3498db
                )

                online_count = 0
                for device in devices[:10]:  # Limit to first 10 devices
                    # Get device info with correct field names from TailscaleClient
                    name = device.get('hostname', device.get('name', 'Unknown'))
                    is_online = device.get('online', False)
                    status = "🟢 Online" if is_online else "🔴 Offline"
                    if is_online:
                        online_count += 1
                    
                    # Handle IP address (string from TailscaleClient vs array from mock data)
                    ip_addr = device.get('ip', 'Unknown')
                    if not ip_addr or ip_addr == 'Unknown':
                        ip_addr = device.get('addresses', ['Unknown'])[0] if device.get('addresses') else 'Unknown'
                        
                    device_info = (
                        f"**Status:** {status}\n"
                        f"**IP:** {ip_addr}\n"
                        f"**OS:** {device.get('os', 'Unknown')}\n"
                        f"**Last Seen:** {device.get('lastSeen', device.get('status', 'Unknown'))}"
                    )
                    
                    embed.add_field(
                        name=f"📱 {name}",
                        value=device_info,
                        inline=True
                    )

                embed.set_footer(text=f"Online: {online_count}/{len(devices)} • Use /device_info <name> for details")
                
                await interaction.response.send_message(embed=embed)
                
                # Record successful access
                self.access_control.record_successful_access(
                    user_id=user_id, username=username, command="devices",
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id) if interaction.channel_id else None
                )

            except Exception as e:
                logger.error(f"Error in devices command: {e}")
                await interaction.response.send_message("❌ Failed to retrieve device list.", ephemeral=True)

        @self.bot.tree.command(name="device_info", description="Get detailed information about a specific device")
        async def device_info_slash(interaction: discord.Interaction, device_name: str):
            """Get detailed device information"""
            user_id = str(interaction.user.id)
            username = str(interaction.user)
            
            try:
                # Security checks
                if not await self._security_check(interaction, user_id, "device_info"):
                    return

                # Get specific device info
                device = await self._get_device_info(device_name)
                
                if not device:
                    await interaction.response.send_message(f"❌ Device '{device_name}' not found.", ephemeral=True)
                    return

                # Create detailed embed
                device_name_display = device.get('hostname', device.get('name', 'Unknown'))
                embed = discord.Embed(
                    title=f"📱 Device: {device_name_display}",
                    color=0x2ecc71 if device.get('online', False) else 0xe74c3c
                )

                # Basic info
                status = "🟢 Online" if device.get('online', False) else "🔴 Offline"
                embed.add_field(name="Status", value=status, inline=True)
                embed.add_field(name="OS", value=device.get('os', 'Unknown'), inline=True)
                embed.add_field(name="Device ID", value=device.get('id', device.get('nodeId', 'Unknown')), inline=True)

                # Network info - handle both string IP and array addresses
                ip_addr = device.get('ip')
                if ip_addr:
                    embed.add_field(name="IP Address", value=ip_addr, inline=True)
                else:
                    addresses = device.get('addresses', [])
                    if addresses:
                        embed.add_field(name="IP Addresses", value="\n".join(addresses[:3]), inline=True)
                
                # Status and timestamps
                device_status = device.get('status', 'Unknown')
                last_seen = device.get('lastSeen', 'Unknown')
                
                embed.add_field(name="Device Status", value=device_status, inline=True)
                embed.add_field(name="Last Seen", value=last_seen, inline=True)
                
                # Additional info from TailscaleClient
                if device.get('isExitNode'):
                    embed.add_field(name="Exit Node", value="✅ Yes", inline=True)
                if device.get('isSubnetRouter'):
                    embed.add_field(name="Subnet Router", value="✅ Yes", inline=True)

                await interaction.response.send_message(embed=embed)
                
                # Record successful access
                self.access_control.record_successful_access(
                    user_id=user_id, username=username, command="device_info",
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id) if interaction.channel_id else None
                )

            except Exception as e:
                logger.error(f"Error in device_info command: {e}")
                await interaction.response.send_message("❌ Failed to retrieve device information.", ephemeral=True)

        @self.bot.tree.command(name="health", description="Get detailed TailSentry health information")
        async def health_slash(interaction: discord.Interaction):
            """Get detailed health check information"""
            user_id = str(interaction.user.id)
            username = str(interaction.user)
            
            try:
                # Security checks
                if not await self._security_check(interaction, user_id, "health"):
                    return

                # Gather health information
                health_data = await self._get_health_info()
                
                embed = discord.Embed(
                    title="🏥 TailSentry Health Check",
                    color=0x2ecc71 if health_data['overall_status'] == 'healthy' else 0xe74c3c
                )

                # Overall status
                status_emoji = "✅" if health_data['overall_status'] == 'healthy' else "⚠️"
                embed.add_field(
                    name="Overall Status", 
                    value=f"{status_emoji} {health_data['overall_status'].title()}", 
                    inline=True
                )

                # Uptime
                embed.add_field(name="Uptime", value=health_data.get('uptime', 'Unknown'), inline=True)

                # Service status
                services_status = ""
                for service, status in health_data.get('services', {}).items():
                    emoji = "✅" if status == 'running' else "❌"
                    services_status += f"{emoji} {service.title()}: {status}\n"
                
                if services_status:
                    embed.add_field(name="Services", value=services_status, inline=False)

                # Resource usage
                resources = health_data.get('resources', {})
                if resources:
                    resource_info = f"CPU: {resources.get('cpu', 'Unknown')}%\nRAM: {resources.get('memory', 'Unknown')}%\nDisk: {resources.get('disk', 'Unknown')}%"
                    embed.add_field(name="Resource Usage", value=resource_info, inline=True)

                embed.set_footer(text=f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                await interaction.response.send_message(embed=embed)
                
                # Record successful access
                self.access_control.record_successful_access(
                    user_id=user_id, username=username, command="health",
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id) if interaction.channel_id else None
                )

            except Exception as e:
                logger.error(f"Error in health command: {e}")
                await interaction.response.send_message("❌ Failed to retrieve health information.", ephemeral=True)

        @self.bot.tree.command(name="audit_logs", description="Get recent security audit logs")
        async def audit_logs_slash(interaction: discord.Interaction, lines: int = 20):
            """Get security audit logs"""
            user_id = str(interaction.user.id)
            username = str(interaction.user)
            
            try:
                # Security checks with elevated permissions required
                if not await self._security_check(interaction, user_id, "audit_logs", elevated=True):
                    return

                # Get audit logs from access control
                audit_data = self.access_control.get_user_activity_summary(user_id, hours=24)
                
                embed = discord.Embed(
                    title="🔒 Security Audit Logs",
                    description="Recent security events and user activity",
                    color=0x9b59b6
                )

                # User activity summary
                activity = (
                    f"**Commands:** {audit_data.get('total_commands', 0)}\n"
                    f"**Failed:** {audit_data.get('failed_commands', 0)}\n"
                    f"**High Risk:** {audit_data.get('high_risk_actions', 0)}\n"
                    f"**Last Activity:** {audit_data.get('last_activity', 'None')}"
                )
                embed.add_field(name="Your Activity (24h)", value=activity, inline=True)

                # Suspicious activity detection
                suspicious = self.access_control.detect_suspicious_activity()
                if suspicious:
                    alerts = "\n".join([f"⚠️ {alert['type']}: {alert.get('user_id', 'Unknown')}" for alert in suspicious[:5]])
                    embed.add_field(name="Security Alerts", value=alerts, inline=False)
                else:
                    embed.add_field(name="Security Alerts", value="✅ No suspicious activity detected", inline=False)

                embed.set_footer(text="Use this command responsibly • Only shows your activity data")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Record successful access with high risk level
                self.access_control.record_successful_access(
                    user_id=user_id, username=username, command="audit_logs",
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id) if interaction.channel_id else None
                )

            except Exception as e:
                logger.error(f"Error in audit_logs command: {e}")
                await interaction.response.send_message("❌ Failed to retrieve audit logs.", ephemeral=True)

        @self.bot.tree.command(name="metrics", description="Get TailSentry performance metrics")
        async def metrics_slash(interaction: discord.Interaction):
            """Get performance metrics"""
            user_id = str(interaction.user.id)
            username = str(interaction.user)
            
            try:
                # Security checks
                if not await self._security_check(interaction, user_id, "metrics"):
                    return

                # Get metrics
                metrics = await self._get_metrics()
                
                embed = discord.Embed(
                    title="📈 TailSentry Metrics",
                    color=0x1abc9c
                )

                # Performance metrics
                perf_info = (
                    f"**Response Time:** {metrics.get('avg_response_time', 'Unknown')}ms\n"
                    f"**Requests/min:** {metrics.get('requests_per_minute', 'Unknown')}\n"
                    f"**Error Rate:** {metrics.get('error_rate', 'Unknown')}%"
                )
                embed.add_field(name="Performance", value=perf_info, inline=True)

                # Discord bot metrics
                bot_info = (
                    f"**Commands Used:** {metrics.get('commands_used', 0)}\n"
                    f"**Active Users:** {metrics.get('active_users', 0)}\n"
                    f"**Uptime:** {metrics.get('bot_uptime', 'Unknown')}"
                )
                embed.add_field(name="Bot Statistics", value=bot_info, inline=True)

                await interaction.response.send_message(embed=embed)
                
                # Record successful access
                self.access_control.record_successful_access(
                    user_id=user_id, username=username, command="metrics",
                    guild_id=str(interaction.guild_id) if interaction.guild_id else None,
                    channel_id=str(interaction.channel_id) if interaction.channel_id else None
                )

            except Exception as e:
                logger.error(f"Error in metrics command: {e}")
                await interaction.response.send_message("❌ Failed to retrieve metrics.", ephemeral=True)

    # HELPER METHODS FOR NEW COMMANDS
    async def _security_check(self, interaction: discord.Interaction, user_id: str, command: str, elevated: bool = False) -> bool:
        """Centralized security check for all commands"""
        try:
            # Check if user is blocked
            if self.access_control.is_user_blocked(user_id):
                await interaction.response.send_message("❌ Access temporarily blocked due to repeated unauthorized attempts.", ephemeral=True)
                return False
            
            # Check if user is allowed (for elevated commands, require explicit permission)
            if elevated and self.allowed_users and user_id not in self.allowed_users:
                self.access_control.record_failed_attempt(user_id, f"elevated_command_{command}")
                await interaction.response.send_message("❌ You don't have permission for elevated commands.", ephemeral=True)
                return False
            elif not self.access_control.is_user_allowed(user_id):
                self.access_control.record_failed_attempt(user_id, "user_not_authorized")
                await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
                return False
            
            # Check rate limit
            if not self.access_control.check_rate_limit(user_id):
                await interaction.response.send_message("❌ Rate limit exceeded. Please wait before using commands again.", ephemeral=True)
                return False
            
            return True
        except Exception as e:
            logger.error(f"Security check failed for {command}: {e}")
            await interaction.response.send_message("❌ Security check failed.", ephemeral=True)
            return False

    async def _get_tailscale_devices(self) -> List[Dict]:
        """Get list of Tailscale devices"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            
            # Try to use the existing TailscaleClient
            try:
                from services.tailscale_service import TailscaleClient
                devices = TailscaleClient.get_all_devices()
                logger.info(f"Retrieved {len(devices) if devices else 0} devices from Tailscale")
                return devices if devices else []
            except ImportError as ie:
                logger.error(f"Failed to import TailscaleClient: {ie}")
                # Fallback: return mock data for testing
                logger.warning("TailscaleClient not available, returning mock data")
                return [
                    {
                        'name': 'mock-device',
                        'nodeId': '12345',
                        'online': True,
                        'os': 'linux',
                        'addresses': ['100.64.0.1'],
                        'created': datetime.now().isoformat(),
                        'lastSeen': datetime.now().isoformat()
                    }
                ]
            except Exception as e:
                logger.error(f"Error calling TailscaleClient.get_all_devices(): {e}")
                # Try to run tailscale status directly as fallback
                try:
                    import subprocess
                    result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info("Successfully got tailscale status, but couldn't parse. Using simple fallback.")
                        # Simple parsing fallback
                        devices = []
                        for line in result.stdout.strip().split('\n'):
                            if line.strip() and not line.startswith('#') and 'Health check:' not in line:
                                parts = line.split()
                                if len(parts) >= 4:
                                    devices.append({
                                        'name': parts[1],
                                        'nodeId': f"parsed-{len(devices)}",
                                        'online': 'active' in line or 'idle' in line,
                                        'os': parts[3] if len(parts) > 3 else 'unknown',
                                        'addresses': [parts[0]],
                                        'created': datetime.now().isoformat(),
                                        'lastSeen': datetime.now().isoformat()
                                    })
                        logger.info(f"Parsed {len(devices)} devices from tailscale status")
                        return devices
                    else:
                        logger.error(f"Tailscale status failed: {result.stderr}")
                        return []
                except Exception as fallback_e:
                    logger.error(f"Fallback tailscale status also failed: {fallback_e}")
                    return []
        except Exception as e:
            logger.error(f"Failed to get Tailscale devices: {e}")
            return []

    async def _get_device_info(self, device_name: str) -> Optional[Dict]:
        """Get detailed information about a specific device"""
        try:
            devices = await self._get_tailscale_devices()
            for device in devices:
                # Check both hostname (TailscaleClient) and name (fallback) fields
                hostname = device.get('hostname', '')
                name = device.get('name', '')
                if (hostname.lower() == device_name.lower() or 
                    name.lower() == device_name.lower()):
                    return device
            return None
        except Exception as e:
            logger.error(f"Failed to get device info for {device_name}: {e}")
            return None

    async def _get_health_info(self) -> Dict:
        """Get TailSentry health information"""
        try:
            # Basic health data
            health_data = {
                'overall_status': 'healthy',
                'uptime': self._format_uptime(),
                'services': {},
                'resources': {}
            }
            
            # Check service status
            health_data['services']['discord_bot'] = 'running' if self.bot.is_ready() else 'stopped'
            health_data['services']['log_file'] = 'accessible' if Path(self.log_file_path).exists() else 'missing'
            
            # Resource usage (with fallback if psutil not available)
            try:
                import psutil
                health_data['resources']['cpu'] = round(psutil.cpu_percent(interval=1), 1)
                health_data['resources']['memory'] = round(psutil.virtual_memory().percent, 1)
                health_data['resources']['disk'] = round(psutil.disk_usage('/').percent, 1)
            except ImportError:
                logger.warning("psutil not available, resource monitoring disabled")
                health_data['resources'] = {'cpu': 'N/A', 'memory': 'N/A', 'disk': 'N/A'}
            except Exception as e:
                logger.error(f"Error getting resource usage: {e}")
                health_data['resources'] = {'cpu': 'Error', 'memory': 'Error', 'disk': 'Error'}
            
            # Overall status check
            if any(status != 'running' and status != 'accessible' for status in health_data['services'].values()):
                health_data['overall_status'] = 'degraded'
            
            return health_data
        except Exception as e:
            logger.error(f"Failed to get health info: {e}")
            return {
                'overall_status': 'error',
                'uptime': 'Unknown',
                'services': {},
                'resources': {}
            }

    async def _get_metrics(self) -> Dict:
        """Get performance metrics"""
        try:
            import time
            
            # Basic metrics (in a real implementation, these would come from a metrics store)
            metrics = {
                'avg_response_time': 'Unknown',
                'requests_per_minute': 'Unknown', 
                'error_rate': 'Unknown',
                'commands_used': len(getattr(self.access_control, 'recent_events', [])),
                'active_users': len(set(event.get('user_id') for event in getattr(self.access_control, 'recent_events', []))),
                'bot_uptime': self._format_uptime()
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {
                'avg_response_time': 'Error',
                'requests_per_minute': 'Error',
                'error_rate': 'Error',
                'commands_used': 0,
                'active_users': 0,
                'bot_uptime': 'Unknown'
            }

    def _format_uptime(self) -> str:
        """Format bot uptime"""
        try:
            if hasattr(self, '_start_time'):
                uptime_seconds = time.time() - self._start_time
                hours, remainder = divmod(uptime_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            return "Unknown"
        except:
            return "Unknown"

    async def _get_logs(self, lines: int = 50, level: Optional[str] = None) -> str:
        """Get recent logs from the log file (raw, unsanitized)"""
        try:
            if not os.path.exists(self.log_file_path):
                return "Log file not found."

            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read all lines and get the last N lines
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) >= lines else all_lines

                # Filter by log level if specified
                if level:
                    filtered_lines = []
                    for line in recent_lines:
                        if f'- {level.upper()} -' in line or f'- {level.lower()} -' in line:
                            filtered_lines.append(line)
                    recent_lines = filtered_lines[-lines:]  # Get last N matching lines

                # Return raw logs (sanitization happens in slash commands)
                return ''.join(recent_lines).strip()

        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return f"Error reading logs: {str(e)}"

    async def _get_status(self) -> dict:
        """Get basic TailSentry status information"""
        try:
            status = {}

            # Log file info
            if os.path.exists(self.log_file_path):
                stat = os.stat(self.log_file_path)
                status["📄 Log Size"] = f"{stat.st_size / 1024:.1f} KB"
                status["📅 Last Modified"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            else:
                status["📄 Log Status"] = "Not found"

            # System uptime (simplified)
            status["⚡ Bot Status"] = "Online"
            status["⏰ Last Check"] = datetime.utcnow().strftime("%H:%M:%S UTC")

            return status

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"❌ Error": str(e)}

    async def start(self):
        """Start the Discord bot"""
        try:
            self._start_time = time.time()
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")
            raise

    def stop(self):
        """Stop the Discord bot"""
        try:
            asyncio.create_task(self.bot.close())
        except Exception as e:
            logger.error(f"Failed to stop Discord bot: {e}")

# NEW DEVICE NOTIFICATION SERVICE
class DeviceNotificationService:
    """Service to monitor for new devices and send Discord notifications"""
    
    def __init__(self, discord_bot: TailSentryDiscordBot, check_interval: int = 300):
        self.discord_bot = discord_bot
        self.check_interval = check_interval  # Check every 5 minutes by default
        self.known_devices = set()
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
            devices = await self.discord_bot._get_tailscale_devices()
            self.known_devices = {device.get('nodeId') for device in devices if device.get('nodeId')}
            logger.info(f"Initialized with {len(self.known_devices)} known devices")
        except Exception as e:
            logger.error(f"Failed to initialize known devices: {e}")

    async def _check_for_new_devices(self):
        """Check for new devices and send notifications"""
        try:
            current_devices = await self.discord_bot._get_tailscale_devices()
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
            if self.discord_bot.log_channel_id:
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

        """Stop device monitoring"""
        self.running = False
        logger.info("Device monitoring stopped")


# Global bot instance
discord_bot = None

async def start_discord_bot():
    """Start the Discord bot if configured"""
    global discord_bot

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.info("Discord bot token not configured, skipping bot startup")
        return

    log_file = os.getenv("LOG_FILE", "logs/tailsentry.log")
    allowed_users = os.getenv("DISCORD_ALLOWED_USERS")
    command_prefix = os.getenv("DISCORD_COMMAND_PREFIX", "!")
    log_channel_id = os.getenv("DISCORD_LOG_CHANNEL_ID")
    status_channel_id = os.getenv("DISCORD_STATUS_CHANNEL_ID")
    
    # Parse allowed users list
    allowed_users_list = None
    if allowed_users:
        allowed_users_list = [user.strip() for user in allowed_users.split(',') if user.strip()]

    # Ensure log file path is absolute
    if not os.path.isabs(log_file):
        base_dir = Path(__file__).resolve().parent.parent
        log_file = base_dir / log_file

    discord_bot = TailSentryDiscordBot(
        token=token,
        log_file_path=str(log_file),
        allowed_users=allowed_users_list,
        command_prefix=command_prefix,
        log_channel_id=log_channel_id,
        status_channel_id=status_channel_id
    )

    # Start bot in background
    asyncio.create_task(discord_bot.start())

async def stop_discord_bot():
    """Stop the Discord bot"""
    global discord_bot
    if discord_bot:
        discord_bot.stop()
        discord_bot = None
