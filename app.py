from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, or_, text
from sqlalchemy.orm import sessionmaker
import os
import csv
import json
import sqlite3
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAZIONE PERCORSI ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, 'Dati')

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(DATA_FOLDER, "master_players.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'chiave_segretissima_beerpong'
db = SQLAlchemy(app)

INTESTAZIONI = [
    "Giocatore", "Miss", "Bordo", "Centro", "Noi", "Loro", "Bersaglio Iniziale", "Colpiti",
    "Formato", "Salvezza", "Posizione", "Bevanda", "Multipli", "Data", "Ora", "Note"
]

# Mappa delle posizioni per ogni formato
CUP_DEFINITIONS = {
    "Piramide": ["3 Sx", "3 Cen", "3 Dx", "2 Sx", "2 Dx", "1 Cen"],
    "Rombo": ["R3 Cen", "R2 Sx", "R2 Dx", "R1 Cen"],
    "Triangolo": ["T2 Sx", "T2 Dx", "T1 Cen"],
    "Linea Verticale": ["LV 2", "LV 1"],
    "Linea Orizzontale": ["LO Sx", "LO Dx"],
    "Singolo Centrale": ["Singolo"]
}

# ==========================================
#              MODELLI DATABASE
# ==========================================

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

# --- MODELLO DATABASE (AGGIORNATO) ---
class ActiveMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_name = db.Column(db.String(50), default="Partita")

    t1_cup_state = db.Column(db.Text, default='[]') 
    t2_cup_state = db.Column(db.Text, default='[]')
    
    # NUOVE COLONNE PER SALVARE QUALI BICCHIERI SONO IN ATTESA DI RIMOZIONE
    t1_pending_list = db.Column(db.Text, default='[]') 
    t2_pending_list = db.Column(db.Text, default='[]')

    status = db.Column(db.String(20), default="running") 
    start_time = db.Column(db.DateTime, default=datetime.now)
    end_time = db.Column(db.DateTime, nullable=True)

    redemption_shots_left = db.Column(db.Integer, default=0)
    redemption_hits = db.Column(db.Integer, default=0)

    t1_p1 = db.Column(db.String(50)); t1_p2 = db.Column(db.String(50))
    t2_p1 = db.Column(db.String(50)); t2_p2 = db.Column(db.String(50))
    
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
    safe_name = player_name.replace(" ", "_").lower()
    db_filename = os.path.join(DATA_FOLDER, f'{safe_name}_tracker.db')
    db_uri = f'sqlite:///{db_filename}'
    if not os.path.exists(db_filename):
        try: conn = sqlite3.connect(db_filename); conn.close()
        except: pass
    engine = create_engine(db_uri)
    class PlayerRecord(Record):
        __tablename__ = 'record'
        __table_args__ = {'extend_existing': True}
    
    with engine.connect() as conn:
        PlayerRecord.metadata.create_all(conn)
        try: conn.execute(text("ALTER TABLE record ADD COLUMN match_id INTEGER")); 
        except: pass
        try: conn.execute(text("ALTER TABLE record ADD COLUMN cups_own INTEGER")); 
        except: pass
        try: conn.execute(text("ALTER TABLE record ADD COLUMN cups_opp INTEGER")); 
        except: pass

    Session = sessionmaker(bind=engine)
    return Session(), PlayerRecord

def dati_tabella_from_records(records):
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
    # Prende tutti i bicchieri del formato scelto e li salva nel DB come JSON
    full_set = CUP_DEFINITIONS.get(format_name, [])
    if team == 't1': match.t1_cup_state = json.dumps(full_set)
    else: match.t2_cup_state = json.dumps(full_set)
    db.session.commit()

def get_match_info(player_name):
    match = ActiveMatch.query.filter(or_(ActiveMatch.t1_p1 == player_name, ActiveMatch.t1_p2 == player_name)).first()
    if match: return match, 't1'
    match = ActiveMatch.query.filter(or_(ActiveMatch.t2_p1 == player_name, ActiveMatch.t2_p2 == player_name)).first()
    if match: return match, 't2'
    return None, None

def apply_pending_damage(match, target_team):
    """
    Applica i danni in sospeso per la squadra target (rimuove fisicamente i bicchieri).
    target_team: 't1' o 't2' (la squadra che SUBISCE il danno e perde i bicchieri)
    """
    # Determina le colonne
    state_col = 't1_cup_state' if target_team == 't1' else 't2_cup_state'
    pending_list_col = 't1_pending_list' if target_team == 't1' else 't2_pending_list'
    pending_int_col = 'pending_damage_for_t1' if target_team == 't1' else 'pending_damage_for_t2'

    try:
        # 1. Carica liste attuali
        current_cups = json.loads(getattr(match, state_col))
        pending_cups = json.loads(getattr(match, pending_list_col))

        if not pending_cups:
            return # Nessun danno da applicare

        # 2. Rimuove i bicchieri pendenti dalla lista attiva
        # (Filtriamo: teniamo solo quelli che NON sono nella lista pending)
        new_cup_state = [cup for cup in current_cups if cup not in pending_cups]

        # 3. Salva la nuova lista pulita
        setattr(match, state_col, json.dumps(new_cup_state))

        # 4. Resetta i contatori di danno pendente
        setattr(match, pending_list_col, '[]')
        setattr(match, pending_int_col, 0)
        
        db.session.commit()
    except Exception as e:
        print(f"Errore applying damage: {e}")

def count_shots_in_match(player_name, match_id):
    if not match_id: return 0
    dbsession, PlayerRecord = get_player_db_session(player_name)
    count = dbsession.query(PlayerRecord).filter_by(match_id=match_id).count()
    dbsession.close()
    return count

# ==========================================
#           LOGICA DI GIOCO (STATE TRACKING)
# ==========================================

def start_overtime(match):
    match.status = 'running'
    # Reset formato visuale a Singolo
    match.format_target_for_t1 = "Singolo Centrale"
    match.format_target_for_t2 = "Singolo Centrale"
    
    # Reimposta i bicchieri reali nel DB (Lista JSON con 1 bicchiere)
    init_cup_state(match, 't1', 'Singolo Centrale')
    init_cup_state(match, 't2', 'Singolo Centrale')
    
    # Reset contatori redenzione
    match.redemption_hits = 0 
    match.redemption_shots_left = 0
    db.session.commit()

def finish_match(match, winner):
    match.status = 'finished'
    match.end_time = datetime.now()
    
    # Reset per la prossima partita (Piramide completa)
    match.format_target_for_t1 = "Piramide"
    match.format_target_for_t2 = "Piramide"
    init_cup_state(match, 't1', 'Piramide')
    init_cup_state(match, 't2', 'Piramide')
    
    match.redemption_hits = 0
    match.t1_format_changed = False 
    match.t2_format_changed = False
    db.session.commit()

def update_game_state(match):
    """
    Questa funzione sincronizza i contatori numerici con le liste JSON
    e gestisce le regole di vittoria/redenzione specifiche.
    """
    if match.status == 'finished': return

    # 1. SINCRONIZZA NUMERI E LISTE (FONDAMENTALE)
    # Calcola quanti bicchieri sono rimasti contando gli elementi nelle liste JSON
    try:
        t1_list = json.loads(match.t1_cup_state)
        t2_list = json.loads(match.t2_cup_state)
        match.cups_target_for_t1 = len(t1_list)
        match.cups_target_for_t2 = len(t2_list)
    except:
        pass # Se c'è errore nei dati (es. DB vecchio), ignora

    # 2. LOGICA FASE NORMALE
    if match.status == 'running':
        # --- SQUADRA 1 ---
        if match.cups_target_for_t1 <= 0:
            # Se < 0: Vittoria Immediata T2 (Overkill)
            if match.cups_target_for_t1 < 0:
                finish_match(match, winner='t2')
            # Se == 0: Tiri Salvezza per T1
            else:
                match.status = 'redemption_t1'
                rimasti_avversari = match.cups_target_for_t2
                # Se manca 1 bicchiere -> 2 tiri, altrimenti pari ai bicchieri
                match.redemption_shots_left = 2 if rimasti_avversari == 1 else rimasti_avversari
                match.redemption_hits = 0

        # --- SQUADRA 2 ---
        elif match.cups_target_for_t2 <= 0:
            if match.cups_target_for_t2 < 0:
                finish_match(match, winner='t1')
            else:
                match.status = 'redemption_t2'
                rimasti_avversari = match.cups_target_for_t1
                match.redemption_shots_left = 2 if rimasti_avversari == 1 else rimasti_avversari
                match.redemption_hits = 0

    # 3. LOGICA TIRI SALVEZZA (REDENZIONE)
    elif match.status.startswith('redemption'):
        redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
        opponent_team = 't2' if redeeming_team == 't1' else 't1'
        
        # Bicchieri dell'avversario (quelli che chi recupera deve "colpire" virtualmente)
        opponent_cups_count = match.cups_target_for_t2 if redeeming_team == 't1' else match.cups_target_for_t1
        
        # Calcolo situazione: Bicchieri Avversari - Colpi Messi a Segno in redenzione
        virtual_remaining = opponent_cups_count - match.redemption_hits
        
        # CONTROLLO FINE TIRI
        if match.redemption_shots_left <= 0:
            
            # Caso A: Pareggio (0) -> Overtime 1vs1
            if virtual_remaining == 0:
                start_overtime(match)
            
            # Caso B: Sorpasso di 1 (-1) -> Inversione ruoli (2 tiri)
            elif virtual_remaining == -1:
                # Inverti chi deve salvarsi
                match.status = f'redemption_{opponent_team}'
                
                # Resettiamo i tiri a 2 per la nuova squadra in pericolo
                match.redemption_shots_left = 2
                match.redemption_hits = 0
                
            # Caso C: Sorpasso di 2 o più (<= -2) -> Vittoria Immediata chi recuperava
            elif virtual_remaining <= -2:
                finish_match(match, winner=redeeming_team)
            
            # Caso D: Non sufficiente (> 0) -> Vince l'avversario (chi aveva chiuso per primo)
            else:
                finish_match(match, winner=opponent_team)

    db.session.commit()


# ==========================================
#                 ROTTE
# ==========================================

@app.route('/')
def select_player():
    with app.app_context():
        # Migrazioni esistenti
        try: 
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE active_match ADD COLUMN redemption_hits INTEGER DEFAULT 0"))
        except: pass
        try: 
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE active_match ADD COLUMN t1_format_changed BOOLEAN DEFAULT 0"))
                conn.execute(text("ALTER TABLE active_match ADD COLUMN t2_format_changed BOOLEAN DEFAULT 0"))
        except: pass

        # --- NUOVE MIGRAZIONI PER LA GESTIONE DEI BICCHIERI PENDENTI ---
        try: 
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE active_match ADD COLUMN t1_pending_list TEXT DEFAULT '[]'"))
                conn.execute(text("ALTER TABLE active_match ADD COLUMN t2_pending_list TEXT DEFAULT '[]'"))
        except: pass
        # -----------------------------------------------------------------

    players = Player.query.order_by(Player.name).all()
    active_matches = ActiveMatch.query.all()
    matches_data = []; busy_players = []
    
    for m in active_matches:
        if m.status != 'finished':
            busy_players.extend([m.t1_p1, m.t1_p2, m.t2_p1, m.t2_p2])
        stats = {
            't1_p1': count_shots_in_match(m.t1_p1, m.id), 't1_p2': count_shots_in_match(m.t1_p2, m.id),
            't2_p1': count_shots_in_match(m.t2_p1, m.id), 't2_p2': count_shots_in_match(m.t2_p2, m.id),
        }
        matches_data.append({'match': m, 'stats': stats})
    return render_template('select_player.html', players=players, matches_data=matches_data, busy_players=busy_players)

@app.route('/setup_match', defaults={'match_id': None}, methods=['GET', 'POST'])
@app.route('/setup_match/<int:match_id>', methods=['GET', 'POST'])
def setup_match(match_id):
    match = None
    if match_id: match = ActiveMatch.query.get_or_404(match_id)
    
    query = ActiveMatch.query.filter(ActiveMatch.status != 'finished')
    if match_id: query = query.filter(ActiveMatch.id != match_id)
    busy_players = set([p for m in query.all() for p in [m.t1_p1, m.t1_p2, m.t2_p1, m.t2_p2]])

    if request.method == 'POST':
        mode = request.form.get('mode')
        if mode == 'singolo': return redirect(url_for('select_player'))
        
        t1_p1 = request.form.get('t1_p1'); t1_p2 = request.form.get('t1_p2')
        t2_p1 = request.form.get('t2_p1'); t2_p2 = request.form.get('t2_p2')
        match_name = request.form.get('match_name') or f"Tavolo {db.session.query(ActiveMatch).count() + 1}"
        
        players_list = [p for p in [t1_p1, t1_p2, t2_p1, t2_p2] if p]
        if len(players_list) != len(set(players_list)): return "Duplicati"
        for p in players_list:
            if p in busy_players: return f"{p} occupato"
            
        if match:
            # Modifica partita esistente
            match.match_name = match_name; match.t1_p1 = t1_p1; match.t1_p2 = t1_p2; match.t2_p1 = t2_p1; match.t2_p2 = t2_p2
        else:
            # --- MODIFICA QUI: Creazione Nuova Partita ---
            match = ActiveMatch(match_name=match_name, t1_p1=t1_p1, t1_p2=t1_p2, t2_p1=t2_p1, t2_p2=t2_p2, status='running')
            db.session.add(match)
            
        # 1. Salviamo la partita per avere l'ID
        db.session.commit()
        
        # 2. SE è una nuova partita (o se i bicchieri sono vuoti), INIZIALIZZIAMO I BICCHIERI
        if not match.t1_cup_state or match.t1_cup_state == '[]':
            init_cup_state(match, 't1', 'Piramide')
        if not match.t2_cup_state or match.t2_cup_state == '[]':
            init_cup_state(match, 't2', 'Piramide')
            
        return redirect(url_for('select_player'))
        
    players = Player.query.order_by(Player.name).all()
    return render_template('setup_match.html', players=players, match=match, busy_players=busy_players)

@app.route('/rematch/<int:match_id>')
def rematch(match_id):
    match = ActiveMatch.query.get_or_404(match_id)
    match.status = 'running'; match.start_time = datetime.now(); match.end_time = None
    match.cups_target_for_t1 = 6; match.cups_target_for_t2 = 6
    match.format_target_for_t1 = "Piramide"; match.format_target_for_t2 = "Piramide"
    match.pending_damage_for_t1 = 0; match.pending_damage_for_t2 = 0
    match.redemption_shots_left = 0; match.redemption_hits = 0
    match.t1_format_changed = False; match.t2_format_changed = False
    db.session.commit()
    return redirect(url_for('select_player'))

@app.route('/end_match/<int:match_id>')
def end_match(match_id):
    db.session.delete(ActiveMatch.query.get_or_404(match_id)); db.session.commit()
    return redirect(url_for('select_player'))

@app.route('/tracker/<player_name>')
def index(player_name):
    dbsession, PlayerRecord = get_player_db_session(player_name)
    records_obj = dbsession.query(PlayerRecord).order_by(PlayerRecord.id.desc()).all()
    clean_records = dati_tabella_from_records(records_obj)
    ultimo_record = dbsession.query(PlayerRecord).order_by(PlayerRecord.id.desc()).first()

    # Inizializzazione predefinita per modalità Singola/Senza Match
    defaults = {'numero_bicchieri': '6', 'formato': 'Piramide', 'postazione': '', 'bevanda': 'Birra', 'giocatore': player_name, 'my_formato': 'Piramide'}
    match, team = get_match_info(player_name)
    
    pending_damage_for_me = 0; pending_damage_for_them = 0
    match_status = None; redemption_info = None
    format_locked = False
    
    # Inizializzazione delle liste di bicchieri per garantire che siano sempre definite
    my_active_cups = CUP_DEFINITIONS['Piramide']
    opp_active_cups = CUP_DEFINITIONS['Piramide']
    my_cups_count = 6; opp_cups_count = 6

    if match:
        # ... (TUTTA LA TUA LOGICA ESISTENTE SOTTO match: )
        update_game_state(match) 

        match_status = match.status
        
        
        # --- Caricamento Liste JSON dal DB ---
        try:
            if team == 't1': 
                my_active_cups = json.loads(match.t1_cup_state) 
                opp_active_cups = json.loads(match.t2_cup_state) 
                
                defaults['my_formato'] = match.format_target_for_t1
                defaults['formato'] = match.format_target_for_t2
                format_locked = match.t1_format_changed
                
                # ... (resto della logica match) ...
            else: 
                my_active_cups = json.loads(match.t2_cup_state)
                opp_active_cups = json.loads(match.t1_cup_state)
                
                defaults['my_formato'] = match.format_target_for_t2
                defaults['formato'] = match.format_target_for_t1
                format_locked = match.t2_format_changed
            
            # Contiamo la lunghezza delle liste per i punteggi numerici
            my_cups_count = len(my_active_cups)
            opp_cups_count = len(opp_active_cups)
            
            # ... (Tutta la logica di pending_damage, redemption, postazione) ...
            if team == 't1': pending_damage_for_me = match.pending_damage_for_t1; pending_damage_for_them = match.pending_damage_for_t2
            else: pending_damage_for_me = match.pending_damage_for_t2; pending_damage_for_them = match.pending_damage_for_t1

        except Exception as e:
             # In caso di errore nel caricamento JSON, ricrea le liste
             print(f"Errore caricamento stato bicchieri: {e}")
             my_active_cups = CUP_DEFINITIONS.get(defaults['my_formato'], CUP_DEFINITIONS['Piramide'])
             opp_active_cups = CUP_DEFINITIONS.get(defaults['formato'], CUP_DEFINITIONS['Piramide'])
             my_cups_count = len(my_active_cups)
             opp_cups_count = len(opp_active_cups)


    # --- Aggiornamento defaults per l'HTML (sia con match che senza) ---
    display_opp_cups = str(opp_cups_count)
    if match and match.status.startswith('redemption'):
        is_my_team_redeeming = (match.status == f'redemption_{team}')
        redemption_info = {'active': True, 'shots_left': match.redemption_shots_left, 'is_me': is_my_team_redeeming}
        if is_my_team_redeeming:
            display_opp_cups = f"{opp_cups_count} - {match.redemption_hits}"

    defaults['numero_bicchieri'] = display_opp_cups
    
    # Inseriamo le liste nel dizionario defaults (QUESTO RISOLVE L'ERRORE JSON)
    defaults['opp_active_cups'] = opp_active_cups
    defaults['my_active_cups'] = my_active_cups

    # Postazione e bevanda (logica fuori da match)
    if ultimo_record:
        if not match: # Solo se non c'è match, altrimenti usa la logica del match
            defaults['postazione'] = ultimo_record.postazione; defaults['bevanda'] = ultimo_record.bevanda
            defaults['numero_bicchieri'] = str(ultimo_record.numero_bicchieri) # Riporta il numero vecchio
        elif player_name == match.t1_p1 or player_name == match.t2_p1: defaults['postazione'] = 'Sinistra'
        elif player_name == match.t1_p2 or player_name == match.t2_p2: defaults['postazione'] = 'Destra'
        if ultimo_record.bevanda: defaults['bevanda'] = ultimo_record.bevanda

    dbsession.close()
    
    teammate = ""
    if match:
        if team == 't1': teammate = match.t1_p2 if match.t1_p1 == player_name else match.t1_p1
        else: teammate = match.t2_p2 if match.t2_p1 == player_name else match.t2_p1

    return render_template('index.html', intestazioni=INTESTAZIONI, dati=clean_records,
                           titolo=f"Tracker - {player_name}", defaults=defaults, player_name=player_name,
                           is_match=bool(match), teammate=teammate, 
                           pending_damage=pending_damage_for_me, waiting_for_opponent=pending_damage_for_them, 
                           match_status=match_status, redemption_info=redemption_info,
                           my_cups=my_cups_count, opp_cups=opp_cups_count, format_locked=format_locked)

@app.route('/force_update/<player_name>', methods=['POST'])
def force_update(player_name):
    match, team = get_match_info(player_name)
    if match and match.status == 'running':
        # Se io (player_name) premo SCALA, voglio che i danni che IO ho inflitto
        # (che sono pendenti su opponent_team) vengano applicati subito.
        opponent_team = 't2' if team == 't1' else 't1'
        
        apply_pending_damage(match, opponent_team)
        
        update_game_state(match)
        db.session.commit()
    return redirect(url_for('index', player_name=player_name))

@app.route('/add/<player_name>', methods=['POST'])
def add_record(player_name):
    dbsession, PlayerRecord = get_player_db_session(player_name)
    match, team = get_match_info(player_name)
    MULTIPLIER_MAP = {'Doppio': 2, 'Triplo': 3, 'Quadruplo': 4, 'Quintuplo': 5, 'Sestuplo': 6}

    submitted_format = request.form.get('formato')
    final_format = submitted_format 

    # --- GESTIONE CAMBIO FORMATO (Se necessario) ---
    if match:
        target_format_db = match.format_target_for_t2 if team == 't1' else match.format_target_for_t1
        if submitted_format and submitted_format != target_format_db:
            already_changed = match.t1_format_changed if team == 't1' else match.t2_format_changed
            if not already_changed:
                if team == 't1':
                    match.format_target_for_t2 = submitted_format; match.t1_format_changed = True
                    # Re-inizializza i bicchieri per il nuovo formato!
                    init_cup_state(match, 't2', submitted_format) 
                else:
                    match.format_target_for_t1 = submitted_format; match.t2_format_changed = True
                    init_cup_state(match, 't1', submitted_format)
                db.session.commit()
            else:
                # Se il formato è già stato cambiato (bloccato), usiamo quello del DB.
                final_format = target_format_db
    
    # --- LOGICA APPLICAZIONE/ACCUMULO DANNI ---
    res = request.form['risultato_tiro']
    hit_list = [] # Lista bicchieri colpiti

    if match:
        # 1. APPLICA I DANNI PENDENTI SU DI ME (È il mio turno, quindi il turno avversario precedente è finito)
        # Questo fa sparire i bicchieri che l'avversario aveva segnato nel suo ultimo tiro.
        apply_pending_damage(match, team)

        # 2. GESTIONE DEL MIO TIRO (Se ho fatto centro)
        if res == 'Centro':
            hit_list = request.form.getlist('bicchiere_colpito')
            
            if match.status.startswith('redemption'):
                 # IN REDEMPTION: il danno viene gestito dai contatori numerici (hits)
                 redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
                 if team == redeeming_team:
                     match.redemption_hits += len(hit_list)
                     match.redemption_shots_left -= 1
            else:
                # FASE NORMALE: ACCUMULO DANNO PENDENTE AGLI AVVERSARI
                opponent_team = 't2' if team == 't1' else 't1'
                
                # Colonne dell'avversario
                opp_pending_list_col = f'{opponent_team}_pending_list'
                opp_pending_int_col = f'pending_damage_for_{opponent_team}'

                # Carica lista pendente attuale, aggiungi i nuovi, salva
                try:
                    current_pending = json.loads(getattr(match, opp_pending_list_col))
                    
                    for h in hit_list:
                        # Controlliamo anche che il bicchiere non sia già stato rimosso
                        if h not in current_pending:
                            current_pending.append(h)
                    
                    setattr(match, opp_pending_list_col, json.dumps(current_pending))
                    
                    # Aggiorna anche l'intero (per il messaggio "Togli N bicchieri")
                    # Qui non sommiamo i bicchieri della hit_list, ma calcoliamo la lunghezza della pending_list
                    setattr(match, opp_pending_int_col, len(current_pending)) 
                except:
                    pass

        # 3. GESTIONE TIRI SALVEZZA SU MISS/BORDO (Logica esistente per la redenzione)
        if match.status.startswith('redemption'):
            redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
            if team == redeeming_team and res != 'Centro':
                match.redemption_shots_left -= 1
        
        # 4. Sincronizzazione finale
        update_game_state(match)
        db.session.commit()

    # --- SALVATAGGIO STORICO (RECORD) ---
    hit_str = ", ".join(hit_list) if res == "Centro" else "N/A"
    post = request.form.get('postazione')
    if not post and match: post = 'Sinistra' if player_name in [match.t1_p1, match.t2_p1] else 'Destra'

    curr_my_cups = 0; curr_opp_cups = 0
    if match:
        try:
            t1_c = len(json.loads(match.t1_cup_state)); t2_c = len(json.loads(match.t2_cup_state))
            if team == 't1': curr_my_cups = t1_c; curr_opp_cups = t2_c
            else: curr_my_cups = t2_c; curr_opp_cups = t1_c
        except: pass

    adesso = datetime.now()
    # Utilizziamo il conteggio dei bicchieri avversari ATTIVI (quelli ancora sul tavolo)
    req_cups = str(curr_opp_cups)
    
    new_rec = PlayerRecord(
        match_id=match.id if match else None,
        miss=("Sì" if res=="Miss" else "No"), bordo=("Sì" if res=="Bordo" else "No"), centro=("Sì" if res=="Centro" else "No"),
        cups_own=curr_my_cups, cups_opp=curr_opp_cups,
        # Nota: bicchiere_colpito e numero_bicchieri nello storico riflettono la situazione
        numero_bicchieri=req_cups, bicchiere_colpito=hit_str, formato=final_format,
        tiro_salvezza=('Sì' if 'tiro_salvezza' in request.form else 'No'), postazione=post, bevanda=request.form['bevanda'].strip().capitalize(), 
        giocatore=player_name, bicchieri_multipli=request.form.get('bicchieri_multipli'), 
        data=adesso.strftime("%d/%m/%Y"), ora=adesso.strftime("%H:%M"), note=request.form['note']
    )
    dbsession.add(new_rec); dbsession.commit(); dbsession.close()
    
    return redirect(url_for('index', player_name=player_name))

@app.route('/edit/<player_name>/<int:id>', methods=['GET', 'POST'])
def edit_record(player_name, id):
    dbsession, PlayerRecord = get_player_db_session(player_name)
    record = dbsession.query(PlayerRecord).get(id)
    if not record: dbsession.close(); abort(404)
    
    match, team = get_match_info(player_name)

    if request.method == 'POST':
        # --- FASE 1: UNDO (Annulla l'effetto del vecchio tiro) ---
        if match and match.status != 'finished' and record.centro == 'Sì':
            try:
                old_cups = [c.strip() for c in record.bicchiere_colpito.split(',')]
                target_col = 't2_cup_state' if team == 't1' else 't1_cup_state'
                current_list = json.loads(getattr(match, target_col))
                
                # Rimettiamo i vecchi bicchieri
                for c in old_cups:
                    if c not in current_list: current_list.append(c)
                
                setattr(match, target_col, json.dumps(current_list))
                
                # Correzione redemption
                if match.status.startswith('redemption'):
                     redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
                     if team == redeeming_team:
                         match.redemption_hits -= len(old_cups)
                         match.redemption_shots_left += 1
            except: pass

        # --- FASE 2: UPDATE (Aggiorna i dati del record) ---
        res = request.form['risultato_tiro']
        record.miss = "Sì" if res=="Miss" else "No"
        record.bordo = "Sì" if res=="Bordo" else "No"
        record.centro = "Sì" if res=="Centro" else "No"
        record.numero_bicchieri = request.form['numero_bicchieri']
        record.formato = request.form['formato']
        record.tiro_salvezza = 'Sì' if 'tiro_salvezza' in request.form else 'No'
        record.bevanda = request.form['bevanda'].strip().capitalize()
        record.bicchieri_multipli = request.form.get('bicchieri_multipli')
        record.note = request.form['note']
        
        hit_list = []
        if res == "Centro":
            hit_list = request.form.getlist('bicchiere_colpito')
            record.bicchiere_colpito = ", ".join(hit_list)
        else:
            record.bicchiere_colpito = "N/A"

        # --- FASE 3: REDO (Applica il nuovo tiro al campo) ---
        if match and match.status != 'finished' and res == 'Centro':
            try:
                target_col = 't2_cup_state' if team == 't1' else 't1_cup_state'
                # Rileggiamo la lista (che ora contiene i bicchieri ripristinati nella FASE 1)
                current_list = json.loads(getattr(match, target_col))
                
                # Togliamo i NUOVI bicchieri colpiti
                updated_list = [c for c in current_list if c not in hit_list]
                setattr(match, target_col, json.dumps(updated_list))
                
                # Riapplica redemption
                if match.status.startswith('redemption'):
                     redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
                     if team == redeeming_team:
                         match.redemption_hits += len(hit_list)
                         match.redemption_shots_left -= 1
            except: pass

        # Sincronizza tutto (punteggi numerici, vittorie, ecc)
        if match: update_game_state(match)

        dbsession.commit(); dbsession.close()
        return redirect(url_for('index', player_name=player_name))
        
    return render_template('edit_record.html', record=record, player_name=player_name)

@app.route('/delete/<player_name>/<int:id>', methods=['POST'])
def delete_record(player_name, id):
    dbsession, PlayerRecord = get_player_db_session(player_name)
    r = dbsession.query(PlayerRecord).get(id)
    
    if r:
        match, team = get_match_info(player_name)
        
        # Se era una partita in corso ed era un CENTRO, dobbiamo ripristinare i bicchieri colpiti
        if match and match.status != 'finished' and r.centro == 'Sì':
            try:
                # 1. Capiamo quali bicchieri erano stati tolti (es. "3 Sx, 2 Dx")
                cups_to_restore = [c.strip() for c in r.bicchiere_colpito.split(',')]
                
                # 2. Capiamo a chi ridarli (se sono T1, ridoy i bicchieri a T2)
                target_col = 't2_cup_state' if team == 't1' else 't1_cup_state'
                current_cups = json.loads(getattr(match, target_col))
                
                # 3. Li riaggiungiamo alla lista se non ci sono già
                for cup in cups_to_restore:
                    if cup not in current_cups:
                        current_cups.append(cup)
                
                # 4. Salviamo e aggiorniamo il conteggio
                setattr(match, target_col, json.dumps(current_cups))
                update_game_state(match)
                
                # Se eravamo in redemption, annulliamo i colpi conteggiati
                if match.status.startswith('redemption'):
                    redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
                    if team == redeeming_team:
                        match.redemption_hits -= len(cups_to_restore)
                        match.redemption_shots_left += 1

            except Exception as e:
                print(f"Errore ripristino bicchieri: {e}")

        dbsession.delete(r)
        dbsession.commit()
    
    dbsession.close()
    return redirect(url_for('index', player_name=player_name))

@app.route('/players')
def manage_players(): return render_template('players.html', players=Player.query.order_by(Player.name).all())

@app.route('/add_player', methods=['POST'])
def add_player():
    pn = request.form['player_name'].strip()
    if pn and not Player.query.filter_by(name=pn).first(): db.session.add(Player(name=pn)); db.session.commit()
    return redirect(url_for('manage_players'))

@app.route('/delete_player/<int:id>', methods=['POST'])
def delete_player(id): 
    db.session.delete(Player.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('manage_players'))

@app.route('/database-viewer')
def database_viewer():
    all_db_content = {}
    if os.path.exists(DATA_FOLDER):
        for filename in os.listdir(DATA_FOLDER):
            if filename.endswith(".db"):
                filepath = os.path.join(DATA_FOLDER, filename)
                try:
                    conn = sqlite3.connect(filepath); cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall(); file_data = {}
                    for t in tables:
                        tn = t[0]
                        if tn.startswith('sqlite_'): continue
                        cursor.execute(f"SELECT * FROM {tn}")
                        rows = cursor.fetchall()
                        col_names = [d[0] for d in cursor.description]
                        file_data[tn] = {'cols': col_names, 'rows': rows}
                    conn.close(); all_db_content[filename] = file_data
                except Exception as e: all_db_content[filename] = {'Err': {'cols': ['E'], 'rows': [[str(e)]]}}
    return render_template('admin_db.html', full_db=all_db_content)

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)