#!/usr/bin/env python3
"""
performance_tester.py - Advanced performance testing for TailSentry
"""
import asyncio
import aiohttp
import time
import statistics
import json
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Dict, Any
import argparse

@dataclass
class TestResult:
    name: str
    success: bool
    duration: float
    error: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class PerformanceTester:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        
    async def test_endpoint_performance(self, session: aiohttp.ClientSession, 
                                      endpoint: str, method: str = "GET", 
                                      iterations: int = 100) -> List[float]:
        """Test endpoint performance with multiple iterations"""
        times = []
        url = f"{self.base_url}{endpoint}"
        
        for i in range(iterations):
            start_time = time.time()
            try:
                async with session.request(method, url) as response:
                    await response.text()
                    end_time = time.time()
                    times.append(end_time - start_time)
            except Exception as e:
                print(f"Request {i+1} failed: {e}")
                
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)
            
        return times
    
    async def test_concurrent_requests(self, session: aiohttp.ClientSession,
                                     endpoint: str, concurrent_users: int = 50) -> Dict[str, Any]:
        """Test concurrent request handling"""
        url = f"{self.base_url}{endpoint}"
        
        async def make_request():
            start_time = time.time()
            try:
                async with session.get(url) as response:
                    status = response.status
                    await response.text()
                    duration = time.time() - start_time
                    return {"success": True, "status": status, "duration": duration}
            except Exception as e:
                duration = time.time() - start_time
                return {"success": False, "error": str(e), "duration": duration}
        
        start_time = time.time()
        tasks = [make_request() for _ in range(concurrent_users)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        return {
            "total_requests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "total_time": total_time,
            "requests_per_second": len(results) / total_time,
            "avg_response_time": statistics.mean([r["duration"] for r in successful]) if successful else 0,
            "max_response_time": max([r["duration"] for r in successful]) if successful else 0,
            "min_response_time": min([r["duration"] for r in successful]) if successful else 0
        }
    
    def test_tailscale_cli_performance(self, iterations: int = 50) -> Dict[str, Any]:
        """Test Tailscale CLI command performance"""
        commands = [
            ["tailscale", "status"],
            ["tailscale", "ip", "-4"],
            ["tailscale", "version"]
        ]
        
        results = {}
        
        for cmd in commands:
            cmd_name = " ".join(cmd)
            times = []
            errors = 0
            
            for i in range(iterations):
                start_time = time.time()
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    end_time = time.time()
                    
                    if result.returncode == 0:
                        times.append(end_time - start_time)
                    else:
                        errors += 1
                except Exception:
                    errors += 1
                
                time.sleep(0.01)  # Small delay
            
            if times:
                results[cmd_name] = {
                    "avg_time": statistics.mean(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "p95_time": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
                    "success_rate": len(times) / iterations,
                    "errors": errors
                }
            else:
                results[cmd_name] = {
                    "avg_time": 0,
                    "min_time": 0,
                    "max_time": 0,
                    "p95_time": 0,
                    "success_rate": 0,
                    "errors": errors
                }
        
        return results
    
    async def test_websocket_performance(self, concurrent_connections: int = 10) -> Dict[str, Any]:
        """Test WebSocket connection performance"""
        # This would require WebSocket endpoint implementation
        # For now, return placeholder
        return {
            "concurrent_connections": concurrent_connections,
            "connection_success_rate": 1.0,
            "avg_connection_time": 0.1,
            "message_throughput": 0,
            "note": "WebSocket testing requires implementation"
        }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive performance test suite"""
        print("🚀 Starting comprehensive performance testing...")
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Basic endpoint performance
            print("Testing basic endpoint performance...")
            endpoints_to_test = [
                "/health",
                "/login",
                "/",
            ]
            
            endpoint_results = {}
            for endpoint in endpoints_to_test:
                try:
                    times = await self.test_endpoint_performance(session, endpoint, iterations=100)
                    if times:
                        endpoint_results[endpoint] = {
                            "avg_time": statistics.mean(times),
                            "min_time": min(times),
                            "max_time": max(times),
                            "p95_time": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
                            "p99_time": statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times),
                            "requests_tested": len(times)
                        }
                    else:
                        endpoint_results[endpoint] = {"error": "No successful requests"}
                except Exception as e:
                    endpoint_results[endpoint] = {"error": str(e)}
            
            # Test 2: Concurrent request handling
            print("Testing concurrent request handling...")
            concurrent_results = {}
            for users in [10, 25, 50]:
                try:
                    result = await self.test_concurrent_requests(session, "/health", users)
                    concurrent_results[f"{users}_users"] = result
                except Exception as e:
                    concurrent_results[f"{users}_users"] = {"error": str(e)}
        
        # Test 3: Tailscale CLI performance
        print("Testing Tailscale CLI performance...")
        cli_results = self.test_tailscale_cli_performance(iterations=50)
        
        # Test 4: WebSocket performance (placeholder)
        print("Testing WebSocket performance...")
        websocket_results = await self.test_websocket_performance()
        
        # Compile final results
        final_results = {
            "test_timestamp": time.time(),
            "test_duration": time.time(),  # Will be updated at the end
            "endpoint_performance": endpoint_results,
            "concurrent_load": concurrent_results,
            "tailscale_cli": cli_results,
            "websocket": websocket_results,
            "summary": self._generate_summary(endpoint_results, concurrent_results, cli_results)
        }
        
        return final_results
    
    def _generate_summary(self, endpoint_results: Dict, concurrent_results: Dict, cli_results: Dict) -> Dict[str, Any]:
        """Generate performance summary"""
        summary = {
            "overall_status": "PASS",
            "issues": [],
            "recommendations": []
        }
        
        # Check endpoint performance
        for endpoint, result in endpoint_results.items():
            if isinstance(result, dict) and "avg_time" in result:
                if result["avg_time"] > 1.0:  # Slow response
                    summary["issues"].append(f"Slow response for {endpoint}: {result['avg_time']:.3f}s")
                    summary["overall_status"] = "WARNING"
                
                if result["p95_time"] > 2.0:  # Very slow P95
                    summary["issues"].append(f"Very slow P95 for {endpoint}: {result['p95_time']:.3f}s")
                    summary["overall_status"] = "WARNING"
        
        # Check concurrent load
        for load_test, result in concurrent_results.items():
            if isinstance(result, dict) and "requests_per_second" in result:
                if result["requests_per_second"] < 10:  # Low throughput
                    summary["issues"].append(f"Low throughput in {load_test}: {result['requests_per_second']:.1f} req/s")
                    summary["overall_status"] = "WARNING"
                
                if result["failed"] > result["total_requests"] * 0.05:  # > 5% failure rate
                    summary["issues"].append(f"High failure rate in {load_test}: {result['failed']}/{result['total_requests']}")
                    summary["overall_status"] = "WARNING"
        
        # Check CLI performance
        for cmd, result in cli_results.items():
            if isinstance(result, dict) and "avg_time" in result:
                if result["avg_time"] > 3.0:  # Slow CLI
                    summary["issues"].append(f"Slow CLI command {cmd}: {result['avg_time']:.3f}s")
                    summary["overall_status"] = "WARNING"
                
                if result["success_rate"] < 0.95:  # Low success rate
                    summary["issues"].append(f"Low CLI success rate for {cmd}: {result['success_rate']:.1%}")
                    summary["overall_status"] = "WARNING"
        
        # Generate recommendations
        if summary["issues"]:
            summary["recommendations"].extend([
                "Consider implementing response caching",
                "Optimize database queries if applicable",
                "Add connection pooling",
                "Monitor resource usage during high load",
                "Consider horizontal scaling",
                "Implement circuit breakers for external dependencies"
            ])
        else:
            summary["recommendations"].append("Performance is within acceptable limits")
        
        return summary

def main():
    parser = argparse.ArgumentParser(description="TailSentry Performance Tester")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL for testing")
    parser.add_argument("--output", default="performance_report.json", help="Output file for results")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    async def run_tests():
        tester = PerformanceTester(args.url)
        
        start_time = time.time()
        results = await tester.run_comprehensive_test()
        end_time = time.time()
        
        results["test_duration"] = end_time - start_time
        
        # Save results
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        print("\n" + "="*50)
        print("🎯 PERFORMANCE TEST SUMMARY")
        print("="*50)
        
        summary = results["summary"]
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Test Duration: {results['test_duration']:.2f} seconds")
        
        if summary["issues"]:
            print("\n⚠️  Issues Found:")
            for issue in summary["issues"]:
                print(f"  - {issue}")
        else:
            print("\n✅ No performance issues detected")
        
        print("\n💡 Recommendations:")
        for rec in summary["recommendations"]:
            print(f"  - {rec}")
        
        print(f"\n📄 Detailed results saved to: {args.output}")
        
        # Print key metrics if verbose
        if args.verbose:
            print("\n📊 Key Metrics:")
            if "endpoint_performance" in results:
                for endpoint, metrics in results["endpoint_performance"].items():
                    if "avg_time" in metrics:
                        print(f"  {endpoint}: {metrics['avg_time']:.3f}s avg, {metrics['p95_time']:.3f}s P95")
            
            if "concurrent_load" in results:
                for load, metrics in results["concurrent_load"].items():
                    if "requests_per_second" in metrics:
                        print(f"  {load}: {metrics['requests_per_second']:.1f} req/s, {metrics['successful']}/{metrics['total_requests']} success")
        
        return 0 if summary["overall_status"] == "PASS" else 1
    
    try:
        exit_code = asyncio.run(run_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
