import logging
import json
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette import status
from services.sso_service import sso_manager
import services.sso_service as sso_service
from services.sso_auth import sso_auth
from auth_user import create_or_update_sso_user
from routes.user import get_current_user

logger = logging.getLogger("tailsentry.sso")
router = APIRouter()

# Templates
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@router.get("/sso/login/{provider}")
async def sso_login(provider: str, request: Request):
    """Initiate SSO login for a provider"""
    try:
        if not sso_manager.is_sso_enabled():
            raise HTTPException(status_code=404, detail="SSO is not enabled")
        
        if provider not in sso_manager.config.get_enabled_providers():
            raise HTTPException(status_code=404, detail="Provider not enabled")
        
        # Get authorization URL
        auth_url, state = sso_auth.get_authorization_url(provider, request)
        
        logger.info(f"[SSO] Redirecting to {provider} for authentication")
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.error(f"[SSO] Login initiation failed for {provider}: {e}")
        return RedirectResponse(url="/login?error=sso_error")

@router.get("/sso/callback/{provider}")
async def sso_callback(provider: str, request: Request):
    """Handle SSO callback from provider"""
    try:
        if not sso_manager.is_sso_enabled():
            raise HTTPException(status_code=404, detail="SSO is not enabled")
        
        # Handle the callback
        user_info = await sso_auth.handle_callback(provider, request)
        
        if not user_info:
            logger.warning(f"[SSO] No user info received from {provider}")
            return RedirectResponse(url="/login?error=sso_failed")
        
        # Check if auto-registration is allowed
        config = sso_manager.config.get_all_config()
        allow_auto_registration = config.get("allow_auto_registration", True)
        
        if not user_info.get("email"):
            logger.warning(f"[SSO] No email provided by {provider}")
            return RedirectResponse(url="/login?error=no_email")
        
        # Create or update user
        user = create_or_update_sso_user(
            sso_provider=provider,
            sso_user_id=user_info["user_id"],
            email=user_info["email"],
            display_name=user_info["name"] or user_info["email"],
            sso_metadata=user_info["raw_data"]
        )
        
        if not user:
            if allow_auto_registration:
                logger.error(f"[SSO] Failed to create user for {provider}:{user_info.get('email')}")
                return RedirectResponse(url="/login?error=user_creation_failed")
            else:
                logger.warning(f"[SSO] Auto-registration disabled, user not found: {user_info.get('email')}")
                return RedirectResponse(url="/login?error=registration_disabled")
        
        # Check if user account is active
        if not user.get("active", 1):
            logger.warning(f"[SSO] Login attempt for disabled SSO account: {user['username']}")
            return RedirectResponse(url="/login?error=account_disabled")
        
        # Set session
        request.session["user"] = user["username"]
        request.session["sso_login"] = True
        
        # Send login notification
        try:
            import notifications_manager
            await notifications_manager.notify_user_login(
                username=user["username"],
                ip_address=request.client.host if request.client else "unknown"
            )
        except Exception as e:
            logger.error(f"[SSO] Failed to send login notification: {e}")
        
        logger.info(f"[SSO] Successful login for user: {user['username']} via {provider}")
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SSO] Callback failed for {provider}: {e}")
        return RedirectResponse(url="/login?error=sso_callback_failed")

@router.get("/api/sso/providers")
async def get_sso_providers():
    """Get available SSO providers for login"""
    try:
        providers = sso_manager.get_login_providers()
        return {"providers": providers, "enabled": sso_manager.is_sso_enabled()}
    except Exception as e:
        logger.error(f"Failed to get SSO providers: {e}")
        return JSONResponse({"error": "Failed to get providers"}, status_code=500)

@router.post("/api/sso/discover")
async def discover_oidc_endpoints(request: Request):
    """Discover OIDC endpoints from issuer URL"""
    try:
        data = await request.json()
        issuer_url = data.get("issuer_url", "").strip()
        
        if not issuer_url:
            return JSONResponse({"error": "Issuer URL is required"}, status_code=400)
        
        success, endpoints, error = await sso_manager.discover_oidc_endpoints(issuer_url)
        
        if success:
            return {"success": True, "endpoints": endpoints}
        else:
            return JSONResponse({"error": error}, status_code=400)
            
    except Exception as e:
        logger.error(f"OIDC discovery failed: {e}")
        return JSONResponse({"error": "Discovery failed"}, status_code=500)

