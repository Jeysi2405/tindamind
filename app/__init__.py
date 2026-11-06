import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()


def create_app(config_class=None):
    app = Flask(__name__)

    if isinstance(config_class, str):
        try:
            from config import config_by_name
            selected_config = config_by_name.get(config_class.lower(), config_by_name['default'])
        except (ImportError, KeyError):
            from config import DevelopmentConfig
            selected_config = DevelopmentConfig
        app.config.from_object(selected_config)
    elif config_class is not None:
        app.config.from_object(config_class)
    else:
        try:
            from config import DevelopmentConfig
            app.config.from_object(DevelopmentConfig)
        except ImportError:
            app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tindamind-secret-key-dev')
            app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/tindamind.db')
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Direct Blueprint Registration
    from app.auth.auth import auth_bp
    from app.inventory.inventory import inventory_bp
    from app.pos.pos import pos_bp
    from app.suppliers.suppliers import suppliers_bp
    from app.analytics.analytics import analytics_bp
    from app.core.core import core_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(core_bp)

    return app