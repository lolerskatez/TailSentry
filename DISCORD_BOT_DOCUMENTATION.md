# TailSentry Discord Bot Documentation

This document provides comprehensive setup and usage instructions for the TailSentry Discord Bot integration.

## Overview

The TailSentry Discord Bot provides interactive monitoring and management capabilities for your TailSentry installation through Discord slash commands. It includes real-time device notifications, system health monitoring, and secure access controls.

## Features

### 🤖 **Interactive Commands (8 total)**
- **System Monitoring**: Health checks, metrics, and status information
- **Device Management**: List devices, get device details, monitor network changes
- **Log Access**: View application logs, audit trails, and security events
- **Real-time Updates**: Automatic notifications for new devices and system events

### 🛡️ **Security Features**
- **Rate Limiting**: 10 commands per minute per user
- **Access Control**: Optional user restrictions with Discord user IDs
- **Audit Logging**: Complete command history with session tracking
- **Data Sanitization**: Automatic removal of sensitive data from outputs
- **Elevated Permissions**: Restricted access for sensitive commands

### 📱 **Rich Discord Integration**
- **Slash Commands**: Modern Discord interface with autocomplete
- **Rich Embeds**: Formatted responses with colors, fields, and status indicators
- **Real-time Notifications**: Automatic alerts for network changes
- **Cross-platform Support**: Works on Windows and Linux

## Quick Setup

### 1. Create Discord Application

