# TailSentry: Lightweight Tailscale Dashboard

A secure, minimal FastAPI + TailwindCSS dashboard for managing a Tailscale subnet router/exit node.

## Features
- Secure login (bcrypt/argon2, session cookies)
- Dashboard: status, peers, stats
- Subnet routing, exit node controls
- Device list, service controls
- Config file management
- Tailscale key management (API)
- Modular, production-ready code

## Quick Start
1. **Install Tailscale** (if not already installed):
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

2. **Install TailSentry**:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/lolerskatez/TailSentry/main/install.sh | sudo bash
   ```

3. **Access the dashboard**:
   - Open http://localhost:8080 in your browser
   - Complete the onboarding wizard to set up your admin account

For manual installation or development setup:
```bash
git clone https://github.com/lolerskatez/TailSentry.git
cd TailSentry
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

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
