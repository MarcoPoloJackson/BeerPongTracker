from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, or_, text
from sqlalchemy.orm import sessionmaker
import os
import json
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash  # Mantenuto qui per la classe Player

# Oggetto db globale (sarà inizializzato nel file principale)
db = SQLAlchemy()

# Variabili globali per percorsi, inizializzate in init_db
DATA_FOLDER = ""
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Costanti di configurazione (spostate qui per centralizzazione)
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

def init_db(app_instance):
    """
    Inizializza l'istanza SQLAlchemy con l'applicazione Flask fornita.
    Crea i percorsi e le tabelle se non esistono.
    """
    global DATA_FOLDER
    DATA_FOLDER = os.path.join(BASE_DIR, 'Dati')
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    # Imposta la configurazione del DB sull'istanza dell'app fornita
    app_instance.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(DATA_FOLDER, "master_players.db")}'
    app_instance.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inizializza l'oggetto db con l'app
    db.init_app(app_instance)

    # Crea le tabelle se non esistono (richiede l'app context)
    with app_instance.app_context():
        db.create_all()


# ==========================================
#              MODELLI DATABASE
# ==========================================

class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    edit = db.Column(db.Boolean, nullable=False, default=False)


class ActiveMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_name = db.Column(db.String(50), default="Partita")
    t1_cup_state = db.Column(db.Text, default='[]')
    t2_cup_state = db.Column(db.Text, default='[]')
    t1_pending_list = db.Column(db.Text, default='[]')
    t2_pending_list = db.Column(db.Text, default='[]')
    winning_team = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(20), default="running")
    start_time = db.Column(db.DateTime, default=datetime.now)
    end_time = db.Column(db.DateTime, nullable=True)
    redemption_shots_left = db.Column(db.Integer, default=0)
    redemption_hits = db.Column(db.Integer, default=0)
    t1_p1 = db.Column(db.String(50));
    t1_p2 = db.Column(db.String(50))
    t2_p1 = db.Column(db.String(50));
    t2_p2 = db.Column(db.String(50))
    cups_target_for_t1 = db.Column(db.Integer, default=6)
    cups_target_for_t2 = db.Column(db.Integer, default=6)
    pending_damage_for_t1 = db.Column(db.Integer, default=0)
    pending_damage_for_t2 = db.Column(db.Integer, default=0)
    format_target_for_t1 = db.Column(db.String(20), default="Piramide")
    format_target_for_t2 = db.Column(db.String(20), default="Piramide")
    t1_format_changed = db.Column(db.Boolean, default=False)
    t2_format_changed = db.Column(db.Boolean, default=False)


class Record(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, nullable=True)
    miss = db.Column(db.String(10), nullable=False)
    bordo = db.Column(db.String(10), nullable=False)
    centro = db.Column(db.String(10), nullable=False)
    cups_own = db.Column(db.Integer, default=0)
    cups_opp = db.Column(db.Integer, default=0)
    numero_bicchieri = db.Column(db.String(20), default="0")
    bicchiere_colpito = db.Column(db.String(255))
    formato = db.Column(db.String(20))
    tiro_salvezza = db.Column(db.String(10), nullable=False)
    postazione = db.Column(db.String(20))
    bevanda = db.Column(db.String(50))
    giocatore = db.Column(db.String(50))
    bicchieri_multipli = db.Column(db.String(20), nullable=True)
    data = db.Column(db.String(20))
    ora = db.Column(db.String(10))
    note = db.Column(db.Text)


# ==========================================
#              HELPER FUNCTIONS
# ==========================================

def get_player_db_session(player_name):
    """
    Crea o si connette al database SQLite specifico del giocatore (<nome>_tracker.db),
    esegue eventuali migrazioni e restituisce Session e il modello Record specifico.
    """
    safe_name = player_name.replace(" ", "_").lower()
    db_filename = os.path.join(DATA_FOLDER, f'{safe_name}_tracker.db')
    db_uri = f'sqlite:///{db_filename}'

    # Crea il file DB se non esiste
    if not os.path.exists(db_filename):
        try:
            conn = sqlite3.connect(db_filename);
            conn.close()
        except:
            pass

    engine = create_engine(db_uri)

    # Definisce il modello concreto PlayerRecord che eredita da Record
    class PlayerRecord(Record):
        __tablename__ = 'record'
        __table_args__ = {'extend_existing': True}

    # Esegue il setup e le migrazioni
    with engine.connect() as conn:
        PlayerRecord.metadata.create_all(conn)
        # Blocchi try/except per migrazioni (alter table)
        try:
            # Nota: L'uso di text() è importante con SQLAlchemy 2.0+
            conn.execute(text("ALTER TABLE record ADD COLUMN match_id INTEGER"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE record ADD COLUMN cups_own INTEGER"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE record ADD COLUMN cups_opp INTEGER"))
        except:
            pass

    Session = sessionmaker(bind=engine)
    return Session(), PlayerRecord


