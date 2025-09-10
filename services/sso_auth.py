import os
import secrets
import logging
import aiohttp
import json
from urllib.parse import urlencode, quote
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException
from services.sso_service import sso_manager

logger = logging.getLogger("tailsentry.sso_auth")

class SSOAuth:
    """SSO Authentication Handler using simple OAuth2 flow"""
    
    def __init__(self):
        self._configured_providers = {}
    
    def configure_provider(self, provider_id: str, config: Dict):
        """Configure OAuth client for a provider"""
        try:
            # For dynamic providers, we use the config directly since all info is stored there
            self._configured_providers[provider_id] = {
                "config": config,
                "info": {
                    "name": config.get("name", provider_id),
                    "authorization_endpoint": config.get("authorization_endpoint"),
                    "token_endpoint": config.get("token_endpoint"),
                    "userinfo_endpoint": config.get("userinfo_endpoint"),
                    "scopes": config.get("scopes", ["openid", "email", "profile"])
                }
            }
            
            logger.info(f"Configured SSO provider: {config.get('name', provider_id)} (ID: {provider_id})")
            
        except Exception as e:
            logger.error(f"Failed to configure SSO provider {provider_id}: {e}")
            raise
    
    def get_authorization_url(self, provider: str, request: Request) -> Tuple[str, str]:
        """Get authorization URL for SSO login"""
        if provider not in self._configured_providers:
            raise ValueError(f"Provider not configured: {provider}")
        
        provider_config = self._configured_providers[provider]
        provider_info = provider_config["info"]
        config = provider_config["config"]
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state in session
        request.session[f"sso_state_{provider}"] = state
        
        # Get redirect URI
        redirect_uri = str(request.url_for("sso_callback", provider=provider))
        
        # Build authorization URL
        params = {
            "client_id": config["client_id"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(provider_info["scopes"]),
            "state": state
        }
        
        # Use custom endpoints for custom OIDC
        if provider == "custom_oidc":
            auth_endpoint = config.get("authorization_endpoint")
        else:
            auth_endpoint = provider_info["authorization_endpoint"]
        
        authorization_url = f"{auth_endpoint}?{urlencode(params)}"
        
        return authorization_url, state
    
    async def handle_callback(self, provider: str, request: Request) -> Optional[Dict]:
        """Handle SSO callback and return user info"""
        if provider not in self._configured_providers:
            raise ValueError(f"Provider not configured: {provider}")
        
        # Verify state parameter
        state = request.query_params.get("state")
        stored_state = request.session.get(f"sso_state_{provider}")
        
        if not state or state != stored_state:
            logger.warning(f"SSO state mismatch for provider {provider}")
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Clean up state from session
        request.session.pop(f"sso_state_{provider}", None)
        
        # Handle authorization code
        code = request.query_params.get("code")
        if not code:
            error = request.query_params.get("error", "unknown_error")
            logger.warning(f"SSO authorization failed for {provider}: {error}")
            raise HTTPException(status_code=400, detail=f"Authorization failed: {error}")
        
        try:
            # Exchange code for token
            access_token = await self._exchange_code_for_token(provider, code, request)
            
            # Get user information
            user_info = await self._get_user_info(provider, access_token)
            
            logger.info(f"SSO authentication successful for {provider}: {user_info.get('email', 'no-email')}")
            return user_info
            
        except Exception as e:
            logger.error(f"SSO callback failed for {provider}: {e}")
            raise HTTPException(status_code=400, detail="Authentication failed")
    
    async def _exchange_code_for_token(self, provider: str, code: str, request: Request) -> str:
        """Exchange authorization code for access token"""
        provider_config = self._configured_providers[provider]
        provider_info = provider_config["info"]
        config = provider_config["config"]
        
        # Use custom token endpoint for custom OIDC
        if provider == "custom_oidc":
            token_endpoint = config.get("token_endpoint")
        else:
            token_endpoint = provider_info["token_endpoint"]
        
        redirect_uri = str(request.url_for("sso_callback", provider=provider))
        
        data = {
            "grant_type": "authorization_code",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_endpoint, data=data, headers=headers) as response:
                if response.status == 200:
                    token_data = await response.json()
                    return token_data.get("access_token")
                else:
                    error_text = await response.text()
                    logger.error(f"Token exchange failed for {provider}: {response.status} - {error_text}")
                    raise Exception(f"Token exchange failed: {response.status}")
    
    async def _get_user_info(self, provider: str, access_token: str) -> Dict:
        """Get user information from SSO provider"""
        provider_config = self._configured_providers[provider]
        provider_info = provider_config["info"]
        
        # Use custom userinfo endpoint for custom OIDC
        if provider == "custom_oidc":
            userinfo_endpoint = provider_config["config"].get("userinfo_endpoint")
        else:
            userinfo_endpoint = provider_info["userinfo_endpoint"]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(userinfo_endpoint, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        return self._normalize_user_info(provider, user_data)
                    else:
                        logger.error(f"Failed to get user info from {provider}: {response.status}")
                        raise Exception(f"Failed to get user info: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error getting user info from {provider}: {e}")
            raise
    
    def _normalize_user_info(self, provider: str, user_data: Dict) -> Dict:
        """Normalize user information from different providers"""
        if provider == "google":
            return {
                "provider": provider,
                "user_id": user_data.get("id"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "given_name": user_data.get("given_name"),
                "family_name": user_data.get("family_name"),
                "picture": user_data.get("picture"),
                "raw_data": user_data
            }
        
        elif provider == "microsoft":
            return {
                "provider": provider,
                "user_id": user_data.get("id"),
                "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                "name": user_data.get("displayName"),
                "given_name": user_data.get("givenName"),
                "family_name": user_data.get("surname"),
                "picture": None,
                "raw_data": user_data
            }
        
        elif provider == "github":
            return {
                "provider": provider,
                "user_id": str(user_data.get("id")),
                "email": user_data.get("email"),
                "name": user_data.get("name") or user_data.get("login"),
                "given_name": None,
                "family_name": None,
                "picture": user_data.get("avatar_url"),
                "raw_data": user_data
            }
        
        elif provider == "custom_oidc":
            return {
                "provider": provider,
                "user_id": user_data.get("sub") or user_data.get("id"),
                "email": user_data.get("email"),
                "name": user_data.get("name") or user_data.get("preferred_username"),
                "given_name": user_data.get("given_name"),
                "family_name": user_data.get("family_name"),
                "picture": user_data.get("picture"),
                "raw_data": user_data
            }
        
        else:
            # Generic normalization
            return {
                "provider": provider,
                "user_id": user_data.get("id") or user_data.get("sub"),
                "email": user_data.get("email"),
                "name": user_data.get("name") or user_data.get("display_name"),
                "given_name": user_data.get("given_name"),
                "family_name": user_data.get("family_name"),
                "picture": user_data.get("picture") or user_data.get("avatar_url"),
                "raw_data": user_data
            }
    
    def initialize_providers(self):
        """Initialize all configured and enabled providers"""
        if not sso_manager.is_sso_enabled():
            logger.info("SSO is disabled, skipping provider initialization")
            return
        
        # Clear existing providers
        self._configured_providers = {}
        
        # Get all providers from the config
        all_providers = sso_manager.config.get_all_providers()
        
        for provider_id, provider_config in all_providers.items():
            if provider_config.get("enabled", False):
                try:
                    self.configure_provider(provider_id, provider_config)
                except Exception as e:
                    logger.error(f"Failed to initialize SSO provider {provider_id}: {e}")

# Global SSO auth instance
sso_auth = SSOAuth()
