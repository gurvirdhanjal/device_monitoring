import uuid
from datetime import datetime
from extensions import db
from models.dashboard import DashboardEvent

class AlertManager:
    """
    Handles alert generation based on device metrics.
    Lifecycle:
    - Detects threshold breaches
    - Creates active alerts (DashboardEvent)
    - Auto-resolves alerts when metrics return to normal
    - Prevents duplicate alerts
    """
    
    # Thresholds
    LATENCY_THRESHOLD_MS = 100
    PACKET_LOSS_THRESHOLD_PCT = 5.0
    
    @staticmethod
    def check_device_metrics(device, latency_ms, packet_loss_pct):
        """
        Evaluate device metrics and trigger/resolve alerts.
        """
        # 1. Check Offline Status
        if not device.is_active: # Assuming 'is_active' or similar indicates Up/Down? 
             # Wait, device.is_active usually means "managed". 
             # We should rely on the scan result passed in, or device.status if it exists.
             # Actually, 'device_monitor.py' likely updates a status field.
             pass

    @classmethod
    def process_scan_result(cls, device, is_online, latency_ms, packet_loss_pct, commit=True):
        """
        Main entry point for processing scan results.
        """
        # --- 1. OFFLINE ALERT ---
        if not is_online:
            cls._trigger_alert(
                device, 
                event_type='STATUS', 
                severity='CRITICAL', 
                metric='status', 
                message=f"Device {device.device_name} ({device.device_ip}) is OFFLINE",
                value=0,
                commit=commit
            )
            return # Don't check latency if offline
        else:
            cls._resolve_alert(device, metric='status', commit=commit)

        # --- 2. HIGH LATENCY ALERT ---
        if latency_ms and latency_ms > cls.LATENCY_THRESHOLD_MS:
            cls._trigger_alert(
                device,
                event_type='performance',
                severity='WARNING',
                metric='latency',
                message=f"High Latency detected: {latency_ms}ms (Threshold: {cls.LATENCY_THRESHOLD_MS}ms)",
                value=latency_ms,
                commit=commit
            )
        else:
            cls._resolve_alert(device, metric='latency', commit=commit)

        # --- 3. PACKET LOSS ALERT ---
        if packet_loss_pct and packet_loss_pct > cls.PACKET_LOSS_THRESHOLD_PCT:
             cls._trigger_alert(
                device,
                event_type='performance',
                severity='CRITICAL', # High loss is usually critical
                metric='packet_loss',
                message=f"High Packet Loss detected: {packet_loss_pct}% (Threshold: {cls.PACKET_LOSS_THRESHOLD_PCT}%)",
                value=packet_loss_pct,
                commit=commit
            )
        else:
            cls._resolve_alert(device, metric='packet_loss', commit=commit)

    @classmethod
    def _trigger_alert(cls, device, event_type, severity, metric, message, value, commit=True):
        """
        Creates an alert if one doesn't already exist for this device+metric.
        """
        existing = DashboardEvent.query.filter_by(
            device_id=device.device_id,
            metric_name=metric,
            resolved=False
        ).first()

        if existing:
            # Update existing alert if severity changed or just to bump timestamp?
            # Usually we don't update timestamp unless we want "last seen". 
            # Let's just update the value.
            existing.value = value
            existing.message = message # Update message with latest value
            existing.timestamp = datetime.utcnow() # Bump timestamp to show it's still active
            if commit:
                db.session.commit()
        else:
            # Create new alert
            event = DashboardEvent(
                event_id=str(uuid.uuid4()),
                device_id=device.device_id,
                device_ip=device.device_ip,
                event_type=event_type,
                severity=severity,
                metric_name=metric,
                message=message,
                value=value,
                timestamp=datetime.utcnow(),
                resolved=False
            )
            db.session.add(event)
            if commit:
                db.session.commit()
            print(f"[ALERT] Triggered {severity} alert for {device.device_ip}: {metric}")
            
            # Phase 1C: Notifications
            if severity == 'CRITICAL':
                try:
                    from services.notification_service import NotificationService
                    NotificationService.send_critical_alert(device, metric, value, message)
                except Exception as e:
                    print(f"[ERROR] Failed to send notification: {e}")

    @classmethod
    def _resolve_alert(cls, device, metric, commit=True):
        """
        Resolves active alerts for this metric if they exist.
        """
        existing = DashboardEvent.query.filter_by(
            device_id=device.device_id,
            metric_name=metric,
            resolved=False
        ).first()

        if existing:
            existing.resolved = True
            existing.resolved_at = datetime.utcnow()
            existing.message += " [RESOLVED]"
            if commit:
                db.session.commit()
            print(f"[ALERT] Resolved alert for {device.device_ip}: {metric}")

# Singleton not needed, using class methods
