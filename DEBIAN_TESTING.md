# TailSentry on Debian 12

## Overview

TailSentry has been updated to work correctly with real Tailscale installations on Debian 12 systems. The main improvements include:

1. Better path detection for Tailscale binaries
2. Debian-specific installation and configuration
3. Production deployment with systemd

## Key Files

- `debian_install.sh` - Automated installation script for Debian systems
- `DEBIAN_DEPLOYMENT.md` - Comprehensive deployment guide
- `debian_config.env` - Example configuration file with Debian-specific settings

## Path Detection

The TailscaleClient class now includes a `get_tailscale_path()` method that:

1. Checks common installation paths based on the platform
2. Falls back to system PATH
3. Works correctly for Debian's typical installation location at `/usr/sbin/tailscale`

## Command Execution

All commands now use the full path to the Tailscale binary:

```python
tailscale_path = TailscaleClient.get_tailscale_path()
cmd = [tailscale_path, "status", "--json"]
```

## Testing on Debian

When testing on your Debian system:

1. Verify that Tailscale is properly installed and authenticated
2. Check that TailSentry can locate the Tailscale binary
3. Ensure that TailSentry has sufficient permissions to execute Tailscale commands
4. Verify that TailSentry can interact with the Tailscaled service

## Notes

- TailSentry requires elevated permissions on Debian to interact with Tailscale
- If you encounter any path-related issues, you can override the Tailscale path in the configuration file
