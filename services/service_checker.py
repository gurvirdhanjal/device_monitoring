"""
Service Checker module for Network Monitoring System.
Provides TCP port checks, HTTP status checks, and DNS query checks.
"""
import socket
import ssl
import asyncio
from datetime import datetime
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class CheckStatus(Enum):
    """Status of a service check."""
    UP = "UP"
    DOWN = "DOWN"
    DEGRADED = "DEGRADED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass
class CheckResult:
    """Result of a service check."""
    status: CheckStatus
    response_time_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    checked_at: datetime = None
    
    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'response_time_ms': self.response_time_ms,
            'message': self.message,
            'details': self.details,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None
        }


class ServiceChecker:
    """
    Service for checking TCP ports, HTTP endpoints, and DNS queries.
    """
    
    def __init__(self, default_timeout: float = 5.0):
        self.default_timeout = default_timeout
    
    # ----------------------------------------------------------------
    # TCP Port Check
    # ----------------------------------------------------------------
    def check_tcp(self, host: str, port: int, timeout: float = None) -> CheckResult:
        """
        Check if a TCP port is open and responding.
        
        Args:
            host: Hostname or IP address
            port: TCP port number
            timeout: Connection timeout in seconds
            
        Returns:
            CheckResult with connection status and response time
        """
        timeout = timeout or self.default_timeout
        start_time = datetime.utcnow()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            start_ms = datetime.utcnow()
            result = sock.connect_ex((host, port))
            end_ms = datetime.utcnow()
            
            response_time = (end_ms - start_ms).total_seconds() * 1000
            
            sock.close()
            
            if result == 0:
                return CheckResult(
                    status=CheckStatus.UP,
                    response_time_ms=round(response_time, 2),
                    message=f"Port {port} is open",
                    details={'host': host, 'port': port}
                )
            else:
                return CheckResult(
                    status=CheckStatus.DOWN,
                    response_time_ms=None,
                    message=f"Port {port} is closed or filtered",
                    details={'host': host, 'port': port, 'error_code': result}
                )
                
        except socket.timeout:
            return CheckResult(
                status=CheckStatus.TIMEOUT,
                message=f"Connection to {host}:{port} timed out",
                details={'host': host, 'port': port, 'timeout': timeout}
            )
        except socket.gaierror as e:
            return CheckResult(
                status=CheckStatus.ERROR,
                message=f"DNS resolution failed: {e}",
                details={'host': host, 'port': port, 'error': str(e)}
            )
        except Exception as e:
            return CheckResult(
                status=CheckStatus.ERROR,
                message=str(e),
                details={'host': host, 'port': port, 'error': str(e)}
            )
    
    async def check_tcp_async(self, host: str, port: int, timeout: float = None) -> CheckResult:
        """Async version of TCP check."""
        timeout = timeout or self.default_timeout
        
        try:
            start_ms = datetime.utcnow()
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            end_ms = datetime.utcnow()
            
            response_time = (end_ms - start_ms).total_seconds() * 1000
            writer.close()
            await writer.wait_closed()
            
            return CheckResult(
                status=CheckStatus.UP,
                response_time_ms=round(response_time, 2),
                message=f"Port {port} is open",
                details={'host': host, 'port': port}
            )
            
        except asyncio.TimeoutError:
            return CheckResult(
                status=CheckStatus.TIMEOUT,
                message=f"Connection to {host}:{port} timed out",
                details={'host': host, 'port': port}
            )
        except Exception as e:
            return CheckResult(
                status=CheckStatus.DOWN,
                message=str(e),
                details={'host': host, 'port': port}
            )
    
    # ----------------------------------------------------------------
    # HTTP Check
    # ----------------------------------------------------------------
    def check_http(
        self,
        url: str,
        method: str = 'GET',
        expected_status: int = 200,
        timeout: float = None,
        verify_ssl: bool = True,
        headers: Dict[str, str] = None,
        expected_content: str = None
    ) -> CheckResult:
        """
        Check HTTP endpoint availability and response.
        
        Args:
            url: Full URL to check (http:// or https://)
            method: HTTP method (GET, HEAD, POST)
            expected_status: Expected HTTP status code
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            headers: Optional headers to send
            expected_content: Optional string that must appear in response
            
        Returns:
            CheckResult with HTTP status and response time
        """
        if not REQUESTS_AVAILABLE:
            return CheckResult(
                status=CheckStatus.ERROR,
                message="requests library not installed"
            )
        
        timeout = timeout or self.default_timeout
        
        try:
            start_ms = datetime.utcnow()
            
            response = requests.request(
                method=method,
                url=url,
                timeout=timeout,
                verify=verify_ssl,
                headers=headers or {},
                allow_redirects=True
            )
            
            end_ms = datetime.utcnow()
            response_time = (end_ms - start_ms).total_seconds() * 1000
            
            details = {
                'url': url,
                'method': method,
                'status_code': response.status_code,
                'reason': response.reason,
                'content_length': len(response.content)
            }
            
            # Check status code
            if response.status_code != expected_status:
                return CheckResult(
                    status=CheckStatus.DEGRADED,
                    response_time_ms=round(response_time, 2),
                    message=f"Expected {expected_status}, got {response.status_code}",
                    details=details
                )
            
            # Check content if specified
            if expected_content and expected_content not in response.text:
                return CheckResult(
                    status=CheckStatus.DEGRADED,
                    response_time_ms=round(response_time, 2),
                    message=f"Expected content not found",
                    details=details
                )
            
            return CheckResult(
                status=CheckStatus.UP,
                response_time_ms=round(response_time, 2),
                message=f"HTTP {response.status_code} {response.reason}",
                details=details
            )
            
        except requests.exceptions.Timeout:
            return CheckResult(
                status=CheckStatus.TIMEOUT,
                message=f"Request to {url} timed out",
                details={'url': url, 'timeout': timeout}
            )
        except requests.exceptions.SSLError as e:
            return CheckResult(
                status=CheckStatus.ERROR,
                message=f"SSL error: {e}",
                details={'url': url, 'error': str(e)}
            )
        except requests.exceptions.ConnectionError as e:
            return CheckResult(
                status=CheckStatus.DOWN,
                message=f"Connection failed: {e}",
                details={'url': url, 'error': str(e)}
            )
        except Exception as e:
            return CheckResult(
                status=CheckStatus.ERROR,
                message=str(e),
                details={'url': url, 'error': str(e)}
            )
    
    # ----------------------------------------------------------------
    # DNS Check
    # ----------------------------------------------------------------
    def check_dns(
        self,
        hostname: str,
        record_type: str = 'A',
        nameserver: str = None,
        timeout: float = None
    ) -> CheckResult:
        """
        Check DNS resolution for a hostname.
        
        Args:
            hostname: Domain name to resolve
            record_type: DNS record type (A, AAAA, MX, CNAME, etc.)
            nameserver: Optional specific nameserver to query
            timeout: Query timeout in seconds
            
        Returns:
            CheckResult with DNS resolution status and records
        """
        timeout = timeout or self.default_timeout
        
        # Fallback to socket if dnspython not available
        if not DNS_AVAILABLE:
            return self._check_dns_socket(hostname, timeout)
        
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = timeout
            resolver.lifetime = timeout
            
            if nameserver:
                resolver.nameservers = [nameserver]
            
            start_ms = datetime.utcnow()
            answers = resolver.resolve(hostname, record_type)
            end_ms = datetime.utcnow()
            
            response_time = (end_ms - start_ms).total_seconds() * 1000
            
            records = [str(rdata) for rdata in answers]
            
            return CheckResult(
                status=CheckStatus.UP,
                response_time_ms=round(response_time, 2),
                message=f"Resolved {len(records)} {record_type} record(s)",
                details={
                    'hostname': hostname,
                    'record_type': record_type,
                    'records': records,
                    'nameserver': nameserver
                }
            )
            
        except dns.resolver.NXDOMAIN:
            return CheckResult(
                status=CheckStatus.DOWN,
                message=f"Domain {hostname} does not exist",
                details={'hostname': hostname, 'record_type': record_type}
            )
        except dns.resolver.NoAnswer:
            return CheckResult(
                status=CheckStatus.DEGRADED,
                message=f"No {record_type} records found",
                details={'hostname': hostname, 'record_type': record_type}
            )
        except dns.resolver.Timeout:
            return CheckResult(
                status=CheckStatus.TIMEOUT,
                message=f"DNS query timed out",
                details={'hostname': hostname, 'timeout': timeout}
            )
        except Exception as e:
            return CheckResult(
                status=CheckStatus.ERROR,
                message=str(e),
                details={'hostname': hostname, 'error': str(e)}
            )
    
    def _check_dns_socket(self, hostname: str, timeout: float) -> CheckResult:
        """Fallback DNS check using socket.getaddrinfo."""
        try:
            socket.setdefaulttimeout(timeout)
            start_ms = datetime.utcnow()
            
            result = socket.getaddrinfo(hostname, None)
            
            end_ms = datetime.utcnow()
            response_time = (end_ms - start_ms).total_seconds() * 1000
            
            ips = list(set([r[4][0] for r in result]))
            
            return CheckResult(
                status=CheckStatus.UP,
                response_time_ms=round(response_time, 2),
                message=f"Resolved to {len(ips)} IP(s)",
                details={
                    'hostname': hostname,
                    'ips': ips
                }
            )
        except socket.gaierror as e:
            return CheckResult(
                status=CheckStatus.DOWN,
                message=f"DNS resolution failed: {e}",
                details={'hostname': hostname, 'error': str(e)}
            )
        except Exception as e:
            return CheckResult(
                status=CheckStatus.ERROR,
                message=str(e),
                details={'hostname': hostname, 'error': str(e)}
            )


# Common port services for quick checks
COMMON_PORTS = {
    'SSH': 22,
    'TELNET': 23,
    'SMTP': 25,
    'DNS': 53,
    'HTTP': 80,
    'HTTPS': 443,
    'POP3': 110,
    'IMAP': 143,
    'SNMP': 161,
    'LDAP': 389,
    'SMB': 445,
    'MSSQL': 1433,
    'MYSQL': 3306,
    'RDP': 3389,
    'POSTGRES': 5432,
    'REDIS': 6379,
    'MONGODB': 27017
}


# Singleton instance
service_checker = ServiceChecker()
