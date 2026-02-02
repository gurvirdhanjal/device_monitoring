import asyncio
from datetime import datetime, timedelta
from extensions import db
from services.network_scanner import NetworkScanner
import statistics

class DeviceMonitor:
    def __init__(self):
        self.scanner = NetworkScanner()
        
        # Initialize Metrics Collector
        from metrics.collector import MetricCollector
        self.collector = MetricCollector()
        
        # Initialize Event System
        from extensions import event_manager
        from thresholds.evaluator import ThresholdEvaluator
        from thresholds.rules import ThresholdRule, ThresholdOperator
        
        # Define Default Rules
        # 1. High Latency Rule (> 100ms warning, > 200ms critical)
        latency_rule = ThresholdRule(
            metric_name="network_latency_ms",
            operator=ThresholdOperator.GT,
            warning_threshold=100.0,
            critical_threshold=200.0,
            samples_required=1  # Fast reaction for demo
        )
        
        # 2. Availability Rule (Normal=1, Offline=0)
        # We want to alert if it is 0. So < 1 is bad.
        availability_rule = ThresholdRule(
            metric_name="device_availability",
            operator=ThresholdOperator.LT,
            warning_threshold=None,
            critical_threshold=0.5, # < 0.5 means 0 (Offline)
            samples_required=1
        )
        
        self.evaluator = ThresholdEvaluator(rules=[latency_rule, availability_rule])
        self.event_manager = event_manager

    def hydrate_collector(self, app):
        """
        Public method to hydrate collector with DB history.
        Must be called with app context.
        """
        print("Hydrating MetricCollector from database...")
        with app.app_context():
            try:
                from models.device import Device
                from models.scan_history import DeviceScanHistory
                from metrics.normalizer import MetricNormalizer
                
                # Get all monitored devices
                devices = Device.query.filter_by(is_monitored=True).all()
                total_loaded = 0
                
                for device in devices:
                    # Get last 50 scans for this device
                    scans = DeviceScanHistory.query.filter_by(device_ip=device.device_ip)\
                        .order_by(DeviceScanHistory.scan_timestamp.desc())\
                        .limit(50).all()
                    
                    # Add to collector (reverse to keep chronological order in deque)
                    for scan in reversed(scans):
                        metrics = MetricNormalizer.normalize_ping(
                            scan.device_ip, 
                            scan.status, 
                            scan.ping_time_ms,
                            scan.scan_timestamp # Use timestamp from DB
                        )
                        self.collector.add_metrics(metrics)
                        total_loaded += 1
                        
                print(f"Hydration complete. Loaded {total_loaded} metrics.")
                
            except Exception as e:
                print(f"Error hydrating collector: {e}")
    
    async def monitor_stored_devices(self):
        """Monitor all stored devices and save results"""
        from models.device import Device
        from models.scan_history import DeviceScanHistory
        from metrics.normalizer import MetricNormalizer
        
        devices = Device.query.filter_by(is_monitored=True).all()
        
        print(f"Monitoring {len(devices)} stored devices...")
        
        scan_results = []
        
        for device in devices:
            status, latency = await self.scanner.ping_device(device.device_ip)
            
            # Save scan history
            scan_record = DeviceScanHistory(
                device_ip=device.device_ip,
                device_name=device.device_name,
                ping_time_ms=latency,
                status=status,
                scan_type='scheduled'
            )
            
            # Normalize and collect metrics
            metrics = MetricNormalizer.normalize_ping(device.device_ip, status, latency)
            self.collector.add_metrics(metrics)
            
            # Evaluate Thresholds & Generate Events
            for metric in metrics:
                transition = self.evaluator.evaluate(metric)
                if transition:
                    print(f"EVENT GENERATED: {transition}")
                    self.event_manager.add_transition(transition)

            db.session.add(scan_record)
            scan_results.append({
                'device_name': device.device_name,
                'device_ip': device.device_ip,
                'status': status,
                'latency': latency,
                'timestamp': datetime.utcnow()
            })
        
        db.session.commit()
        return scan_results
    
    def get_device_statistics(self, device_ip, hours=24):
        """Get statistics for a device over specified hours"""
        from models.scan_history import DeviceScanHistory
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        scans = DeviceScanHistory.query.filter(
            DeviceScanHistory.device_ip == device_ip,
            DeviceScanHistory.scan_timestamp >= cutoff_time
        ).order_by(DeviceScanHistory.scan_timestamp).all()
        
        if not scans:
            return None
        
        online_scans = [scan for scan in scans if scan.status == 'Online']
        offline_scans = [scan for scan in scans if scan.status == 'Offline']
        
        latencies = [scan.ping_time_ms for scan in online_scans if scan.ping_time_ms is not None]
        
        stats = {
            'total_scans': len(scans),
            'online_count': len(online_scans),
            'offline_count': len(offline_scans),
            'uptime_percentage': (len(online_scans) / len(scans)) * 100 if scans else 0,
            'downtime_percentage': (len(offline_scans) / len(scans)) * 100 if scans else 0,
        }
        
        if latencies:
            stats.update({
                'avg_latency': statistics.mean(latencies),
                'min_latency': min(latencies),
                'max_latency': max(latencies),
                'latency_std_dev': statistics.stdev(latencies) if len(latencies) > 1 else 0
            })
        
        return stats
    
    def get_daily_report(self, date=None):
        """Generate daily report for all monitored devices"""
        from models.device import Device
        from models.scan_history import DeviceScanHistory
        
        if date is None:
            date = datetime.utcnow().date()
        
        start_time = datetime.combine(date, datetime.min.time())
        end_time = datetime.combine(date, datetime.max.time())
        
        devices = Device.query.filter_by(is_monitored=True).all()
        report = {
            'date': date,
            'total_monitored_devices': len(devices),
            'devices': []
        }
        
        for device in devices:
            daily_scans = DeviceScanHistory.query.filter(
                DeviceScanHistory.device_ip == device.device_ip,
                DeviceScanHistory.scan_timestamp.between(start_time, end_time)
            ).all()
            
            if daily_scans:
                stats = self.get_device_statistics(device.device_ip, 24)
                if stats:
                    report['devices'].append({
                        'device_name': device.device_name,
                        'device_ip': device.device_ip,
                        'stats': stats
                    })
        
        return report