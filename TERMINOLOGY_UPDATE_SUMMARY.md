# TailSentry Terminology Standardization Update

## Overview
Updated TailSentry to use official Tailscale terminology and distinguish between different types of keys to reduce user confusion.

## Key Changes Made

### 1. Terminology Standardization
- **Old**: "Personal Access Token (PAT)" 
- **New**: "API Access Token"
- This aligns with official Tailscale documentation and reduces confusion

### 2. Clear Distinction Between Key Types

#### Auth Keys (tskey-auth-...)
- **Purpose**: Device registration and initial authentication
- **Format**: `tskey-auth-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Usage**: One-time device onboarding to tailnet
- **UI Location**: "Device Authentication" section

#### API Access Tokens (tskey-api-...)
- **Purpose**: Management operations via Tailscale API
- **Format**: `tskey-api-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Usage**: Ongoing dashboard functionality, device management, settings
- **UI Location**: "API Access Token" section

### 3. Files Updated

#### Frontend Templates
- `templates/tailscale_settings.html`:
  - Updated labels: "Personal Access Token" → "API Access Token"
  - Enhanced descriptions to clarify purpose and format
  - Updated section header: "Machine Authentication" → "Device Authentication"
  - Updated JavaScript functions: `savePatToken()` → `saveApiToken()`
  - Updated variable names: `personalAccessToken` → `apiAccessToken`
  - Updated API payload: `tailscale_pat` → `tailscale_api_token`

#### Backend Routes
- `routes/tailscale_settings.py`:
  - Added backward compatibility for both `tailscale_pat` and `tailscale_api_token` keys
  - Updated comments to reflect new terminology
  - Enhanced error messages

#### Services
- `services/tailscale_service.py`:
  - Updated error messages to use "API Access Token" terminology
  - Enhanced warning messages for clarity

#### Documentation
- `TAILSCALE_INTEGRATION.md`: Updated section headers
- `QUICK_FIX_INSTRUCTIONS.md`: Updated setup instructions
- `INSTALLATION_GUIDE.md`: Updated PAT references
- `SECURITY.md`: Already used correct tskey-api- format

#### Configuration Files
- `.env.example`: Updated comments and examples to show correct token format
- `config/.env.example`: Updated token description

### 4. Backward Compatibility
The backend now accepts both parameter names:
- `tailscale_pat` (legacy)
- `tailscale_api_token` (new)

This ensures existing installations continue to work while new users get the clearer terminology.

### 5. Environment Variable
The `TAILSCALE_PAT` environment variable name remains unchanged to avoid breaking existing deployments, but documentation now clearly indicates it should contain an API Access Token (tskey-api-...).

## Benefits
1. **Reduced Confusion**: Clear distinction between Auth Keys and API Access Tokens
2. **Official Terminology**: Aligns with Tailscale's documentation
3. **Better UX**: Users understand what each key type is for
4. **Backward Compatible**: Existing installations continue working
5. **Future-Proof**: Consistent with Tailscale's API evolution

## User Impact
- **New Users**: See clear, official terminology from the start
- **Existing Users**: Continue using current setup without interruption
- **Documentation**: More accurate and helpful guidance

This update significantly improves the user experience by eliminating confusion about Tailscale key types and purposes.
