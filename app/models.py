import os
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Initialize SQLAlchemy
db = SQLAlchemy()

# ==========================================
#         CONFIGURATION CONSTANTS
# ==========================================

INTESTAZIONI = [
    "Giocatore", "Miss", "Bordo", "Centro", "Noi", "Loro", "Bersaglio Iniziale", "Colpiti",
    "Formato", "Salvezza", "Posizione", "Bevanda", "Multipli", "Data", "Ora", "Note"
]

CUP_DEFINITIONS = {
    "Piramide": ["3 Sx", "3 Cen", "3 Dx", "2 Sx", "2 Dx", "1 Cen"],
    "Rombo": ["R3 Cen", "R2 Sx", "R2 Dx", "R1 Cen"],
    "Triangolo": ["T2 Sx", "T2 Dx", "T1 Cen"],
    "Linea Verticale": ["LV 2", "LV 1"],
    "Linea Orizzontale": ["LO Sx", "LO Dx"],
    "Singolo Centrale": ["Singolo"]
}


# ==========================================
#              DATABASE MODELS
# ==========================================

class Player(db.Model):
    """
    Represents a registered user in the system.
    """
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Increased length for hashes
    is_admin = db.Column(db.Boolean, default=False)
    edit = db.Column(db.Boolean, default=False)  # Kept for compatibility if used elsewhere

    # Relationship to access all records for this player easily
    records = db.relationship('PlayerRecord', backref='player', lazy=True)


class ActiveMatch(db.Model):
    """
    Represents a game session (Match).
    Stores the state of the game (cups remaining, turn, etc.)
    """
    __tablename__ = 'active_matches'

    id = db.Column(db.Integer, primary_key=True)
    match_name = db.Column(db.String(50), default="Partita")
    status = db.Column(db.String(20), default="running")  # running, finished, redemption_t1, etc.

    # Timestamps
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)

    # Turn Management
    current_turn = db.Column(db.Integer, default=0)

    # Teams (Storing Player Names)
    t1_p1 = db.Column(db.String(50))
    t1_p2 = db.Column(db.String(50))
    t2_p1 = db.Column(db.String(50))
    t2_p2 = db.Column(db.String(50))

    # Cup State (JSON Strings)
    t1_cup_state = db.Column(db.Text, default='[]')
    t2_cup_state = db.Column(db.Text, default='[]')
    t1_pending_list = db.Column(db.Text, default='[]')
    t2_pending_list = db.Column(db.Text, default='[]')

    # Game Logic Fields
    winning_team = db.Column(db.String(10), nullable=True)
    redemption_shots_left = db.Column(db.Integer, default=0)
    redemption_hits = db.Column(db.Integer, default=0)

    # Configuration / Targets (UI Helpers)
    cups_target_for_t1 = db.Column(db.Integer, default=6)
    cups_target_for_t2 = db.Column(db.Integer, default=6)
    pending_damage_for_t1 = db.Column(db.Integer, default=0)
    pending_damage_for_t2 = db.Column(db.Integer, default=0)

    format_target_for_t1 = db.Column(db.String(20), default="Piramide")
    format_target_for_t2 = db.Column(db.String(20), default="Piramide")
    t1_format_changed = db.Column(db.Boolean, default=False)
    t2_format_changed = db.Column(db.Boolean, default=False)

    # Relationships
    records = db.relationship('PlayerRecord', backref='match', lazy=True)


class PlayerRecord(db.Model):
    """
    Represents a single shot/event in a game.
    Now centralized in one table instead of scattered files.
    """
    __tablename__ = 'records'

    id = db.Column(db.Integer, primary_key=True)

    # Foreign Keys
    match_id = db.Column(db.Integer, db.ForeignKey('active_matches.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)

    # Shot Details (Mapped to your template needs)
    miss = db.Column(db.String(10), default="No")
    bordo = db.Column(db.String(10), default="No")
    centro = db.Column(db.String(10), default="No")

    bicchiere_colpito = db.Column(db.String(255))  # "3 Cen, 2 Dx" or N/A

    # Snapshot of game state at this moment (For history/undo)
    cups_own = db.Column(db.Integer, default=0)
    cups_opp = db.Column(db.Integer, default=0)
    numero_bicchieri = db.Column(db.String(20), default="0")  # Legacy string format support

    # Metadata
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text)

    # Extra Game info
    tiro_salvezza = db.Column(db.String(10), default="No")
    bicchieri_multipli = db.Column(db.String(20), nullable=True)  # "Double", "Triple"

    # Legacy fields to match your template/logic perfectly without rewrite
    formato = db.Column(db.String(20))
    postazione = db.Column(db.String(20))
    bevanda = db.Column(db.String(50))

    # Helper property for template compatibility if it uses r.outcome instead of miss/bordo/centro check
    @property
    def outcome(self):
        if self.centro == "Sì": return "Centro"
        if self.bordo == "Sì": return "Bordo"
        return "Miss"


# ==========================================
#         INITIALIZATION FUNCTION
# ==========================================

def init_db(app):
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # Using a single main DB file now
    db_path = os.path.join(BASE_DIR, 'instance', 'beerpong.db')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()


# ==========================================
#      HELPER FUNCTIONS (Compatibility)
# ==========================================

def get_all_db_content():
    """
    Returns content of the main database for the admin viewer.
    Replaces the old multi-file scanner.
    """
    # Simply inspect the current database engine
    engine = db.engine
    data = {}
    try:
        with engine.connect() as conn:
            # Get table names
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result if not row[0].startswith('sqlite_')]

            for table in tables:
                result = conn.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                cols = list(result.keys())
                data[table] = {'cols': cols, 'rows': [list(row) for row in rows]}
    except Exception as e:
        data['Error'] = {'cols': ['Error'], 'rows': [[str(e)]]}

    return data  # Returns dictionary mapping filename (now just one) -> table data