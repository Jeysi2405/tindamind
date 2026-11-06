import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import config_by_name

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return None


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    selected_config = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(selected_config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = 'core.login'
    login_manager.login_message_category = 'warning'

    from app.core import core_bp
    app.register_blueprint(core_bp)

    return app
