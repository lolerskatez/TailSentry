from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi import status as http_status
import json
import os
import logging
from dotenv import set_key, find_dotenv
from services.tailscale_service import TailscaleClient

router = APIRouter()
tailscale_settings_router = router
logger = logging.getLogger("tailsentry.tailscale_settings")

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'tailscale_settings.json')

def load_settings():
    try:
        with open(SETTINGS_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(settings):
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=2)

@router.get("/api/tailscale-settings")
async def get_tailscale_settings():
    settings = load_settings()
    
    # Set defaults for any missing settings
    defaults = {
        'hostname': 'tailsentry-router',
        'accept_routes': True,
        'accept_dns': False,
        'advertise_exit_node': False,
        'advertised_routes': []
    }
    
    for key, default_value in defaults.items():
        if key not in settings:
            settings[key] = default_value
    
    # Add PAT status (without exposing the actual value)
    settings['tailscale_pat'] = ''  # Don't expose actual API Access Token
    settings['has_pat'] = bool(os.getenv('TAILSCALE_PAT'))
    
    # Add Auth Key status (without exposing the actual value)
    settings['tailscale_auth_key'] = ''  # Don't expose actual Auth Key
    settings['has_auth_key'] = bool(os.getenv('TAILSCALE_AUTH_KEY'))
    
    # Remove legacy auth_key field to avoid confusion
    if 'auth_key' in settings:
        del settings['auth_key']
    
    # Override exit node status from actual Tailscale state (more reliable than saved setting)
    try:
        status = TailscaleClient.status_json()
        logger.info(f"Raw Tailscale status type: {type(status)}")
        if status and isinstance(status, dict) and 'Self' in status:
            self_info = status['Self']
            logger.info(f"Self info type: {type(self_info)}")
            if isinstance(self_info, dict):
                # Check exit node status using the correct fields
                # ExitNodeOption: true means device is currently advertising as exit node
                # ExitNode: true means currently being used as exit node by other peers
                exit_node_option = self_info.get('ExitNodeOption', False)  # Currently advertising as exit node
                exit_node_active = self_info.get('ExitNode', False)  # Currently being used as exit node
                
                # Check for exit node routes in AllowedIPs (when advertising)
                allowed_ips = self_info.get('AllowedIPs', [])
                has_exit_routes = any(ip in allowed_ips for ip in ['0.0.0.0/0', '::/0'])
                
                logger.info(f"ExitNodeOption (advertising): {exit_node_option}, ExitNode (in_use): {exit_node_active}, Has exit routes: {has_exit_routes}")
                
                # The device is acting as exit node if ExitNodeOption is true
                # OR if it has exit routes in AllowedIPs (redundant check)
                is_exit_node = exit_node_option or has_exit_routes
                settings['advertise_exit_node'] = is_exit_node
                
                # Determine detailed status for UI
                if is_exit_node:
                    if exit_node_active:
                        settings['exit_node_status'] = 'active_in_use'
                        logger.info("Exit node is advertising and currently being used by peers")
                    else:
                        settings['exit_node_status'] = 'approved'
                        logger.info("Exit node is advertising and available but not currently being used")
                else:
                    # Check if we have a saved setting indicating user wants exit node enabled
                    # This handles the case where admin approved but device isn't advertising yet
                    saved_setting = settings.get('advertise_exit_node', False)
                    if saved_setting:
                        settings['exit_node_status'] = 'pending_approval'
                        settings['advertise_exit_node'] = True  # Keep UI consistent with user intent
                        logger.info("Exit node requested by user but not yet advertising (may need approval or re-application)")
                    else:
                        settings['exit_node_status'] = 'disabled'
                        settings['advertise_exit_node'] = False
                        logger.info("Exit node is disabled - not advertising")
                
                # Add admin console URL for approval
                tailnet = os.getenv('TAILSCALE_TAILNET', '-')
                if tailnet == '-':
                    settings['admin_console_url'] = 'https://login.tailscale.com/admin/machines'
                else:
                    settings['admin_console_url'] = f'https://login.tailscale.com/admin/machines/{tailnet}'
                
                # Also get advertised routes for subnet routing (separate from exit node)
                advertised_routes = self_info.get('AdvertisedRoutes', [])
                logger.info(f"AdvertisedRoutes: {advertised_routes}")
                
                # Update subnet routes from actual state (exclude exit node routes - these are handled separately)
                if advertised_routes:
                    # For subnet routing, we only care about specific subnets, not exit node routes
                    subnet_routes = [r for r in advertised_routes if r not in ('0.0.0.0/0', '::/0')]
                    settings['advertised_routes'] = subnet_routes
            else:
                logger.warning(f"Self info is not a dict: {self_info}")
        else:
            logger.warning(f"Status is invalid or missing 'Self': {status}")
    except Exception as e:
        logger.error(f"Failed to get current Tailscale state: {e}")
    
    return JSONResponse(settings)

