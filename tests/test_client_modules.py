import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time

# Add parent directory to path to import client_modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client_modules.system_core import NetworkMonitor
from client_modules.system_context import WindowMonitor
from client_modules.system_processes import ProcessMonitor

class TestNetworkMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = NetworkMonitor()

    @patch('psutil.net_io_counters')
    @patch('time.time')
    def test_warmup_and_delta(self, mock_time, mock_io):
        # 1. Warm-up (First Call)
        mock_time.return_value = 1000.0
        mock_io.return_value = MagicMock(bytes_sent=1000, bytes_recv=1000)
        
        metrics = self.monitor.get_network_metrics()
        self.assertEqual(metrics['upload_speed_kbps'], 0.0)
        self.assertEqual(metrics['download_speed_kbps'], 0.0)
        
        # 2. Second Call (5 seconds later, +10KB sent, +20KB recv)
        mock_time.return_value = 1005.0
        # 10KB = 10240 bytes
        mock_io.return_value = MagicMock(bytes_sent=11240, bytes_recv=21480)
        
        metrics = self.monitor.get_network_metrics()
        
        # Upload: 10KB / 5s = 2 KB/s
        self.assertAlmostEqual(metrics['upload_speed_kbps'], 2.0)
        # Download: 20KB / 5s = 4 KB/s
        self.assertAlmostEqual(metrics['download_speed_kbps'], 4.0)

    @patch('psutil.net_io_counters')
    @patch('time.time')
    def test_negative_delta_handling(self, mock_time, mock_io):
        # Init
        mock_time.return_value = 1000.0
        mock_io.return_value = MagicMock(bytes_sent=5000, bytes_recv=5000)
        self.monitor.get_network_metrics()
        
        # Interface Reset (Counters drop to 0)
        mock_time.return_value = 1005.0
        mock_io.return_value = MagicMock(bytes_sent=100, bytes_recv=100)
        
        metrics = self.monitor.get_network_metrics()
        # Should report 0, not negative
        self.assertEqual(metrics['upload_speed_kbps'], 0.0)
        self.assertEqual(metrics['download_speed_kbps'], 0.0)


class TestWindowMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = WindowMonitor()

    def test_gating_disabled(self):
        # Should return None immediately without calling system APIs
        result = self.monitor.get_active_window(enabled=False)
        self.assertIsNone(result)

    @patch('platform.system')
    def test_non_windows_handling(self, mock_platform):
        mock_platform.return_value = 'Linux'
        result = self.monitor.get_active_window(enabled=True)
        self.assertIsNone(result)

    @patch('platform.system')
    def test_truncation(self, mock_platform):
        # Mocking import logic is hard, so we assume we are either on Windows or we mock the inner logic 
        # But system_context.py imports win32 inside the method.
        # We will mock modules in sys.modules
        mock_platform.return_value = 'Windows'
        
        mock_win32gui = MagicMock()
        mock_win32process = MagicMock()
        
        with patch.dict(sys.modules, {'win32gui': mock_win32gui, 'win32process': mock_win32process}):
            # Setup valid window
            mock_win32gui.GetForegroundWindow.return_value = 123
            
            # Setup Long Title (300 chars)
            long_title = "A" * 300
            mock_win32gui.GetWindowText.return_value = long_title
            
            # Setup PID
            mock_win32process.GetWindowThreadProcessId.return_value = (0, 456)
            
            with patch('psutil.Process') as mock_psutil_proc:
                mock_psutil_proc.return_value.name.return_value = "notepad.exe"
                
                result = self.monitor.get_active_window(enabled=True)
                
                self.assertIsNotNone(result)
                self.assertEqual(len(result['title']), 256) # 253 + "..."
                self.assertTrue(result['title'].endswith("..."))
                self.assertEqual(result['app_name'], "notepad.exe")


class TestProcessMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = ProcessMonitor()

    @patch('psutil.process_iter')
    def test_process_priming(self, mock_iter):
        # Mock Process
        mock_proc = MagicMock()
        mock_proc.info = {'pid': 100, 'name': 'test_app', 'memory_info': MagicMock(rss=10485760)} # 10MB
        
        # First call: cpu_percent() called first for priming, then for value
        # We want the first call (inside loop, priming) to return 0.0, 
        # but usage is actually cleaner if we just check the output logic.
        # The monitor logic calls cpu_percent(interval=None) repeatedly.
        
        # Setup mock behavior: first call 0.0, second call 50.0
        mock_proc.cpu_percent.side_effect = [0.0, 50.0, 50.0] 
        
        mock_iter.return_value = [mock_proc]
        
        # Run 1: First time seeing PID 100
        # The code calls cpu_percent once for priming (ignoring result), then again for value.
        # Actually my implementation calls it twice? Let's check implementation.
        # Implementation:
        # if pid not in cache: cache[pid]=proc; proc.cpu_percent() (Prime)
        # val = proc.cpu_percent() (Value)
        
        # So yes, side_effect=[0.0, 50.0] works perfectly.
        
        top = self.monitor.get_top_processes(limit=1)
        
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]['pid'], 100)
        self.assertEqual(top[0]['cpu_percent'], 50.0) # Correctly primed and read
        self.assertEqual(top[0]['memory_mb'], 10.0)

if __name__ == '__main__':
    unittest.main()
