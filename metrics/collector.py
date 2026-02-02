from collections import deque, defaultdict
from typing import List, Dict, Optional
from datetime import datetime
from .normalizer import Metric

class MetricCollector:
    """
    Collects and stores metrics in memory.
    Designed to be lightweight and fast.
    """
    def __init__(self, max_history: int = 100):
        # Storage format: {device_ip: {metric_name: deque([Metric, ...])}}
        self._storage: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=max_history)))
        self._max_history = max_history

    def add_metric(self, metric: Metric):
        """
        Add a single metric to the collector.
        """
        self._storage[metric.device_ip][metric.name].append(metric)

    def add_metrics(self, metrics: List[Metric]):
        """
        Add multiple metrics to the collector.
        """
        for metric in metrics:
            self.add_metric(metric)

    def get_metrics(self, device_ip: str, metric_name: Optional[str] = None) -> List[Metric]:
        """
        Retrieve metrics for a device.
        
        Args:
            device_ip: Target device IP
            metric_name: Optional specific metric name to filter by
            
        Returns:
            List of Metric objects
        """
        if device_ip not in self._storage:
            return []
            
        if metric_name:
            if metric_name in self._storage[device_ip]:
                return list(self._storage[device_ip][metric_name])
            return []
        
        # Return all metrics for the device
        all_metrics = []
        for name in self._storage[device_ip]:
            all_metrics.extend(self._storage[device_ip][name])
        
        # Sort by timestamp
        return sorted(all_metrics, key=lambda m: m.timestamp)

    def get_latest(self, device_ip: str, metric_name: str) -> Optional[Metric]:
        """
        Get the most recent value for a specific metric.
        """
        if device_ip in self._storage and metric_name in self._storage[device_ip]:
            dq = self._storage[device_ip][metric_name]
            if dq:
                return dq[-1]
        return None

    def clear_device(self, device_ip: str):
        """
        Clear metrics for a device (e.g., if removed).
        """
        if device_ip in self._storage:
            del self._storage[device_ip]
