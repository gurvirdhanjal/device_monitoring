from extensions import db
from datetime import datetime

class SSHProfile(db.Model):
    __tablename__ = 'ssh_profiles'
    
    profile_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True) # e.g. "Main TACACS", "Local Admin"
    
    # Credentials
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=True) # Should be encrypted in production
    key_path = db.Column(db.String(255), nullable=True) # If using SSH keys
    
    # Metadata
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SSHProfile {self.name}>'
    
    def to_dict(self):
        return {
            'profile_id': self.profile_id,
            'name': self.name,
            'username': self.username,
            'has_password': bool(self.password),
            'has_key': bool(self.key_path),
            'description': self.description
        }
