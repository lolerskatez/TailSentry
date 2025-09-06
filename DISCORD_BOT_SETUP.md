# 🤖 TailSentry Discord Bot Complete Setup Guide

This guide provides step-by-step instructions to set up the TailSentry Discord bot for interactive commands and log monitoring.

## 📋 Prerequisites

- TailSentry installed and running
- Discord account with server admin permissions
- Access to Discord Developer Portal

## 🚀 Step 1: Create Discord Application & Bot

### 1.1 Create Application
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Enter application name: `TailSentry` (or your preferred name)
4. Click **"Create"**

### 1.2 Create Bot
1. In your application, click **"Bot"** in the left sidebar
2. Click **"Add Bot"**
3. Confirm by clicking **"Yes, do it!"**

### 1.3 Configure Bot Settings
1. **Bot Username**: Set to `TailSentry` or your preferred name
2. **Bot Avatar**: Upload an icon (optional)
3. **Public Bot**: ✅ Enable (allows others to invite your bot)
4. **Require OAuth2 Code Grant**: ❌ Disable

### 1.4 Bot Permissions & Intents
**Important**: We don't need privileged intents since we use slash commands.

**Gateway Intents** (leave these DISABLED):
- ❌ Presence Intent
- ❌ Server Members Intent  
- ❌ Message Content Intent *(Not needed for slash commands)*

## 🔑 Step 2: Get Bot Token

1. In the **"Bot"** section, find **"Token"**
2. Click **"Reset Token"** (if this is a new bot)
3. Click **"Copy"** to copy the bot token
4. **⚠️ IMPORTANT**: Keep this token secure and never share it publicly

## 🔗 Step 3: Generate Bot Invite URL

### 3.1 Configure OAuth2 Scopes
1. Go to **"OAuth2"** → **"URL Generator"** in the left sidebar
2. **Select Scopes**:
   - ✅ `bot`
   - ✅ `applications.commands`

### 3.2 Configure Bot Permissions
**Select these permissions**:
- ✅ `View Channels`
- ✅ `Send Messages`
- ✅ `Use Slash Commands`
- ✅ `Read Message History`
- ✅ `Embed Links` (for status embeds)

### 3.3 Copy Invite URL
1. Copy the **Generated URL** at the bottom
2. Save this URL - you'll need it to invite the bot

## ⚙️ Step 4: Configure TailSentry

### 4.1 Environment Variables
Add these to your `.env` file:

```bash
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_BOT_ENABLED=true
DISCORD_COMMAND_PREFIX=!

# Optional: Restrict bot access to specific users
DISCORD_ALLOWED_USERS=user_id1,user_id2,username1,username2

# Optional: Channel-specific notifications
DISCORD_LOG_CHANNEL_ID=channel_id_here
DISCORD_STATUS_CHANNEL_ID=channel_id_here
```

### 4.2 Required Settings
**Minimum required configuration**:
```bash
DISCORD_BOT_TOKEN=your_actual_bot_token_here
DISCORD_BOT_ENABLED=true
```

### 4.3 Optional Security Settings

**Restrict Access by User ID**:
```bash
DISCORD_ALLOWED_USERS=123456789012345678,987654321098765432
```

**Restrict Access by Username**:
```bash
DISCORD_ALLOWED_USERS=username1,username2
```

**Mixed Access Control**:
```bash
DISCORD_ALLOWED_USERS=123456789012345678,username1,987654321098765432
```

## 🏠 Step 5: Invite Bot to Your Server

### 5.1 Use Invite URL
1. Open the **invite URL** you generated in Step 3.3
2. **Select your Discord server** from the dropdown
3. **Verify permissions** are correct
4. Click **"Authorize"**
5. Complete any **CAPTCHA** if prompted

### 5.2 Verify Bot Joined
1. Check your Discord server member list
2. You should see **TailSentry** (or your bot name) with a "BOT" tag
3. The bot should appear **online** (green status)

## 🔄 Step 6: Start/Restart TailSentry

### 6.1 Restart TailSentry
```bash
# Stop TailSentry if running (Ctrl+C)
# Then restart:
python main.py
```

### 6.2 Verify Bot Connection
Check the logs for these success messages:
```
INFO - tailsentry.discord_bot - Discord bot logged in as TailSentry#8455
INFO - tailsentry.discord_bot - Bot ID: 1413414223945662506
INFO - tailsentry.discord_bot - Connected to 1 guilds  # Should be 1+ (not 0)
INFO - tailsentry.discord_bot - Attempting to sync slash commands...
INFO - tailsentry.discord_bot - Synced 3 slash commands
INFO - tailsentry.discord_bot - Registered command: /logs - Get recent logs from TailSentry
INFO - tailsentry.discord_bot - Registered command: /status - Get TailSentry status
INFO - tailsentry.discord_bot - Registered command: /help - Show available commands
```

