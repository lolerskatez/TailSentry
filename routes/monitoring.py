"""Route handlers for monitoring and metrics."""
import time
from fastapi import APIRouter, Request, HTTPException, Depends
from middleware.monitoring import MonitoringMiddleware
from services.rbac_service import requires_permission

router = APIRouter()

@router.get("/metrics")
@requires_permission("monitoring:metrics:view")
async def get_metrics(request: Request):
    """Get application metrics and monitoring data."""
    monitoring = request.app.middleware_stack.app
    while monitoring and not isinstance(monitoring, MonitoringMiddleware):
        monitoring = getattr(monitoring, "app", None)
    
    if not monitoring:
        raise HTTPException(status_code=500, detail="Monitoring middleware not found")
    
    # Get monitoring stats
    stats = monitoring.stats.get_stats()
    system_metrics = monitoring.get_system_metrics()
    
    return {
        "application": stats,
        "system": system_metrics,
        "uptime": (monitoring.start_time - request.app.state.start_time).total_seconds()
    }

@router.get("/health")
async def health_check(request: Request):
    """Enhanced health check endpoint."""
    uptime = time.time() - request.app.state.start_time
    
    # Get system health metrics
    monitoring = request.app.middleware_stack.app
    while monitoring and not isinstance(monitoring, MonitoringMiddleware):
        monitoring = getattr(monitoring, "app", None)
    
    system_health = {}
    if monitoring:
        system_metrics = monitoring.get_system_metrics()
        system_health = {
            "cpu_healthy": system_metrics["cpu_percent"] < 80,
            "memory_healthy": system_metrics["memory_percent"] < 80,
            "connections_healthy": system_metrics["connections"] < 1000
        }
    
    return {
        "status": "healthy" if all(system_health.values()) else "degraded",
        "version": request.app.version,
        "uptime": f"{uptime:.2f} seconds",
        "system_health": system_health
    }