def dati_tabella_from_records(records):
    """Converte oggetti record in una lista di dizionari per il template."""
    dati = []
    for r in records:
        dati.append({
            "ID": r.id, "Giocatore": r.giocatore, "Miss": r.miss, "Bordo": r.bordo,
            "Centro": r.centro, "Noi": r.cups_own, "Loro": r.cups_opp,
            "Bersaglio Iniziale": r.numero_bicchieri, "Colpiti": r.bicchiere_colpito,
            "Formato": r.formato, "Salvezza": r.tiro_salvezza, "Posizione": r.postazione,
            "Bevanda": r.bevanda, "Multipli": r.bicchieri_multipli if r.bicchieri_multipli else "-",
            "Data": r.data, "Ora": r.ora, "Note": r.note
        })
    return dati


def init_cup_state(match, team, format_name):
    """Inizializza lo stato dei bicchieri per una squadra in una partita."""
    full_set = CUP_DEFINITIONS.get(format_name, [])
    if team == 't1':
        match.t1_cup_state = json.dumps(full_set)
    else:
        match.t2_cup_state = json.dumps(full_set)
    db.session.commit()


def get_match_info(player_name):
    """Trova la partita attiva in cui è impegnato un giocatore e il team di appartenenza."""
    match = ActiveMatch.query.filter(or_(ActiveMatch.t1_p1 == player_name, ActiveMatch.t1_p2 == player_name)).first()
    if match: return match, 't1'
    match = ActiveMatch.query.filter(or_(ActiveMatch.t2_p1 == player_name, ActiveMatch.t2_p2 == player_name)).first()
    if match: return match, 't2'
    return None, None


def count_shots_in_match(player_name, match_id):
    """
    Conta quanti record (tiri) sono stati registrati per un giocatore
    in una specifica partita (usando il suo DB tracker).
    """
    if not match_id: return 0
    dbsession, PlayerRecord = get_player_db_session(player_name)
    count = dbsession.query(PlayerRecord).filter_by(match_id=match_id).count()
    dbsession.close()
    return count


# Le funzioni di logica di gioco (start_overtime, finish_match, update_game_state, apply_pending_damage)
# rimangono nel file principale o in un modulo 'game_logic.py',
# in quanto la loro logica è più vicina alla gestione del gioco che all'accesso puro al DB.
# Tuttavia, dato che erano già nel tuo codice originale e usano db.session.commit(), le ho mantenute
# per comodità di migrazione.

# ==========================================
#           LOGICA DI GIOCO (Richiede db)
# ==========================================

def apply_pending_damage(match, target_team):
    """Applica i danni pendenti modificando ActiveMatch nel DB."""
    state_col = 't1_cup_state' if target_team == 't1' else 't2_cup_state'
    pending_list_col = 't1_pending_list' if target_team == 't1' else 't2_pending_list'
    pending_int_col = 'pending_damage_for_t1' if target_team == 't1' else 'pending_damage_for_t2'

    try:
        current_cups = json.loads(getattr(match, state_col))
        pending_cups = json.loads(getattr(match, pending_list_col))

        if not pending_cups: return
        remaining_count = len(set(current_cups)) - len(set(pending_cups))

        if remaining_count <= 0:
            setattr(match, pending_int_col, 0)
            return

        new_cup_state = [cup for cup in current_cups if cup not in pending_cups]

        setattr(match, state_col, json.dumps(new_cup_state))
        setattr(match, pending_list_col, '[]')
        setattr(match, pending_int_col, 0)

        db.session.commit()
    except Exception as e:
        print(f"Errore applying damage: {e}")


def start_overtime(match):
    """Reset e avvio dell'Overtime (Richiede db)."""
    match.status = 'running'
    match.format_target_for_t1 = "Singolo Centrale"
    match.format_target_for_t2 = "Singolo Centrale"
    match.t1_cup_state = json.dumps(["Singolo"])
    match.t2_cup_state = json.dumps(["Singolo"])
    match.t1_pending_list = '[]';
    match.t2_pending_list = '[]'
    match.pending_damage_for_t1 = 0;
    match.pending_damage_for_t2 = 0
    match.redemption_hits = 0;
    match.redemption_shots_left = 0
    match.t1_format_changed = True;
    match.t2_format_changed = True
    db.session.commit()


