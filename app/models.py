import os
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Inizializza SQLAlchemy
db = SQLAlchemy()

# ==========================================
#         COSTANTI DI CONFIGURAZIONE
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
#         FUNZIONE DI INIZIALIZZAZIONE
# ==========================================

def init_db(app):
    """
    Collega il database all'app Flask e crea le tabelle se mancano.
    """
    basedir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(basedir)
    db_path = os.path.join(project_root, 'instance', 'beerpong.db')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

# ==========================================
#              MODELLI DATABASE
# ==========================================

class Player(db.Model):
    """Tabella Utenti/Giocatori"""
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    edit = db.Column(db.Boolean, default=False) 

    # Relazione: permette di ottenere tutti i tiri di un giocatore con player.records
    records = db.relationship('PlayerRecord', backref='player', lazy=True)


class ActiveMatch(db.Model):
    """
    Tabella Partite Attive.
    Contiene lo stato del gioco, i bicchieri rimasti, ecc.
    """
    __tablename__ = 'active_matches'

    id = db.Column(db.Integer, primary_key=True)
    match_name = db.Column(db.String(50), default="Partita")
    
    # [NUOVO CAMPO AGGIUNTO] Modalità di gioco (es. 'squadre', '1vs1')
    mode = db.Column(db.String(20), default="squadre")

    status = db.Column(db.String(20), default="running") # running, finished, redemption_t1...

    start_time = db.Column(db.DateTime, default=datetime.now)
    end_time = db.Column(db.DateTime, nullable=True)
    
    # Nomi dei giocatori (per compatibilità rapida)
    t1_p1 = db.Column(db.String(50)); t1_p2 = db.Column(db.String(50))
    t2_p1 = db.Column(db.String(50)); t2_p2 = db.Column(db.String(50))

    # Stato Bicchieri (Salvato come stringa JSON es: '["3 Cen", "2 Dx"]')
    t1_cup_state = db.Column(db.Text, default='[]')
    t2_cup_state = db.Column(db.Text, default='[]')
    
    # Bicchieri in attesa di conferma (blu/azzurri)
    t1_pending_list = db.Column(db.Text, default='[]')
    t2_pending_list = db.Column(db.Text, default='[]')

    # Logica di vittoria
    winning_team = db.Column(db.String(10), nullable=True)
    redemption_shots_left = db.Column(db.Integer, default=0)
    redemption_hits = db.Column(db.Integer, default=0)

    # Campi di supporto per i calcoli e la UI
    cups_target_for_t1 = db.Column(db.Integer, default=6)
    cups_target_for_t2 = db.Column(db.Integer, default=6)
    pending_damage_for_t1 = db.Column(db.Integer, default=0)
    pending_damage_for_t2 = db.Column(db.Integer, default=0)

    format_target_for_t1 = db.Column(db.String(20), default="Piramide")
    format_target_for_t2 = db.Column(db.String(20), default="Piramide")
    t1_format_changed = db.Column(db.Boolean, default=False)
    t2_format_changed = db.Column(db.Boolean, default=False)

    # Relazione con i record dei tiri
    records = db.relationship('PlayerRecord', backref='match', lazy=True)


class PlayerRecord(db.Model):
    """
    Tabella dei Tiri (Records).
    Sostituisce i vecchi file _tracker.db multipli.
    """
    __tablename__ = 'records'

    id = db.Column(db.Integer, primary_key=True)

    # Chiavi Esterne (Foreign Keys)
    match_id = db.Column(db.Integer, db.ForeignKey('active_matches.id'), nullable=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)

    # Dati del tiro
    miss = db.Column(db.String(10), default="No")
    bordo = db.Column(db.String(10), default="No")
    centro = db.Column(db.String(10), default="No")
    bicchiere_colpito = db.Column(db.String(255)) 

    # Snapshot dello stato al momento del tiro
    cups_own = db.Column(db.Integer, default=0)
    cups_opp = db.Column(db.Integer, default=0)
    numero_bicchieri = db.Column(db.String(20), default="0")

    # Metadata
    timestamp = db.Column(db.DateTime, default=datetime.now) # Sostituisce Data/Ora separati
    note = db.Column(db.Text)

    # Info Extra
    tiro_salvezza = db.Column(db.String(10), default="No")
    bicchieri_multipli = db.Column(db.String(20), nullable=True)
    formato = db.Column(db.String(20))
    postazione = db.Column(db.String(20))
    bevanda = db.Column(db.String(50))

    # --- PROPRIETÀ DI COMPATIBILITÀ (MAGIC) ---
    @property
    def data(self):
        return self.timestamp.strftime("%d/%m/%Y")

    @property
    def ora(self):
        return self.timestamp.strftime("%H:%M")

    @property
    def giocatore(self):
        return self.player.name if self.player else "Sconosciuto"

# ==========================================
#      HELPER FUNCTIONS (Per Admin DB)
# ==========================================

def get_all_db_content():
    """Restituisce tutto il contenuto del DB per la pagina Admin"""
    engine = db.engine
    data = {}
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result if not row[0].startswith('sqlite_')]

            for table in tables:
                result = conn.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                cols = list(result.keys())
                data[table] = {'cols': cols, 'rows': [list(row) for row in rows]}
    except Exception as e:
        data['Error'] = {'cols': ['Error'], 'rows': [[str(e)]]}
    return data