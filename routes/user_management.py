from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from extensions import db, bcrypt
from models.user import User

user_management_bp = Blueprint('user_management_bp', __name__, url_prefix='')

@user_management_bp.route('/user_management')
def user_management():
    if 'logged_in' not in session:
        return redirect(url_for('auth_bp.login'))
    
    # Check if user is admin
    if session.get('role') != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('monitoring_bp.dashboard'))
    
    users = User.query.all()
    user = None

    if 'edit_id' in request.args:
        user = User.query.get(request.args.get('edit_id'))

    if 'delete_id' in request.args:
        user = User.query.get(request.args.get('delete_id'))
        if user:
            # Prevent deleting own account
            if user.id == session.get('user_id'):
                flash('You cannot delete your own account.', 'danger')
            else:
                db.session.delete(user)
                db.session.commit()
                flash('User deleted successfully.', 'success')
        return redirect(url_for('user_management_bp.user_management'))

    return render_template('user_management.html', users=users, user=user)

@user_management_bp.route('/user_management/save', methods=['POST'])
def save_user():
    if 'logged_in' not in session:
        return redirect(url_for('auth_bp.login'))
    
    # Check if user is admin
    if session.get('role') != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('monitoring_bp.dashboard'))
    
    try:
        user_id = request.form.get('user_id')
        username = request.form['username']
        password = request.form.get('password', '')  # Make optional for updates
        role = request.form['role']
        email = request.form['email']
        phone_number = request.form.get('phone_number', '')

        # Check if username already exists (for new users or when changing username)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and (not user_id or existing_user.id != int(user_id)):
            flash('Username already exists!', 'danger')
            return redirect(url_for('user_management_bp.user_management'))

        # Check if email already exists (for new users or when changing email)
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and (not user_id or existing_email.id != int(user_id)):
            flash('Email already exists!', 'danger')
            return redirect(url_for('user_management_bp.user_management'))

        if user_id:
            # Update existing user
            user = User.query.get(user_id)
            user.username = username
            # Only update password if provided
            if password:
                user.password = bcrypt.generate_password_hash(password).decode('utf-8')
            user.role = role
            user.email = email
            user.phone_number = phone_number
            flash('User updated successfully.', 'success')
        else:
            # Create new user - password is required for new users
            if not password:
                flash('Password is required for new users.', 'danger')
                return redirect(url_for('user_management_bp.user_management'))
                
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(
                username=username, 
                password=hashed_password, 
                role=role, 
                email=email, 
                phone_number=phone_number
            )
            db.session.add(user)
            flash('User created successfully.', 'success')

        db.session.commit()
        return redirect(url_for('user_management_bp.user_management'))
    
    except Exception as e:
        flash(f'Error saving user: {str(e)}', 'danger')
        return redirect(url_for('user_management_bp.user_management'))

@user_management_bp.route('/api/users/<int:user_id>/toggle_status', methods=['POST'])
def toggle_user_status(user_id):
    if 'logged_in' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(user_id)
    if user:
        # Prevent deactivating own account
        if user.id == session.get('user_id'):
            return jsonify({'error': 'You cannot deactivate your own account'}), 400
        
        user.is_active = not user.is_active
        db.session.commit()
        return jsonify({'success': True, 'is_active': user.is_active})
    else:
        return jsonify({'error': 'User not found'}), 404