from flask import Flask
from config import Config
from app.models import init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database using your existing custom function
    init_db(app)

    # Register Blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    return app