@router.post("/api/tailscale-settings")
async def apply_tailscale_settings(request: Request):
    data = await request.json()
    
    # Handle API Access Token separately - save to .env file
    # Support both old 'tailscale_pat' and new 'tailscale_api_token' keys for backward compatibility
    pat_was_updated = False
    new_pat_value = None
    api_token_key = 'tailscale_api_token' if 'tailscale_api_token' in data else 'tailscale_pat'
    if api_token_key in data:
        pat_value = data.get(api_token_key, '').strip()
        try:
            env_file = find_dotenv()
            if not env_file:
                logger.error("No .env file found")
                return JSONResponse({"success": False, "error": ".env file not found"}, status_code=500)
                
            if pat_value:
                set_key(env_file, 'TAILSCALE_PAT', f"'{pat_value}'")
                logger.info("Tailscale PAT updated successfully")
                pat_was_updated = True
                new_pat_value = pat_value
            else:
                # Clear PAT if empty
                set_key(env_file, 'TAILSCALE_PAT', '')
                logger.info("Tailscale PAT cleared")
        except Exception as e:
            logger.error(f"Failed to update TAILSCALE_PAT in .env: {e}", exc_info=True)
            return JSONResponse({"success": False, "error": f"Failed to update PAT: {e}"}, status_code=500)
    
    # Handle Auth Key separately - save to .env file
    auth_key_was_updated = False
    new_auth_key_value = None
    if 'tailscale_auth_key' in data:
        auth_key_value = data.get('tailscale_auth_key', '').strip()
        try:
            env_file = find_dotenv()
            if not env_file:
                logger.error("No .env file found")
                return JSONResponse({"success": False, "error": ".env file not found"}, status_code=500)
                
            if auth_key_value:
                set_key(env_file, 'TAILSCALE_AUTH_KEY', f"'{auth_key_value}'")
                logger.info("Tailscale Auth Key updated successfully")
                auth_key_was_updated = True
                new_auth_key_value = auth_key_value
            else:
                # Clear Auth Key if empty
                set_key(env_file, 'TAILSCALE_AUTH_KEY', '')
                logger.info("Tailscale Auth Key cleared")
        except Exception as e:
            logger.error(f"Failed to update TAILSCALE_AUTH_KEY in .env: {e}", exc_info=True)
            return JSONResponse({"success": False, "error": f"Failed to update Auth Key: {e}"}, status_code=500)

    # Load current settings
    current_settings = load_settings()
    
    # Update settings with new values (excluding API Access Token and Auth Key)
    settings_data = {k: v for k, v in data.items() if k not in ['tailscale_pat', 'tailscale_api_token', 'tailscale_auth_key']}
    current_settings.update(settings_data)
    
    # Save updated settings to file
    try:
        save_settings(current_settings)
        logger.info(f"Settings saved: {settings_data}")
    except Exception as e:
        logger.error(f"Failed to write tailscale_settings.json: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": f"Failed to write settings: {e}"}, status_code=500)
    
    # Only apply Tailscale configuration in specific cases
    try:
        if auth_key_was_updated and new_auth_key_value:
            # Auth Key updated - need to authenticate with new Auth Key
            logger.info("Auth Key was updated, using it for tailscale up authentication")
            result = TailscaleClient.up(authkey=new_auth_key_value, extra_args=['--reset'])
            # After successful auth, apply all saved settings
            if result is True:
                result = apply_all_settings_to_tailscale(current_settings)
        elif pat_was_updated and new_pat_value:
            # PAT updated - need to authenticate with new PAT (legacy support)
            logger.info("PAT was updated, using it as authkey for tailscale up")
            result = TailscaleClient.up(authkey=new_pat_value, extra_args=['--reset'])
            # After successful auth, apply all saved settings
            if result is True:
                result = apply_all_settings_to_tailscale(current_settings)
        else:
            # Regular setting change - apply all current settings from file
            result = apply_all_settings_to_tailscale(current_settings)
        
        logger.info(f"TailscaleClient operation result: {result}")
        if result is not True:
            logger.error(f"Tailscale operation failed: {result}")
            return JSONResponse({"success": False, "error": str(result)}, status_code=500)
            
        # Generate appropriate success message
        if auth_key_was_updated:
            success_message = "Auth Key updated and device authenticated successfully!"
        elif pat_was_updated:
            success_message = "API Access Token updated and connected to tailnet!"
        else:
            success_message = "Settings applied successfully!"
            
        return JSONResponse({"success": True, "message": success_message})
    except Exception as e:
        logger.error(f"Failed to apply settings via TailscaleClient: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": f"Failed to apply settings: {e}"}, status_code=500)

