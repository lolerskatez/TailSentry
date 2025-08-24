# Hostname Setting Feature Implementation

## Overview
Added a hostname setting field to the Tailscale Settings page that allows users to set a custom hostname for their device in the Tailnet using the Tailscale CLI.

## Frontend Changes (`templates/tailscale_settings.html`)

### 1. New Hostname Setting Section
Added a new section in the Basic Settings tab:
```html
<div class="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
    <div class="flex items-center justify-between mb-4">
        <h4 class="text-lg font-medium text-gray-800 dark:text-gray-200">Device Hostname</h4>
    </div>
    <form @submit.prevent="saveHostname">
        <div class="flex gap-2">
            <input type="text" x-model="hostname" :placeholder="status?.Self?.HostName || 'Enter hostname...'" 
                   class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-800 dark:text-white">
            <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md font-medium">
                Save
            </button>
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Set a custom hostname for this device in the Tailnet. Current: <span x-text="status?.Self?.HostName || 'Unknown'" class="font-mono"></span>
        </p>
    </form>
</div>
```

### 2. JavaScript Data Variable
Added `hostname: ''` to the Alpine.js data section.

### 3. Save Hostname Function
Added `saveHostname()` function that:
- Sends POST request to `/api/tailscale-settings` with hostname parameter
- Shows success/error messages
- Refreshes status to display updated hostname
- Clears the input field on success

## Backend Changes

### 1. TailscaleClient Service (`services/tailscale_service.py`)
Added `set_hostname()` static method:
```python
@staticmethod
def set_hostname(hostname: str):
    """Set the hostname for this Tailscale device"""
    if not hostname or not hostname.strip():
        return {"error": "Hostname cannot be empty"}
        
    tailscale_path = TailscaleClient.get_tailscale_path()
    cmd = [tailscale_path, "set", "--hostname", hostname.strip()]
    
    try:
        logger.info(f"Setting Tailscale hostname: {hostname}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            logger.info(f"Hostname set successfully to: {hostname}")
            return {"success": True, "hostname": hostname}
        else:
            error_msg = f"Failed to set hostname (exit code {result.returncode})"
            if result.stderr:
                error_msg += f": {result.stderr}"
            logger.error(error_msg)
            return {"error": error_msg}
    except Exception as e:
        logger.error(f"Exception setting hostname: {str(e)}")
        return {"error": str(e)}
```

### 2. Tailscale Settings API (`routes/tailscale_settings.py`)
Added hostname handling in the POST endpoint:
- Checks for `hostname` parameter in request data
- Calls `TailscaleClient.set_hostname()` with the provided value
- Returns appropriate success/error responses
- Excludes hostname from JSON file storage (handled via CLI)

## Usage

1. **Access**: Go to Tailscale Settings → Basic tab
2. **Current Hostname**: Displayed in the helper text showing current device hostname
3. **Set New Hostname**: 
   - Enter desired hostname in the input field
   - Click "Save" button
   - Success message will confirm the change
   - Status will refresh to show new hostname

## Technical Details

### Tailscale CLI Command
Uses: `tailscale set --hostname <hostname>`

### API Endpoint
- **URL**: `/api/tailscale-settings`
- **Method**: POST
- **Payload**: `{"hostname": "new-hostname"}`
- **Response**: `{"success": true}` or `{"success": false, "error": "error message"}`

### Error Handling
- Empty hostname validation
- Tailscale CLI execution errors
- Network/API errors
- User feedback via toast messages

## Security Considerations
- Hostname validation prevents empty values
- Uses existing Tailscale authentication (no additional permissions needed)
- Commands are executed safely via subprocess with proper error handling

## Benefits
- Easy hostname management directly from TailSentry interface
- Real-time feedback and status updates
- Consistent with other Tailscale settings in the same interface
- Uses official Tailscale CLI for reliability
