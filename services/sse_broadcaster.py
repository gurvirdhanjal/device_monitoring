"""
SSE Event Broadcaster for Real-Time Dashboard Updates.

Manages SSE client connections and broadcasts events to all connected clients
with rate limiting and graceful disconnection handling.
"""
import queue
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Callable, Optional
from collections import defaultdict


class SSEBroadcaster:
    """
    Thread-safe SSE event broadcaster.
    
    Features:
    - Client registry with per-client message queues
    - Event rate limiting (prevents flooding)
    - Heartbeat support for keep-alive
    - Graceful client cleanup
    """
    
    def __init__(self, max_events_per_second: int = 10):
        self._clients: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()
        self._max_events_per_second = max_events_per_second
        
        # Rate limiting: track events per type per second
        self._event_counts: Dict[str, list] = defaultdict(list)
        self._rate_limit_lock = threading.Lock()
    
    def register_client(self, client_id: str) -> queue.Queue:
        """
        Register a new SSE client and return its message queue.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Queue for receiving events
        """
        client_queue = queue.Queue(maxsize=100)  # Bounded queue to prevent memory issues
        
        with self._lock:
            self._clients[client_id] = client_queue
            print(f"[SSE] Client {client_id[:8]} connected. Total clients: {len(self._clients)}")
        
        return client_queue
    
    def unregister_client(self, client_id: str) -> None:
        """Remove a client from the registry."""
        with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                print(f"[SSE] Client {client_id[:8]} disconnected. Total clients: {len(self._clients)}")
    
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        with self._lock:
            return len(self._clients)
    
    def _is_rate_limited(self, event_type: str) -> bool:
        """Check if event type has exceeded rate limit."""
        current_time = time.time()
        
        with self._rate_limit_lock:
            # Clean old timestamps (older than 1 second)
            self._event_counts[event_type] = [
                ts for ts in self._event_counts[event_type]
                if current_time - ts < 1.0
            ]
            
            if len(self._event_counts[event_type]) >= self._max_events_per_second:
                return True
            
            self._event_counts[event_type].append(current_time)
            return False
    
    def broadcast(self, event_type: str, payload: dict) -> bool:
        """
        Broadcast an event to all connected clients.
        
        Args:
            event_type: Type of event (device_status, alert_created, etc.)
            payload: Event data
            
        Returns:
            True if broadcast was successful, False if rate limited
        """
        # Rate limit check
        if self._is_rate_limited(event_type):
            print(f"[SSE] Rate limited: {event_type}")
            return False
        
        # Build SSE event
        event_id = str(uuid.uuid4())
        event_data = {
            'event_id': event_id,
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'payload': payload
        }
        
        # Format as SSE message
        import json
        sse_message = f"id: {event_id}\nevent: {event_type}\ndata: {json.dumps(event_data)}\n\n"
        
        # Broadcast to all clients
        disconnected_clients = []
        
        with self._lock:
            for client_id, client_queue in self._clients.items():
                try:
                    client_queue.put_nowait(sse_message)
                except queue.Full:
                    # Client queue is full, mark for removal (slow client)
                    disconnected_clients.append(client_id)
                    print(f"[SSE] Client {client_id[:8]} queue full, marking for removal")
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.unregister_client(client_id)
        
        return True
    
    def send_heartbeat(self) -> None:
        """Send a heartbeat comment to all clients to keep connections alive."""
        heartbeat_message = f": heartbeat {datetime.utcnow().isoformat()}\n\n"
        
        with self._lock:
            for client_id, client_queue in list(self._clients.items()):
                try:
                    client_queue.put_nowait(heartbeat_message)
                except queue.Full:
                    pass  # Skip heartbeat for slow clients


# Global broadcaster instance
_broadcaster: Optional[SSEBroadcaster] = None
_broadcaster_lock = threading.Lock()


def get_broadcaster() -> SSEBroadcaster:
    """Get or create the global SSE broadcaster instance."""
    global _broadcaster
    
    with _broadcaster_lock:
        if _broadcaster is None:
            _broadcaster = SSEBroadcaster(max_events_per_second=10)
            
            # Start heartbeat thread
            def heartbeat_loop():
                while True:
                    time.sleep(30)
                    if _broadcaster:
                        _broadcaster.send_heartbeat()
            
            heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
            heartbeat_thread.start()
        
        return _broadcaster


def broadcast_event(event_type: str, payload: dict) -> bool:
    """
    Convenience function to broadcast an event.
    
    Args:
        event_type: One of 'device_status', 'alert_created', 'latency_spike', 'interface_threshold'
        payload: Event-specific data
        
    Returns:
        True if broadcast was successful
        
    Example:
        broadcast_event('device_status', {
            'device_ip': '192.168.1.1',
            'old_status': 'up',
            'new_status': 'down',
            'device_name': 'Core Switch'
        })
    """
    return get_broadcaster().broadcast(event_type, payload)
