from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from services.discovery import get_discovery_service
from models.scan_history import NetworkScan
from extensions import db
from datetime import datetime
import socket
import ipaddress
import psutil

# ===============================
# CONFIG (SAFETY FIRST)
# ===============================

MAX_HOSTS_PER_SCAN = 4096      # prevents system freeze
ALLOW_PUBLIC_NETWORKS = False # LAN only
PING_TIMEOUT = 2

# ===============================
# BLUEPRINT SETUP
# ===============================

scanning_bp = Blueprint('scanning_bp', __name__, url_prefix='')

# ===============================
# NETWORK DETECTION
# ===============================

# Function detect_local_network_cidr removed (replaced by service.scanner.get_local_ip_range)

def validate_network(cidr):
    if not cidr:
        return False, "No network CIDR provided"
    
    try:
        net = ipaddress.IPv4Network(cidr, strict=False)
    except Exception as e:
        return False, f"Invalid CIDR format: {str(e)}"

    if net.num_addresses > MAX_HOSTS_PER_SCAN:
        return False, f"Network too large ({net.num_addresses} hosts)"

    if not ALLOW_PUBLIC_NETWORKS and not net.is_private:
        return False, "Public networks not allowed"

    return True, net


# ===============================
# ROUTES
# ===============================

@scanning_bp.route('/scanner')
def scanner_page():
    if 'logged_in' not in session:
        return redirect(url_for('auth_bp.login'))
    return render_template('scanning.html')

@scanning_bp.route('/api/get_local_ip_range')
def get_local_ip_range():
    try:
        service = get_discovery_service()
        network = service.scanner.get_local_ip_range()
        return jsonify({'ip_range': network})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scanning_bp.route('/api/scan_network', methods=['POST'])
def scan_network():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    ip_range = data.get('ip_range')
    
    # If no IP range provided, try to detect automatically
    if not ip_range:
        try:
            service = get_discovery_service()
            ip_range = service.scanner.get_local_ip_range()
        except Exception:
             return jsonify({'error': 'Unable to detect network. Please enter IP range manually.'}), 400

    ok, result = validate_network(ip_range)
    if not ok:
        return jsonify({'error': result}), 400

    username = session.get('username', 'system')
    
    try:
        service = get_discovery_service()
        scan_id = service.start_scan(str(result), username)
        return jsonify({'scan_id': scan_id, 'status': 'started'}), 202
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scanning_bp.route('/api/scan_progress/<scan_id>')
def scan_progress(scan_id):
    service = get_discovery_service()
    status = service.get_scan_status(scan_id)
    
    if not status:
        return jsonify({'error': 'Scan not found'}), 404
        
    # If scan completed, save to DB (idempotency needed or move to service callback)
    # Ideally, the service should handle persistence, but for now we keep it here or just log it
    # We can check if it's the *first* time we see it completed if needed, but the current UI polls until complete
    
    if status['status'] == 'completed':
         # Optional: Trigger DB save here if not done yet
         # For simplicity, we'll let the "save_scan_to_db" be handled if we move it to service or invoke here
         # But since 'get_scan_status' is a getter, it shouldn't have side effects ideally.
         # The previous implementation saved at end of thread. 
         # We will rely on the service buffer for results.
         pass

    return jsonify(status)

@scanning_bp.route('/api/active_scan')
def active_scan():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    username = session.get('username', 'system')
    service = get_discovery_service()
    scan_id = service.get_active_scan_id(username)
    
    if scan_id:
        # Get current progress immediately
        status = service.get_scan_status(scan_id)
        # Also return all accumulated devices so we can repopulate the table!
        devices = service.get_scan_results(scan_id)
        
        return jsonify({
            'scan_id': scan_id,
            'status': status['status'],
            'progress': status['progress'],
            'scanned_hosts': status['scanned_hosts'],
            'total_hosts': status['total_hosts'],
            'devices': devices # Send ALL devices to restore table
        })
    
    return jsonify({'scan_id': None})

@scanning_bp.route('/api/stop_scan/<scan_id>', methods=['POST'])
def stop_scan(scan_id):
    service = get_discovery_service()
    if service.stop_scan(scan_id):
        return jsonify({'status': 'stopped'})
    return jsonify({'error': 'Scan not found'}), 404

@scanning_bp.route('/api/ping_device', methods=['POST'])
def ping_device():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    ip = request.get_json().get('ip_address')
    if not ip:
        return jsonify({'error': 'IP required'}), 400

    import asyncio
    service = get_discovery_service()
    
    # We need to run async ping since we are in a sync route
    # Ideally, we should have an async route or use the service's executor if exposed
    # For now, creating a loop is safe enough for low volume
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        status, latency = loop.run_until_complete(
            service.scanner.ping_device(ip, timeout=PING_TIMEOUT)
        )
        
        # Return format expected by JavaScript
        if status == 'Online':
            return jsonify({
                'success': True,
                'latency': latency,
                'ttl': 64,  # Standard TTL value
                'ip_address': ip
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Host is offline or unreachable'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })
    finally:
        loop.close()

@scanning_bp.route('/api/scan_ports', methods=['POST'])
def scan_ports():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    ip_address = data.get('ip_address')
    
    if not ip_address:
        return jsonify({'error': 'IP address required'}), 400

    import asyncio
    service = get_discovery_service()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Re-use scanner from service
        open_ports = loop.run_until_complete(service.scanner.scan_ports(ip_address))
        return jsonify({
            'ip_address': ip_address,
            'open_ports': open_ports
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        loop.close()

@scanning_bp.route('/api/add_to_inventory', methods=['POST'])
def add_to_inventory():
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from models.device import Device
        
        data = request.get_json()
        ip_address = data.get('ip_address', '').strip()
        hostname = data.get('hostname', 'Unknown').strip()
        mac_address = data.get('mac_address', 'N/A').strip()
        
        if not ip_address:
            return jsonify({'success': False, 'message': 'IP address required'}), 400
        
        # Check if exists
        existing = Device.query.filter_by(device_ip=ip_address).first()
        if existing:
            return jsonify({
                'success': False,
                'message': f'Device {ip_address} already exists in inventory'
            }), 400
        
        # Create device
        device = Device(
            device_name=hostname or f"Device-{ip_address}",
            device_ip=ip_address,
            device_type='Network Device',
            macaddress=mac_address or 'N/A',
            hostname=hostname or 'Unknown',
            manufacturer='Unknown',
            is_monitored=True,
            is_active=True
        )
        
        db.session.add(device)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Device added successfully',
            'device': {
                'device_id': device.device_id,
                'device_ip': ip_address,
                'device_name': hostname,
                'macaddress': mac_address
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

