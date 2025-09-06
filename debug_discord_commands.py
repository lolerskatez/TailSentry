#!/usr/bin/env python3
"""
Debug Discord Bot Commands
Test individual command functionality
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
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_metrics_command():
    """Test the metrics command functionality"""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Import and create bot
        from services.discord_bot import TailSentryDiscordBot
        
        log_file = Path("logs/tailsentry.log")
        log_file.parent.mkdir(exist_ok=True)
        
        bot = TailSentryDiscordBot(
            token="dummy_token",  # Don't actually connect
            log_file_path=str(log_file),
            allowed_users=[],
            command_prefix="!",
            log_channel_id=None,
            status_channel_id=None
        )
        
        # Test the _get_metrics method directly
        logger.info("🧪 Testing _get_metrics method...")
        metrics = await bot._get_metrics()
        logger.info(f"✅ Metrics result: {metrics}")
        
        # Check command registration
        logger.info("🧪 Testing command registration...")
        commands = bot.bot.tree.get_commands()
        logger.info(f"📋 Registered commands ({len(commands)}):")
        
        for cmd in commands:
            logger.info(f"   • /{cmd.name} - {cmd.description}")
            if cmd.name == "metrics":
                logger.info(f"✅ Metrics command found: {cmd}")
                
        # Test command name restrictions
        logger.info("🧪 Testing command names for Discord compatibility...")
        for cmd in commands:
            name = cmd.name
            if '-' in name:
                logger.warning(f"⚠️ Command '{name}' contains hyphen - this may cause issues in Discord")
            if len(name) > 32:
                logger.warning(f"⚠️ Command '{name}' is too long ({len(name)} chars, max 32)")
            if not name.islower():
                logger.warning(f"⚠️ Command '{name}' contains uppercase - Discord requires lowercase")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

def main():
    """Main test function"""
    logger.info("🔍 Discord Bot Command Debug Tool")
    success = asyncio.run(test_metrics_command())
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
