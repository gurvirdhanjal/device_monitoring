"""
Unit tests for NMS Backend Features:
- SNMP Integration
- Service Checks
- Dashboard APIs
"""
import unittest
import json
from app import create_app, db
from models.user import User
from models.device import Device
from models.snmp_config import DeviceSnmpConfig

class TestNMSBackend(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Create Test User
            user = User(username='admin', email='admin@test.com')
            user.set_password('password')
            db.session.add(user)
            
            # Create Test Device
            device = Device(
                device_name='Test Router',
                device_ip='192.168.1.1',
                device_type='Router',
                manufacturer='Cisco',
                is_monitored=True
            )
            db.session.add(device)
            db.session.commit()
            self.device_id = device.device_id
            
            # Login
            with self.client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user_id'] = user.id
                sess['role'] = 'admin'

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # ----------------------------------------------------------------
    # SNMP Tests
    # ----------------------------------------------------------------
    def test_snmp_config_creation(self):
        """Test creating SNMP configuration"""
        response = self.client.post('/api/snmp/config', json={
            'device_id': self.device_id,
            'community_string': 'secret',
            'snmp_version': '2c',
            'snmp_port': 161
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify persistence
        with self.app.app_context():
            config = DeviceSnmpConfig.query.filter_by(device_id=self.device_id).first()
            self.assertIsNotNone(config)
            self.assertEqual(config.community_string, 'secret')

    def test_snmp_api_access(self):
        """Test SNMP API endpoint access restrictions"""
        # Logout
        with self.client.session_transaction() as sess:
            sess.clear()
            
        response = self.client.get(f'/api/snmp/config/{self.device_id}')
        self.assertEqual(response.status_code, 401)

    # ----------------------------------------------------------------
    # Service Checks Tests
    # ----------------------------------------------------------------
    def test_tcp_check_api(self):
        """Test TCP check API (mocking the actual check logic implies basic route test)"""
        # We perform a real check against localhost which might fail or succeed,
        # but we just want to ensure the API handles the request.
        response = self.client.get('/api/services/check/tcp?host=127.0.0.1&port=12345&timeout=0.1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['check_type'], 'tcp')
        self.assertIn('status', data)

    def test_http_check_api(self):
        """Test HTTP check API"""
        response = self.client.get('/api/services/check/http?url=https://google.com&timeout=1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['check_type'], 'http')

    # ----------------------------------------------------------------
    # Dashboard Inventory Tests
    # ----------------------------------------------------------------
    def test_inventory_api(self):
        """Test Inventory Statistics API"""
        # Add SNMP config to test stats
        with self.app.app_context():
            config = DeviceSnmpConfig(device_id=self.device_id, is_enabled=True)
            db.session.add(config)
            db.session.commit()
            
        response = self.client.get('/api/dashboard/inventory')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data['total_devices'], 1)
        self.assertEqual(data['by_vendor']['Cisco'], 1)
        self.assertEqual(data['by_type']['Router'], 1)
        self.assertEqual(data['snmp_status']['enabled'], 1)
        self.assertEqual(data['snmp_status']['percent_enabled'], 100.0)

if __name__ == '__main__':
    unittest.main()
