"""
Maintenance API routes for Network Monitoring System.
Provides endpoints to trigger and monitor database maintenance tasks.
"""
from flask import Blueprint, jsonify, request, session
from datetime import datetime, date

maintenance_bp = Blueprint('maintenance_bp', __name__, url_prefix='/api/maintenance')


# ============================================================
# POST /api/maintenance/cleanup
# ============================================================
@maintenance_bp.route('/cleanup', methods=['POST'])
def run_cleanup():
    """
    Run database cleanup tasks.
    Body (optional): { scan_days, metrics_days, events_days }
    """
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if user is admin (cleanup is admin-only)
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from services.maintenance_service import maintenance_service
        
        data = request.get_json() or {}
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'tasks': {}
        }
        
        # Cleanup scan history
        scan_days = data.get('scan_days', 7)
        results['tasks']['scan_history'] = maintenance_service.cleanup_old_scan_history(scan_days)
        
        # Cleanup interface metrics
        metrics_days = data.get('metrics_days', 3)
        results['tasks']['interface_metrics'] = maintenance_service.cleanup_old_interface_metrics(metrics_days)
        
        # Cleanup events
        events_days = data.get('events_days', 30)
        results['tasks']['events'] = maintenance_service.cleanup_old_events(events_days)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/maintenance/aggregate
# ============================================================
@maintenance_bp.route('/aggregate', methods=['POST'])
def run_aggregation():
    """
    Run daily stats aggregation.
    Body (optional): { date: "YYYY-MM-DD" }
    """
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from services.maintenance_service import maintenance_service
        
        data = request.get_json() or {}
        target_date = None
        
        if 'date' in data:
            target_date = date.fromisoformat(data['date'])
        
        result = maintenance_service.aggregate_daily_stats(target_date)
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/maintenance/run-all
# ============================================================
@maintenance_bp.route('/run-all', methods=['POST'])
def run_all_maintenance():
    """Run all maintenance tasks (aggregation + cleanup)."""
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from services.maintenance_service import maintenance_service
        
        result = maintenance_service.run_all_maintenance()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/maintenance/status
# ============================================================
@maintenance_bp.route('/status')
def get_maintenance_status():
    """
    Get database statistics for maintenance monitoring.
    Returns counts and oldest records for each table.
    """
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from models.scan_history import DeviceScanHistory
        from models.interfaces import InterfaceTrafficHistory
        from models.dashboard import DashboardEvent, DailyDeviceStats
        from sqlalchemy import func
        
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'tables': {}
        }
        
        # Scan history stats
        scan_count = DeviceScanHistory.query.count()
        oldest_scan = DeviceScanHistory.query.order_by(
            DeviceScanHistory.scan_timestamp
        ).first()
        
        status['tables']['scan_history'] = {
            'count': scan_count,
            'oldest_record': oldest_scan.scan_timestamp.isoformat() if oldest_scan and oldest_scan.scan_timestamp else None
        }
        
        # Interface metrics stats
        metrics_count = InterfaceTrafficHistory.query.count()
        oldest_metric = InterfaceTrafficHistory.query.order_by(
            InterfaceTrafficHistory.timestamp
        ).first()
        
        status['tables']['interface_metrics'] = {
            'count': metrics_count,
            'oldest_record': oldest_metric.timestamp.isoformat() if oldest_metric and oldest_metric.timestamp else None
        }
        
        # Events stats
        events_count = DashboardEvent.query.count()
        unresolved_count = DashboardEvent.query.filter_by(resolved=False).count()
        
        status['tables']['dashboard_events'] = {
            'count': events_count,
            'unresolved': unresolved_count
        }
        
        # Daily stats
        daily_count = DailyDeviceStats.query.count()
        latest_stat = DailyDeviceStats.query.order_by(
            DailyDeviceStats.date.desc()
        ).first()
        
        status['tables']['daily_device_stats'] = {
            'count': daily_count,
            'latest_date': latest_stat.date.isoformat() if latest_stat and latest_stat.date else None
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
