import unittest
from unittest.mock import MagicMock, patch
import json
from services.discovery import DiscoveryService
from flask import Flask, session
from routes.devices import devices_bp
from extensions import db
from models.device import Device
import threading
import time

class TestDiscoveryService(unittest.TestCase):
    def setUp(self):
        self.service = DiscoveryService()
        # Mock the scanner execution to avoid real network calls
        self.service.scanner = MagicMock()
        self.service.scanner.scan_network_range_incremental = MagicMock()

    def test_start_scan_initializes_state(self):
        scan_id = self.service.start_scan('192.168.1.0/24')
        
        self.assertIn(scan_id, self.service.active_scans)
        scan_state = self.service.active_scans[scan_id]
        self.assertEqual(scan_state['status'], 'scanning')
        self.assertEqual(scan_state['ip_range'], '192.168.1.0/24')
        self.assertEqual(scan_state['total_hosts'], 256) # Approx for /24

    def test_stop_scan_flags_state(self):
        scan_id = self.service.start_scan('192.168.1.0/24')
        result = self.service.stop_scan(scan_id)
        
        self.assertTrue(result)
        self.assertTrue(self.service.active_scans[scan_id]['stop'])

    def test_get_scan_status_clears_buffer(self):
        scan_id = self.service.start_scan('192.168.1.0/24')
        
        # Simulate results in buffer
        device_mock = {'ip': '192.168.1.10', 'status': 'Online'}
        with self.service.active_scans_lock:
            self.service.active_scans[scan_id]['new_devices'].append(device_mock)
            self.service.active_scans[scan_id]['devices'].append(device_mock)
            
        # First call gets devices
        status = self.service.get_scan_status(scan_id)
        self.assertEqual(len(status['new_devices']), 1)
        self.assertEqual(status['new_devices'][0]['ip'], '192.168.1.10')
        
        # Second call buffer should be empty
        status_2 = self.service.get_scan_status(scan_id)
        self.assertEqual(len(status_2['new_devices']), 0)


class TestBulkAddEndpoint(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'test'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(self.app)
        # Blueprint already includes /api in routes, so prefix should be empty or handle accordingly
        # In main app it's registered with url_prefix=''
        self.app.register_blueprint(devices_bp)
        
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_bulk_add_devices(self):
        payload = [
            {'ip': '10.0.0.1', 'hostname': 'Device-1', 'mac': '00:00:00:00:00:01', 'manufacturer': 'VendorA'},
            {'ip': '10.0.0.2', 'hostname': 'Device-2', 'mac': '00:00:00:00:00:02', 'manufacturer': 'VendorB'}
        ]
        
        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['logged_in'] = True
                
            response = client.post('/api/devices/bulk_add', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
            
            data = response.get_json()
            self.assertEqual(response.status_code, 201)
            self.assertTrue(data['success'])
            self.assertEqual(data['added'], 2)
            self.assertEqual(data['skipped'], 0)
            
            # Verify in DB
            with self.app.app_context():
                count = Device.query.count()
                self.assertEqual(count, 2)
                d1 = Device.query.filter_by(device_ip='10.0.0.1').first()
                self.assertIsNotNone(d1)
                self.assertEqual(d1.device_name, 'Device-1')

    def test_bulk_add_skips_duplicates(self):
        # Pre-add a device
        with self.app.app_context():
            existing = Device(device_ip='10.0.0.1', device_name='Existing', device_type='Network Device')
            db.session.add(existing)
            db.session.commit()
            
        payload = [
            {'ip': '10.0.0.1', 'hostname': 'Device-1', 'mac': '00:00:00:00:00:01'}, # Duplicate IP
            {'ip': '10.0.0.2', 'hostname': 'Device-2', 'mac': '00:00:00:00:00:02'}  # New
        ]
        
        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['logged_in'] = True
                
            response = client.post('/api/devices/bulk_add', 
                                 data=json.dumps(payload),
                                 content_type='application/json')
            
            data = response.get_json()
            self.assertEqual(data['added'], 1)
            self.assertEqual(data['skipped'], 1)
            
            with self.app.app_context():
                self.assertEqual(Device.query.count(), 2)
