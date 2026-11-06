from flask import current_app, jsonify, render_template, redirect, url_for
from app.core import core_bp


@core_bp.route('/')
def index():
    """Redirect root traffic to the login screen."""
    return redirect(url_for('core.login'))


@core_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Render the login template."""
    return render_template('login.html')


@core_bp.route('/health')
def health_check():
    """System health check endpoint."""
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    dialect = db_uri.split(':')[0] if db_uri else 'unknown'
    return jsonify({
        "system": "TindaMind",
        "status": "healthy",
        "blueprint": "core",
        "database_dialect": dialect,
        "debug": current_app.config.get('DEBUG', False)
    }), 200