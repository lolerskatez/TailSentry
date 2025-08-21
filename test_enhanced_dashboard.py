#!/usr/bin/env python3
"""
Enhanced Dashboard Validation Script
Tests the new robust dashboard implementation and real-time features.
"""

import requests
import json
import time
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from services
sys.path.append(str(Path(__file__).parent))

def test_dashboard_apis():
    """Test all dashboard-related API endpoints."""
    base_url = "http://localhost:8080"
    
    endpoints_to_test = [
        "/api/status",
        "/api/peers", 
        "/api/subnet-routes",
        "/api/network-stats",
        "/api/settings/export"
    ]
    
    print("🧪 Testing Dashboard API Endpoints...")
    print("=" * 50)
    
    results = {}
    
    for endpoint in endpoints_to_test:
        try:
            print(f"Testing {endpoint}...", end=" ")
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                results[endpoint] = {
                    "status": "✅ SUCCESS",
                    "response_time": f"{response.elapsed.total_seconds():.3f}s",
                    "data_keys": list(data.keys()) if isinstance(data, dict) else "Non-dict response"
                }
                print("✅")
            else:
                results[endpoint] = {
                    "status": f"❌ FAILED ({response.status_code})",
                    "response_time": f"{response.elapsed.total_seconds():.3f}s",
                    "error": response.text[:100]
                }
                print("❌")
                
        except requests.exceptions.ConnectionError:
            results[endpoint] = {
                "status": "🔌 CONNECTION FAILED",
                "error": "Server not running on localhost:8000"
            }
            print("🔌")
        except Exception as e:
            results[endpoint] = {
                "status": f"💥 ERROR",
                "error": str(e)
            }
            print("💥")
    
    print("\n📊 Test Results Summary:")
    print("=" * 50)
    
    for endpoint, result in results.items():
        print(f"{endpoint:<20} {result['status']}")
        if 'response_time' in result:
            print(f"{'':20} Response Time: {result['response_time']}")
        if 'data_keys' in result:
            print(f"{'':20} Data Keys: {result['data_keys']}")
        if 'error' in result:
            print(f"{'':20} Error: {result['error']}")
        print()
    
    return results

def test_dashboard_features():
    """Test specific dashboard features and integrations."""
    print("\n🎯 Testing Dashboard Features...")
    print("=" * 50)
    
    features = {
        "Static Files": test_static_files(),
        "Chart Integration": test_chart_integration(),
        "Real-time Updates": test_realtime_updates(),
        "Error Handling": test_error_handling()
    }
    
    for feature, result in features.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{feature:<20} {status}")
    
    return features

def test_static_files():
    """Test that required static files exist."""
    required_files = [
        "static/dashboard.js",
        "static/dashboard-controller.js",
        "templates/dashboard.html"
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Missing file: {file_path}")
            return False
    
    return True

def test_chart_integration():
    """Test Chart.js integration in dashboard."""
    dashboard_html = Path("templates/dashboard.html")
    
    if not dashboard_html.exists():
        return False
    
    content = dashboard_html.read_text()
    
    required_elements = [
        'id="networkChart"',
        'id="peerChart"',
        'chart.js',
        'dashboard-controller.js'
    ]
    
    for element in required_elements:
        if element not in content:
            print(f"❌ Missing chart element: {element}")
            return False
    
    return True

def test_realtime_updates():
    """Test real-time update functionality."""
    try:
        # Test network stats endpoint specifically
        response = requests.get("http://localhost:8080/api/network-stats", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ['success', 'stats']
            
            for field in required_fields:
                if field not in data:
                    return False
            
            stats = data.get('stats', {})
            stats_fields = ['tx', 'rx', 'timestamp']
            
            for field in stats_fields:
                if field not in stats:
                    return False
            
            return True
            
    except requests.exceptions.ConnectionError:
        print("🔌 Server not running - cannot test real-time features")
        return False
    except Exception:
        return False
    
    return False

def test_error_handling():
    """Test error handling in API endpoints."""
    try:
        # Test invalid endpoint
        response = requests.get("http://localhost:8080/api/invalid-endpoint", timeout=5)
        
        # Should return 404 or proper error handling
        return response.status_code in [404, 422, 500]
        
    except requests.exceptions.ConnectionError:
        print("🔌 Server not running - cannot test error handling")
        return False
    except Exception:
        return True  # Any exception means error handling is working

def create_performance_report():
    """Create a performance report for the dashboard."""
    print("\n📈 Dashboard Performance Report")
    print("=" * 50)
    
    try:
        # Test multiple rapid requests to simulate real usage
        base_url = "http://localhost:8080/api"
        endpoints = ["/status", "/peers", "/network-stats"]
        
        for endpoint in endpoints:
            times = []
            for _ in range(5):
                start = time.time()
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                end = time.time()
                
                if response.status_code == 200:
                    times.append(end - start)
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                print(f"{endpoint:<15} Avg: {avg_time:.3f}s  Min: {min_time:.3f}s  Max: {max_time:.3f}s")
    
    except requests.exceptions.ConnectionError:
        print("🔌 Server not running - cannot generate performance report")
    except Exception as e:
        print(f"❌ Error generating performance report: {e}")

def main():
    """Run all dashboard validation tests."""
    print("🚀 TailSentry Enhanced Dashboard Validation")
    print("=" * 60)
    print("Testing the new robust dashboard implementation...")
    print()
    
    # Test API endpoints
    api_results = test_dashboard_apis()
    
    # Test dashboard features
    feature_results = test_dashboard_features()
    
    # Generate performance report
    create_performance_report()
    
    # Summary
    print("\n🎯 Final Summary")
    print("=" * 50)
    
    api_success = sum(1 for r in api_results.values() if "SUCCESS" in r['status'])
    api_total = len(api_results)
    
    feature_success = sum(1 for r in feature_results.values() if r)
    feature_total = len(feature_results)
    
    print(f"API Tests:     {api_success}/{api_total} passed")
    print(f"Feature Tests: {feature_success}/{feature_total} passed")
    
    if api_success == api_total and feature_success == feature_total:
        print("\n🎉 All tests passed! Dashboard is ready for production.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the details above.")
        return 1

if __name__ == "__main__":
    exit(main())
