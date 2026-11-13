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

    @app.context_processor
    def inject_global_data():
        role_str = 'owner'
        user_name = 'Aling Terry (Owner)'
        if current_user and current_user.is_authenticated:
            resolved_role = get_user_role(current_user).lower()
            role_str = 'cashier' if resolved_role == 'cashier' else 'owner'
            user_name = getattr(current_user, 'full_name', None) or getattr(current_user, 'username', 'User')

        notifications_list = []
        store_settings_obj = None
        try:
            store_settings_obj = StoreSetting.get_settings()
            if role_str == 'owner':
                products = Product.query.order_by(Product.stock_quantity.asc()).all()
                for p in products:
                    if p.stock_quantity == 0:
                        notifications_list.append({
                            'type': 'danger',
                            'title': 'Out of Stock Alert',
                            'message': f"{p.product_name} has 0 units left!",
                            'time': 'Action needed'
                        })
                    elif p.stock_quantity <= p.reorder_level:
                        notifications_list.append({
                            'type': 'warning',
                            'title': 'Low Stock Alert',
                            'message': f"{p.product_name} has only {p.stock_quantity} items left.",
                            'time': 'Reorder soon'
                        })
                pending_pos = PurchaseOrder.query.filter_by(status='Pending').limit(3).all()
                for po in pending_pos:
                    sup_name = po.supplier.supplier_name if po.supplier else 'Supplier'
                    notifications_list.append({
                        'type': 'info',
                        'title': 'Pending Delivery',
                        'message': f"{po.po_number} from {sup_name} is awaiting receipt.",
                        'time': 'In transit'
                    })
        except Exception:
            pass

        return dict(
            current_role=role_str,
            current_user_name=user_name,
            system_notifications=notifications_list,
            store_settings=store_settings_obj
        )

    # Direct Blueprint Registration
    from app.auth.auth import auth_bp
    from app.inventory.inventory import inventory_bp
    from app.pos.pos import pos_bp
    from app.suppliers.suppliers import suppliers_bp
    from app.analytics.analytics import analytics_bp
    from app.settings.settings import settings_bp
    from app.core.core import core_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(core_bp, url_prefix='/')

    return app
