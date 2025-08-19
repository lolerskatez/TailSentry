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
