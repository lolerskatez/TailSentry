# TailSentry Notifications System

## Overview

TailSentry includes a comprehensive notifications system that supports multiple channels:
- **SMTP Email** - Traditional email notifications
- **Telegram** - Instant messaging via Telegram bots
- **Discord** - Rich notifications via Discord webhooks

The system provides real-time alerts for system events, Tailscale network changes, security incidents, and administrative actions.

## Features

### 🔔 Multi-Channel Support
- **SMTP Email**: Full HTML/text email support with TLS/SSL
- **Telegram**: Rich formatting with HTML/Markdown support
- **Discord**: Rich embeds with custom colors and avatars

### ⚙️ Comprehensive Configuration
- Individual channel enable/disable controls
- Rate limiting to prevent notification spam
- Retry logic for failed deliveries
- Global notification toggle

### 📝 Customizable Templates
- Pre-configured templates for common events
- Custom message formatting with variable substitution
- Enable/disable notifications per event type

### 🔒 Secure Management
- Sensitive credentials safely stored in environment variables
- Masked password fields in the UI
- Secure webhook URL handling

## Setup Instructions

### SMTP Email Configuration

1. Navigate to **Settings > Notifications**
2. Go to the **📧 SMTP Email** tab
3. Configure your email provider settings:

```
SMTP Server: smtp.gmail.com (for Gmail)
Port: 587 (TLS) or 465 (SSL)
Username: your-email@domain.com
Password: your-app-password
From Email: noreply@yourdomain.com
From Name: TailSentry
```

**Popular SMTP Settings:**
- **Gmail**: smtp.gmail.com:587 (TLS)
- **Outlook**: smtp.office365.com:587 (TLS)
- **Yahoo**: smtp.mail.yahoo.com:587 (TLS)
- **Custom**: Your provider's SMTP settings

### Telegram Bot Setup

