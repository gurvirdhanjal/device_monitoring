import unittest
from datetime import datetime, timedelta
from events.event_manager import EventManager
from events.event_model import Event, EventSeverity

class TestEventManager(unittest.TestCase):

    def setUp(self):
        self.manager = EventManager(max_history=10)

    def test_add_transition_valid_ok(self):
        transition = {
            "device_ip": "192.168.1.10",
            "metric_name": "cpu_load",
            "old_state": "WARNING",
            "new_state": "OK",
            "value": 15.5,
            "timestamp": datetime.utcnow().isoformat()
        }
        event = self.manager.add_transition(transition)
        
        self.assertIsInstance(event, Event)
        self.assertEqual(event.severity, EventSeverity.OK)
        self.assertEqual(event.metric_name, "cpu_load")
        self.assertEqual(event.device_ip, "192.168.1.10")
        self.assertEqual(event.value, 15.5)
        self.assertTrue("cpu_load entered OK state" in event.message)

    def test_add_transition_valid_critical(self):
        transition = {
            "device_ip": "192.168.1.11",
            "metric_name": "network_latency_ms",
            "old_state": "OK",
            "new_state": "CRITICAL",
            "value": 250.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        event = self.manager.add_transition(transition)
        
        self.assertEqual(event.severity, EventSeverity.CRITICAL)
        self.assertEqual(event.value, 250.0)
        self.assertTrue("network_latency_ms entered CRITICAL state" in event.message)

    def test_invalid_transition_missing_keys(self):
        transition = {
            "device_ip": "192.168.1.12",
            # Missing metric_name
            "new_state": "WARNING",
            "value": 85.0
        }
        with self.assertRaises(ValueError):
            self.manager.add_transition(transition)

    def test_invalid_severity(self):
        transition = {
            "device_ip": "192.168.1.13",
            "metric_name": "memory_usage",
            "old_state": "OK",
            "new_state": "UNKNOWN_STATE", # Invalid
            "value": 99.9,
            "timestamp": datetime.utcnow().isoformat()
        }
        with self.assertRaises(ValueError):
            self.manager.add_transition(transition)

    def test_get_recent_events_limit_and_ordering(self):
        # Add 3 events with distinct timestamps
        # 1. Oldest
        t1 = datetime.utcnow() - timedelta(minutes=10)
        self.manager.add_transition({
            "device_ip": "10.0.0.1",
            "metric_name": "m1",
            "new_state": "WARNING",
            "value": 1.0,
            "timestamp": t1.isoformat()
        })
        
        # 2. Newest
        t3 = datetime.utcnow()
        self.manager.add_transition({
            "device_ip": "10.0.0.1",
            "metric_name": "m3",
            "new_state": "CRITICAL",
            "value": 3.0,
            "timestamp": t3.isoformat()
        })
        
        # 3. Middle
        t2 = datetime.utcnow() - timedelta(minutes=5)
        self.manager.add_transition({
            "device_ip": "10.0.0.1",
            "metric_name": "m2",
            "new_state": "OK",
            "value": 2.0,
            "timestamp": t2.isoformat()
        })
        
        # Fetch recent 2
        events = self.manager.get_recent_events(limit=2)
        
        self.assertEqual(len(events), 2)
        # Should be sorted DESC: Newest first
        self.assertEqual(events[0].metric_name, "m3")
        self.assertEqual(events[1].metric_name, "m2")

    def test_max_history_limit(self):
        # Max history is set to 10 in setUp
        base_time = datetime.utcnow()
        for i in range(15):
            self.manager.add_transition({
                "device_ip": "10.0.0.1",
                "metric_name": f"m{i}",
                "new_state": "OK",
                "value": float(i),
                "timestamp": (base_time + timedelta(seconds=i)).isoformat()
            })
            
        events = self.manager.get_recent_events(limit=20)
        self.assertEqual(len(events), 10)
        # Should only have m5 to m14 (latest 10)
        # Since get_recent_events sorts DESC, first event should be m14 (latest timestamp)
        self.assertEqual(events[0].metric_name, "m14")

if __name__ == '__main__':
    unittest.main()
