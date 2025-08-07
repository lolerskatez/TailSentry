"""
TailSentry Integration Health Monitor
Continuously monitors and validates Tailscale integration
"""

import asyncio
import logging
import time
import json
import subprocess
import httpx
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger("tailsentry.integration")

@dataclass
class IntegrationHealth:
    """Integration health status"""
    cli_available: bool
    api_available: bool
    service_running: bool
    last_check: datetime
    error_count: int
    response_time: float

class TailscaleIntegrationMonitor:
    """Monitor and maintain Tailscale integration health"""
    
    def __init__(self):
        self.health = IntegrationHealth(
            cli_available=False,
            api_available=False,
            service_running=False,
            last_check=datetime.now(),
            error_count=0,
            response_time=0.0
        )
        self.error_threshold = 5
        self.check_interval = 60  # seconds
        
    async def monitor_integration(self):
        """Continuous integration monitoring"""
        while True:
            try:
                await self.check_integration_health()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Integration monitor error: {e}")
                await asyncio.sleep(30)  # Shorter retry on error
    
    async def check_integration_health(self) -> IntegrationHealth:
        """Check all integration components"""
        start_time = time.time()
        
        try:
            # Check CLI availability
            self.health.cli_available = await self._check_cli()
            
            # Check API availability (if configured)
            self.health.api_available = await self._check_api()
            
            # Check service status
            self.health.service_running = await self._check_service()
            
            # Reset error count on success
            if self.health.cli_available and self.health.service_running:
                self.health.error_count = 0
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.health.error_count += 1
            
        finally:
            self.health.response_time = time.time() - start_time
            self.health.last_check = datetime.now()
            
        # Trigger recovery if needed
        if self.health.error_count >= self.error_threshold:
            await self._attempt_recovery()
            
        return self.health
    
    async def _check_cli(self) -> bool:
        """Check Tailscale CLI availability"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "tailscale", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            return proc.returncode == 0
        except (asyncio.TimeoutError, FileNotFoundError, Exception):
            return False
    
    async def _check_api(self) -> bool:
        """Check Tailscale API availability"""
        try:
            pat = os.getenv("TAILSCALE_PAT")
            if not pat:
                return True  # API not configured, consider healthy
                
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.tailscale.com/api/v2/tailnet/-/devices",
                    headers={"Authorization": f"Bearer {pat}"}
                )
                return response.status_code == 200
                
        except Exception:
            return False
                )
                return response.status_code == 200
                
        except Exception:
            return False
    
    async def _check_service(self) -> bool:
        """Check tailscaled service status"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "is-active", "tailscaled",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            stdout, _ = await proc.communicate()
            return stdout.decode().strip() == "active"
        except Exception:
            return False
    
        if not self.health.service_running:
            import os
            if os.geteuid() != 0:
                logger.error("Insufficient privileges to restart tailscaled. Please run as root.")
            else:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "systemctl", "restart", "tailscaled"
                    )
                    await asyncio.wait_for(proc.wait(), timeout=30.0)
                    logger.info("Restarted tailscaled service")
                except Exception as e:
                    logger.error(f"Failed to restart tailscaled: {e}")
        
        # Reset error count after recovery attempt
        self.health.error_count = 0
            except Exception as e:
                logger.error(f"Failed to restart tailscaled: {e}")
        
        # Reset error count after recovery attempt
        self.health.error_count = 0
    
    def get_health_status(self) -> Dict:
        """Get current health status for API"""
        return {
            "cli_available": self.health.cli_available,
            "api_available": self.health.api_available,
            "service_running": self.health.service_running,
            "last_check": self.health.last_check.isoformat(),
            "error_count": self.health.error_count,
            "response_time": self.health.response_time,
            "status": self._get_overall_status()
        }
    
    def _get_overall_status(self) -> str:
        """Determine overall integration status"""
        if self.health.cli_available and self.health.service_running:
            return "healthy"
        elif self.health.error_count >= self.error_threshold:
            return "critical"
        else:
            return "degraded"

# Global instance
integration_monitor = TailscaleIntegrationMonitor()

async def start_integration_monitoring():
    """Start the integration monitoring task"""
    logger.info("Starting Tailscale integration monitoring")
    await integration_monitor.monitor_integration()

def get_integration_health() -> Dict:
    """Get current integration health status"""
    return integration_monitor.get_health_status()

# Synchronous wrapper for health check
def check_integration_sync() -> bool:
    """Synchronous integration health check"""
    try:
        # Quick CLI check
        result = subprocess.run(
            ["tailscale", "status"],
            capture_output=True,
            timeout=5.0
        )
        return result.returncode == 0
    except Exception:
        return False
