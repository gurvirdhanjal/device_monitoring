import asyncio
import threading
import uuid
from datetime import datetime
from services.network_scanner import NetworkScanner

# Global instance
_discovery_service = None

def get_discovery_service():
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = DiscoveryService()
    return _discovery_service

class DiscoveryService:
    def __init__(self):
        self.scanner = NetworkScanner()
        self.active_scans = {}
        self.active_scans_lock = threading.Lock()
        
    def start_scan(self, ip_range, username='system'):
        """
        Start a new background scan.
        Returns the scan_id.
        """
        scan_id = str(uuid.uuid4())
        
        # Calculate approximate host count for initial stats
        try:
            import ipaddress
            net = ipaddress.IPv4Network(ip_range, strict=False)
            total_hosts = net.num_addresses
        except:
            total_hosts = 0

        with self.active_scans_lock:
            self.active_scans[scan_id] = {
                'id': scan_id,
                'devices': [],       # List of all found devices (accumulated)
                'new_devices': [],   # Buffer for polling (cleared on read)
                'status': 'scanning',
                'progress': 0,
                'total_found': 0,
                'scanned_hosts': 0,
                'total_hosts': total_hosts,
                'start_time': datetime.utcnow().isoformat(),
                'username': username,
                'ip_range': ip_range,
                'stop': False,
                'error': None
            }

        # Start background thread
        t = threading.Thread(
            target=self._run_async_scan_wrapper,
            args=(scan_id, ip_range),
            daemon=True
        )
        t.start()
        
        return scan_id

    def stop_scan(self, scan_id):
        """Stop a running scan."""
        with self.active_scans_lock:
            if scan_id in self.active_scans:
                self.active_scans[scan_id]['stop'] = True
                # We don't change status immediately; the scanner loop will see the flag and exit
                return True
        return False

    def get_scan_status(self, scan_id):
        """
        Get status and *newly discovered* devices since last call.
        Clears the 'new_devices' buffer.
        """
        with self.active_scans_lock:
            scan = self.active_scans.get(scan_id)
            if not scan:
                return None

            # Pop new devices for the UI
            new_devices = list(scan['new_devices'])
            scan['new_devices'] = []  # Clear buffer

            return {
                'id': scan_id,
                'status': scan['status'],
                'progress': scan['progress'],
                'total_found': scan['total_found'],
                'scanned_hosts': scan['scanned_hosts'],
                'total_hosts': scan['total_hosts'],
                'new_devices': new_devices,
                'error': scan.get('error')
            }

    def get_scan_results(self, scan_id):
        """
        Get ALL discovered devices for a scan (not just new ones).
        """
        with self.active_scans_lock:
            scan = self.active_scans.get(scan_id)
            if not scan:
                return None
            # Return a copy of the list
            return list(scan['devices'])

    def get_active_scan_id(self, username='system'):
        """
        Find an active scan ID for the user.
        """
        with self.active_scans_lock:
            for scan_id, scan in self.active_scans.items():
                if scan['status'] == 'scanning' and scan.get('username') == username:
                    return scan_id
        return None

    def _run_async_scan_wrapper(self, scan_id, ip_range):
        """
        Wrapper to run async scanner in a thread.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # We pass self.active_scans and lock so the scanner can update progress/check stop
            # The NetworkScanner.scan_network_range_incremental expects these
            devices = loop.run_until_complete(
                self.scanner.scan_network_range_incremental(
                    ip_range,
                    scan_id,
                    self.active_scans,
                    self.active_scans_lock
                )
            )

            # Mark complete
            with self.active_scans_lock:
                if scan_id in self.active_scans:
                    scan = self.active_scans[scan_id]
                    if scan['status'] != 'error': # Don't overwrite error status
                         # If stopped, it might already be marked stopped by scanner, but ensure consistency
                        if scan['stop']:
                             scan['status'] = 'stopped'
                        else:
                             scan['status'] = 'completed'
                        
                        scan['progress'] = 100
                        # Final sync of devices just in case
                        scan['devices'] = devices 

        except Exception as e:
            import traceback
            traceback.print_exc()
            with self.active_scans_lock:
                if scan_id in self.active_scans:
                    self.active_scans[scan_id]['status'] = 'error'
                    self.active_scans[scan_id]['error'] = str(e)
        finally:
            loop.close()
    def start_recursive_discovery(self, seed_ip):
        """
        Start a recursive discovery process starting from a seed IP.
        (Phase 1 implementation: Single-depth neighbor scan)
        """
        from services.ssh_service import SSHService
        from models import Device, db
        
        print(f"[Discovery] Starting recursive scan from {seed_ip}")
        
        # 1. Ensure seed device exists
        seed_device = Device.query.filter_by(device_ip=seed_ip).first()
        if not seed_device:
            print(f"[Discovery] Seed device {seed_ip} not found in inventory. Adding placeholder.")
            seed_device = Device(
                device_ip=seed_ip, 
                device_name=f"Seed-Core-{seed_ip}",
                device_type='Switch',
                is_monitored=True
            )
            db.session.add(seed_device)
            db.session.commit()
            
        # 2. Get Neighbors via SSH
        ssh_svc = SSHService()
        neighbors = ssh_svc.get_lldp_neighbors(seed_device)
        print(f"[Discovery] Found {len(neighbors)} neighbors for {seed_ip}")
        
        # 3. Process Neighbors
        for n in neighbors:
            remote_ip = n.get('remote_ip')
            if not remote_ip: continue
            
            # Check if exists
            neighbor = Device.query.filter_by(device_ip=remote_ip).first()
            if not neighbor:
                neighbor = Device(
                    device_ip=remote_ip,
                    device_name=n.get('remote_hostname', f"Discovered-{remote_ip}"),
                    device_type='Switch', # Assume switch for now
                    parent_switch_id=seed_device.device_id, # Temporary direct link
                    last_discovery_method='LLDP'
                )
                db.session.add(neighbor)
                print(f"[Discovery] Added new neighbor {remote_ip}")
            else:
                # Update topology info
                neighbor.parent_switch_id = seed_device.device_id
                neighbor.last_discovery_method = 'LLDP'
                
            db.session.commit()

    def map_devices_to_ports(self):
        """
        Analyze topology table (if populated) and update parent/child relationships.
        For now, this is a placeholder or basic implementation.
        """
        print("[Discovery] Mapping devices to ports...")
        # In a real implementation effectively use SwitchTopology table
        # to set parent_port_id on devices.
        pass
