import socket
import subprocess
import platform
from utils.helpers import validate_ip_address

def test_port(ip, port, timeout=2):
    """Test if a port is open on a device"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            return result == 0
    except:
        return False

def test_http_service(ip, port=80, timeout=2):
    """Test HTTP service on a device"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((ip, port))
            sock.send(b"GET / HTTP/1.0\r\n\r\n")
            response = sock.recv(1024)
            return True, response.decode('utf-8', errors='ignore')[:500]
    except Exception as e:
        return False, str(e)

def test_https_service(ip, port=443, timeout=2):
    """Test HTTPS service on a device"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((ip, port))
            # Send a simple request to check if service responds
            sock.send(b"GET / HTTP/1.0\r\n\r\n")
            response = sock.recv(1024)
            return True, response.decode('utf-8', errors='ignore')[:500]
    except Exception as e:
        return False, str(e)

def get_service_name(port):
    """Get common service name for port"""
    common_services = {
        21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
        80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS', 
        993: 'IMAPS', 995: 'POP3S', 3389: 'RDP'
    }
    return common_services.get(port, 'Unknown')