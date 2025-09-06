#!/usr/bin/env python3
"""
Force Discord Bot Command Sync
This script connects to Discord and forces a fresh sync of all slash commands
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def force_sync_commands():
    """Force sync Discord commands"""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        discord_token = os.getenv('DISCORD_BOT_TOKEN')
        if not discord_token:
            logger.error("Discord bot token not found in .env file")
            return False
            
        # Import and create bot
        from services.discord_bot import TailSentryDiscordBot
        
        log_file = Path("logs/tailsentry.log")
        log_file.parent.mkdir(exist_ok=True)
        
        bot = TailSentryDiscordBot(
            token=discord_token,
            log_file_path=str(log_file),
            allowed_users=[],  # Allow all users for testing
            command_prefix="!",
            log_channel_id=None,
            status_channel_id=None
        )
        
        logger.info("🔄 Starting Discord bot to force command sync...")
        
        # Override the on_ready event to force sync and then shutdown
        @bot.bot.event
        async def on_ready():
            logger.info(f"✅ Discord bot logged in as {bot.bot.user}")
            logger.info(f"📊 Connected to {len(bot.bot.guilds)} guilds")
            
            try:
                logger.info("🔄 Forcing global command sync...")
                
                # Don't clear commands, just sync them
                # Re-register commands (they're already registered in __init__)
                logger.info("📝 Using existing command registration")
                
                # Force sync globally (this can take up to 1 hour to propagate)
                synced = await bot.bot.tree.sync()
                logger.info(f"✅ Synced {len(synced)} slash commands globally")
                
                # Also sync to specific guilds for immediate availability (faster)
                guild_sync_count = 0
                for guild in bot.bot.guilds:
                    try:
                        guild_synced = await bot.bot.tree.sync(guild=guild)
                        logger.info(f"🏠 Synced {len(guild_synced)} commands to guild: {guild.name}")
                        guild_sync_count += 1
                    except Exception as e:
                        logger.warning(f"❌ Failed to sync to guild {guild.name}: {e}")
                
                logger.info(f"🎉 Command sync complete!")
                logger.info(f"📊 Global sync: {len(synced)} commands")
                logger.info(f"🏠 Guild sync: {guild_sync_count} guilds")
                logger.info("💡 Commands should appear immediately in your servers")
                logger.info("⏰ Global commands may take up to 1 hour to appear everywhere")
                
                # List all synced commands
                logger.info("📋 Synced commands:")
                for cmd in synced:
                    logger.info(f"   • /{cmd.name} - {cmd.description}")
                
            except Exception as e:
                logger.error(f"❌ Failed to sync commands: {e}")
                logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            finally:
                logger.info("🛑 Shutting down bot...")
                await bot.bot.close()
        
        # Start the bot
        await bot.bot.start(discord_token)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    
    return True

def main():
    """Main function"""
    logger.info("🚀 Discord Command Sync Tool")
    logger.info("This will force a fresh sync of all Discord slash commands")
    
    success = asyncio.run(force_sync_commands())
    
    if success:
        logger.info("✅ Command sync completed successfully!")
        logger.info("💡 Try typing '/' in your Discord server - you should see all 8 commands:")
        logger.info("   • /logs - Get recent logs")
        logger.info("   • /status - System status")  
        logger.info("   • /help - Show commands")
        logger.info("   • /devices - List devices")
        logger.info("   • /device-info - Device details")
        logger.info("   • /health - Health metrics")
        logger.info("   • /audit-logs - Audit logs")
        logger.info("   • /metrics - Performance metrics")
    else:
        logger.error("❌ Command sync failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