def apply_all_settings_to_tailscale(settings):
    """
    Build and execute tailscale up command from all current settings.
    This is the single source of truth for applying configuration.
    """
    # Apply defaults to ensure consistency (same as get_tailscale_settings)
    defaults = {
        'hostname': 'tailsentry-router',
        'accept_routes': True,
        'accept_dns': False,
        'advertise_exit_node': False,
        'advertised_routes': []
    }
    
    for key, default_value in defaults.items():
        if key not in settings:
            settings[key] = default_value
    
    logger.info(f"Settings with defaults applied: {settings}")
    
    args = ["--reset"]  # Start clean
    
    # Hostname
    hostname = settings.get('hostname', 'tailsentry-router')
    args.extend(["--hostname", hostname])
    
    # Accept routes
    if settings.get('accept_routes', True):
        args.append("--accept-routes")
    
    # Accept DNS  
    if settings.get('accept_dns', False):
        args.append("--accept-dns")
    
    # Build advertised routes
    advertised_routes = []
    
    # Add subnet routes if configured
    subnet_routes = settings.get('advertised_routes', [])
    if subnet_routes:
        if isinstance(subnet_routes, str):
            subnet_routes = [r.strip() for r in subnet_routes.split(',') if r.strip()]
        advertised_routes.extend(subnet_routes)
    
    # Handle exit node setting with dedicated flag
    advertise_exit = settings.get('advertise_exit_node', False)
    logger.info(f"advertise_exit_node setting: {advertise_exit}")
    if advertise_exit is True:
        args.append("--advertise-exit-node")
        logger.info("Added --advertise-exit-node flag")
    else:
        logger.info("Exit node disabled, not adding exit node flag")
    
    # Apply advertised routes only if we have any (for subnet routing)
    if advertised_routes:
        args.extend(["--advertise-routes", ",".join(advertised_routes)])
        logger.info(f"Final advertised routes: {advertised_routes}")
    else:
        logger.info("No subnet routes to advertise")
    
    # Log the complete command for debugging
    logger.info(f"Applying Tailscale configuration with args: {args}")
    
    return TailscaleClient.up(extra_args=args)

