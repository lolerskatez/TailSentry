"""Monitoring middleware for application telemetry."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import time
import psutil
import logging
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger("tailsentry")

class RequestStats:
    def __init__(self):
        self.total_requests = 0
        self.requests_per_minute = defaultdict(int)
        self.response_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.last_cleanup = datetime.now()
    
    def cleanup_old_stats(self):
        """Clean up statistics older than 1 hour."""
        now = datetime.now()
        if now - self.last_cleanup < timedelta(minutes=5):
            return
        
        hour_ago = now - timedelta(hours=1)
        for endpoint in list(self.response_times.keys()):
            self.response_times[endpoint] = [
                t for t in self.response_times[endpoint]
                if t["timestamp"] > hour_ago
            ]
        
        self.last_cleanup = now
    
    def add_request(self, endpoint: str, response_time: float, status_code: int):
        """Record statistics for a request."""
        self.total_requests += 1
        self.requests_per_minute[endpoint] += 1
        
        self.response_times[endpoint].append({
            "timestamp": datetime.now(),
            "duration": response_time
        })
        
        if status_code >= 400:
            self.error_counts[endpoint] += 1
        
        self.cleanup_old_stats()
    
    def get_stats(self) -> Dict:
        """Get current statistics."""
        stats = {
            "total_requests": self.total_requests,
            "requests_per_minute": dict(self.requests_per_minute),
            "errors": dict(self.error_counts),
            "response_times": {}
        }
        
        # Calculate average response times
        for endpoint, times in self.response_times.items():
            if times:
                avg_time = sum(t["duration"] for t in times) / len(times)
                stats["response_times"][endpoint] = avg_time
        
        return stats

class MonitoringMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.stats = RequestStats()
        self.start_time = datetime.now()
    
    def get_system_metrics(self) -> Dict:
        """Get system resource usage metrics."""
        process = psutil.Process()
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "open_files": len(process.open_files()),
            "threads": process.num_threads(),
            "connections": len(process.connections())
        }
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Monitor request/response cycle."""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Record request statistics
            self.stats.add_request(
                endpoint=request.url.path,
                response_time=duration,
                status_code=response.status_code
            )
            
            # Log slow requests
            if duration > 1.0:  # More than 1 second
                logger.warning(
                    f"Slow request detected: {request.url.path} "
                    f"took {duration:.2f} seconds"
                )
            
            # Add monitoring headers in development
            if request.app.debug:
                response.headers["X-Response-Time"] = f"{duration:.3f}s"
                
            return response
            
        except Exception as e:
            logger.error(f"Request error: {str(e)}", exc_info=True)
            raise