**❌ If you see "Connected to 0 guilds"**: The bot hasn't been invited to any servers yet.

## 🎮 Step 7: Test Bot Commands

### 7.1 Available Commands
In your Discord server, type `/` and you should see:

- **`/logs [lines] [level]`** - Get recent TailSentry logs
  - `lines`: Number of lines (1-1000, default: 50)
  - `level`: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  
- **`/status`** - Get TailSentry system status

- **`/help`** - Show command help

### 7.2 Example Usage
```
/logs
/logs lines:100
/logs level:ERROR
/logs lines:50 level:WARNING
/status
/help
```

### 7.3 Expected Response
- Commands should respond immediately
- Logs should be formatted in code blocks
- Status should show system information in an embed
- Access should be restricted if `DISCORD_ALLOWED_USERS` is configured

## 🛠️ Troubleshooting

### Bot Not Responding
**Check these items**:

1. **Bot Token**: Verify `DISCORD_BOT_TOKEN` in `.env` is correct
2. **Bot Online**: Bot should show as online in server member list
3. **Permissions**: Bot needs `Use Slash Commands` permission
4. **Guild Count**: Logs should show "Connected to 1+ guilds" (not 0)
5. **Command Sync**: Logs should show "Synced 3 slash commands"

### Commands Not Appearing
**Possible solutions**:

1. **Refresh Discord**: Press `Ctrl+R` or restart Discord client
2. **Re-invite Bot**: Use OAuth2 URL again with `applications.commands` scope
3. **Check Permissions**: Ensure bot has `Use Slash Commands` permission
4. **Wait for Sync**: Slash commands can take up to 1 hour to appear globally

### Permission Denied
**If users get "permission denied" errors**:

1. **Check User Restrictions**: Verify `DISCORD_ALLOWED_USERS` configuration
2. **User ID vs Username**: Make sure you're using the correct format
3. **Case Sensitivity**: Usernames are case-sensitive

### Getting User IDs
**To find Discord User IDs**:

1. **Enable Developer Mode**: Discord Settings → Advanced → Developer Mode
2. **Right-click user** → **Copy ID**
3. **Use in config**: `DISCORD_ALLOWED_USERS=123456789012345678`

## 🔒 Security Best Practices

### 1. Bot Token Security
- ✅ Never commit bot tokens to version control
- ✅ Use environment variables (`.env` file)
- ✅ Regularly rotate bot tokens
- ✅ Restrict `.env` file permissions

### 2. Access Control
- ✅ Use `DISCORD_ALLOWED_USERS` to restrict access
- ✅ Limit bot to specific channels if needed
- ✅ Monitor bot usage in logs
- ✅ Review bot permissions regularly

### 3. Server Security
- ✅ Only invite bot to servers you control
- ✅ Review bot permissions before authorizing
- ✅ Monitor bot activity
- ✅ Remove bot access if compromised

## 📝 Configuration Reference

### Complete .env Example
```bash
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_actual_bot_token_here
DISCORD_BOT_ENABLED=true
DISCORD_COMMAND_PREFIX=!
DISCORD_ALLOWED_USERS=123456789012345678,admin_user,987654321098765432

# Optional: Channel Configuration
DISCORD_LOG_CHANNEL_ID=1234567890123456789
DISCORD_STATUS_CHANNEL_ID=9876543210987654321

# Discord Webhook (separate from bot)
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_id/your_webhook_token
```

### Environment Variable Reference
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | ✅ Yes | None | Bot token from Discord Developer Portal |
| `DISCORD_BOT_ENABLED` | No | `false` | Enable/disable bot functionality |
| `DISCORD_COMMAND_PREFIX` | No | `!` | Prefix for legacy commands (not used with slash commands) |
| `DISCORD_ALLOWED_USERS` | No | None | Comma-separated list of user IDs/usernames allowed to use bot |
| `DISCORD_LOG_CHANNEL_ID` | No | None | Channel ID for log notifications |
| `DISCORD_STATUS_CHANNEL_ID` | No | None | Channel ID for status updates |

## 🎉 Success!

If everything is configured correctly, you should now have:

- ✅ Discord bot online in your server
- ✅ Slash commands (`/logs`, `/status`, `/help`) available
- ✅ Bot responding to commands with TailSentry data
- ✅ Access control working (if configured)
- ✅ Detailed logging in TailSentry logs

Your TailSentry Discord bot is now ready for monitoring and log retrieval! 🚀

## 📞 Support

If you encounter issues:

1. **Check TailSentry logs** for error messages
2. **Verify Discord Developer Portal** settings
3. **Test bot permissions** in Discord server settings
4. **Review this guide** for missed steps
5. **Check Discord API status** at https://discordstatus.com

---

*Last updated: September 5, 2025*
