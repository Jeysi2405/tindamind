import os
from app import create_app

# Determine environment and instantiate application via factory
env_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(env_name)

if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    debug_mode = app.config.get('DEBUG', True)
    
    app.run(host=host, port=port, debug=debug_mode)