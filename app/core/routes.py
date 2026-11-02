from flask import current_app, jsonify, render_template
from jinja2 import TemplateNotFound
from app.core import core_bp


@core_bp.route('/')
def index():
    """Landing page route."""
    try:
        return render_template('core/index.html')
    except TemplateNotFound:
        return jsonify({
            "system": "TindaMind",
            "status": "online",
            "blueprint": "core",
            "message": "Core blueprint active. Base templates will be created in Module 1.3."
        }), 200


@core_bp.route('/health')
def health_check():
    """Health check route to verify factory and environment status."""
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    dialect = db_uri.split(':')[0] if db_uri else 'unknown'
    return jsonify({
        "system": "TindaMind",
        "status": "healthy",
        "blueprint": "core",
        "database_dialect": dialect,
        "debug": current_app.config.get('DEBUG', False)
    }), 200