"""Security headers middleware for enhanced protection."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from typing import Dict, List, Union
import logging

logger = logging.getLogger("tailsentry")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, csp: Union[Dict[str, List[str]], None] = None):
        """Initialize with optional CSP directives."""
        super().__init__(app)
        self.csp = csp or {}
    
    def _build_csp_header(self) -> str:
        """Build Content Security Policy header value."""
        directives = []
        for directive, sources in self.csp.items():
            directive_value = f"{directive} {' '.join(sources)}"
            directives.append(directive_value)
        return "; ".join(directives)
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Add security headers to response."""
        client_ip = request.client.host if request.client else request.headers.get("X-Forwarded-For", "unknown")
        
        try:
            response = await call_next(request)
            
            # Standard security headers
            response.headers.update({
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Embedder-Policy": "require-corp"
            })
            
            # Log potentially suspicious requests
            if request.headers.get("User-Agent", "").lower().startswith(("curl", "postman", "insomnia")):
                logger.warning(
                    f"API tool detected - IP: {client_ip}, "
                    f"Path: {request.url.path}, "
                    f"User-Agent: {request.headers.get('User-Agent')}"
                )
            
            # Add CSP header if configured
            if self.csp:
                csp_value = self._build_csp_header()
                response.headers["Content-Security-Policy"] = csp_value
            
            # In production, ensure HTTPS
            if not request.url.scheme == "https":
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}", exc_info=True)
            raise
