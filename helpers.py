from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import logging
import os
import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Configure logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Enhanced logging configuration
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logging.basicConfig(
    level=getattr(logging, log_level),
    format=log_format,
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "tailsentry.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("tailsentry")

# Prometheus metrics
if os.getenv("METRICS_ENABLED", "false").lower() == "true":
    REQUEST_COUNT = Counter('tailsentry_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
    REQUEST_DURATION = Histogram('tailsentry_request_duration_seconds', 'Request duration')
    ACTIVE_CONNECTIONS = Gauge('tailsentry_websocket_connections', 'Active WebSocket connections')
    TAILSCALE_PEERS = Gauge('tailsentry_tailscale_peers', 'Number of Tailscale peers')
else:
    REQUEST_COUNT = REQUEST_DURATION = ACTIVE_CONNECTIONS = TAILSCALE_PEERS = None

# Create background scheduler
scheduler = BackgroundScheduler()

# Background tasks
def update_status_cache():
    """Update cached Tailscale status"""
    from tailscale_client import TailscaleClient
    try:
        logger.debug("Updating Tailscale status cache...")
        status = TailscaleClient.status_json()
        
        # Update metrics if enabled
        if TAILSCALE_PEERS and "Peer" in status:
            TAILSCALE_PEERS.set(len(status["Peer"]))
            
    except Exception as e:
        logger.error(f"Error updating status cache: {e}")

def cleanup_old_logs():
    """Clean up old log files"""
    try:
        import glob
        log_files = glob.glob(os.path.join(log_dir, "*.log.*"))
        cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30 days
        
        for log_file in log_files:
            if os.path.getmtime(log_file) < cutoff_time:
                os.remove(log_file)
                logger.info(f"Removed old log file: {log_file}")
                
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")

# Start scheduler
def start_scheduler():
    # Update status every minute
    scheduler.add_job(update_status_cache, 'interval', minutes=1, id='status_cache')
    # Clean up logs daily
    scheduler.add_job(cleanup_old_logs, 'interval', hours=24, id='log_cleanup')
    scheduler.start()
    logger.info("Background scheduler started")

# Shutdown scheduler
def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Background scheduler stopped")

# Rate limiting middleware
class RateLimitMiddleware:
    def __init__(self, app, requests_per_minute=60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.request_times = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        client_ip = scope.get("client", ["unknown"])[0]
        current_time = time.time()
        
        # Clean old entries
        self.request_times = {
            ip: times for ip, times in self.request_times.items()
            if any(t > current_time - 60 for t in times)
        }
        
        # Check rate limit
        if client_ip in self.request_times:
            self.request_times[client_ip] = [
                t for t in self.request_times[client_ip] 
                if t > current_time - 60
            ]
            if len(self.request_times[client_ip]) >= self.requests_per_minute:
                await self._send_rate_limit_response(send)
                return
        else:
            self.request_times[client_ip] = []
            
        self.request_times[client_ip].append(current_time)
        await self.app(scope, receive, send)

    async def _send_rate_limit_response(self, send):
        response = {
            "type": "http.response.start",
            "status": 429,
            "headers": [
                [b"content-type", b"application/json"],
                [b"retry-after", b"60"]
            ]
        }
        await send(response)
        
        body = b'{"error": "Rate limit exceeded"}'
        await send({
            "type": "http.response.body",
            "body": body
        })

# Enhanced security headers middleware
class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                
                # Security headers
                security_headers = [
                    (b"X-Content-Type-Options", b"nosniff"),
                    (b"X-Frame-Options", b"DENY"),
                    (b"X-XSS-Protection", b"1; mode=block"),
                    (b"Strict-Transport-Security", b"max-age=31536000; includeSubDomains"),
                    (b"Content-Security-Policy", b"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; frame-ancestors 'none';"),
                    (b"Referrer-Policy", b"strict-origin-when-cross-origin"),
                    (b"Permissions-Policy", b"accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"),
                    (b"X-Permitted-Cross-Domain-Policies", b"none"),
                    (b"Clear-Site-Data", b'"cache", "cookies", "storage"') if scope["path"] == "/logout" else None
                ]
                
                headers.extend([h for h in security_headers if h is not None])
                message["headers"] = headers
                
                # Record metrics
                if REQUEST_COUNT:
                    method = scope.get("method", "GET")
                    path = scope.get("path", "/")
                    status = message.get("status", 200)
                    REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
                    
            elif message["type"] == "http.response.body" and REQUEST_DURATION:
                duration = time.time() - start_time
                REQUEST_DURATION.observe(duration)
                
            await send(message)

        await self.app(scope, receive, send_with_security_headers)

# Metrics endpoint handler
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    if not os.getenv("METRICS_ENABLED", "false").lower() == "true":
        raise HTTPException(status_code=404, detail="Metrics not enabled")
        
    return generate_latest().decode("utf-8")
