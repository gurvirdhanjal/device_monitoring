# Change the import to get the existing 'app' instance
from app import app, db 
from models.user import User
from extensions import bcrypt

# Do NOT call create_app() again. Use the imported 'app'.

with app.app_context():
    # Find the admin user
    user = User.query.filter_by(username='admin').first()
    
    if user:
        # Force set the new password
        hashed_password = bcrypt.generate_password_hash("admin123").decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        print("Success! Password reset to: admin123")
    else:
        print("Error: User 'admin' not found in database.")