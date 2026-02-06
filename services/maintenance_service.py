"""
Database Maintenance Service for Network Monitoring System.
Handles data retention, cleanup, and daily aggregation rollups.
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
from sqlalchemy import func, and_
from extensions import db


class MaintenanceService:
    """
    Service for database maintenance tasks:
    - Cleanup old scan history
    - Aggregate daily statistics
    - Cleanup old interface metrics
    - Cleanup old events
    """
    
    def __init__(self):
        # Retention periods (days)
        self.scan_history_retention_days = 7
        self.interface_metrics_retention_days = 3
        self.events_retention_days = 30
        self.daily_stats_retention_days = 365
    
    def cleanup_old_scan_history(self, days: int = None) -> Dict:
        """
        Delete scan history older than specified days.
        
        Args:
            days: Retention period (default: 7 days)
            
        Returns:
            Dict with deletion count and status
        """
        days = days or self.scan_history_retention_days
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        try:
            from models.scan_history import DeviceScanHistory
            
            # Count before delete
            count = DeviceScanHistory.query.filter(
                DeviceScanHistory.scan_timestamp < cutoff
            ).count()
            
            if count > 0:
                DeviceScanHistory.query.filter(
                    DeviceScanHistory.scan_timestamp < cutoff
                ).delete()
                db.session.commit()
            
            return {
                'success': True,
                'deleted_count': count,
                'cutoff_date': cutoff.isoformat(),
                'retention_days': days
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_old_interface_metrics(self, days: int = None) -> Dict:
        """Delete interface metrics older than specified days."""
        days = days or self.interface_metrics_retention_days
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        try:
            from models.interfaces import InterfaceTrafficHistory
            
            count = InterfaceTrafficHistory.query.filter(
                InterfaceTrafficHistory.timestamp < cutoff
            ).count()
            
            if count > 0:
                InterfaceTrafficHistory.query.filter(
                    InterfaceTrafficHistory.timestamp < cutoff
                ).delete()
                db.session.commit()
            
            return {
                'success': True,
                'deleted_count': count,
                'cutoff_date': cutoff.isoformat(),
                'retention_days': days
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def cleanup_old_events(self, days: int = None) -> Dict:
        """Delete resolved events older than specified days."""
        days = days or self.events_retention_days
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        try:
            from models.dashboard import DashboardEvent
            
            count = DashboardEvent.query.filter(
                and_(
                    DashboardEvent.timestamp < cutoff,
                    DashboardEvent.resolved == True
                )
            ).count()
            
            if count > 0:
                DashboardEvent.query.filter(
                    and_(
                        DashboardEvent.timestamp < cutoff,
                        DashboardEvent.resolved == True
                    )
                ).delete()
                db.session.commit()
            
            return {
                'success': True,
                'deleted_count': count,
                'cutoff_date': cutoff.isoformat(),
                'retention_days': days
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def aggregate_daily_stats(self, target_date: date = None) -> Dict:
        """
        Aggregate scan history into daily statistics.
        Should be run once per day for the previous day.
        
        Args:
            target_date: Date to aggregate (default: yesterday)
            
        Returns:
            Dict with aggregation results
        """
        target_date = target_date or (datetime.utcnow().date() - timedelta(days=1))
        
        try:
            from models.device import Device
            from models.scan_history import DeviceScanHistory
            from models.dashboard import DailyDeviceStats, DashboardEvent
            
            # Get all devices for aggregation (User requested full visibility)
            devices = Device.query.all()
            
            start_dt = datetime.combine(target_date, datetime.min.time())
            end_dt = datetime.combine(target_date, datetime.max.time())
            
            aggregated = 0
            
            for device in devices:
                # Check if stats already exist for this date
                existing = DailyDeviceStats.query.filter_by(
                    device_id=device.device_id,
                    date=target_date
                ).first()
                
                if existing:
                    continue  # Skip if already aggregated
                
                # Get scans for this device on target date
                scans = DeviceScanHistory.query.filter(
                    and_(
                        DeviceScanHistory.device_ip == device.device_ip,
                        DeviceScanHistory.scan_timestamp >= start_dt,
                        DeviceScanHistory.scan_timestamp <= end_dt
                    )
                ).all()
                
                if not scans:
                    continue
                
                # Calculate aggregates
                total_scans = len(scans)
                online_scans = len([s for s in scans if s.status == 'Online'])
                uptime_percent = (online_scans / total_scans) * 100 if total_scans > 0 else 0
                
                latencies = [s.ping_time_ms for s in scans if s.ping_time_ms is not None]
                packet_losses = [s.packet_loss for s in scans if s.packet_loss is not None]
                
                avg_latency = sum(latencies) / len(latencies) if latencies else None
                max_latency = max(latencies) if latencies else None
                min_latency = min(latencies) if latencies else None
                avg_packet_loss = sum(packet_losses) / len(packet_losses) if packet_losses else 0
                
                # Count alerts for this device
                alert_count = DashboardEvent.query.filter(
                    and_(
                        DashboardEvent.device_id == device.device_id,
                        DashboardEvent.timestamp >= start_dt,
                        DashboardEvent.timestamp <= end_dt
                    )
                ).count()
                
                # Create daily stats record
                daily_stat = DailyDeviceStats(
                    device_id=device.device_id,
                    date=target_date,
                    uptime_percent=round(uptime_percent, 2),
                    avg_latency_ms=round(avg_latency, 2) if avg_latency else None,
                    max_latency_ms=round(max_latency, 2) if max_latency else None,
                    min_latency_ms=round(min_latency, 2) if min_latency else None,
                    avg_packet_loss_pct=round(avg_packet_loss, 2),
                    total_scans=total_scans,
                    online_scans=online_scans,
                    total_alerts=alert_count
                )
                
                db.session.add(daily_stat)
                aggregated += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'target_date': target_date.isoformat(),
                'devices_aggregated': aggregated,
                'total_devices': len(devices)
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def run_all_maintenance(self) -> Dict:
        """
        Run all maintenance tasks.
        Suitable for a daily cron job.
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'tasks': {}
        }
        
        # 1. Aggregate yesterday's stats (before cleanup)
        results['tasks']['aggregate_daily'] = self.aggregate_daily_stats()
        
        # 2. Cleanup old scan history
        results['tasks']['cleanup_scans'] = self.cleanup_old_scan_history()
        
        # 3. Cleanup old interface metrics
        results['tasks']['cleanup_metrics'] = self.cleanup_old_interface_metrics()
        
        # 4. Cleanup old resolved events
        results['tasks']['cleanup_events'] = self.cleanup_old_events()
        
        # Summary
        all_success = all(
            task.get('success', False) 
            for task in results['tasks'].values()
        )
        results['overall_success'] = all_success
        
        return results


# Singleton instance
maintenance_service = MaintenanceService()
