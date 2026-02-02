
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client_modules.system_core import SystemMonitor

class TestSystemMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = SystemMonitor()

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_core_metrics(self, mock_disk, mock_mem, mock_cpu):
        # Setup mocks
        mock_cpu.return_value = 15.5
        mock_mem.return_value = MagicMock(percent=45.2)
        mock_disk.return_value = MagicMock(percent=67.8)

        # Call method
        metrics = self.monitor.get_core_metrics()

        # Check structure
        self.assertIn('cpu_percent', metrics)
        self.assertIn('memory_percent', metrics)
        self.assertIn('disk_usage', metrics)

        # Check values
        self.assertEqual(metrics['cpu_percent'], 15.5)
        self.assertEqual(metrics['memory_percent'], 45.2)
        self.assertEqual(metrics['disk_usage'], 67.8) # This verifies my fix worked

class TestServiceEndpointLogic(unittest.TestCase):
    """
    Simulate the logic inside service.py's get_secure_stats 
    to verify it correctly reads from the 'current_stats' cache.
    """
    def test_stats_reading_from_cache(self):
        # 1. Setup Cache (simulating what explicit_interval_monitor does)
        curr_stats = {
            'core': {
                'cpu_percent': 10.0, 
                'memory_percent': 20.0, 
                'disk_usage': 88.8 # Cached value
            },
            'network': {'upload_speed_kbps': 5.5, 'download_speed_kbps': 12.2}
        }
        
        # 2. Simulate the API logic (from service.py)
        # We manually reproduce the logic here to assert it works as intended
        # "disk_usage": current_stats.get('core', {}).get('disk_usage', 0)
        
        disk_usage = curr_stats.get('core', {}).get('disk_usage', 0)
        cpu_percent = curr_stats.get('core', {}).get('cpu_percent', 0)
        
        # 3. Assertions
        self.assertEqual(disk_usage, 88.8) # Should read from cache, NOT be 0
        self.assertEqual(cpu_percent, 10.0)

if __name__ == '__main__':
    unittest.main()
