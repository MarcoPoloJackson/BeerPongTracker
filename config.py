import os

# Trova la cartella principale del progetto (BeerPongTracker)
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chiave_segretissima_beerpong'
    
    # Crea il database dentro una cartella chiamata 'instance'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'beerpong.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False