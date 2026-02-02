import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///device_monitoring.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=5)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Monitoring Settings
    MONITORING_INTERVAL = 300  # 5 minutes in seconds
    SCAN_SAMPLES_PER_HOUR = 12  # 12 samples per hour (every 5 minutes)
    
    # Email Settings
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'trackoffice247@gmail.com')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'seha sjlc kzqf uwnf')
    
    # API Settings
    API_KEY = os.environ.get('API_KEY', '8f42v73054r1749f8g58848be5e6502c')