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
    """Detect available local subnets."""
    subnets = []
    try:
        # This approach works on Linux systems
        import netifaces
        
        for interface in netifaces.interfaces():
            # Skip loopback
            if interface == 'lo':
                continue
                
            addrs = netifaces.ifaddresses(interface)
            # Check for IPv4 addresses
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    if 'addr' in addr and 'netmask' in addr:
                        # Calculate CIDR from netmask
                        ip = addr['addr']
                        netmask = addr['netmask']
                        
                        # Convert netmask to CIDR prefix length
                        netmask_bits = bin(int.from_bytes(socket.inet_aton(netmask), 'big')).count('1')
                        
                        # Create network address
                        ip_int = int.from_bytes(socket.inet_aton(ip), 'big')
                        mask_int = int.from_bytes(socket.inet_aton(netmask), 'big')
                        network_int = ip_int & mask_int
                        network_ip = socket.inet_ntoa(network_int.to_bytes(4, 'big'))
                        
                        cidr = f"{network_ip}/{netmask_bits}"
                        subnets.append(cidr)
    except (ImportError, Exception) as e:
        print(f"Error detecting local subnets: {e}")
    
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