@router.post("/api/subnet-routes")
async def set_subnet_routes(request: Request):
    """Set advertised subnet routes"""
    try:
        data = await request.json()
        routes = data.get("routes", [])
        
        # Save to settings file
        current_settings = load_settings()
        current_settings['advertised_routes'] = routes
        save_settings(current_settings)
        
        # Apply all settings (including the new routes)
        result = apply_all_settings_to_tailscale(current_settings)
        if result is True:
            return JSONResponse({"success": True, "message": "Routes updated successfully"})
        else:
            return JSONResponse({"success": False, "error": str(result)}, status_code=500)
    except Exception as e:
        logger.error(f"Failed to set subnet routes: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/api/accept-routes")
async def set_accept_routes(request: Request):
    """Toggle accept routes setting"""
    try:
        data = await request.json()
        accept_routes = data.get("accept_routes", True)
        
        # Save to settings file
        current_settings = load_settings()
        current_settings['accept_routes'] = accept_routes
        save_settings(current_settings)
        
        # Apply all settings
        result = apply_all_settings_to_tailscale(current_settings)
        if result is True:
            return JSONResponse({"success": True, "message": "Accept routes setting updated"})
        else:
            return JSONResponse({"success": False, "error": str(result)}, status_code=500)
    except Exception as e:
        logger.error(f"Failed to set accept routes: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/api/accept-dns")
