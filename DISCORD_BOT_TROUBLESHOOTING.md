# Discord Bot Troubleshooting Quick Reference

## Issue: `/devices` Command Shows Mock Data

### Symptoms
```
Found 1 devices in tailnet
📱 mock-device
Status: 🟢 Online
IP: 100.64.0.1
OS: linux
Last Seen: 2025-09-06T00:06:16.554950
```

### Quick Fix Steps

1. **Check Tailscale Installation**
   ```bash
   tailscale status
   ```
   ✅ Should show your actual devices
   ❌ If "command not found", install Tailscale CLI

2. **Test TailscaleClient Integration**
   ```bash
   python test_tailscale_devices.py
   ```
   ✅ Should show 6+ real devices with hostnames
   ❌ If import errors, check TailscaleClient setup

3. **Test Discord Bot Integration**
   ```bash
   python test_discord_device_integration.py
   ```
   ✅ Should confirm bot can access real device data
   ❌ If errors, check services/discord_bot.py

4. **Check Application Logs**
   ```bash
   grep "TailscaleClient" logs/tailsentry.log
   grep "mock data" logs/tailsentry.log
   ```
   Look for import errors or fallback messages

5. **Restart TailSentry**
   ```bash
   # Stop current instance (Ctrl+C)
   python main.py
   ```
   Check startup logs for TailscaleClient import success

### Expected Working Output

After fix, `/devices` should show:
```
🌐 Tailscale Devices (6 total)

📱 godzilla
Status: 🟢 Online
IP: 100.74.214.67
OS: windows
Last Seen: idle; offers exit node

📱 shenron
Status: 🟢 Online
IP: 100.109.90.25
OS: linux
Last Seen: idle, tx 6652 rx 7588

📱 bryson-desktop
Status: 🔴 Offline
IP: 100.124.58.64
OS: windows
Last Seen: 2025-08-15T22:48:21.1Z

Summary
Online: 2/6 • Use /device_info <name> for details
```

### Other Common Issues

**Commands not appearing in Discord:**
```bash
python force_sync_discord_commands.py
```

**Bot not responding:**
- Check DISCORD_BOT_TOKEN in .env
- Verify bot permissions in Discord server
- Check TailSentry is running: `python main.py`

**Permission errors:**
- Add your Discord user ID to DISCORD_ALLOWED_USERS
- Check rate limiting (10 commands/minute max)

**Device info lookup fails:**
- Use exact device hostname from `/devices` list
- Try `/device_info godzilla` instead of `/device_info server-main`

### Files Updated in Fix
- `services/discord_bot.py` - TailscaleClient integration
- `README.md` - Updated examples and troubleshooting
- `DISCORD_BOT_DOCUMENTATION.md` - Added mock data troubleshooting
- `test_tailscale_devices.py` - New diagnostic tool
- `test_discord_device_integration.py` - New integration test

### Support Commands
```bash
# Full diagnostic suite
python test_tailscale_devices.py
python test_discord_device_integration.py
python test_discord_functionality.py

# Force command refresh
python force_sync_discord_commands.py

# Check service status
systemctl status tailsentry  # Linux
# or just check process manually on Windows
```
