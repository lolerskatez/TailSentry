# TailSentry 🛡️

TailSentry is a secure, web-based management dashboard for Tailscale networks. It provides an intuitive interface for managing devices, users, and network configurations while maintaining enterprise-grade security standards.

## ✨ Features

- **Device Management**: View, organize, and control all Tailscale devices
- **User Management**: Comprehensive user administration with RBAC
- **Security Monitoring**: Real-time security alerts and audit logging
- **Network Analytics**: Traffic insights and performance monitoring
- **Multi-platform**: Runs on Linux bare metal or Docker containers
- **API Integration**: Full REST API for automation and integration

## 🚀 Quick Installation

### Interactive Setup (Recommended)
```bash
# Download setup script
wget https://raw.githubusercontent.com/lolerskatez/TailSentry/main/setup.sh
chmod +x setup.sh

# Run interactive installation
sudo ./setup.sh
```

### Command Line Install
```bash
# Fresh installation
sudo ./setup.sh install

# Update existing installation
sudo ./setup.sh update

# Show status
sudo ./setup.sh status
```

### Docker Deployment
```bash
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry
cp .env.example .env  # Configure your settings
docker-compose -f docker-compose.prod.yml up -d
```

> **Note**: The installer automatically configures secure defaults for production use. The interactive menu provides safe options for installation, updates, and management.

## 📋 Prerequisites

- **Linux system** (Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+)
- **Python 3.9+** with pip and venv
- **Tailscale** installed and configured
- **512MB+ RAM** and **1GB+ disk space**

### Pre-installation Check
```bash
# Install Tailscale first
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Ensure system requirements are met
sudo apt-get install -y python3 python3-venv python3-pip git curl
```

## ⚙️ Configuration

After installation:

1. **Access TailSentry**: http://localhost:8080
2. **Default login**: admin/admin123 (⚠️ change immediately!)
3. **Configure Tailscale**: Add your PAT in settings
4. **Set up notifications**: Configure email/webhook alerts

For detailed configuration options, see [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md).

## 🤖 Discord Bot Setup (Optional)

TailSentry includes an optional Discord bot for interactive log retrieval and status monitoring.

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Copy the bot token

### 2. Configure Bot Permissions

In the "Bot" section:
- Enable "Message Content Intent" under "Privileged Gateway Intents"
- Set bot permissions (optional but recommended):
  - Send Messages
  - Read Message History
  - Use Slash Commands

### 3. Invite Bot to Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`, `applications.commands`
3. Select permissions: `Send Messages`, `Read Messages`
4. Use the generated URL to invite the bot

### 4. Configure TailSentry

Add to your `.env` file:
```bash
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_ALLOWED_USERS=user_id1,user_id2  # Optional: restrict to specific users
```

### 5. Bot Commands

Once configured, use these commands in Discord:

- `!logs [lines] [level]` - Get recent logs (default: 50 lines)
  - Example: `!logs 100 ERROR`
- `!status` - Get TailSentry status
- `!help` - Show available commands

### Security Notes

- **Restrict Access**: Use `DISCORD_ALLOWED_USERS` to limit who can use commands
- **Log Access**: Only administrators should have access to logs
- **Bot Token**: Keep your bot token secure and never commit to version control

## 🔧 Management Commands

### Bare Metal Installation
```bash
sudo ./setup.sh status            # Check status
sudo ./setup.sh update            # Update application
sudo ./setup.sh                   # Interactive menu for all options
systemctl status tailsentry       # Check service status
journalctl -u tailsentry -f       # View logs
```

### Docker Installation
```bash
./docker-deploy.sh status         # Check status
./docker-deploy.sh update         # Update containers
./docker-deploy.sh logs           # View logs
./docker-deploy.sh restart        # Restart containers
```

## 📖 Documentation

- **[Installation Guide](INSTALLATION.md)** - Complete installation instructions
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment best practices
- **[Security Guide](SECURITY.md)** - Security configuration and hardening
- **[API Documentation](routes/)** - REST API reference

## Contributing & Developer Onboarding

### Quick Setup
1. Copy `.env.example` to `.env` and fill in required values (see comments in the file).
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Install frontend test dependencies:
   ```bash
   npm install --save-dev jest @testing-library/dom @testing-library/jest-dom
   ```
4. Run backend tests:
   ```bash
   python -m unittest tests.py
   ```
5. Run frontend tests:
   ```bash
   npx jest static/alt_dashboard.test.js
   ```

