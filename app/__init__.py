import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import config_by_name

# Initialize Flask extensions in an unbound global state
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()


def create_app(config_name=None):
    """
    Application Factory constructing the Flask application instance.
    Loads environment-specific configuration and initializes extensions.
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    
    # Load configuration object
    selected_config = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(selected_config)

    # Bind extensions to the current application instance
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Configure Flask-Login defaults (enforced in Phase 2)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    # Register Blueprints
    core_module_path = os.path.join(os.path.dirname(__file__), 'core')
    if os.path.exists(core_module_path):
        from app.core import core_bp
        app.register_blueprint(core_bp)

    return app