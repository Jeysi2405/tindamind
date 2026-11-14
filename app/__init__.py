import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user

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

    setattr(login_manager, 'login_view', 'auth.login')
    login_manager.login_message_category = 'info'

    from app.models import User, Product, PurchaseOrder, StoreSetting
    from app.auth.auth import get_user_role

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    # Direct Blueprint Registration
    from app.auth.auth import auth_bp
    from app.inventory.inventory import inventory_bp
    from app.pos.pos import pos_bp, checkout as api_pos_checkout
    from app.suppliers.suppliers import suppliers_bp, create_po as api_generate_po
    from app.analytics.analytics import analytics_bp, sales_summary_api as api_daily_revenue
    from app.settings.settings import settings_bp
    from app.core.core import core_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(core_bp, url_prefix='/')

    # Top-Level API Route Aliases matching Backend Checklist Specifications
    app.add_url_rule('/api/pos/checkout', endpoint='api_pos_checkout', view_func=api_pos_checkout, methods=['POST'])
    app.add_url_rule('/api/sales/daily-revenue', endpoint='api_daily_revenue', view_func=api_daily_revenue, methods=['GET'])
    app.add_url_rule('/api/orders/generate-po', endpoint='api_generate_po', view_func=api_generate_po, methods=['POST'])

    return app