### Troubleshooting
- If you see platform or bytes/string errors, ensure you are not globally mocking subprocess or platform internals in live mode.
- For Tailscale CLI errors, check that the binary is installed and in your PATH.
- For session/auth issues, ensure `SESSION_SECRET` is set and cookies are enabled in your browser.
- For rate limiting or CORS issues, check your `.env` and FastAPI middleware settings.

### How to Contribute
- Fork the repo and create a feature branch.
- Add or update tests for your changes.
- Run all tests and ensure they pass in both live and mock modes.
- Open a pull request with a clear description of your changes and testing steps.

We welcome improvements to security, UI/UX, documentation, and test coverage!
## Testing & Development

### Running Tests
TailSentry includes a robust test suite that works with both real Tailscale data and mock data.

- **Live mode (default):**
   - Runs tests against your actual Tailscale environment.
   - To run:
      ```bash
      python -m unittest tests.py
      ```
- **Mock mode:**
   - Uses mocked Tailscale responses for safe, repeatable tests.
   - To enable, set the environment variable:
      ```bash
      set TAILSENTRY_FORCE_LIVE_DATA=false  # Windows
      export TAILSENTRY_FORCE_LIVE_DATA=false  # Linux/macOS
      python -m unittest tests.py
      ```

### Troubleshooting Platform Detection
If you see errors like `TypeError: cannot use a string pattern on a bytes-like object` from the `platform` module, ensure you are not mocking `subprocess.check_output` globally. The codebase now includes robust fallbacks for platform detection, but avoid patching core Python internals in live mode.

### Code Quality & Maintainability
- Alpine.js frontend logic is DRY and uses reusable helpers for feedback/loading.
- Backend Tailscale CLI integration is robust and always includes all required flags.
- Tests are compatible with both real and mock data, and skip or relax assertions as needed.
- All platform detection is robust to bytes/string mismatches and works on Windows, Linux, and macOS.
# TailSentry: Lightweight Tailscale Dashboard

A secure, minimal FastAPI + TailwindCSS dashboard for managing a Tailscale subnet router/exit node.

## Features
- Secure login (bcrypt/argon2, session cookies)
- Dashboard: status, peers, stats
- Subnet routing, exit node controls
- Device list, service controls
- Config file management
- Tailscale key management (API)
- **🔔 Multi-channel notifications (SMTP, Telegram, Discord)**
- Modular, production-ready code

## Quick Start
1. **Install Tailscale** (if not already installed):
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

2. **Install TailSentry**:
   ```bash
   wget https://raw.githubusercontent.com/lolerskatez/TailSentry/main/setup.sh
   chmod +x setup.sh
   sudo ./setup.sh
   ```

3. **Access the dashboard**:
   - Open http://localhost:8080 in your browser
   - Login with admin/admin123 and change password


For manual installation or development setup:
```bash
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Project Structure

- `config/` — All configuration and environment files (`.env`, `tailscale_settings.json`, etc.)
- `services/` — Core business logic modules (e.g., `tailscale_service.py`, `rbac_service.py`)
- `routes/` — API route handlers
- `middleware/` — Custom FastAPI middleware
- `static/`, `templates/` — Frontend assets and HTML templates
- `tests/` — Automated test suite (`tests.py`), with manual/diagnostic scripts in `tests/manual/`
- `scripts/` — Deployment, backup, and test scripts

## Configuration

All environment and config files are now in the `config/` directory. Update your `.env` and `tailscale_settings.json` there. Scripts and services reference these new paths.

### Notifications Setup

TailSentry includes a comprehensive notifications system supporting SMTP email, Telegram, and Discord. See [NOTIFICATIONS.md](NOTIFICATIONS.md) for detailed setup instructions.

Quick setup:
1. Go to **Settings > Notifications** in the web interface
2. Configure your preferred notification channels
3. Test notifications to ensure proper delivery

Supported events include system startup/shutdown, Tailscale network changes, security alerts, and configuration updates.

## Running Tests

Run all automated tests:
```bash
python -m unittest tests.py
```

Manual/diagnostic scripts are in `tests/manual/` (see `test_real_data.py`, `test_auth_api.py`, etc.).
The first time you run TailSentry, you'll be prompted to create an admin account. This will automatically generate a secure session key and store your credentials safely.

## Deployment
- Use NGINX or Caddy for HTTPS and IP restriction.
- Dockerfile included for container deployment.

## Requirements
- Python 3.9+
- Tailscale installed and running
- Debian 12+/Ubuntu 22.04+

## License
MIT
