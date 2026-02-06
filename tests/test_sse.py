"""
Tests for SSE (Server-Sent Events) implementation.
"""
import pytest
import time
import threading
import queue
from unittest.mock import patch, MagicMock
from services.sse_broadcaster import SSEBroadcaster, broadcast_event, get_broadcaster


class TestSSEBroadcaster:
    """Tests for the SSEBroadcaster class."""

    def setup_method(self):
        """Create a fresh broadcaster for each test."""
        self.broadcaster = SSEBroadcaster(max_events_per_second=5)

    def test_register_client(self):
        """Test client registration returns a queue."""
        client_id = "test-client-1"
        client_queue = self.broadcaster.register_client(client_id)
        
        assert isinstance(client_queue, queue.Queue)
        assert self.broadcaster.get_client_count() == 1

    def test_unregister_client(self):
        """Test client unregistration."""
        client_id = "test-client-1"
        self.broadcaster.register_client(client_id)
        
        assert self.broadcaster.get_client_count() == 1
        
        self.broadcaster.unregister_client(client_id)
        assert self.broadcaster.get_client_count() == 0

    def test_broadcast_to_single_client(self):
        """Test broadcasting event to a single client."""
        client_id = "test-client-1"
        client_queue = self.broadcaster.register_client(client_id)
        
        result = self.broadcaster.broadcast('device_status', {
            'device_ip': '192.168.1.1',
            'new_status': 'down'
        })
        
        assert result is True
        assert not client_queue.empty()
        
        message = client_queue.get_nowait()
        assert 'event: device_status' in message
        assert '192.168.1.1' in message
        assert 'down' in message

    def test_broadcast_to_multiple_clients(self):
        """Test broadcasting event to multiple clients."""
        queues = []
        for i in range(5):
            q = self.broadcaster.register_client(f"client-{i}")
            queues.append(q)
        
        self.broadcaster.broadcast('alert_created', {
            'severity': 'CRITICAL',
            'message': 'Test alert'
        })
        
        for q in queues:
            assert not q.empty()
            message = q.get_nowait()
            assert 'event: alert_created' in message

    def test_rate_limiting(self):
        """Test that rate limiting prevents event flooding."""
        client_queue = self.broadcaster.register_client("test-client")
        
        # Send more events than rate limit allows
        success_count = 0
        for i in range(10):
            if self.broadcaster.broadcast('device_status', {'index': i}):
                success_count += 1
        
        # Should be limited to max_events_per_second (5)
        assert success_count == 5
        
        # Wait for rate limit window to reset
        time.sleep(1.1)
        
        # Should be able to send again
        result = self.broadcaster.broadcast('device_status', {'after_reset': True})
        assert result is True

    def test_rate_limiting_per_event_type(self):
        """Test that rate limiting is per event type."""
        client_queue = self.broadcaster.register_client("test-client")
        
        # Fill up device_status rate limit
        for i in range(5):
            self.broadcaster.broadcast('device_status', {'index': i})
        
        # device_status should be limited
        result = self.broadcaster.broadcast('device_status', {'extra': True})
        assert result is False
        
        # But alert_created should still work (separate limit)
        result = self.broadcaster.broadcast('alert_created', {'new': True})
        assert result is True

    def test_full_queue_client_removed(self):
        """Test that clients with full queues are removed."""
        # Create broadcaster with smaller queue
        broadcaster = SSEBroadcaster(max_events_per_second=100)
        
        client_id = "slow-client"
        client_queue = broadcaster.register_client(client_id)
        
        # Don't consume from queue - let it fill up
        # Queue maxsize is 100, so broadcast > 100 events
        for i in range(150):
            broadcaster.broadcast('device_status', {'index': i})
        
        # Client should have been removed due to full queue
        assert broadcaster.get_client_count() == 0

    def test_heartbeat(self):
        """Test heartbeat sends to all clients."""
        queues = []
        for i in range(3):
            q = self.broadcaster.register_client(f"client-{i}")
            queues.append(q)
        
        self.broadcaster.send_heartbeat()
        
        for q in queues:
            assert not q.empty()
            message = q.get_nowait()
            assert 'heartbeat' in message

    def test_event_id_uniqueness(self):
        """Test that each event has a unique ID."""
        client_queue = self.broadcaster.register_client("test-client")
        
        event_ids = set()
        for i in range(5):
            self.broadcaster.broadcast('device_status', {'index': i})
            message = client_queue.get_nowait()
            # Extract event ID from message
            for line in message.split('\n'):
                if line.startswith('id: '):
                    event_ids.add(line[4:])
        
        assert len(event_ids) == 5  # All unique


class TestBroadcastEventFunction:
    """Tests for the broadcast_event convenience function."""

    def test_broadcast_event_convenience(self):
        """Test the broadcast_event function."""
        # Get the global broadcaster
        broadcaster = get_broadcaster()
        client_queue = broadcaster.register_client("test-client")
        
        result = broadcast_event('latency_spike', {
            'device_ip': '10.0.0.1',
            'latency_ms': 250
        })
        
        assert result is True
        assert not client_queue.empty()
        
        # Cleanup
        broadcaster.unregister_client("test-client")


class TestSSEEndpoint:
    """Tests for the SSE Flask endpoint."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import create_app
        app = create_app({'TESTING': True})
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_stream_endpoint_requires_auth(self, client):
        """Test that SSE endpoint requires authentication."""
        response = client.get('/api/events/stream')
        assert response.status_code == 401

    def test_stream_endpoint_with_auth(self, client, app):
        """Test SSE endpoint with authentication."""
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'test_user'
        
        # Start request but don't consume entire stream
        response = client.get('/api/events/stream')
        
        assert response.status_code == 200
        assert response.content_type == 'text/event-stream'

    def test_status_endpoint(self, client, app):
        """Test SSE status endpoint."""
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'test_user'
        
        response = client.get('/api/events/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'connected_clients' in data
        assert 'status' in data