# Admin routes for SSO configuration
@router.get("/settings/sso")
async def sso_settings(request: Request, user=Depends(get_current_user)):
    """SSO settings page"""
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    try:
        config = sso_manager.config.get_all_config()
        
        return templates.TemplateResponse("sso_settings.html", {
            "request": request,
            "current_user": user,
            "sso_config": config
        })
    except Exception as e:
        logger.error(f"Failed to load SSO settings: {e}")
        return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

@router.post("/settings/sso/toggle")
async def toggle_sso(request: Request, enabled: bool = Form(...), user=Depends(get_current_user)):
    """Toggle SSO globally"""
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    try:
        if enabled:
            sso_manager.config.enable_sso()
            logger.info(f"[SSO] SSO enabled by admin: {user['username']}")
        else:
            sso_manager.config.disable_sso()
            logger.info(f"[SSO] SSO disabled by admin: {user['username']}")
        
        return RedirectResponse(url="/settings/sso", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Failed to toggle SSO: {e}")
        return RedirectResponse(url="/settings/sso?error=toggle_failed", status_code=status.HTTP_302_FOUND)

@router.post("/settings/sso/provider/add")
async def add_sso_provider(
    request: Request,
    name: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    issuer_url: str = Form(""),
    authorization_endpoint: str = Form(""),
    token_endpoint: str = Form(""),
    userinfo_endpoint: str = Form(""),
    jwks_uri: str = Form(""),
    scopes: str = Form("openid email profile"),
    response_type: str = Form("code"),
    prompt: str = Form(""),
    login_hint: str = Form(""),
    group_claim: str = Form(""),
    role_mappings: str = Form(""),
    logo_url: str = Form(""),
    enabled: bool = Form(False),
    user=Depends(get_current_user)
):
    """Add a new comprehensive OIDC SSO provider"""
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    try:
        # Parse role mappings from JSON string if provided
        parsed_role_mappings = {}
        if role_mappings.strip():
            try:
                parsed_role_mappings = json.loads(role_mappings)
            except json.JSONDecodeError:
                return RedirectResponse(
                    url="/settings/sso?error=Invalid role mappings JSON format",
                    status_code=status.HTTP_302_FOUND
                )
        
        provider_config = {
            "name": name.strip(),
            "client_id": client_id.strip(),
            "client_secret": client_secret.strip(),
            "issuer_url": issuer_url.strip(),
            "authorization_endpoint": authorization_endpoint.strip(),
            "token_endpoint": token_endpoint.strip(),
            "userinfo_endpoint": userinfo_endpoint.strip(),
            "jwks_uri": jwks_uri.strip(),
            "scopes": [scope.strip() for scope in scopes.split(",") if scope.strip()],
            "response_type": response_type.strip() or "code",
            "prompt": prompt.strip(),
            "login_hint": login_hint.strip(),
            "group_claim": group_claim.strip(),
            "role_mappings": parsed_role_mappings,
            "logo_url": logo_url.strip(),
            "enabled": enabled
        }
        
        # If issuer_url is provided, try to auto-discover endpoints
        if provider_config["issuer_url"] and not all([
            provider_config["authorization_endpoint"],
            provider_config["token_endpoint"],
            provider_config["userinfo_endpoint"]
        ]):
            try:
                success, discovered, error = await sso_manager.discover_oidc_endpoints(provider_config["issuer_url"])
                if success:
                    # Auto-populate discovered endpoints
                    for key, value in discovered.items():
                        if value and not provider_config.get(key):
                            provider_config[key] = value
                    logger.info(f"[SSO] Auto-discovered OIDC endpoints for {name}")
                else:
                    logger.warning(f"[SSO] OIDC discovery failed for {name}: {error}")
            except Exception as e:
                logger.error(f"[SSO] OIDC discovery error for {name}: {e}")
        
        # Validate configuration
        is_valid, error_msg = sso_manager.validate_provider_config(provider_config)
        if not is_valid:
            logger.warning(f"[SSO] Invalid configuration for new provider: {error_msg}")
            return RedirectResponse(
                url=f"/settings/sso?error={error_msg}",
                status_code=status.HTTP_302_FOUND
            )
        
        # Add the provider
        provider_id = sso_manager.add_provider(name, provider_config)
        
        # Re-initialize providers if SSO is enabled
        if sso_manager.is_sso_enabled():
            sso_auth.initialize_providers()
        
        logger.info(f"[SSO] Provider {name} (ID: {provider_id}) added by admin: {user['username']}")
        return RedirectResponse(url="/settings/sso", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Failed to add SSO provider: {e}")
        return RedirectResponse(
            url="/settings/sso?error=add_failed",
            status_code=status.HTTP_302_FOUND
        )

@router.post("/settings/sso/provider/{provider_id}/update")
async def update_sso_provider(
    provider_id: str,
    request: Request,
    name: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    issuer_url: str = Form(""),
    authorization_endpoint: str = Form(""),
    token_endpoint: str = Form(""),
    userinfo_endpoint: str = Form(""),
    jwks_uri: str = Form(""),
    scopes: str = Form("openid email profile"),
    response_type: str = Form("code"),
    prompt: str = Form(""),
    login_hint: str = Form(""),
    group_claim: str = Form(""),
    role_mappings: str = Form(""),
    logo_url: str = Form(""),
    enabled: bool = Form(False),
    user=Depends(get_current_user)
):
    """Update an existing comprehensive OIDC SSO provider"""
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    try:
        # Parse role mappings if provided
        parsed_role_mappings = None
        if role_mappings.strip():
            try:
                parsed_role_mappings = json.loads(role_mappings.strip())
            except json.JSONDecodeError:
                logger.error(f"Invalid role mappings JSON for provider {provider_id}")
                return RedirectResponse(
                    url="/settings/sso?error=invalid_role_mappings",
                    status_code=status.HTTP_302_FOUND
                )
        
        # Build comprehensive provider config
        provider_config = {
            "name": name.strip(),
            "client_id": client_id.strip(),
            "client_secret": client_secret.strip(),
            "enabled": enabled,
            "scopes": [scope.strip() for scope in scopes.split(",") if scope.strip()],
            "response_type": response_type.strip() or "code"
        }
        
        # Add OIDC discovery fields
        if issuer_url.strip():
            provider_config["issuer_url"] = issuer_url.strip()
        
        # Add manual endpoints (fallback if discovery fails)
        if authorization_endpoint.strip():
            provider_config["authorization_endpoint"] = authorization_endpoint.strip()
        if token_endpoint.strip():
            provider_config["token_endpoint"] = token_endpoint.strip()
        if userinfo_endpoint.strip():
            provider_config["userinfo_endpoint"] = userinfo_endpoint.strip()
        if jwks_uri.strip():
            provider_config["jwks_uri"] = jwks_uri.strip()
        
        # Add advanced OIDC fields
        if prompt.strip():
            provider_config["prompt"] = prompt.strip()
        if login_hint.strip():
            provider_config["login_hint"] = login_hint.strip()
        if group_claim.strip():
            provider_config["group_claim"] = group_claim.strip()
        if parsed_role_mappings:
            provider_config["role_mappings"] = parsed_role_mappings
        if logo_url.strip():
            provider_config["logo_url"] = logo_url.strip()
        
        # Validate the provider configuration
        is_valid, error_msg = sso_manager.validate_provider_config(provider_config)
        if not is_valid:
            logger.error(f"Invalid provider config for update {provider_id}: {error_msg}")
            return RedirectResponse(
                url=f"/settings/sso?error={error_msg}",
                status_code=status.HTTP_302_FOUND
            )
        
        # Update the provider
        sso_manager.update_provider(provider_id, provider_config)
        
        # Re-initialize providers if SSO is enabled
        if sso_manager.is_sso_enabled():
            sso_auth.initialize_providers()
        
        logger.info(f"[SSO] Provider {provider_id} updated by admin: {user['username']}")
        return RedirectResponse(url="/settings/sso", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Failed to update SSO provider {provider_id}: {e}")
        return RedirectResponse(
            url="/settings/sso?error=update_failed",
            status_code=status.HTTP_302_FOUND
        )

@router.post("/settings/sso/provider/{provider_id}/delete")
async def delete_sso_provider(
    provider_id: str,
    request: Request,
    user=Depends(get_current_user)
):
    """Delete an SSO provider"""
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    try:
        # Remove the provider
        sso_manager.remove_provider(provider_id)
        
        # Re-initialize providers if SSO is enabled
        if sso_manager.is_sso_enabled():
            sso_auth.initialize_providers()
        
        logger.info(f"[SSO] Provider {provider_id} deleted by admin: {user['username']}")
        return RedirectResponse(url="/settings/sso", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Failed to delete SSO provider {provider_id}: {e}")
        return RedirectResponse(
            url="/settings/sso?error=delete_failed",
            status_code=status.HTTP_302_FOUND
        )
