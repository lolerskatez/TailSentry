"""
TailSentry Discord Bot Service
Handles Discord bot integration for interactive commands and log retrieval
"""

import discord
from discord.ext import commands
import logging
import os
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta
import re

logger = logging.getLogger("tailsentry.discord_bot")

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
            except Exception as e:
                logger.error(f"Failed to sync slash commands: {e}")
                logger.error(f"Error details: {type(e).__name__}: {str(e)}")

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
            try:
                # Check permissions
                if self.allowed_users and str(interaction.user.id) not in self.allowed_users and str(interaction.user) not in self.allowed_users:
                    await interaction.response.send_message("❌ You don't have permission to view logs.", ephemeral=True)
                    return

                # Read logs
                logs = await self._get_logs(lines, level)

                if not logs:
                    await interaction.response.send_message("📄 No logs found.", ephemeral=True)
                    return

                # Format logs
                log_content = f"```\n{logs}\n```"

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

            except Exception as e:
                logger.error(f"Error in logs slash command: {e}")
                await interaction.response.send_message("❌ Failed to retrieve logs.", ephemeral=True)

        @self.bot.tree.command(name="status", description="Get TailSentry status")
        async def status_slash(interaction: discord.Interaction):
            """Get basic TailSentry status via slash command"""
            try:
                # Check permissions
                if self.allowed_users and str(interaction.user.id) not in self.allowed_users and str(interaction.user) not in self.allowed_users:
                    await interaction.response.send_message("❌ You don't have permission to view status.", ephemeral=True)
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

            except Exception as e:
                logger.error(f"Error in status slash command: {e}")
                await interaction.response.send_message("❌ Failed to get status.", ephemeral=True)

        @self.bot.tree.command(name="help", description="Show available commands")
        async def help_slash(interaction: discord.Interaction):
            """Show help information via slash command"""
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

            embed.set_footer(text="TailSentry Monitoring System")
            await interaction.response.send_message(embed=embed)

    async def _get_logs(self, lines: int = 50, level: Optional[str] = None) -> str:
        """Get recent logs from the log file"""
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
            logger.info("Starting TailSentry Discord bot...")
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")
            raise

    def stop(self):
        """Stop the Discord bot"""
        logger.info("Stopping TailSentry Discord bot...")
        asyncio.create_task(self.bot.close())

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
