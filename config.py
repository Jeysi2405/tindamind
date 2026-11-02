import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base configuration class with universal settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'tindamind-default-dev-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    """Development environment configuration using SQLite."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(basedir, 'tindamind.db')}"


class TestingConfig(Config):
    """Testing configuration utilizing an in-memory database."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration optimized for Render PostgreSQL deployment."""
    DEBUG = False
    
    # Handle Render's postgres:// URI scheme compatibility for SQLAlchemy
    raw_database_url = os.environ.get('DATABASE_URL')
    if raw_database_url and raw_database_url.startswith('postgres://'):
        raw_database_url = raw_database_url.replace('postgres://', 'postgresql://', 1)
        
    SQLALCHEMY_DATABASE_URI = raw_database_url


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}