import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock cv2 before importing routes.camera_streaming
sys.modules['cv2'] = MagicMock()

from routes.camera_streaming import CameraStream, start_camera_stream, stop_camera_stream, active_streams

class TestCameraStream(unittest.TestCase):

    def setUp(self):
        # Reset active streams before each test
        active_streams.clear()

    @patch('routes.camera_streaming.cv2')
    def test_camera_stream_initialization(self, mock_cv2):
        stream = CameraStream(1, "rtsp://test")
        self.assertEqual(stream.device_id, 1)
        self.assertEqual(stream.rtsp_link, "rtsp://test")
        self.assertFalse(stream.is_running)

    @patch('routes.camera_streaming.cv2')
    def test_start_stream_success(self, mock_cv2):
        # Setup mock capture
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, MagicMock()) # Success read
        mock_cv2.VideoCapture.return_value = mock_cap
        
        stream = CameraStream(1, "rtsp://test")
        result = stream.start_stream()
        
        self.assertTrue(result)
        self.assertTrue(stream.is_running)
        self.assertIsNotNone(stream.capture_thread)
        self.assertTrue(stream.capture_thread.is_alive())
        
        # Stop stream to clean up thread
        stream.stop_stream()

    @patch('routes.camera_streaming.cv2')
    def test_start_stream_failure_open(self, mock_cv2):
        # Setup mock capture failure
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cv2.VideoCapture.return_value = mock_cap
        
        stream = CameraStream(1, "rtsp://test")
        result = stream.start_stream()
        
        self.assertFalse(result)
        self.assertFalse(stream.is_running)
        self.assertEqual(stream.last_error, "Failed to open stream")

    @patch('routes.camera_streaming.cv2')
    def test_start_stream_failure_read(self, mock_cv2):
        # Setup mock capture open success but read fail
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None) # Fail read
        mock_cv2.VideoCapture.return_value = mock_cap
        
        stream = CameraStream(1, "rtsp://test")
        result = stream.start_stream()
        
        self.assertFalse(result)
        # Should clean up
        mock_cap.release.assert_called()

    @patch('routes.camera_streaming.cv2')
    def test_reconnect_logic(self, mock_cv2):
        stream = CameraStream(1, "rtsp://test")
        # Manually trigger reconnect
        stream._reconnect_camera()
        
        mock_cv2.VideoCapture.assert_called_with("rtsp://test")

    def test_helper_start_stop(self):
        with patch('routes.camera_streaming.CameraStream') as MockStream:
            mock_instance = MockStream.return_value
            mock_instance.start_stream.return_value = True
            
            # Test Start
            result = start_camera_stream(99, "rtsp://test")
            self.assertTrue(result)
            self.assertIn(99, active_streams)
            
            # Test Stop
            result = stop_camera_stream(99)
            self.assertTrue(result)
            self.assertNotIn(99, active_streams)

if __name__ == '__main__':
    unittest.main()
