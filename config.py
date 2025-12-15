import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chiave_segretissima_beerpong'
    # SQLALCHEMY_DATABASE_URI can go here later if you switch from raw SQLite to SQLAlchemy full URL