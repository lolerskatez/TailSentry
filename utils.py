import re
import ipaddress
import socket
from typing import List, Dict, Any, Union, Optional


def validate_cidr(cidr: str) -> bool:
    """Validate if a string is a valid CIDR notation."""
    try:
        ipaddress.ip_network(cidr)
        return True
    except ValueError:
        return False


def sanitize_cmd_arg(arg: str) -> str:
    """Sanitize a command line argument to prevent injection."""
    # Allow only alphanumeric, some punctuation, and common path chars
    safe_chars = re.compile(r'^[a-zA-Z0-9\-_.,=:/]+$')
    if safe_chars.match(arg):
        return arg
    raise ValueError(f"Invalid command argument: {arg}")


def get_local_subnets() -> List[str]:
    """Detect available local subnets using modern Python libraries."""
    subnets = []
    try:
        import psutil
        import ipaddress
        
        # Get network interface stats
        for interface_name, interface_addresses in psutil.net_if_addrs().items():
            # Skip loopback interfaces
            if interface_name.startswith('lo') or 'loopback' in interface_name.lower():
                continue
                
            for addr in interface_addresses:
                # Only process IPv4 addresses
                if addr.family == socket.AF_INET and addr.address and addr.netmask:
                    try:
                        # Create network object from IP and netmask
                        ip = ipaddress.IPv4Address(addr.address)
                        netmask = ipaddress.IPv4Address(addr.netmask)
                        
                        # Calculate network address
                        network = ipaddress.IPv4Network(f"{addr.address}/{addr.netmask}", strict=False)
                        
                        # Skip certain networks (localhost, link-local, etc.)
                        if not (network.is_loopback or network.is_link_local or network.is_multicast):
                            subnets.append(str(network))
                            
                    except (ipaddress.AddressValueError, ValueError) as e:
                        # Skip invalid addresses
                        continue
                        
    except (ImportError, Exception) as e:
        print(f"Error detecting local subnets: {e}")
        # Fallback: try common private network ranges
        subnets = ["192.168.1.0/24", "10.0.0.0/24", "172.16.0.0/24"]
    
    return subnets


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable format."""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024**2:
        return f"{bytes_value/1024:.2f} KB"
    elif bytes_value < 1024**3:
        return f"{bytes_value/1024**2:.2f} MB"
    else:
        return f"{bytes_value/1024**3:.2f} GB"
