from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# Initialize extensions without app
db = SQLAlchemy()
bcrypt = Bcrypt()

# Global Event Manager
from events.event_manager import EventManager
event_manager = EventManager()