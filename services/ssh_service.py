import logging
import socket
import time
from models import Device, SSHProfile, SwitchTopology, db

# Try to import paramiko, handle missing dependency gracefully
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

class SSHService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def test_connection(self, host, username, password=None, key_path=None, port=22):
        """
        Test SSH connection to a host.
        Returns (success, message)
        """
        if not PARAMIKO_AVAILABLE:
            return False, "Paramiko library not installed. Cannot perform SSH."

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Prepare kwargs
            connect_kwargs = {
                'hostname': host,
                'port': port,
                'username': username,
                'timeout': 10,
                'banner_timeout': 10
            }
            if password:
                connect_kwargs['password'] = password
            if key_path:
                connect_kwargs['key_filename'] = key_path
                
            client.connect(**connect_kwargs)
            client.close()
            return True, "Connection successful"
            
        except paramiko.AuthenticationException:
            return False, "Authentication failed"
        except paramiko.SSHException as e:
            return False, f"SSH error: {str(e)}"
        except socket.timeout:
            return False, "Connection timed out"
        except Exception as e:
            return False, f"Error: {str(e)}"
        finally:
            client.close()

    def execute_command(self, host, profile_id, command, timeout=10):
        """
        Execute a single command on a device using a stored profile.
        Returns (output, error) or raises Exception.
        """
        if not PARAMIKO_AVAILABLE:
            raise ImportError("Paramiko not installed")

        profile = SSHProfile.query.get(profile_id)
        if not profile:
            raise ValueError(f"SSH Profile {profile_id} not found")
            
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            client.connect(
                hostname=host,
                username=profile.username,
                password=profile.password,
                key_filename=profile.key_path,
                timeout=timeout
            )
            
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            out_str = stdout.read().decode('utf-8')
            err_str = stderr.read().decode('utf-8')
            
            return out_str, err_str
            
        except Exception as e:
            self.logger.error(f"SSH Execute fail on {host}: {e}")
            raise
        finally:
            client.close()

    def get_lldp_neighbors(self, device):
        """
        Connect to device, run 'show lldp neighbors detail' (or equivalent),
        parse output, and return list of neighbor dicts.
        
        Mock implementation for now if no SSH profile.
        """
        if not device.ssh_profile_id:
            return self._simulate_lldp_neighbors(device)

        # Real implementation would be here...
        # For now, fallback to simulation to avoid blocking dev
        return self._simulate_lldp_neighbors(device)

    def _simulate_lldp_neighbors(self, device):
        """
        Return fake neighbors for testing topology.
        """
        import random
        neighbors = []
        
        # Simulate 0-2 neighbors
        num_neighbors = random.randint(0, 2)
        
        for i in range(num_neighbors):
             neighbors.append({
                 'remote_ip': f"192.168.1.{random.randint(50, 200)}",
                 'remote_hostname': f"Switch-{random.randint(1,99)}",
                 'remote_port': f"Gi0/{random.randint(1,24)}",
                 'local_port': f"Gi0/{random.randint(1,48)}",
                 'remote_desc': "Simulated Switch"
             })
             
        return neighbors
