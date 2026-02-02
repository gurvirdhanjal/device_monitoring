from extensions import db
from datetime import datetime

class Device(db.Model):
    device_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(100), nullable=False)
    device_ip = db.Column(db.String(50), nullable=False)
    port = db.Column(db.String(50), nullable=True)
    rstplink = db.Column(db.String(100), nullable=True)
    macaddress = db.Column(db.String(50), nullable=True)
    hostname = db.Column(db.String(100), nullable=True)
    manufacturer = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_monitored = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Device {self.device_name} ({self.device_ip})>'
    
    def to_dict(self):
        return {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'device_ip': self.device_ip,
            'port': self.port,
            'macaddress': self.macaddress,
            'hostname': self.hostname,
            'manufacturer': self.manufacturer,
            'is_monitored': self.is_monitored
        }