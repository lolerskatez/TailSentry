# Environment Variable Update: TAILSCALE_PAT → TAILSCALE_API_KEY

## Overview
Updated the environment variable name from `TAILSCALE_PAT` to `TAILSCALE_API_KEY` throughout the TailSentry codebase to align with consistent "Tailscale API Key" terminology.

## Files Updated

### 1. Configuration Files
- **`.env.example`**: Updated variable name and comments
  - `TAILSCALE_PAT=` → `TAILSCALE_API_KEY=`
  - Removed duplicate entry
  - Updated comment examples

### 2. Core Service Files
- **`services/tailscale_service.py`**: 
  - Updated global variable: `TAILSCALE_PAT = os.getenv("TAILSCALE_PAT")` → `TAILSCALE_API_KEY = os.getenv("TAILSCALE_API_KEY")`
  - Updated all references in API request functions
  - Updated error messages and logging

### 3. Route Files
- **`routes/tailscale_settings.py`**:
  - Updated environment variable checks
  - Updated .env file writing operations
  - Updated error logging messages

- **`routes/api.py`**:
  - Updated all API endpoint mode detection logic
  - Updated environment variable checks throughout all endpoints
  - Fixed import statement that was corrupted during replacement

- **`routes/tailsentry_settings.py`**:
  - Updated TailscaleSettings class field: `tailscale_pat` → `tailscale_api_key`
  - Updated environment variable loading and saving
  - Updated API response fields

## Environment Variable Migration

### Before:
```bash
TAILSCALE_PAT=tskey-api-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### After:
```bash
TAILSCALE_API_KEY=tskey-api-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## API Response Changes

### Before:
```json
{
  "tailscale_api_key": "",
  "has_api_key": true
}
```

### After: 
(Response structure remains the same, but now reads from `TAILSCALE_API_KEY` environment variable)

## Migration Notes

**BREAKING CHANGE**: Existing deployments will need to update their environment variables:

1. **Manual Migration Required**:
   ```bash
   # In your .env file, change:
   TAILSCALE_PAT=your-api-key-here
   # to:
   TAILSCALE_API_KEY=your-api-key-here
   ```

2. **Docker/Container Deployments**:
   - Update docker-compose.yml environment variables
   - Update any deployment scripts or Kubernetes manifests
   - Update systemd service files if applicable

3. **Verification**:
   - Check that TailSentry can still access Tailscale API after the change
   - Verify that "Configured" indicator appears correctly in the UI
   - Test API functionality to ensure endpoints work properly

## Files That Reference the Environment Variable

All the following files now use `TAILSCALE_API_KEY`:
- `services/tailscale_service.py` (main API client)
- `routes/api.py` (all API endpoints)
- `routes/tailscale_settings.py` (settings management)
- `routes/tailsentry_settings.py` (configuration export)
- `.env.example` (documentation)

## Backwards Compatibility

**⚠️ This is a breaking change** - there is no backwards compatibility. All deployments must update their environment variable names from `TAILSCALE_PAT` to `TAILSCALE_API_KEY`.

## Testing Checklist

After updating:
- [ ] Restart TailSentry service
- [ ] Verify "Configured" indicator appears for Tailscale API Key
- [ ] Test API endpoints that require Tailscale API access
- [ ] Check logs for any environment variable related errors
- [ ] Verify CLI-only mode still works when API key is not set
