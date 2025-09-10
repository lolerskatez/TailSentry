import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid

logger = logging.getLogger("tailsentry.sso")

class SSOConfig:
    """SSO Configuration Management"""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "config" / "sso_config.json"
        self.config_path.parent.mkdir(exist_ok=True)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load SSO configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load SSO config: {e}")
        
        # Return default configuration
        return {
            "enabled": False,
            "allow_auto_registration": True,
            "default_role": "user",
            "providers": {}
        }
    
    def _save_config(self):
        """Save SSO configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info("SSO configuration saved")
        except Exception as e:
            logger.error(f"Failed to save SSO config: {e}")
            raise
    
    def is_enabled(self) -> bool:
        """Check if SSO is enabled"""
        return self._config.get("enabled", False)
    
    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled SSO providers"""
        if not self.is_enabled():
            return []
        
        enabled = []
        for provider, config in self._config.get("providers", {}).items():
            if config.get("enabled", False):
                enabled.append(provider)
        return enabled
    
    def get_provider_config(self, provider: str) -> Optional[Dict]:
        """Get configuration for a specific provider"""
        return self._config.get("providers", {}).get(provider)
    
    def set_provider_config(self, provider: str, config: Dict):
        """Set configuration for a specific provider"""
        if "providers" not in self._config:
            self._config["providers"] = {}
        
        self._config["providers"][provider] = config
        self._save_config()
    
    def remove_provider(self, provider: str):
        """Remove a provider configuration"""
        if "providers" in self._config and provider in self._config["providers"]:
            del self._config["providers"][provider]
            self._save_config()
    
    def enable_sso(self):
        """Enable SSO globally"""
        self._config["enabled"] = True
        self._save_config()
    
    def disable_sso(self):
        """Disable SSO globally"""
        self._config["enabled"] = False
        self._save_config()
    
    def get_all_config(self) -> Dict:
        """Get complete SSO configuration"""
        return self._config.copy()
    
    def update_config(self, config: Dict):
        """Update SSO configuration"""
        self._config.update(config)
        self._save_config()
    
    def get_all_providers(self) -> Dict:
        """Get all configured providers"""
        return self._config.get("providers", {})

class SSOManager:
    """Main SSO Management Class"""
    
    def __init__(self):
        self.config = SSOConfig()
    
    def is_sso_enabled(self) -> bool:
        """Check if SSO is enabled"""
        return self.config.is_enabled()
    
    def get_login_providers(self) -> List[Dict]:
        """Get list of providers available for login"""
        if not self.is_sso_enabled():
            return []
        
        login_providers = []
        for provider_id, provider_config in self.config.get_all_providers().items():
            if provider_config.get("enabled", False):
                login_providers.append({
                    "id": provider_id,
                    "name": provider_config.get("name", provider_id),
                    "enabled": True
                })
        
        return login_providers
    
    def add_provider(self, name: str, config: Dict) -> str:
        """Add a new SSO provider"""
        # Generate a unique provider ID
        provider_id = f"provider_{uuid.uuid4().hex[:8]}"
        
        # Ensure the provider has a name
        config["name"] = name
        config["enabled"] = config.get("enabled", False)
        
        # Save the provider configuration
        self.config.set_provider_config(provider_id, config)
        
        logger.info(f"Added SSO provider: {name} (ID: {provider_id})")
        return provider_id
    
    def update_provider(self, provider_id: str, config: Dict):
        """Update an existing SSO provider"""
        existing_config = self.config.get_provider_config(provider_id)
        if not existing_config:
            raise ValueError(f"Provider {provider_id} not found")
        
        # Merge with existing config
        updated_config = existing_config.copy()
        updated_config.update(config)
        
        self.config.set_provider_config(provider_id, updated_config)
        logger.info(f"Updated SSO provider: {provider_id}")
    
    def remove_provider(self, provider_id: str):
        """Remove an SSO provider"""
        self.config.remove_provider(provider_id)
        logger.info(f"Removed SSO provider: {provider_id}")
    
    def get_provider(self, provider_id: str) -> Optional[Dict]:
        """Get a specific provider configuration"""
        return self.config.get_provider_config(provider_id)
    
    def validate_provider_config(self, config: Dict) -> tuple[bool, str]:
        """Validate comprehensive OIDC provider configuration"""
        
        # Required core fields
        required_fields = ["name", "client_id", "client_secret"]
        for field in required_fields:
            if not config.get(field):
                return False, f"Missing required field: {field}"
        
        # Either issuer_url OR manual endpoints are required
        has_issuer = config.get("issuer_url", "").strip()
        has_endpoints = all([
            config.get("authorization_endpoint", "").strip(),
            config.get("token_endpoint", "").strip(),
            config.get("userinfo_endpoint", "").strip()
        ])
        
        if not has_issuer and not has_endpoints:
            return False, "Either 'Issuer URL' OR all manual endpoints (authorization, token, userinfo) must be provided"
        
        # Validate URLs if provided
        url_fields = [
            "issuer_url", "authorization_endpoint", "token_endpoint", 
            "userinfo_endpoint", "jwks_uri"
        ]
        for field in url_fields:
            url = config.get(field, "").strip()
            if url and not url.startswith(("http://", "https://")):
                return False, f"{field} must be a valid URL"
        
        # Validate response_type if provided
        response_type = config.get("response_type", "code").strip()
        valid_response_types = ["code", "token", "id_token", "code token", "code id_token", "token id_token", "code token id_token"]
        if response_type and response_type not in valid_response_types:
            return False, f"Invalid response_type. Must be one of: {', '.join(valid_response_types)}"
        
        # Validate role mappings if provided
        role_mappings = config.get("role_mappings", {})
        if role_mappings:
            valid_roles = ["admin", "user", "readonly"]
            for idp_role, tailsentry_role in role_mappings.items():
                if tailsentry_role not in valid_roles:
                    return False, f"Invalid role mapping '{idp_role}' → '{tailsentry_role}'. Valid TailSentry roles: {', '.join(valid_roles)}"
        
        return True, ""
    
    async def discover_oidc_endpoints(self, issuer_url: str) -> tuple[bool, Dict, str]:
        """Discover OIDC endpoints from issuer URL"""
        try:
            # Ensure issuer URL doesn't end with slash
            issuer_url = issuer_url.rstrip('/')
            discovery_url = f"{issuer_url}/.well-known/openid-configuration"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(discovery_url, timeout=10) as response:
                    if response.status == 200:
                        config = await response.json()
                        
                        discovered_endpoints = {
                            "authorization_endpoint": config.get("authorization_endpoint"),
                            "token_endpoint": config.get("token_endpoint"),
                            "userinfo_endpoint": config.get("userinfo_endpoint"),
                            "jwks_uri": config.get("jwks_uri"),
                            "issuer": config.get("issuer"),
                            "scopes_supported": config.get("scopes_supported", ["openid", "email", "profile"]),
                            "response_types_supported": config.get("response_types_supported", ["code"])
                        }
                        
                        return True, discovered_endpoints, ""
                    else:
                        return False, {}, f"Failed to discover OIDC configuration: HTTP {response.status}"
                        
        except asyncio.TimeoutError:
            return False, {}, "Discovery request timed out"
        except Exception as e:
            return False, {}, f"Discovery failed: {str(e)}"

# Global SSO manager instance
sso_manager = SSOManager()
