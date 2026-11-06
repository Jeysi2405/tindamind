from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from jinja2 import TemplateNotFound
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)


def get_user_role(user):
    """Safely extracts the role name across relational models, properties, or scalar attributes."""
    if not user or not user.is_authenticated:
        return 'Cashier'
    
    role = getattr(user, 'role', None)
    if isinstance(role, str):
        return role
    if hasattr(role, 'role_name'):
        return role.role_name
    if getattr(user, 'role_id', None) == 1:
        return 'Admin'
    if getattr(user, 'is_admin', False):
        return 'Admin'
    return 'Cashier'


def admin_required(f):
    """Custom decorator for Role-Based Access Control (RBAC).

    Restricts route access exclusively to Admin users.
    Redirects Cashier accounts to the POS checkout terminal.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        role_name = get_user_role(current_user)

        if role_name.lower() != 'admin':
            flash('Access Denied: Cashier accounts do not have permission to access this module.', 'danger')
            return redirect(url_for('pos.index'))
        return f(*args, **kwargs)

    return decorated_function


def render_login_template():
    """Renders login.html safely across template directories."""
    try:
        return render_template('login.html')
    except TemplateNotFound:
        return render_template('auth/login.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Cashiers directly land on POS, Admin lands on Dashboard
        role_name = get_user_role(current_user)
        if role_name.lower() == 'cashier':
            return redirect(url_for('pos.index'))
        return redirect(url_for('core.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = True if request.form.get('remember') else False

        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_login_template()

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            role_name = get_user_role(user)

            flash(f'Mabuhay! Welcome back, {user.full_name}!', 'success')

            if role_name.lower() == 'cashier':
                return redirect(url_for('pos.index'))

            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('core.index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_login_template()


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))