async def set_accept_dns(request: Request):
    """Toggle accept DNS setting"""
    try:
        data = await request.json()
        accept_dns = data.get("accept_dns", False)
        
        # Save to settings file
        current_settings = load_settings()
        current_settings['accept_dns'] = accept_dns
        save_settings(current_settings)
        
        # Apply all settings
        result = apply_all_settings_to_tailscale(current_settings)
        if result is True:
            return JSONResponse({"success": True, "message": "Accept DNS setting updated"})
        else:
            return JSONResponse({"success": False, "error": str(result)}, status_code=500)
    except Exception as e:
        logger.error(f"Failed to set accept DNS: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.get("/api/local-subnets")
async def get_local_subnets():
    """Get detected local subnets"""
    try:
        subnets = TailscaleClient.detect_local_subnets()
        return JSONResponse(subnets)
    except Exception as e:
        logger.error(f"Failed to detect local subnets: {e}", exc_info=True)
        return JSONResponse([], status_code=500)

@router.post("/api/exit-node")
async def set_exit_node(request: Request):
    """Set or unset exit node"""
    try:
        data = await request.json()
        node_id = data.get("node_id")  # Frontend sends node_id
        
        if node_id:
            result = TailscaleClient.set_exit_node(True, {"exit_node": node_id})
        else:
            result = TailscaleClient.set_exit_node(False)
            
        if result is True:
            return JSONResponse({"success": True, "message": "Exit node updated successfully"})
        else:
            return JSONResponse({"success": False, "error": str(result)}, status_code=500)
    except Exception as e:
        logger.error(f"Failed to set exit node: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/api/tailscale-service")
async def tailscale_service_control(request: Request):
    """Control Tailscale service (start, stop, restart, status)"""
    try:
        data = await request.json()
        action = data.get("action")
        
        logger.info(f"Tailscale service control requested: {action}")
        
        # Validate action
        allowed_actions = ["start", "stop", "restart", "status", "up", "down"]
        if action not in allowed_actions:
            return JSONResponse({"success": False, "error": f"Invalid action: {action}. Must be one of {allowed_actions}"}, status_code=400)
        
        if action == "status":
            try:
                status = TailscaleClient.service_status()
                return JSONResponse({"success": True, "status": status})
            except Exception as e:
                logger.error(f"Failed to get service status: {e}")
                return JSONResponse({"success": False, "error": f"Failed to get service status: {str(e)}"}, status_code=500)
                
        elif action in ["start", "stop"]:
            # Only allow start/stop, not restart to avoid killing TailSentry
            try:
                result = TailscaleClient.service_control(action)
                logger.info(f"Service control {action} result: {result}")
                
                # Consider it successful if no exception was raised
                if result is True or (isinstance(result, str) and "error" not in result.lower() and "failed" not in result.lower()):
                    return JSONResponse({"success": True, "message": f"Service {action} completed", "details": str(result)})
                else:
                    return JSONResponse({"success": False, "error": str(result)}, status_code=500)
            except Exception as e:
                logger.error(f"Failed to {action} service: {e}")
                return JSONResponse({"success": False, "error": f"Failed to {action} service: {str(e)}"}, status_code=500)
                
        elif action == "restart":
            # For restart, use a safer approach with tailscale down/up instead of systemctl restart
            try:
                logger.info("Using tailscale down/up sequence instead of systemctl restart for safety")
                
                # First try to disconnect
                down_result = TailscaleClient.down()
                logger.info(f"Tailscale down result: {down_result}")
                
                if down_result is not True:
                    return JSONResponse({"success": False, "error": f"Failed to disconnect: {str(down_result)}"}, status_code=500)
                
                # Small delay to ensure clean disconnect
                import asyncio
                await asyncio.sleep(2)
                
                # Then reconnect
                up_result = TailscaleClient.up()
                logger.info(f"Tailscale up result: {up_result}")
                
                if up_result is True:
                    return JSONResponse({"success": True, "message": "Tailscale restarted successfully (down/up sequence)"})
                else:
                    return JSONResponse({"success": False, "error": f"Failed to reconnect after disconnect: {str(up_result)}"}, status_code=500)
                    
            except Exception as e:
                logger.error(f"Failed to restart Tailscale: {e}")
                return JSONResponse({"success": False, "error": f"Failed to restart Tailscale: {str(e)}"}, status_code=500)
                
        elif action == "up":
            try:
                result = TailscaleClient.up()
                logger.info(f"Tailscale up result: {result}")
                
                if result is True:
                    return JSONResponse({"success": True, "message": "Tailscale connected successfully"})
                else:
                    return JSONResponse({"success": False, "error": str(result)}, status_code=500)
            except Exception as e:
                logger.error(f"Failed to bring Tailscale up: {e}")
                return JSONResponse({"success": False, "error": f"Failed to bring Tailscale up: {str(e)}"}, status_code=500)
                
        elif action == "down":
            try:
                result = TailscaleClient.down()
                logger.info(f"Tailscale down result: {result}")
                
                if result is True:
                    return JSONResponse({"success": True, "message": "Tailscale disconnected successfully"})
                else:
                    return JSONResponse({"success": False, "error": str(result)}, status_code=500)
            except Exception as e:
                logger.error(f"Failed to bring Tailscale down: {e}")
                return JSONResponse({"success": False, "error": f"Failed to bring Tailscale down: {str(e)}"}, status_code=500)
                
    except Exception as e:
        logger.error(f"Failed to process service control request: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": f"Failed to process request: {str(e)}"}, status_code=500)

@router.get("/api/tailscale-logs")
async def get_tailscale_logs():
    """Get Tailscale logs"""
    try:
        logs = TailscaleClient.logs()
        return JSONResponse({"success": True, "logs": logs})
    except Exception as e:
        logger.error(f"Failed to get logs: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e), "logs": ""}, status_code=500)

@router.get("/api/network-metrics")
async def get_network_metrics():
    """Get network metrics"""
    try:
        metrics = TailscaleClient.get_network_metrics()
        return JSONResponse({"success": True, "metrics": metrics})
    except Exception as e:
        logger.error(f"Failed to get network metrics: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/api/clear-cache")
async def clear_cache():
    """Clear Tailscale status cache"""
    try:
        TailscaleClient.clear_cache()
        return JSONResponse({"success": True, "message": "Cache cleared successfully"})
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
