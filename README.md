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
1. Copy `.env.example` to `.env` and fill in secrets.
2. Hash your admin password (see below).
3. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080
   ```

## Hashing Password
Use bcrypt or argon2 to hash your password:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'YOURPASS', bcrypt.gensalt()).decode())"
```
Paste the hash into `.env` as `ADMIN_PASSWORD_HASH`.

## Deployment
- Use NGINX or Caddy for HTTPS and IP restriction.
- Dockerfile included for container deployment.

## Requirements
- Python 3.9+
- Tailscale installed and running
- Debian 12+/Ubuntu 22.04+

## License
MIT
