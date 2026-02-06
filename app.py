import os
import threading
import webbrowser
from datetime import timedelta

from flask import Flask
from sqlalchemy.exc import IntegrityError

from config import Config
from extensions import db, bcrypt


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # ---------------------------
    # Session configuration
    # ---------------------------
    app.config.update(
        SECRET_KEY=os.environ.get(
            'SECRET_KEY',
            'change-this-secret-key-in-production'
        ),
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=5),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=False,   # True only if HTTPS
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_REFRESH_EACH_REQUEST=True,
        SESSION_PERMANENT=False
    )

    # ---------------------------
    # Initialize extensions
    # ---------------------------
    db.init_app(app)
    bcrypt.init_app(app)

    # ---------------------------
    # SQLite Performance Tuning (WAL Mode + Busy Timeout)
    # ---------------------------
    from sqlalchemy import event
    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if app.config['SQLALCHEMY_DATABASE_URI'].startswith("sqlite"):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=30000") # 30s timeout
                cursor.close()

    # ---------------------------
    # Database setup
    # ---------------------------
    with app.app_context():
        from models import (
            User, Device, DashboardEvent, DailyDeviceStats, 
            DeviceInterface, InterfaceTrafficHistory, DeviceSnmpConfig,
            SSHProfile, SwitchTopology, TrackedDevice,
            DeviceScanHistory, NetworkScan, PortScanResult
        )

        db.create_all()

        # ---------------------------
        # Safe admin creation
        # ---------------------------
        admin_email = "admin@trackoffice.com"

        existing_admin = User.query.filter_by(email=admin_email).first()

        if not existing_admin:
            try:
                admin_user = User(
                    username="admin",
                    email=admin_email,
                    role="admin",
                    password=bcrypt
                    .generate_password_hash("admin123")
                    .decode("utf-8"),
                    is_active=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print("[OK] Default admin user created.")
            except IntegrityError:
                db.session.rollback()
                print("[WARN] Admin user already exists. Skipping creation.")

    # ---------------------------
    # Register blueprints
    # ---------------------------
    from routes.auth import auth_bp
    from routes.devices import devices_bp
    from routes.monitoring import monitoring_bp
    from routes.scanning import scanning_bp
    from routes.reports import reports_bp
    from routes.user_management import user_management_bp
    from routes.tracking import tracking_bp
    from routes.camera_streaming import camera_bp
    from routes.file_transfer import file_transfer_bp
    from routes.dashboard import dashboard_bp
    from routes.snmp import snmp_bp
    from routes.service_checks import service_checks_bp
    from routes.maintenance import maintenance_bp
    from routes.sse import sse_bp
    from routes.switch_discovery import switch_discovery_bp

    from middleware.session_middleware import setup_auth_middleware

    protected_blueprints = [
        devices_bp,
        monitoring_bp,
        scanning_bp,
        reports_bp,
        user_management_bp,
        tracking_bp,
        camera_bp,
        file_transfer_bp,
        dashboard_bp,
        snmp_bp,
        service_checks_bp,
        maintenance_bp,
        sse_bp,
        switch_discovery_bp,
    ]

    for bp in protected_blueprints:
        setup_auth_middleware(bp)

    app.register_blueprint(auth_bp)
    for bp in protected_blueprints:
        app.register_blueprint(bp)

    return app


# ---------------------------
# Scheduler setup
# ---------------------------
from services.scheduler import MonitoringScheduler


def open_browser():
    webbrowser.open_new("http://localhost:5001")


# ---------------------------
# Main entry point
# ---------------------------
if __name__ == "__main__":
    try:
        app = create_app()
        scheduler = MonitoringScheduler(app)
        from services.interface_poller import interface_poller
        
        print("Starting Device Monitoring System...")
        print("Access URL: http://localhost:5001")
        print("Default admin: admin / admin123")

        scheduler.start_scheduled_monitoring()
        interface_poller.start_polling(app)

        threading.Timer(2.0, open_browser).start()

        # Hydrate collector with DB history
        from routes.monitoring import monitor
        monitor.hydrate_collector(app)

        app.run(
            host="0.0.0.0",
            port=5001,
            debug=False,          # ❗ NEVER TRUE IN EXE
            use_reloader=False
        )

    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Startup error: {e}")
    finally:
        if 'scheduler' in locals():
            scheduler.stop_scheduled_monitoring()
            print("Scheduler stopped.")
        if 'interface_poller' in locals():
            interface_poller.stop_polling()
