from flask import Flask
from config import Config
from app.models import init_db
from flask_socketio import SocketIO
# 1. NUOVI IMPORT
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

socketio = SocketIO()

# 2. CREIAMO IL LIMITATORE
# get_remote_address serve a bloccare l'IP specifico di chi sta attaccando
limiter = Limiter(key_func=get_remote_address)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    init_db(app)
    socketio.init_app(app)
    
    # 3. INIZIALIZZIAMO IL LIMITATORE CON L'APP
    limiter.init_app(app)

    # Registrazione Blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.password import gate_bp
    app.register_blueprint(gate_bp)

    return app