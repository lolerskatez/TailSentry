#!/usr/bin/env python3
"""
Test script to check if the Discord bot can properly retrieve and format device data
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

async def test_discord_device_method():
    """Test the Discord bot's device retrieval method"""
    print("🔍 Testing Discord bot device retrieval...")
    
    try:
        # Import the Discord bot
        from services.discord_bot import TailSentryDiscordBot
        
        # Create a bot instance (without actually connecting to Discord)
        bot = TailSentryDiscordBot("dummy_token", "logs/tailsentry.log")
        
        # Test the device retrieval method
        devices = await bot._get_tailscale_devices()
        print(f"📱 Discord bot found {len(devices) if devices else 0} devices")
        
        if devices:
            print("\n📋 Device data format:")
            for i, device in enumerate(devices[:3], 1):  # Show first 3 devices
                print(f"  {i}. {device}")
                print(f"     Name/Hostname: {device.get('hostname', device.get('name', 'Unknown'))}")
                print(f"     Online: {device.get('online', 'Unknown')}")
                print(f"     OS: {device.get('os', 'Unknown')}")
                print(f"     IP: {device.get('ip', device.get('addresses', ['Unknown'])[0] if device.get('addresses') else 'Unknown')}")
                print()
                
            # Test device info lookup
            if len(devices) > 0:
                first_device_name = devices[0].get('hostname', devices[0].get('name', 'test'))
                print(f"🔍 Testing device info lookup for '{first_device_name}'...")
                device_info = await bot._get_device_info(first_device_name)
                if device_info:
                    print(f"✅ Found device info: {device_info.get('hostname', device_info.get('name'))}")
                else:
                    print("❌ Device info lookup failed")
        else:
            print("❌ No devices found")
            
    except Exception as e:
        print(f"❌ Error testing Discord bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    print("🧪 Discord Bot Device Test")
    print("=" * 50)
    
    asyncio.run(test_discord_device_method())
    
    print("\n✅ Test complete!")
