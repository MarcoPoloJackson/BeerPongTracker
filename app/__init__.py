from flask import Flask
from config import Config
from app.models import init_db
from flask_socketio import SocketIO # <-- 1. NUOVO IMPORT

# <-- 2. CREIAMO L'OGGETTO QUI FUORI
# Lo creiamo vuoto per ora, così altri file possono importarlo
socketio = SocketIO()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database using your existing custom function
    init_db(app)
    
    # <-- 3. INIZIALIZZIAMO SOCKETIO CON L'APP
    socketio.init_app(app)

    # Register Blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    return app