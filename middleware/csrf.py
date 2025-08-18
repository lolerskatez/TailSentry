"""CSRF protection middleware."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import secrets
import logging

logger = logging.getLogger("tailsentry")

class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        csrf_cookie_name: str = "csrf_token",
        csrf_header_name: str = "X-CSRF-Token",
        safe_methods: set = {"GET", "HEAD", "OPTIONS"},
        exempt_paths: set = {"/login", "/"}  # Exempt login from CSRF
    ):
        super().__init__(app)
        self.csrf_cookie_name = csrf_cookie_name
        self.csrf_header_name = csrf_header_name
        self.safe_methods = safe_methods
        self.exempt_paths = exempt_paths

    def _is_exempt(self, path: str) -> bool:
        # Exempt if exact match or if path starts with any exempt path ending with '*'
        for exempt in self.exempt_paths:
            if exempt.endswith('*'):
                if path.startswith(exempt[:-1]):
                    return True
            elif path == exempt:
                return True
        return False
    
    def _generate_csrf_token(self) -> str:
        """Generate a secure CSRF token."""
        return secrets.token_urlsafe(32)
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request/response and enforce CSRF protection."""
        # Skip CSRF check for safe methods or exempt paths (with wildcard support)
        if request.method in self.safe_methods or self._is_exempt(request.url.path):
            response = await call_next(request)
            # Set CSRF cookie if not present
            if self.csrf_cookie_name not in request.cookies:
                response.set_cookie(
                    key=self.csrf_cookie_name,
                    value=self._generate_csrf_token(),
                    httponly=True,
                    secure=not request.url.scheme == "http",
                    samesite="strict"
                )
            return response

        # For unsafe methods, verify CSRF token
        csrf_cookie = request.cookies.get(self.csrf_cookie_name)
        csrf_header = request.headers.get(self.csrf_header_name)

        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            logger.warning(
                f"CSRF validation failed for {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'} | "
                f"Exempt paths: {self.exempt_paths} | "
                f"Method: {request.method} | "
                f"CSRF cookie: {csrf_cookie} | CSRF header: {csrf_header}"
            )
            raise HTTPException(
                status_code=403,
                detail="CSRF token validation failed"
            )

        return await call_next(request)