1. Visit [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and name it (e.g., "TailSentry")
3. Navigate to **"Bot"** section
4. Click **"Add Bot"**
5. Copy the **Bot Token** (keep this secure!)

### 2. Configure Bot Permissions

Required OAuth2 Scopes:
- `bot` - Basic bot functionality
- `applications.commands` - Slash command support

Required Bot Permissions:
- **Send Messages** - Command responses
- **Use Slash Commands** - Interactive commands  
- **Read Message History** - Context awareness
- **Embed Links** - Rich formatted responses

### 3. Invite Bot to Server

1. Go to **"OAuth2" → "URL Generator"**
2. Select scopes: `bot`, `applications.commands`
3. Select the permissions listed above
4. Use the generated URL to invite bot to your Discord server

### 4. Configure TailSentry

Add these settings to your `.env` file:

```bash
# Discord Bot Configuration
DISCORD_BOT_ENABLED=true
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_COMMAND_PREFIX=!

# Optional: Access Control
DISCORD_ALLOWED_USERS=123456789012345678,987654321098765432

# Optional: Notification Channels
DISCORD_LOG_CHANNEL_ID=channel_id_for_logs
DISCORD_STATUS_CHANNEL_ID=channel_id_for_status
```

### 5. Start TailSentry

The Discord bot will automatically start when TailSentry launches:

```bash
python main.py
```

Look for these log messages:
```
INFO - Discord bot logged in as TailSentry#8455
INFO - Synced 8 slash commands
INFO - Connected to 1 guilds
```

## Available Commands

### Core System Commands

#### `/status` - System Status
Get overall TailSentry system status and basic health information.

**Example Response:**
```
📊 TailSentry Status
Overall Status: ✅ Healthy
Uptime: 2h 15m 30s
Services: ✅ Discord Bot: running
Last Check: 2025-09-06 00:15:30
```

#### `/health` - Detailed Health Check
Comprehensive system health metrics including resource usage.

**Example Response:**
```
🏥 TailSentry Health Check
Overall Status: ✅ Healthy
Uptime: 2h 15m 30s
Services: ✅ Discord_Bot: running, ❌ Log_File: accessible
Resource Usage: CPU: 12.3%, RAM: 45.2%, Disk: 8.1%
Last checked: 2025-09-06 00:15:30
```

#### `/metrics` - Performance Metrics
Performance statistics and bot usage metrics.

**Example Response:**
```
📈 TailSentry Metrics
Performance: Response Time: 45ms, Requests/min: 12, Error Rate: 0.1%
Bot Statistics: Commands Used: 47, Active Users: 3, Uptime: 2h 15m 30s
```

### Device Management Commands

#### `/devices` - Device List
List all Tailscale devices on your network with status indicators.

**Example Response:**
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

� bryson-desktop
Status: 🔴 Offline
IP: 100.124.58.64
OS: windows
Last Seen: 2025-08-15T22:48:21.1Z

Summary
Online: 2/6 • Use /device_info <name> for details
```

#### `/device_info <device_name>` - Device Details
Get detailed information about a specific device.

**Parameters:**
- `device_name` (required) - Name of the device to query

**Example Usage:**
```
/device_info godzilla
```

**Example Response:**
```
� Device: godzilla
Status: 🟢 Online
OS: windows  
Device ID: device_0
IP Address: 100.74.214.67
Device Status: idle; offers exit node
Last Seen: recent
Exit Node: ✅ Yes
```

### Logging and Audit Commands

#### `/logs [lines] [level]` - Application Logs
Retrieve recent application logs with optional filtering.

**Parameters:**
- `lines` (optional) - Number of lines to retrieve (1-1000, default: 50)
- `level` (optional) - Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Example Usage:**
```
/logs 100 ERROR
/logs 20
```

**Example Response:**
```
📋 TailSentry Logs (Last 50 lines)
2025-09-06 00:15:30 - INFO - TailSentry started successfully
2025-09-06 00:15:31 - INFO - Discord bot connected
2025-09-06 00:14:45 - WARNING - Rate limit approached for user
[Logs are automatically sanitized for security]
```

#### `/audit_logs [lines]` - Security Audit Logs
View security-related events and command usage history. **Requires elevated access.**

**Parameters:**
- `lines` (optional) - Number of audit entries to retrieve (default: 20)

**Example Usage:**
```
/audit_logs 50
```

**Example Response:**
```
🔒 Security Audit Logs (Last 20 entries)
2025-09-06 00:15:30 - Command 'health' used by user daniiiflix
2025-09-06 00:14:45 - Failed login attempt from 192.168.1.100
2025-09-06 00:13:20 - Configuration change: Discord bot enabled
```

### Information Commands

#### `/help` - Command Help
Display all available commands with descriptions and usage examples.

**Example Response:**
```
🤖 TailSentry Discord Bot Help

Core Commands:
• /status - Get TailSentry system status
• /health - Detailed health check with resource usage
• /metrics - Performance metrics and bot statistics

Device Management:
• /devices - List all Tailscale devices
• /device_info <name> - Get detailed device information

Logging:
• /logs [lines] [level] - Get application logs
• /audit_logs [lines] - Security audit logs (restricted)

• /help - Show this help message

Security: All commands are logged and rate-limited
```

## Device Notifications

The bot automatically monitors your Tailscale network and sends notifications when new devices join.

### Notification Example
```
🖥️ New Device Joined Tailnet

Device Name: laptop-new
Device ID: abc123def456
OS: Windows 11
IP Address: 100.64.0.25
First Seen: 2025-09-06T00:20:15Z

TailSentry Device Monitor
```

### Notification Settings

Configure where notifications are sent:

```bash
# Send to specific channel
DISCORD_LOG_CHANNEL_ID=1234567890123456789

# Or let bot find available channels automatically
# (will send to first channel with send permissions)
```

## Security Configuration

### Access Control

Restrict bot usage to specific Discord users:

```bash
# Get Discord User IDs (Developer Mode required in Discord)
DISCORD_ALLOWED_USERS=123456789012345678,987654321098765432
```

To find Discord User IDs:
1. Enable Developer Mode in Discord settings
2. Right-click on user → "Copy User ID"

### Rate Limiting

Built-in rate limiting prevents abuse:
- **10 commands per minute** per user
- **Automatic blocking** after 5 failed attempts
- **Cleanup** of old rate limit data every hour

### Elevated Commands

Some commands require elevated access:
- `/audit_logs` - Security audit trail access

Configure elevated users:
```bash
# Users who can access audit logs and sensitive commands
DISCORD_ALLOWED_USERS=admin_user_id_here
```

### Data Protection

The bot automatically protects sensitive data:
- **Log Sanitization**: Removes tokens, passwords, and API keys
- **Session Tracking**: Unique session IDs for audit trails
- **Secure Storage**: Tokens and secrets are encrypted

## Troubleshooting

### Commands Not Appearing

If slash commands don't show up in Discord:

1. **Force Command Sync:**
   ```bash
   python force_sync_discord_commands.py
   ```

2. **Check Bot Permissions:**
   - Ensure bot has "Use Slash Commands" permission
   - Verify bot can send messages in the channel

3. **Wait for Propagation:**
   - Global commands can take up to 1 hour to appear
   - Guild-specific commands appear immediately

### Common Error Messages

#### "Interaction failed"
- **Cause**: Bot lacks permissions or is offline
- **Solution**: Check bot permissions and TailSentry status

#### "Rate limit exceeded"
- **Cause**: Too many commands in short time
- **Solution**: Wait 1 minute and try again

#### "Access temporarily blocked"
- **Cause**: Too many failed authorization attempts
- **Solution**: Wait 1 hour or restart TailSentry

#### "You don't have permission"
- **Cause**: User not in `DISCORD_ALLOWED_USERS` list
- **Solution**: Add user ID to allowed users or remove restriction

#### "Found 1 devices in tailnet" with mock-device
- **Cause**: TailscaleClient import failed, bot using fallback mock data
- **Solution**: Ensure Tailscale is properly installed and `tailscale status` command works
- **Debug**: Check logs for TailscaleClient import errors

#### "/devices shows mock data instead of real devices"
- **Cause**: TailscaleService/TailscaleClient integration issue
- **Solution**: Verify Tailscale installation and permissions
- **Debug**: Run `python test_tailscale_devices.py` to test integration

### Debug Tools

Test bot functionality:
```bash
# Test all Discord bot features
python test_discord_functionality.py

# Debug specific command issues
python debug_discord_commands.py

# Test Tailscale device integration
python test_tailscale_devices.py

# Test Discord bot device integration
python test_discord_device_integration.py
```

### Data Integration Verification

If `/devices` shows mock data instead of real devices:

1. **Check Tailscale Installation:**
   ```bash
   tailscale status
   ```
   Should show your actual devices, not "command not found"

2. **Test TailscaleClient Integration:**
   ```bash
   python test_tailscale_devices.py
   ```
   Should show your real devices with proper field names

3. **Verify Discord Bot Integration:**
   ```bash
   python test_discord_device_integration.py
   ```
   Should confirm bot can access real device data

4. **Check Application Logs:**
   ```bash
   # Look for TailscaleClient import errors
   grep "TailscaleClient" logs/tailsentry.log
   
   # Check for fallback to mock data
   grep "mock data" logs/tailsentry.log
   ```

### Log Analysis

Check TailSentry logs for Discord bot issues:
```bash
# View recent logs
tail -f logs/tailsentry.log | grep discord

# Check for specific errors
grep "discord" logs/tailsentry.log | grep ERROR
```

## Advanced Configuration

### Custom Command Prefix

While slash commands are recommended, prefix commands are also supported:

```bash
DISCORD_COMMAND_PREFIX=ts!
```

Then use: `ts!status`, `ts!logs`, etc.

### Multiple Discord Servers

The bot can operate in multiple Discord servers simultaneously. Commands will work in any server where the bot has been invited with proper permissions.

### Webhook Integration

For additional notification channels, configure Discord webhooks:

```bash
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Development Mode

For testing and development:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG

# Test with mock data
TAILSENTRY_FORCE_LIVE_DATA=false
```

## API Integration

The Discord bot integrates with TailSentry's internal APIs:

- **Tailscale Service**: Device information and network status
- **Logging Service**: Application and audit logs
- **Health Service**: System health and metrics
- **Notification Service**: Real-time event handling

## Performance Considerations

### Resource Usage
- **Memory**: ~50MB additional for Discord bot
- **CPU**: Minimal impact (<1% additional usage)
- **Network**: ~1KB per command, ~5KB per notification

### Optimization Tips
- Use `DISCORD_ALLOWED_USERS` to limit access
- Configure specific notification channels to reduce spam
- Monitor audit logs to track usage patterns

## Security Best Practices

1. **Keep Bot Token Secure**: Never share or commit tokens to version control
2. **Restrict Access**: Use `DISCORD_ALLOWED_USERS` for sensitive environments
3. **Monitor Usage**: Review audit logs regularly
4. **Update Regularly**: Keep Discord.py and TailSentry updated
5. **Principle of Least Privilege**: Only grant necessary Discord permissions

## Support and Maintenance

### Regular Maintenance
- Monitor audit logs for unauthorized access attempts
- Update Discord bot permissions as needed
- Review and rotate bot tokens periodically

### Getting Help
- Check TailSentry logs for error messages
- Use debug tools to identify configuration issues
- Review Discord Developer Console for bot status
- Consult TailSentry documentation for integration details

## Migration and Updates

When updating TailSentry:
1. Bot configuration is preserved in `.env` file
2. Command registrations are automatically updated
3. Audit logs and user permissions are maintained
4. No additional setup required for existing installations

---

For additional support, refer to the main [TailSentry README](README.md) or check the project documentation.