1. Create a bot by messaging [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy the bot token (format: `123456789:ABCDEF...`)
4. Get your chat ID:
   - For personal messages: Message [@userinfobot](https://t.me/userinfobot)
   - For group chats: Add your bot to the group and get the group chat ID
5. Configure in TailSentry:

```
Bot Token: 123456789:ABCDEF1234567890ABCDEF
Chat ID: 123456789 (personal) or -123456789 (group)
Parse Mode: HTML (recommended)
```

### Discord Webhook Setup

1. Go to your Discord server settings
2. Navigate to **Integrations > Webhooks**
3. Click **"New Webhook"** or **"Create Webhook"**
4. Set a name and select a channel
5. Copy the webhook URL
6. Configure in TailSentry:

```
Webhook URL: https://discord.com/api/webhooks/...
Username: TailSentry
Embed Color: #3498db (blue)
Avatar URL: (optional custom avatar)
```

## Event Types

### System Events
- **system_startup**: TailSentry application started
- **system_shutdown**: TailSentry application stopped
- **configuration_change**: Settings updated by admin
- **security_alert**: Security-related events detected

### Tailscale Events
- **tailscale_connection**: Device connected to Tailscale
- **tailscale_disconnection**: Device disconnected from Tailscale
- **peer_online**: Peer device came online
- **peer_offline**: Peer device went offline
- **subnet_route_change**: Subnet routing configuration changed
- **exit_node_change**: Exit node configuration changed

### Administrative Events
- **backup_completed**: Configuration backup successful
- **backup_failed**: Configuration backup failed
- **health_check_failure**: System health check failed

## Environment Variables

The notification system uses these environment variables (automatically managed):

```bash
# Global Settings
NOTIFICATIONS_ENABLED=true
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_RETRY_DELAY=60
NOTIFICATION_RATE_LIMIT=true
NOTIFICATION_RATE_LIMIT_PER_HOUR=100

# SMTP Settings
SMTP_ENABLED=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_USERNAME=your-email@domain.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=TailSentry

# Telegram Settings
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=123456789:ABCDEF...
TELEGRAM_CHAT_ID=123456789
TELEGRAM_PARSE_MODE=HTML
TELEGRAM_DISABLE_PREVIEW=true

# Discord Settings
DISCORD_ENABLED=false
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_USERNAME=TailSentry
DISCORD_EMBED_COLOR=0x3498db
DISCORD_AVATAR_URL=https://example.com/avatar.png
```

## API Endpoints

### Configuration Management
- `GET /api/notification-settings` - Get current notification configuration
- `POST /api/notification-settings` - Update notification configuration
- `GET /api/notification-templates` - Get notification templates
- `POST /api/notification-templates` - Update notification templates

### Testing and Sending
- `POST /api/test-notification` - Send test notifications
- `POST /api/send-notification` - Send custom notifications

### Example API Usage

```python
# Send a custom notification
import httpx

async def send_custom_notification():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/api/send-notification",
            json={
                "event_type": "security_alert",
                "data": {
                    "details": "Failed login attempt detected",
                    "ip_address": "192.168.1.100",
                    "timestamp": "2024-01-01 12:00:00"
                }
            }
        )
        return response.json()
```

## Integration in Code

The notification system can be easily integrated throughout the application:

```python
from notifications_manager import notifications

# System events
await notifications.notify_system_startup()
await notifications.notify_system_shutdown()

# Tailscale events
await notifications.notify_tailscale_connection("my-device")
await notifications.notify_exit_node_change("exit-node-1")

# Administrative events
await notifications.notify_configuration_change("admin")
await notifications.notify_security_alert("Unauthorized access attempt")

# Custom notifications
await notifications.notify_custom(
    "custom_event",
    message="Custom event occurred",
    severity="high"
)
```

## Rate Limiting

To prevent notification spam, the system includes:
- **Hourly limits**: Configurable maximum notifications per hour
- **Retry logic**: Failed notifications are retried with exponential backoff
- **Global toggle**: Master switch to disable all notifications

## Security Considerations

- **Credential Storage**: Sensitive data (passwords, tokens, webhook URLs) are stored in environment variables
- **Input Validation**: All configuration inputs are validated before saving
- **Access Control**: Notification configuration requires admin authentication
- **Audit Logging**: All configuration changes are logged with user attribution

## Troubleshooting

### Common Issues

1. **SMTP Authentication Failed**
   - Verify username and password
   - Enable "App Passwords" for Gmail/Outlook
   - Check if 2FA is enabled on email account

2. **Telegram Bot Not Responding**
   - Verify bot token format
   - Ensure bot is not blocked
   - Check chat ID format (positive for users, negative for groups)

3. **Discord Webhook Failed**
   - Verify webhook URL is correct
   - Check if webhook was deleted from Discord
   - Ensure webhook has permission to post to channel

4. **Notifications Not Sending**
   - Check global notification toggle
   - Verify rate limits haven't been exceeded
   - Review application logs for error messages

### Debugging

Enable debug logging to troubleshoot issues:

```bash
LOG_LEVEL=DEBUG
```

Check the logs at `logs/tailsentry.log` for detailed error information.

## Advanced Configuration

### Custom Templates

You can customize notification templates using variable substitution:

```json
{
  "custom_event": {
    "title": "🚨 {severity} Alert",
    "message": "Event: {event_name}\nTime: {timestamp}\nDetails: {details}",
    "enabled": true
  }
}
```

### Webhook Testing

Test webhooks using curl:

```bash
# Test Discord webhook
curl -X POST "YOUR_DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "TailSentry",
    "embeds": [{
      "title": "Test Message",
      "description": "This is a test from TailSentry",
      "color": 3447003
    }]
  }'
```

### Multiple Chat IDs

For multiple Telegram recipients, you can set up multiple notification configurations or use Telegram groups.

## Performance

The notification system is designed for high performance:
- **Asynchronous**: All notifications are sent asynchronously
- **Non-blocking**: Failed notifications don't block the main application
- **Efficient**: Minimal resource usage with connection pooling
- **Scalable**: Rate limiting prevents resource exhaustion

---

For additional support or feature requests, please refer to the main TailSentry documentation or open an issue on the project repository.
