import time
import math
import random
import threading
from datetime import datetime
from extensions import db
from models.device import Device
from models.interfaces import DeviceInterface, InterfaceTrafficHistory
from services.snmp_service import snmp_service

class InterfacePoller:
    """
    Service to poll interface statistics from devices and store history.
    Includes simulation mode for demo purposes.
    """
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._app = None

    def start_polling(self, app):
        """Start the background polling thread"""
        self._app = app
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            print("Interface Poller Service started.")

    def stop_polling(self):
        """Stop the background polling thread"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            print("Interface Poller Service stopped.")

    def _run_loop(self):
        """Main polling loop"""
        while not self._stop_event.is_set():
            try:
                with self._app.app_context():
                    self._poll_all_devices()
            except Exception as e:
                print(f"Error in interface poller loop: {e}")
            
            # Sleep for 10 seconds (aggressive polling for real-time feel)
            # In production, this might be configurable per device or global 60s
            time.sleep(10)

    def _poll_all_devices(self):
        """Polls all monitored devices or simulates data"""
        devices = Device.query.filter_by(is_monitored=True).all()
        
        for device in devices:
            # TRY REAL SNMP POLL
            # In a real scenario, we'd check if SNMP is enabled for this device.
            # Here we will try, and if it fails (likely in dev env), we simulate.
            
            success = self._poll_device_real(device)
            if not success:
               self._simulate_device_traffic(device)
        
        # Batch commit for ALL devices
        db.session.commit()

    def _poll_device_real(self, device) -> bool:
        """
        Attempt to poll real SNMP data.
        Returns True if successful, False if failed/no-response.
        """
        # Placeholder for real SNMP retrieval logic:
        # 1. Get credentials (snmp_config)
        # 2. snmp_service.get_interface_counters(...)
        # 3. Update DB
        
        # Since we likely don't have real SNMP devices in this environment, 
        # we return False to trigger simulation.
        # To enable real polling, implement the credential lookup here.
        return False

    def _simulate_device_traffic(self, device):
        """
        Generates simulated traffic data for demo purposes.
        Creates/Updates interfaces and appends history.
        """
        # Ensure we have "fake" interfaces for this device
        interfaces = DeviceInterface.query.filter_by(device_id=device.device_id).all()
        
        if not interfaces:
            # Create standard set of interfaces for simulation
            fake_ifs = [
                {'name': 'GigabitEthernet0/1', 'alias': 'Uplink', 'speed': 1000000000},
                {'name': 'GigabitEthernet0/2', 'alias': 'Server-Agg', 'speed': 1000000000},
                {'name': 'Vlan10', 'alias': 'Mgmt', 'speed': 100000000},
                {'name': 'Vlan20', 'alias': 'Corp-Wifi', 'speed': 1000000000},
                {'name': 'Tunnel0', 'alias': 'VPN-Gateway', 'speed': 100000000}
            ]
            
            for index, fake in enumerate(fake_ifs, 1):
                iface = DeviceInterface(
                    device_id=device.device_id,
                    if_index=index,
                    name=fake['name'],
                    alias=fake['alias'],
                    speed_bps=fake['speed'],
                    if_type=6, # ethernet
                    admin_status='up',
                    oper_status='up'
                )
                db.session.add(iface)
            # db.session.commit() removed for batching
            interfaces = DeviceInterface.query.filter_by(device_id=device.device_id).all()
        
        # Generate traffic
        timestamp = datetime.utcnow()
        
        for iface in interfaces:
            # Simulate Sine Wave Traffic
            # Use time dependent function to make it look like a trend
            t = time.time()
            
            # Base load + Sine wave variation + Random noise
            # Unique phase per interface based on ID
            phase = iface.interface_id * 10 
            
            # Traffic pattern logic
            if 'Uplink' in (iface.alias or ''):
                base_bps = 500_000_000 # 500 Mbps avg
                variance = 200_000_000
                period = 300 # 5 min cycle
            elif 'Wifi' in (iface.alias or ''):
                base_bps = 150_000_000
                variance = 100_000_000
                period = 180
            else:
                base_bps = 20_000_000
                variance = 15_000_000
                period = 600

            # Calculate RX/TX Rate
            rx_rate = base_bps + (math.sin((t + phase) / period) * variance) + random.randint(-5000000, 5000000)
            tx_rate = rx_rate * (0.1 + (math.sin(t/period) * 0.05)) # TX is a fraction of RX usually
            
            # Ensure non-negative
            rx_rate = max(0, rx_rate)
            tx_rate = max(0, tx_rate)
            
            # Calculate Utilization %
            rx_util = (rx_rate / iface.speed_bps * 100) if iface.speed_bps else 0
            tx_util = (tx_rate / iface.speed_bps * 100) if iface.speed_bps else 0
            
            # Record History
            history = InterfaceTrafficHistory(
                interface_id=iface.interface_id,
                timestamp=timestamp,
                rx_bps=rx_rate,
                tx_bps=tx_rate,
                rx_utilization_pct=min(100, rx_util),
                tx_utilization_pct=min(100, tx_util)
            )
            db.session.add(history)
            
            # iface.last_in_octets = ... (omitted for simulation as we write rate directly)
            
        # db.session.commit() removed for batching
        
        # Cleanup old history (keep last 24 hours only to prevent bloat)
        # In a real app, do this less frequently (e.g. daily job)
        cutoff = datetime.utcnow().timestamp() - 86400
        # Simple bulk delete requires careful SQLAlchemy usage or raw SQL
        # Skipping for now to keep it fast

# Singleton
interface_poller = InterfacePoller()
