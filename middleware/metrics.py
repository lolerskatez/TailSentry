"""Metrics middleware for collecting Prometheus metrics."""
from prometheus_client import Counter, Histogram, Gauge
import time
from fastapi import Request

# Define metrics
REQUEST_COUNT = Counter(
    'tailsentry_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'tailsentry_http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'tailsentry_http_active_requests',
    'Number of active HTTP requests'
)

async def metrics_middleware(request: Request, call_next):
    """Middleware to collect metrics about requests."""
    ACTIVE_REQUESTS.inc()
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record request count and latency
    duration = time.time() - start_time
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    ACTIVE_REQUESTS.dec()
    return response
