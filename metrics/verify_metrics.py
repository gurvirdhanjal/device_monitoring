import unittest
from datetime import datetime
from metrics.normalizer import MetricNormalizer, Metric, DEVICE_AVAILABILITY, NETWORK_LATENCY_MS, OPEN_PORTS_COUNT
from metrics.collector import MetricCollector

class TestMetricLayer(unittest.TestCase):
    def test_normalizer_online(self):
        metrics = MetricNormalizer.normalize_ping("192.168.1.10", "Online", 15.5)
        self.assertEqual(len(metrics), 2)
        
        avail = next(m for m in metrics if m.name == DEVICE_AVAILABILITY)
        self.assertEqual(avail.value, 1)
        self.assertEqual(avail.device_ip, "192.168.1.10")
        
        latency = next(m for m in metrics if m.name == NETWORK_LATENCY_MS)
        self.assertEqual(latency.value, 15.5)
        self.assertEqual(latency.unit, "ms")

    def test_normalizer_offline(self):
        metrics = MetricNormalizer.normalize_ping("192.168.1.11", "Offline", None)
        self.assertEqual(len(metrics), 1)
        
        avail = metrics[0]
        self.assertEqual(avail.name, DEVICE_AVAILABILITY)
        self.assertEqual(avail.value, 0)

    def test_collector_storage(self):
        collector = MetricCollector(max_history=5)
        # Add 6 metrics
        for i in range(6):
            m = Metric(name="test_metric", value=i, unit="count", device_ip="1.1.1.1")
            collector.add_metric(m)
            
        metrics = collector.get_metrics("1.1.1.1", "test_metric")
        self.assertEqual(len(metrics), 5) # Should cap at 5
        self.assertEqual(metrics[-1].value, 5) # Last one should be 5
        self.assertEqual(metrics[0].value, 1)  # First one should be 1 (0 was dropped)

    def test_collector_retrieval(self):
        collector = MetricCollector()
        m1 = Metric(name=DEVICE_AVAILABILITY, value=1, unit="bool", device_ip="2.2.2.2")
        m2 = Metric(name=NETWORK_LATENCY_MS, value=20.0, unit="ms", device_ip="2.2.2.2")
        collector.add_metrics([m1, m2])
        
        all_metrics = collector.get_metrics("2.2.2.2")
        self.assertEqual(len(all_metrics), 2)
        
        lat_metric = collector.get_latest("2.2.2.2", NETWORK_LATENCY_MS)
        self.assertEqual(lat_metric.value, 20.0)

if __name__ == '__main__':
    unittest.main()
