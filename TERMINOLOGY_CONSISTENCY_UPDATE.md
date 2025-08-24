# Terminology Consistency Update

## Overview
Updated TailSentry to use consistent terminology aligned with Tailscale's official documentation. Changed "Personal Access Token" and "API Access Token" references to "Tailscale API Key" throughout the user interface and documentation.

## Changes Made

### 1. Frontend Template Updates (`templates/tailscale_settings.html`)
- **Section Header**: "API Access Token (Optional)" → "Tailscale API Key (Optional)"
- **Input Placeholder**: "Enter Tailscale API Access Token" → "Enter Tailscale API Key"
- **Success Messages**: "API Access Token saved successfully" → "Tailscale API Key saved successfully"
- **Error Messages**: "Error saving API Access Token" → "Error saving Tailscale API Key"
- **API Response Field**: Updated JavaScript to use `has_api_key` instead of `has_pat`

### 2. Backend API Updates (`routes/tailscale_settings.py`)
- **Response Fields**: 
  - `tailscale_pat` → `tailscale_api_key`
  - `has_pat` → `has_api_key`
- **Comments**: Updated all comments to refer to "Tailscale API Key" instead of "API Access Token"

### 3. API Endpoint Updates (`routes/api.py`)
- **Variable Names**: `has_api_token` → `has_api_key` throughout all endpoints
- **Comments**: Updated comments to use "Tailscale API Key" terminology

### 4. Configuration Updates (`.env.example`)
- **Comments**: Updated TAILSCALE_PAT description to "Tailscale API Key" instead of "API Access Token"

## Technical Details

### Environment Variable
- **Kept**: `TAILSCALE_PAT` environment variable name unchanged for backwards compatibility
- **Updated**: All user-facing documentation and comments to refer to "Tailscale API Key"

### API Response Structure
**Before:**
```json
{
  "tailscale_pat": "",
  "has_pat": true
}
```

**After:**
```json
{
  "tailscale_api_key": "",
  "has_api_key": true
}
```

### Status Indicators
- Auth Key section: Shows "Configured" when valid auth key is present (either in TAILSCALE_AUTH_KEY env var or legacy JSON file)
- API Key section: Shows "Configured" when TAILSCALE_PAT environment variable is set

## Backwards Compatibility
- Environment variable `TAILSCALE_PAT` remains unchanged
- API accepts both old and new field names for settings updates
- Existing configurations continue to work without changes

## User Impact
- More consistent and clear terminology aligned with Tailscale documentation
- Clearer distinction between Auth Keys (for device authentication) and API Keys (for API access)
- Status indicators now properly reflect actual configuration state

## Verification
After these changes:
1. Auth Key shows "Configured" when you have a working Tailscale connection
2. API Key shows "Configured" only when TAILSCALE_PAT environment variable is set
3. All user-facing text consistently uses "Tailscale API Key" terminology
