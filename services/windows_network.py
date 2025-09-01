"""
Windows Network Detection Module for TailSentry
Provides Windows-specific network interface and subnet detection functionality.
"""

import subprocess
import json
import ipaddress
import platform
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("tailsentry.windows_network")

class WindowsNetworkDetector:
    """Windows-specific network detection using PowerShell and Windows APIs"""

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows"""
        return platform.system() == "Windows"

    @staticmethod
    def get_network_interfaces() -> List[Dict]:
        """Get network interfaces using PowerShell Get-NetAdapter"""
        if not WindowsNetworkDetector.is_windows():
            logger.warning("Windows network detection called on non-Windows platform")
            return []

        try:
            # PowerShell command to get network adapters
            cmd = [
                'powershell.exe',
                '-Command',
                'Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, MacAddress, InterfaceIndex | ConvertTo-Json'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                try:
                    adapters = json.loads(result.stdout)
                    # Handle single adapter (PowerShell returns object, not array)
                    if isinstance(adapters, dict):
                        adapters = [adapters]
                    return adapters
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse network adapter JSON: {e}")
                    return []
            else:
                logger.error(f"PowerShell command failed: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            logger.error("Network interface detection timed out")
            return []
        except Exception as e:
            logger.error(f"Error detecting network interfaces: {e}")
            return []

    @staticmethod
    def get_ip_configuration() -> List[Dict]:
        """Get IP configuration for all adapters using PowerShell"""
        if not WindowsNetworkDetector.is_windows():
            logger.warning("Windows IP configuration detection called on non-Windows platform")
            return []

        try:
            # PowerShell command to get IP configuration with simplified output
            cmd = [
                'powershell.exe',
                '-Command',
                'Get-NetIPConfiguration | Select-Object InterfaceAlias, IPv4Address, IPv6Address, DNSServer | ConvertTo-Json'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                try:
                    configs = json.loads(result.stdout)
                    # Handle single config (PowerShell returns object, not array)
                    if isinstance(configs, dict):
                        configs = [configs]
                    return configs
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse IP configuration JSON: {e}")
                    return []
            else:
                logger.error(f"PowerShell IP config command failed: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            logger.error("IP configuration detection timed out")
            return []
        except Exception as e:
            logger.error(f"Error getting IP configuration: {e}")
            return []

    @staticmethod
    def detect_local_subnets() -> List[Dict[str, str]]:
        """Detect all available local subnets on Windows"""
        if not WindowsNetworkDetector.is_windows():
            logger.info("Local subnet detection not supported on non-Windows platforms")
            return []

        detected_subnets = []

        try:
            # Try the primary method first
            ip_configs = WindowsNetworkDetector.get_ip_configuration()

            for config in ip_configs:
                interface_name = config.get('InterfaceAlias', 'Unknown')

                # Skip loopback and tunnel interfaces
                if 'loopback' in interface_name.lower() or 'tunnel' in interface_name.lower():
                    continue

                # Process IPv4 addresses
                ipv4_addresses = config.get('IPv4Address', [])
                if isinstance(ipv4_addresses, dict):
                    ipv4_addresses = [ipv4_addresses]
                elif not isinstance(ipv4_addresses, list):
                    ipv4_addresses = []

                for ipv4 in ipv4_addresses:
                    if isinstance(ipv4, dict):
                        ip = ipv4.get('IPAddress')
                        prefix_length = ipv4.get('PrefixLength')
                    else:
                        # Handle string format
                        ip = str(ipv4)
                        prefix_length = 24  # Default assumption

                    if ip and prefix_length:
                        try:
                            # Validate IP address format
                            ipaddress.IPv4Address(ip)
                            # Create subnet from IP and prefix
                            network = ipaddress.IPv4Network(f"{ip}/{prefix_length}", strict=False)

                            detected_subnets.append({
                                'interface': interface_name,
                                'cidr': str(network),
                                'ip': ip,
                                'prefix_length': prefix_length,
                                'family': 'IPv4',
                                'network_address': str(network.network_address),
                                'broadcast_address': str(network.broadcast_address)
                            })

                            logger.debug(f"Detected subnet: {network} on {interface_name}")

                        except ValueError as e:
                            logger.warning(f"Invalid subnet {ip}/{prefix_length}: {e}")
                            continue

            # If no subnets found, try fallback method
            if not detected_subnets:
                logger.info("Primary method found no subnets, trying fallback...")
                detected_subnets = WindowsNetworkDetector._detect_subnets_fallback()

            logger.info(f"Windows subnet detection completed: found {len(detected_subnets)} subnets")
            return detected_subnets

        except Exception as e:
            logger.error(f"Error detecting local subnets: {e}")
            return []

    @staticmethod
    def _detect_subnets_fallback() -> List[Dict[str, str]]:
        """Fallback method for subnet detection using ipconfig"""
        detected_subnets = []

        try:
            # Use ipconfig as fallback
            cmd = ['ipconfig', '/all']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_adapter = None
                current_ip = None
                current_mask = None

                for line in lines:
                    line = line.strip()
                    if 'adapter' in line.lower() and ':' in line:
                        current_adapter = line.split(':')[0].strip()
                    elif 'IPv4 Address' in line and ':' in line:
                        ip_part = line.split(':')[1].strip()
                        current_ip = ip_part.split('(')[0].strip()  # Remove subnet mask if present
                    elif 'Subnet Mask' in line and ':' in line:
                        mask_part = line.split(':')[1].strip()
                        current_mask = mask_part

                        # Try to create subnet if we have all info
                        if current_adapter and current_ip and current_mask:
                            try:
                                network = ipaddress.IPv4Network(f"{current_ip}/{current_mask}", strict=False)
                                detected_subnets.append({
                                    'interface': current_adapter,
                                    'cidr': str(network),
                                    'ip': current_ip,
                                    'prefix_length': network.prefixlen,
                                    'family': 'IPv4',
                                    'network_address': str(network.network_address),
                                    'broadcast_address': str(network.broadcast_address)
                                })
                            except ValueError as e:
                                logger.warning(f"Fallback subnet detection failed for {current_ip}/{current_mask}: {e}")

                            # Reset for next adapter
                            current_ip = None
                            current_mask = None

            logger.info(f"Fallback subnet detection found {len(detected_subnets)} subnets")
            return detected_subnets

        except Exception as e:
            logger.error(f"Fallback subnet detection failed: {e}")
            return []

    @staticmethod
    def get_default_gateway() -> Optional[str]:
        """Get the default gateway IP address"""
        if not WindowsNetworkDetector.is_windows():
            return None

        try:
            cmd = [
                'powershell.exe',
                '-Command',
                'Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Select-Object -First 1 | Select-Object NextHop | ConvertTo-Json'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                try:
                    route_info = json.loads(result.stdout)
                    return route_info.get('NextHop')
                except (json.JSONDecodeError, KeyError):
                    pass

        except Exception as e:
            logger.error(f"Error getting default gateway: {e}")

        return None

    @staticmethod
    def get_dns_servers() -> List[str]:
        """Get DNS server addresses"""
        if not WindowsNetworkDetector.is_windows():
            return []

        try:
            cmd = [
                'powershell.exe',
                '-Command',
                'Get-DnsClientServerAddress | Where-Object {$_.AddressFamily -eq 2} | Select-Object -ExpandProperty ServerAddresses | ConvertTo-Json'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                try:
                    dns_servers = json.loads(result.stdout)
                    if isinstance(dns_servers, list):
                        return dns_servers
                    elif isinstance(dns_servers, str):
                        return [dns_servers]
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.error(f"Error getting DNS servers: {e}")

        return []

    @staticmethod
    def test_connectivity(host: str = "8.8.8.8", timeout: int = 5) -> bool:
        """Test network connectivity to a host"""
        if not WindowsNetworkDetector.is_windows():
            return False

        try:
            cmd = [
                'powershell.exe',
                '-Command',
                f'Test-NetConnection -ComputerName {host} -Port 53 -InformationLevel Quiet'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return result.returncode == 0

        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False
