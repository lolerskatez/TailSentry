# Automated Testing Script for TailSentry Dashboard
# This script performs tests to ensure the TailSentry components work as expected.

import unittest
import subprocess
import os
import requests
import json
import time
import logging
from unittest.mock import patch, MagicMock

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_tailsentry")

# Path to our application
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Add the app directory to path for imports
import sys
sys.path.append(APP_DIR)

# Test imports - will fail if dependencies aren't installed
try:
    from tailscale_client import TailscaleClient
    import utils
    from auth import verify_password
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you've installed dependencies with 'pip install -r requirements.txt'")
    sys.exit(1)

class MockSubprocess:
    """Mock subprocess for testing"""
    @staticmethod
    def mock_check_output(*args, **kwargs):
        """Mock subprocess.check_output"""
        if args[0][0] == 'tailscale' and args[0][1] == 'status':
            # Return mock tailscale status
            return json.dumps({
                "Self": {
                    "ID": "1234",
                    "HostName": "test-machine",
                    "TailscaleIPs": ["100.100.100.100"],
                    "OS": "linux",
                    "Capabilities": {"ExitNode": True, "SubnetRouter": True},
                    "AdvertisedRoutes": ["192.168.1.0/24"],
                    "TXBytes": 1024,
                    "RXBytes": 2048
                },
                "Peer": {
                    "5678": {
                        "ID": "5678",
                        "HostName": "other-machine",
                        "TailscaleIPs": ["100.100.100.101"],
                        "OS": "windows",
                        "LastSeen": "2022-01-01T00:00:00Z",
                        "Online": True
                    }
                }
            }).encode('utf-8')
        elif args[0][0] == 'systemctl':
            # Mock systemctl output
            return b"Active: active (running)"
        else:
            # Default response
            return b"mocked output"

class TailscaleClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.force_live = os.getenv("TAILSENTRY_FORCE_LIVE_DATA", "true").lower() == "true"
    """Test the TailscaleClient class"""
    
    @patch('subprocess.check_output', MockSubprocess.mock_check_output)
    def test_status_json(self):
        """Test getting Tailscale status"""
        status = TailscaleClient.status_json()
        self.assertIn("Self", status)
        self.assertIn("Peer", status)
        
    @patch('subprocess.check_output', MockSubprocess.mock_check_output)
    def test_subnet_routes(self):
        """Test getting subnet routes"""
        routes = TailscaleClient.subnet_routes()
        if self.force_live:
            self.assertIsInstance(routes, list)
        else:
            self.assertEqual(routes, ["192.168.1.0/24"])
        
    @patch('subprocess.check_output', MockSubprocess.mock_check_output)
    def test_get_ip(self):
        """Test getting Tailscale IP"""
        ip = TailscaleClient.get_ip()
        if self.force_live:
            self.assertIsInstance(ip, str)
            self.assertRegex(ip, r"^\d+\.\d+\.\d+\.\d+$|Not available")
        else:
            self.assertEqual(ip, "100.100.100.100")
        
    def test_get_device_info(self):
        """Test getting device info"""
        if self.force_live:
            info = TailscaleClient.get_device_info()
            self.assertIn("tailscale", info)
            self.assertIsInstance(info["tailscale"], dict)
        else:
            with patch('subprocess.check_output', MockSubprocess.mock_check_output):
                info = TailscaleClient.get_device_info()
                self.assertIn("tailscale", info)
                self.assertTrue(info["tailscale"]["is_exit_node"])
        
    @patch('subprocess.check_call')
    def test_set_subnet_routes_validation(self, mock_check_call):
        """Test validation in set_subnet_routes"""
        # Valid CIDR
        TailscaleClient.set_subnet_routes(["192.168.1.0/24"])
        mock_check_call.assert_called_once()
        
        # Invalid CIDR should not call subprocess
        mock_check_call.reset_mock()
        result = TailscaleClient.set_subnet_routes(["invalid"])
        mock_check_call.assert_not_called()
        self.assertIn("Invalid CIDR format", result)

class UtilsTests(unittest.TestCase):
    """Test utility functions"""
    
    def test_validate_cidr(self):
        """Test CIDR validation"""
        self.assertTrue(utils.validate_cidr("192.168.1.0/24"))
        self.assertFalse(utils.validate_cidr("invalid"))
        
    def test_sanitize_cmd_arg(self):
        """Test command argument sanitization"""
        # Valid arguments
        self.assertEqual(utils.sanitize_cmd_arg("valid"), "valid")
        self.assertEqual(utils.sanitize_cmd_arg("192.168.1.0/24"), "192.168.1.0/24")
        
        # Invalid arguments should raise ValueError
        with self.assertRaises(ValueError):
            utils.sanitize_cmd_arg("invalid;rm -rf /")
            
    def test_format_bytes(self):
        """Test bytes formatting"""
        self.assertEqual(utils.format_bytes(500), "500 B")
        self.assertEqual(utils.format_bytes(1500), "1.46 KB")
        self.assertEqual(utils.format_bytes(1500000), "1.43 MB")

class AuthTests(unittest.TestCase):
    """Test authentication functions"""
    
    def test_verify_password(self):
        """Test password verification"""
        # Generate a test hash - this is how a real hash would be created
        import bcrypt
        password = "testpassword"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        # Verification should pass with correct password
        self.assertTrue(verify_password(password, hashed))
        
        # Verification should fail with incorrect password
        self.assertFalse(verify_password("wrongpassword", hashed))

if __name__ == "__main__":
    unittest.main()
