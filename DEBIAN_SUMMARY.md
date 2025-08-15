# TailSentry Improvements for Debian Systems

## Changes Made

1. **Added Path Detection**
   - Created `get_tailscale_path()` method to locate Tailscale binary
   - Added platform-specific search paths including Debian default locations
   - Made all commands use the detected Tailscale path

2. **Added Constants**
   - Added `STATUS_CACHE_FILE` to fix caching issues
   - Added `TAILSCALE_PATHS` dictionary with platform-specific paths

3. **Added Debian-Specific Files**
   - Created `debian_install.sh` for easy installation
   - Created `DEBIAN_DEPLOYMENT.md` with comprehensive setup instructions
   - Created `debian_config.env` as a template for Debian deployments

4. **Enhanced Logging**
   - Added more detailed logging for Tailscale commands
   - Better error handling for command failures

## How to Deploy on Debian

1. Transfer all TailSentry files to your Debian system
2. Make the installation script executable:
   ```bash
   chmod +x debian_install.sh
   ```
3. Run the installation script as root:
   ```bash
   sudo ./debian_install.sh
   ```
4. Set an admin password:
   ```bash
   cd /opt/tailsentry
   python change_password.py admin
   ```
5. Access the dashboard at `http://<server-ip>:8000`

## Manual Path Configuration

If the automatic path detection doesn't work, you can manually set the Tailscale path in the configuration:

1. Edit `/etc/tailsentry/config.env`
2. Uncomment and set the Tailscale path:
   ```
   TAILSCALE_PATH=/path/to/tailscale
   ```

## Notes

- No mock implementations are used - TailSentry now works directly with real Tailscale
- All Tailscale commands are executed with the full path to avoid PATH issues
- The service runs as root to ensure proper permissions for Tailscale operations