def finish_match(match, winner):
    """Registra la fine della partita e il vincitore (Richiede db)."""
    match.status = 'finished'
    match.end_time = datetime.now()
    match.winning_team = winner
    db.session.commit()

    # Reset per la prossima partita
    match.format_target_for_t1 = "Piramide";
    match.format_target_for_t2 = "Piramide"
    init_cup_state(match, 't1', 'Piramide');
    init_cup_state(match, 't2', 'Piramide')
    match.redemption_hits = 0
    match.t1_format_changed = False;
    match.t2_format_changed = False
    db.session.commit()


def update_game_state(match):
    """
    Gestisce le regole di vittoria, sconfitta, overtime e ribaltone.
    """
    if match.status == 'finished': return

    # --- INIZIALIZZAZIONE e 1. CALCOLO BILANCIO REALE ---
    t1_active_count = 0; t2_active_count = 0
    try:
        t1_list = json.loads(match.t1_cup_state); t2_list = json.loads(match.t2_cup_state)
        t1_pending = json.loads(match.t1_pending_list); t2_pending = json.loads(match.t2_pending_list)

        # [MODIFICA 2]: Rimossi set() per contare i duplicati (Balls Back)
        t1_active_count = len(t1_list) - len(t1_pending)
        t2_active_count = len(t2_list) - len(t2_pending)

        match.cups_target_for_t1 = t1_active_count
        match.cups_target_for_t2 = t2_active_count
    except:
        return

    # 2. LOGICA FASE NORMALE (Running)
    if match.status == 'running':
        if t1_active_count <= 0:
            if t1_active_count <= -1: finish_match(match, winner='t2') # Overkill
            else:
                match.status = 'redemption_t1'
                rimasti_avv = t2_active_count
                match.redemption_shots_left = 2 if rimasti_avv == 1 else rimasti_avv
                match.redemption_hits = 0 # Reset counter

        elif t2_active_count <= 0:
            if t2_active_count <= -1: finish_match(match, winner='t1') # Overkill
            else:
                match.status = 'redemption_t2'
                rimasti_avv = t1_active_count
                match.redemption_shots_left = 2 if rimasti_avv == 1 else rimasti_avv
                match.redemption_hits = 0

    # 3. LOGICA FASE REDENZIONE
    elif match.status.startswith('redemption'):
        redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
        opponent_team = 't2' if redeeming_team == 't1' else 't1'

        # [MODIFICA 3]: Usiamo DIRETTAMENTE active_count.
        # Non sottraiamo più match.redemption_hits perché i bicchieri sono già
        # stati messi in pending_list in app.py, quindi active_count è già sceso.
        target_balance = t2_active_count if redeeming_team == 't1' else t1_active_count

        # --- CONTROLLO VITTORIA IMMEDIATA ---
        if target_balance < -1:
            finish_match(match, winner=redeeming_team)
            return

        # --- CONTROLLO FINE TIRI ---
        if match.redemption_shots_left <= 0:
            if target_balance == 0:
                start_overtime(match)
            elif target_balance == -1: # Ribaltone
                match.status = f'redemption_{opponent_team}'
                match.redemption_shots_left = 2
                match.redemption_hits = 0
                # Pulizia immediata liste avversario
                if redeeming_team == 't1': match.t2_cup_state = '[]'; match.t2_pending_list = '[]'
                else: match.t1_cup_state = '[]'; match.t1_pending_list = '[]'
            elif target_balance > 0:
                finish_match(match, winner=opponent_team)

def get_all_db_content():
    """
            Scansiona la cartella Dati e restituisce il contenuto di tutti i file .db
            in un formato dizionario per la visualizzazione.
            """
    # Usiamo la variabile globale DATA_FOLDER definita in databases.py
    # (Assicurati che DATA_FOLDER sia accessibile o ricavalo qui)
    local_data_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'Dati')

    all_db_content = {}
    if os.path.exists(local_data_folder):
        for filename in os.listdir(local_data_folder):
            if filename.endswith(".db"):
                filepath = os.path.join(local_data_folder, filename)
                try:
                    conn = sqlite3.connect(filepath)
                    cursor = conn.cursor()

                    # Ottieni lista tabelle
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()

                    file_data = {}
                    for t in tables:
                        tn = t[0]
                        if tn.startswith('sqlite_'): continue

                        # Ottieni dati tabella
                        cursor.execute(f"SELECT * FROM {tn}")
                        rows = cursor.fetchall()
                        col_names = [d[0] for d in cursor.description]
                        file_data[tn] = {'cols': col_names, 'rows': rows}

                    conn.close()
                    all_db_content[filename] = file_data
                except Exception as e:
                    all_db_content[filename] = {'Err': {'cols': ['E'], 'rows': [[str(e)]]}}
    return all_db_content
