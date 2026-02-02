import schedule
import time
import threading
from datetime import datetime
from services.device_monitor import DeviceMonitor
import asyncio

class MonitoringScheduler:
    def __init__(self, app):
        self.app = app
        self.monitor = DeviceMonitor()
        self.is_running = False
        self.scheduler_thread = None
    
    def start_scheduled_monitoring(self):
        """Start the scheduled monitoring tasks"""
        # Monitor every 5 minutes
        schedule.every(5).minutes.do(self.run_monitoring_task)
        
        # Daily report at 23:59
        schedule.every().day.at("23:59").do(self.generate_daily_report)
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self.run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        # Run immediate scan in background so UI has data
        threading.Thread(target=self.run_monitoring_task).start()
        
        print("Scheduled monitoring started (initial scan triggered)...")
    
    def stop_scheduled_monitoring(self):
        """Stop the scheduled monitoring"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("Scheduled monitoring stopped.")
    
    def run_scheduler(self):
        """Run the scheduler loop"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def run_monitoring_task(self):
        """Run monitoring task within application context"""
        with self.app.app_context():
            try:
                asyncio.run(self.monitor.monitor_stored_devices())
                print(f"Scheduled monitoring completed at {datetime.now()}")
            except Exception as e:
                print(f"Error in scheduled monitoring: {e}")
    
    def generate_daily_report(self):
        """Generate daily report"""
        with self.app.app_context():
            try:
                report = self.monitor.get_daily_report()
                print(f"Daily report generated for {report['date']}")
                # Here you can add email sending or other reporting mechanisms
            except Exception as e:
                print(f"Error generating daily report: {e}")