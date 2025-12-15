from flask import Blueprint

# 'main' is the name of the blueprint.
# Note: In templates, url_for('index') becomes url_for('main.index')
bp = Blueprint('main', __name__)

from app.main import routes