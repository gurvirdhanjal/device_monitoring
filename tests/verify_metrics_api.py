import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from datetime import datetime, timedelta
from metrics.normalizer import Metric
from services.device_monitor import DeviceMonitor
import unittest
import json
from unittest.mock import MagicMock, patch

class TestMetricsAPI(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Mock session to simulate logged in user
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user_id'] = 1
            sess['role'] = 'admin'

    def tearDown(self):
        self.app_context.pop()

    def test_metrics_endpoint(self):
        # 1. Populate some metrics in the collector
        # We need to access the monitor instance. 
        # In routes/monitoring.py, 'monitor' is a global instance.
        # We can patch it.
        
        with patch('routes.monitoring.monitor') as mock_monitor:
            # Setup mock data flow
            now = datetime.now()
            
            # 3 sample metrics
            metrics = [
                Metric(
                    device_ip='127.0.0.1',
                    name='network_latency_ms',
                    value=10.0,
                    timestamp=now - timedelta(minutes=30),
                    unit='ms'
                ),
                Metric(
                    device_ip='127.0.0.1',
                    name='network_latency_ms',
                    value=20.0,
                    timestamp=now - timedelta(minutes=15),
                    unit='ms'
                ),
                Metric(
                    device_ip='127.0.0.1',
                    name='network_latency_ms',
                    value=30.0,
                    timestamp=now - timedelta(minutes=1),
                    unit='ms'
                )
            ]
            
            # Setup get_metrics return
            # It expects (device_ip, metric_name)
            mock_monitor.collector.get_metrics.return_value = metrics
            
            # 2. Call the API
            response = self.client.get('/api/monitoring/metrics?device_ip=127.0.0.1&metric_name=network_latency_ms&time_range=last_1h')
            
            # 3. Verify Response
            print(f"Status Code: {response.status_code}")
            try:
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                
                print(f"\nAPI Response: {json.dumps(data, indent=2)}")
                
                if 'error' in data:
                    print(f"API Returned Error: {data['error']}")
                    self.fail(f"API Error: {data['error']}")

                # Verify aggregation
                summary = data.get('summary', {})
                self.assertEqual(summary.get('min'), 10.0, f"Min mismatch: {summary.get('min')}")
                self.assertEqual(summary.get('max'), 30.0, f"Max mismatch: {summary.get('max')}")
                self.assertEqual(summary.get('avg'), 20.0, f"Avg mismatch: {summary.get('avg')}")
                
                # Verify data points
                self.assertEqual(len(data.get('data', [])), 3, "Data points mismatch")
                
                sys.stderr.write("✔ API Verification Passed\n")
            except Exception as e:
                sys.stderr.write(f"❌ TEST FAILED: {e}\n")
                raise e

if __name__ == '__main__':
    unittest.main(buffer=False)
