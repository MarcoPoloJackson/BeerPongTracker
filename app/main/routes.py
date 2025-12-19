from flask import render_template, request, flash, redirect, url_for, session, abort, current_app
from app.main import bp
from app.models import db, Player, ActiveMatch, PlayerRecord, CUP_DEFINITIONS
from datetime import datetime, timedelta
from itertools import groupby
import json
from app import socketio

# ==========================================
#        HELPER FUNCTIONS (Ricostruite)
# ==========================================

def get_match_info(player_name):
    """
    Cerca se il giocatore è in una partita attiva e ritorna (match, team).
    Team è 't1' o 't2'.
    """
    matches = ActiveMatch.query.filter(ActiveMatch.status != 'finished').all()
    for m in matches:
        if player_name in [m.t1_p1, m.t1_p2]:
            return m, 't1'
        if player_name in [m.t2_p1, m.t2_p2]:
            return m, 't2'
    return None, None

# Incolla questo all'inizio di routes.py, dopo gli import

def count_cups(json_str):
    """Conta i bicchieri attivi da una stringa JSON."""
    try:
        if not json_str: return 0
        data = json.loads(json_str)
        return len(data) if isinstance(data, list) else 0
    except:
        return 0

# Cerca la funzione start_overtime e modificala così:

def start_overtime(match):
    """Reset e avvio dell'Overtime."""
    match.status = 'running'
    match.mode = 'overtime'  # Fondamentale
    
    match.format_target_for_t1 = "Singolo Centrale" # O "Triangolo Piccolo", come preferisci
    match.format_target_for_t2 = "Singolo Centrale"
    
    # Reset liste bicchieri
    match.t1_cup_state = json.dumps(["Singolo"]) # O bicchieri dell'overtime
    match.t2_cup_state = json.dumps(["Singolo"])
    
    match.t1_pending_list = '[]'
    match.t2_pending_list = '[]'
    match.pending_damage_for_t1 = 0
    match.pending_damage_for_t2 = 0
    match.redemption_hits = 0
    match.redemption_shots_left = 0
    match.t1_format_changed = True
    match.t2_format_changed = True
    
    # --- AGGIUNTA FONDAMENTALE PER ANIMAZIONE ---
    # Questo flag dice al template: "È appena iniziato l'overtime, fai il FLASH!"
    session['animazione_overtime_start'] = True 
    
    db.session.commit()

# --- AGGIORNA ANCHE QUESTA PER RESETTARE QUANDO RIGIOCHI ---
@bp.route('/rematch/<int:match_id>')
def rematch(match_id):
    match = ActiveMatch.query.get_or_404(match_id)
    
    # 1. Reset completo parametri
    match.status = 'running'
    match.mode = 'squadre' # <--- IMPORTANTISSIMO: Resetta la modalità
    
    match.start_time = datetime.now()
    match.end_time = None
    match.winning_team = None
    
    match.redemption_shots_left = 0
    match.redemption_hits = 0
    
    match.format_target_for_t1 = "Piramide"
    match.format_target_for_t2 = "Piramide"
    match.t1_format_changed = False
    match.t2_format_changed = False
    
    match.t1_pending_list = '[]'
    match.t2_pending_list = '[]'
    match.pending_damage_for_t1 = 0
    match.pending_damage_for_t2 = 0

    init_cup_state(match, 't1', 'Piramide')
    init_cup_state(match, 't2', 'Piramide')

    db.session.commit()
    
    return redirect(url_for('main.setup_match', match_id=match_id))

def finish_match(match, winner):
    """
    Registra la fine della partita e il vincitore.
    NON resetta i bicchieri qui, per permettere di vedere il risultato finale.
    """
    match.status = 'finished'
    match.end_time = datetime.now()
    match.winning_team = winner
    
    # Salviamo solo lo stato finale. 
    # Il reset avverrà nella funzione 'rematch' o creando una nuova partita.
    db.session.commit()


@bp.route('/rematch_create/<int:old_match_id>')
def rematch_create(old_match_id):
    # 1. Prendi la vecchia partita
    old_match = ActiveMatch.query.get_or_404(old_match_id)
    
    # 2. Pulisci il nome (se si chiamava già "Rematch: Tavolo 1", resta "Rematch: Tavolo 1")
    base_name = old_match.match_name.replace("Rematch: ", "")
    
    # 3. Crea una NUOVA partita (Nuovo ID) copiando i giocatori
    new_match = ActiveMatch(
        match_name=f"Rematch: {base_name}",
        status='running',
        start_time=datetime.now(),
        mode=old_match.mode,
        
        # Copia i giocatori identici
        t1_p1=old_match.t1_p1, t1_p2=old_match.t1_p2,
        t2_p1=old_match.t2_p1, t2_p2=old_match.t2_p2,
        
        # Imposta tutto a zero/default
        format_target_for_t1="Piramide",
        format_target_for_t2="Piramide",
        t1_pending_list='[]', t2_pending_list='[]',
        pending_damage_for_t1=0, pending_damage_for_t2=0,
        redemption_shots_left=0, redemption_hits=0,
        t1_format_changed=False, t2_format_changed=False
    )
    
    # 4. Salva la nuova partita nel DB
    db.session.add(new_match)
    
    # 5. Inizializza i bicchieri
    init_cup_state(new_match, 't1', 'Piramide')
    init_cup_state(new_match, 't2', 'Piramide')
    
    db.session.commit()
    
    # 6. Torna alla Home (così vedi la nuova partita in cima alla lista LIVE)
    return redirect(url_for('main.select_player'))


def count_shots_in_match(player_name, match_id):
    if not player_name: return 0
    player = Player.query.filter_by(name=player_name).first()
    if not player: return 0
    return PlayerRecord.query.filter_by(match_id=match_id, player_id=player.id).count()

def init_cup_state(match, team, format_name):
    full_set = CUP_DEFINITIONS.get(format_name, [])
    if team == 't1':
        match.t1_cup_state = json.dumps(full_set)
    else:
        match.t2_cup_state = json.dumps(full_set)

def update_game_state(match):
    """
    Gestisce le regole di vittoria, sconfitta, overtime e ribaltone.
    Calcola lo stato includendo i danni pendenti per una reattività immediata.
    """
    if not match: return
    if match.status == 'finished': return

    try:
        # Carichiamo gli stati attuali
        t1_active = json.loads(match.t1_cup_state)
        t2_active = json.loads(match.t2_cup_state)
        
        # Carichiamo i danni pendenti (colpi andati a segno ma non ancora "tolti")
        t1_pending = json.loads(match.t1_pending_list)
        t2_pending = json.loads(match.t2_pending_list)

        # --- CALCOLO "VITA REALE" (Attivi - Colpiti in attesa) ---
        # Questo è il trucco: sottraiamo i pendenti per vedere se la squadra è "morta"
        t1_live_count = len(t1_active) - len(t1_pending)
        t2_live_count = len(t2_active) - len(t2_pending)
        
        # Aggiorna contatori interi per query veloci (opzionale, per visualizzazione)
        match.cups_target_for_t1 = t1_live_count
        match.cups_target_for_t2 = t2_live_count

        # 1. LOGICA DELLA FASE NORMALE
        if match.status == 'running':
            # Se T1 finisce i bicchieri (contando anche quelli appena colpiti)
            if t1_live_count <= 0:
                match.status = 'redemption_t1'
                rimasti_avv = t2_live_count
                match.redemption_shots_left = 2 if rimasti_avv == 1 else rimasti_avv
                match.redemption_hits = 0 
            
            elif t2_live_count <= 0:
                match.status = 'redemption_t2'
                rimasti_avv = t1_live_count
                match.redemption_shots_left = 2 if rimasti_avv == 1 else rimasti_avv
                match.redemption_hits = 0 

        # 2. LOGICA DELLA FASE REDEMPTION
        elif match.status.startswith('redemption'):
            redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
            opponent_team = 't2' if redeeming_team == 't1' else 't1'
            
            # Recuperiamo i bicchieri della squadra che sta redimendo (quella a 0 o -1)
            redeeming_team_cups = t1_live_count if redeeming_team == 't1' else t2_live_count
            
            # Recuperiamo i bicchieri dell'avversario (il target da pareggiare)
            target_balance = t2_live_count if redeeming_team == 't1' else t1_live_count
            
            # --- [NUOVO] CHECK VITTORIA IMMEDIATA(Prima era in "running", ma ora "redemption" si attiva subito, quindi
            # è stato spostato qua
            if redeeming_team_cups <= -1:
                finish_match(match, winner=opponent_team)
                return
            
            # --- A. CONTROLLO VITTORIA SCHIACCIANTE (< -1) ---
            if target_balance < -1:
                finish_match(match, winner=redeeming_team)
                return

            # --- B. CONTROLLO TIRI FINITI ---
            # Solo se ho finito i tiri controllo il risultato
            if match.redemption_shots_left <= 0:
                
                # Caso Pareggio -> OVERTIME
                if target_balance == 0:
                    start_overtime(match)
                
                # Caso Perso
                elif target_balance > 0:
                    finish_match(match, winner=opponent_team)
                
                # Caso Ribaltone (-1 esatto)
                elif target_balance == -1: 
                   match.status = f'redemption_{opponent_team}'
                   match.redemption_shots_left = 2 
                   match.redemption_hits = 0
                   # Reset immediato delle liste dell'altra squadra
                   # Qui puliamo tutto perché inizia un nuovo "turno" di redenzione inversa
                   if redeeming_team == 't1': 
                       match.t2_cup_state = '[]'; match.t2_pending_list = '[]'
                   else: 
                       match.t1_cup_state = '[]'; match.t1_pending_list = '[]'

    except Exception as e:
        print(f"Errore update_game_state: {e}")
            

    except Exception as e:
        print(f"Errore update_game_state: {e}")

def apply_pending_damage(match, target_team):
    """
    Applica i danni pendenti rimuovendo i bicchieri dalla lista attiva.
    """
    if not match: return

    # --- LOGICA CORRETTA ---
    # Dobbiamo capire se 'target_team' è la squadra che sta cercando di salvarsi (Redemption)
    # o se è la squadra che sta vincendo.
    
    # Se siamo in Redemption:
    if match.status.startswith('redemption'):
        redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
        
        # Se stiamo cercando di applicare danni alla squadra che sta VINCENDO (l'avversario di chi redime),
        # ALLORA ci fermiamo. Perché quei colpi sono i tiri di salvezza, e non devono sparire visivamente
        # finché non vediamo se il pareggio riesce.
        if target_team != redeeming_team:
            return

        # SE INVECE target_team == redeeming_team (chi sta perdendo),
        # significa che ci sono ancora dei pending vecchi che devono essere rimossi 
        # (es. l'ultimo colpo che li ha mandati in redemption).
        # Quindi lasciamo che il codice prosegua e li rimuova.

    # --- FINE LOGICA CORRETTA ---

    # Selezione dinamica delle colonne
    target_state_col = 't1_cup_state' if target_team == 't1' else 't2_cup_state'
    target_pending_col = 't1_pending_list' if target_team == 't1' else 't2_pending_list'
    target_int_col = 'pending_damage_for_t1' if target_team == 't1' else 'pending_damage_for_t2'
    
    try:
        current_state = json.loads(getattr(match, target_state_col))
        pending_list = json.loads(getattr(match, target_pending_col))

        if not pending_list: return

        # Rimuove i bicchieri
        new_state = [c for c in current_state if c not in pending_list]
        
        setattr(match, target_state_col, json.dumps(new_state))
        setattr(match, target_pending_col, '[]')
        setattr(match, target_int_col, 0)
        
    except Exception as e:
        print(f"Errore apply_pending_damage: {e}")
        print(f"Errore apply_pending_damage: {e}")


# ==========================================
#                 ROUTES
# ==========================================

def get_score_points(match):
    """
    Calcola i punti totali (Bicchieri affondati) analizzando i tiri.
    Supporta:
    - Multihits (Doppi/Tripli contano 2/3 punti)
    - Overtime e Redemption (vengono contati nel totale)
    """
    try:
        score_t1 = 0
        score_t2 = 0
        
        # 1. Recuperiamo gli ID dei giocatori delle due squadre
        t1_names = [n for n in [match.t1_p1, match.t1_p2] if n]
        t2_names = [n for n in [match.t2_p1, match.t2_p2] if n]
        
        t1_ids = [p.id for p in Player.query.filter(Player.name.in_(t1_names)).all()]
        t2_ids = [p.id for p in Player.query.filter(Player.name.in_(t2_names)).all()]

        # 2. Prendiamo TUTTI i tiri andati a segno (Centro) di questa partita
        hits = PlayerRecord.query.filter(
            PlayerRecord.match_id == match.id,
            PlayerRecord.centro == 'Sì'
        ).all()

        for record in hits:
            # --- CALCOLO VALORE DEL TIRO ---
            points = 1 # Default: vale almeno 1
            
            if record.bicchiere_colpito:
                # Esempio stringa: "3 Cen, 2 Dx" -> Dividiamo per virgola
                # Esempio lista: ["3 Cen", "2 Dx"] -> Lunghezza 2
                cups_hit_list = [c for c in record.bicchiere_colpito.split(',') if c.strip()]
                
                if len(cups_hit_list) > 1:
                    points = len(cups_hit_list) # Vale 2, 3, ecc.
            
            # --- ASSEGNAZIONE PUNTI ---
            if record.player_id in t1_ids:
                score_t1 += points
            elif record.player_id in t2_ids:
                score_t2 += points
                
        return score_t1, score_t2

    except Exception as e:
        print(f"Errore calcolo punteggio avanzato: {e}")
        return 0, 0


# --- SOSTITUISCI LA ROTTA "select_player" CON QUESTA ---

@bp.route('/')
def select_player():
    # 1. PARTITE ATTIVE
    active_matches = ActiveMatch.query.filter(ActiveMatch.status != 'finished').all()
    
    matches_data = []
    busy_players = []

    for m in active_matches:
        busy_players.extend([m.t1_p1, m.t1_p2, m.t2_p1, m.t2_p2])
        
        # CALCOLO PUNTEGGIO (Punti Fatti)
        s1, s2 = get_score_points(m)
        
        stats = {
            't1_p1': count_shots_in_match(m.t1_p1, m.id),
            't1_p2': count_shots_in_match(m.t1_p2, m.id),
            't2_p1': count_shots_in_match(m.t2_p1, m.id),
            't2_p2': count_shots_in_match(m.t2_p2, m.id),
        }
        matches_data.append({
            'match': m, 
            'stats': stats, 
            'score_t1': s1, 
            'score_t2': s2
        })

    # 2. STORICO 24H (PARTITE FINITE)
    last_24h = datetime.now() - timedelta(hours=24)
    finished_matches = ActiveMatch.query.filter(
        ActiveMatch.status == 'finished',
        ActiveMatch.end_time >= last_24h
    ).all()

    # Logica Raggruppamento (Identica a prima)
    def get_match_key(m):
        t1 = sorted([p for p in [m.t1_p1, m.t1_p2] if p])
        t1_str = " & ".join(t1)
        t2 = sorted([p for p in [m.t2_p1, m.t2_p2] if p])
        t2_str = " & ".join(t2)
        return " VS ".join(sorted([t1_str, t2_str]))

    finished_matches.sort(key=get_match_key)
    
    grouped_history = {}
    
    for key, group in groupby(finished_matches, key=get_match_key):
        match_list = list(group)
        match_list.sort(key=lambda x: x.end_time if x.end_time else datetime.min, reverse=True)
        
        processed_matches = []
        for m in match_list:
            # CALCOLO PUNTEGGIO (Punti Fatti) ANCHE PER STORICO
            s1, s2 = get_score_points(m)
            
            winner = m.winning_team if m.winning_team else 'draw'
            
            processed_matches.append({
                'obj': m,
                't1_score': s1,
                't2_score': s2,
                'winner': winner,
                'time_ago': m.end_time.strftime("%H:%M") if m.end_time else "--:--"
            })
            
        grouped_history[key] = processed_matches

    players = Player.query.order_by(Player.name).all()

    return render_template('home.html', 
                           matches_data=matches_data, 
                           grouped_history=grouped_history,
                           players=players,
                           busy_players=busy_players)


@bp.route('/setup_match', defaults={'match_id': None}, methods=['GET', 'POST'])
@bp.route('/setup_match/<int:match_id>', methods=['GET', 'POST'])
def setup_match(match_id):
    match = None
    if match_id: match = ActiveMatch.query.get_or_404(match_id)

    # Calcolo giocatori occupati
    query = ActiveMatch.query.filter(ActiveMatch.status != 'finished')
    if match_id: query = query.filter(ActiveMatch.id != match_id)
    busy_players = set([p for m in query.all() for p in [m.t1_p1, m.t1_p2, m.t2_p1, m.t2_p2] if p])

    if request.method == 'POST':
        t1_p1 = request.form.get('t1_p1'); t1_p2 = request.form.get('t1_p2')
        t2_p1 = request.form.get('t2_p1'); t2_p2 = request.form.get('t2_p2')
        match_name = request.form.get('match_name') or f"Tavolo {ActiveMatch.query.count() + 1}"

        players_list = [p for p in [t1_p1, t1_p2, t2_p1, t2_p2] if p]
        if len(players_list) != len(set(players_list)): return "Duplicati"
        
        # Creazione o Aggiornamento Match
        if match:
            match.match_name = match_name
            match.t1_p1 = t1_p1; match.t1_p2 = t1_p2
            match.t2_p1 = t2_p1; match.t2_p2 = t2_p2
        else:
            match = ActiveMatch(match_name=match_name, t1_p1=t1_p1, t1_p2=t1_p2, t2_p1=t2_p1, t2_p2=t2_p2,
                                status='running')
            db.session.add(match)
            # Inizializza bicchieri
            init_cup_state(match, 't1', 'Piramide')
            init_cup_state(match, 't2', 'Piramide')

        db.session.commit()
        return redirect(url_for('main.select_player'))

    players = Player.query.order_by(Player.name).all()
    return render_template('setup_match.html', players=players, match=match, busy_players=busy_players)


@bp.route('/tracker/<player_name>')
def index(player_name):
    # 1. Trova giocatore
    player = Player.query.filter_by(name=player_name).first()
    if not player: return "Giocatore non trovato", 404

    # 2. Trova partita e team
    match, team = get_match_info(player_name)
    
    # --- RECUPERO PARTITA FINITA ---
    if not match:
        last_match = ActiveMatch.query.filter(
            ActiveMatch.status == 'finished',
            (ActiveMatch.t1_p1 == player.name) | (ActiveMatch.t1_p2 == player.name) |
            (ActiveMatch.t2_p1 == player.name) | (ActiveMatch.t2_p2 == player.name)
        ).order_by(ActiveMatch.id.desc()).first()
        
        if last_match:
            match = last_match
            if player.name in [match.t1_p1, match.t1_p2]:
                team = 't1'
            else:
                team = 't2'
    # -----------------------------

    # 3. Recupera storico records
    match_id_filter = match.id if match else None
    records_obj = PlayerRecord.query.filter_by(player_id=player.id).order_by(PlayerRecord.id.desc())
    if match_id_filter:
        records_obj = records_obj.filter_by(match_id=match_id_filter)
    records_obj = records_obj.all()
    
    clean_records = []
    for r in records_obj:
        clean_records.append({
            'ID': r.id, 'Miss': r.miss, 'Bordo': r.bordo, 'Centro': r.centro,
            'Noi': r.cups_own, 'Loro': r.cups_opp, 'Colpiti': r.bicchiere_colpito,
            'Data': r.timestamp.strftime("%H:%M") if r.timestamp else "-", 
            'Note': r.note, 'Multipli': r.bicchieri_multipli,
            'Posizione': r.postazione, 'Bevanda': r.bevanda, 'Salvezza': r.tiro_salvezza
        })

    ultimo_record = records_obj[0] if records_obj else None

    # 4. Defaults
    defaults = {
        'numero_bicchieri': '6', 'formato': 'Piramide', 'postazione': '', 'bevanda': 'Birra',
        'giocatore': player_name, 'my_formato': 'Piramide', 'match_id': 0,
        'opp_active_cups': [], 'my_active_cups': [],
        'opp_pending_cups': [], 'my_pending_cups': []
    }
    
    pending_damage_for_me = 0
    pending_damage_for_them = 0
    match_status = None
    redemption_info = None
    game_result = None
    format_locked = False
    match_score_diff = 0
    diff_real_life = 0 # Da controllare se giusto

    # 5. Logica Principale
    # 5. Logica Principale
    if match:
        defaults['match_id'] = match.id

        update_game_state(match) 
        db.session.commit()

        match_status = match.status

        # --- FIX OVERTIME VISUALIZZAZIONE ---
        # Se la logica è "running" ma siamo in modalità "overtime",
        # diciamo al frontend che è "overtime" così mostra la grafica.
        if match.status == 'running' and match.mode == 'overtime':
            match_status = 'overtime'


        try:
            if team == 't1':
                my_active_list = json.loads(match.t1_cup_state)
                opp_active_list = json.loads(match.t2_cup_state)
                opp_pending_list = json.loads(match.t2_pending_list)
                my_pending_list = json.loads(match.t1_pending_list)
                defaults['my_formato'] = match.format_target_for_t1
                defaults['formato'] = match.format_target_for_t2
                format_locked = match.t1_format_changed 
                pending_damage_for_me = match.pending_damage_for_t1
                pending_damage_for_them = match.pending_damage_for_t2
            else:
                my_active_list = json.loads(match.t2_cup_state)
                opp_active_list = json.loads(match.t1_cup_state)
                opp_pending_list = json.loads(match.t1_pending_list)
                my_pending_list = json.loads(match.t2_pending_list)
                defaults['my_formato'] = match.format_target_for_t2
                defaults['formato'] = match.format_target_for_t1
                format_locked = match.t2_format_changed
                pending_damage_for_me = match.pending_damage_for_t2
                pending_damage_for_them = match.pending_damage_for_t1
        except:
            my_active_list = []; opp_active_list = []; opp_pending_list = []; my_pending_list = []

        defaults['my_active_cups'] = my_active_list
        defaults['opp_active_cups'] = opp_active_list
        defaults['my_pending_cups'] = my_pending_list
        defaults['opp_pending_cups'] = opp_pending_list


        # === GESTIONE RISULTATO E RETE DI SICUREZZA ===
        
        opp_real_life = len(opp_active_list) - len(opp_pending_list)
        my_real_life = len(my_active_list) - len(my_pending_list)
        diff_real_life = my_real_life - opp_real_life

        fe_risultato_partita=""
        
        # 1. Partita ufficialmente finita
        if match.status == 'finished':
            if not match.winning_team:
                match.winning_team = (
                    None if diff_real_life == 0 # Pareggio
                    else team if diff_real_life > 0 # Vittoria
                    else ('t2' if team == 't1' else 't1')) # Sconfitta

            game_result = (
                'draw' if diff_real_life == 0 # Pareggio
                else 'win' if match.winning_team == team # Vittoria
                else 'loss') # Sconfitta


        # 2. RETE DI SICUREZZA INTELLIGENTE
        # Interviene solo se il DB non ha ancora segnato 'finished' ma i conti dicono altro
        elif opp_real_life <= -1:
             
             # CASO A: SIAMO IN RUNNING
             # Se porto a -1 in running, inizia la redemption, non ho ancora vinto.
             if match.status == 'running':
                game_result = 'win'
                match_status = 'finished'
                # Front end Visualizzazione Fine Partita
                fe_risultato_partita = "VITTORIA ASSICURATA"
                

             # CASO B: SIAMO IN REDEMPTION
             elif match.status.startswith('redemption'):
                 # Capiamo chi sta tirando
                 is_my_team_redeeming = (match.status == f'redemption_{team}')
                 
                 if is_my_team_redeeming:
                     # Sono io che cerco di salvarmi.
                     # Se vado a -1 esatto -> RIBALTONE (Non è vittoria, si continua a giocare)
                     # Se vado a < -1 (es. -2) -> VITTORIA SCHIACCIANTE
                     if opp_real_life < -1:
                         game_result = 'win'
                         match_status = 'finished'
                         # Front end Visualizzazione Fine Partita
                         fe_risultato_partita = "VITTORIA ASSICURATA DAI TIRI SALVEZZA!!"

                 else:
                     # (l'altro team è in redemption a 0 bicchieri).
                     # Se li porto a -1 -> VITTORIA IMMEDIATA
                     game_result = 'win'
                     match_status = 'finished'
                     # Front end Visualizzazione Fine Partita
                     fe_risultato_partita = "VITTORIA ASSICURATA"

        # Calcolo Overkill
        try:
             t1_real = len(json.loads(match.t1_cup_state)) - len(json.loads(match.t1_pending_list))
             t2_real = len(json.loads(match.t2_cup_state)) - len(json.loads(match.t2_pending_list))
             diff = t1_real - t2_real if team == 't1' else t2_real - t1_real
             match_score_diff = diff
        except:
             match_score_diff = 0
        
        # ===============================================

        display_opp_cups = str(len(opp_active_list))
        if match.status.startswith('redemption'):
            is_my_team_redeeming = (match.status == f'redemption_{team}')
            redemption_info = {
                'active': True, 
                'shots_left': match.redemption_shots_left,
                'is_me': is_my_team_redeeming
            }
            if is_my_team_redeeming:
                display_opp_cups = f"{len(opp_active_list)} - {match.redemption_hits}"
        
        defaults['numero_bicchieri'] = display_opp_cups

    if ultimo_record:
        # MODIFICA: La bevanda la recuperiamo SEMPRE, anche durante il match
        defaults['bevanda'] = ultimo_record.bevanda
        
        # La postazione invece la recuperiamo dallo storico solo se NON siamo in match
        # (perché in match viene calcolata in base alle squadre poco sotto)
        if not match:
            defaults['postazione'] = ultimo_record.postazione
    
    if match and not defaults['postazione']:
        if player_name in [match.t1_p1, match.t2_p1]: defaults['postazione'] = 'Sinistra'
        else: defaults['postazione'] = 'Destra'


    # Per vedere quanti bicchieri sono da eliminare quando si è nei tiri Salvezza
    # ... dentro la funzione index ...

        display_opp_cups = str(len(opp_active_list))
        
        # --- MODIFICA REDEMPTION INFO ---
        if match.status.startswith('redemption'):
            is_my_team_redeeming = (match.status == f'redemption_{team}')
            
            # Calcoliamo quanti ne mancano per il pareggio (Overtime)
            # Logica: Bicchieri Attivi Avversario - Bicchieri che abbiamo già colpito in questa fase (Pending)
            cups_needed_to_tie = len(opp_active_list) - len(opp_pending_list)
            
            # Se è negativo (es. -1), vuol dire che siamo già in zona vittoria/ribaltone
            if cups_needed_to_tie < 0: cups_needed_to_tie = 0

            redemption_info = {
                'active': True, 
                'shots_left': match.redemption_shots_left,
                'is_me': is_my_team_redeeming,
                'cups_to_tie': cups_needed_to_tie  # <--- NUOVO DATO
            }
            
            if is_my_team_redeeming:
                display_opp_cups = f"{len(opp_active_list)} - {match.redemption_hits}"
        


    teammate = ""
    if match:
        if team == 't1': teammate = match.t1_p2 if match.t1_p1 == player_name else match.t1_p1
        else: teammate = match.t2_p2 if match.t2_p1 == player_name else match.t2_p1

    # Front End Visualizzazione Partita Finita
    # Controllo Prioritario "Vittoria Assicurata"
    # Se ho vinto e il conteggio è -1 o peggio, è una vittoria speciale.
    if game_result == 'win' and opp_real_life <= -1:
        
        if "SALVEZZA" not in fe_risultato_partita:
            
            # Se i bicchieri "reali" sono -2 o meno, significa che c'è stato un overkill 
            if opp_real_life < -1:
                fe_risultato_partita = "VITTORIA ASSICURATA DAI TIRI SALVEZZA!!"
            else:
                # Se è esattamente -1, è la classica Death Cup / Vittoria Assicurata standard.
                fe_risultato_partita = "VITTORIA ASSICURATA"

    # 3. Gestione Pareggio
    if game_result == "draw":
        fe_risultato_partita = "PAREGGIO"
    
    # 4. Visualizzazione Standard (Vittoria +X / Sconfitta -X)
    # Scrive questo SOLO se fe_risultato_partita è ancora vuoto
    if fe_risultato_partita == "":
        if game_result in ("win", "loss") and diff_real_life != 0:
            fe_risultato_partita = (
                f"{'VITTORIA' if diff_real_life > 0 else 'SCONFITTA'} {diff_real_life:+d}"
            )

    is_split_context = (request.args.get('context') == 'split')
    # Recupera i flag di animazione
    show_anim = session.pop('animazione_pending', False)
    
    # Recuperiamo il flag specifico per l'inizio overtime
    show_ot_flash = session.pop('animazione_overtime_start', False)


    return render_template('player_record.html', 
                           dati=clean_records, 
                           defaults=defaults, 
                           player_name=player_name,
                           is_match=bool(match), 
                           teammate=teammate,
                           waiting_for_opponent=pending_damage_for_them,
                           match_status=match_status, 
                           redemption_info=redemption_info,
                           format_locked=format_locked,
                           fe_risultato_partita=fe_risultato_partita,
                           game_result=game_result,
                           match_score_diff=match_score_diff,
                           is_split_context=is_split_context,
                           show_animation=show_anim,
                           show_ot_flash=show_ot_flash)


@bp.route('/force_update/<player_name>', methods=['POST'])
def force_update(player_name):
    # Logica per forzare l'applicazione dei danni (il tasto "Conferma" o simili)
    match, team = get_match_info(player_name)
    if match and match.status == 'running':
        opponent_team = 't2' if team == 't1' else 't1'
        apply_pending_damage(match, opponent_team)
        update_game_state(match)
        db.session.commit()
    return redirect(url_for('main.index', player_name=player_name))


@bp.route('/add/<player_name>', methods=['POST'])
def add_record(player_name):
    player = Player.query.filter_by(name=player_name).first()
    match, team = get_match_info(player_name)

    submitted_format = request.form.get('formato')
    
    # --- GESTIONE CAMBIO FORMATO SINCRONIZZATO ---
    format_updated = False # Flag per capire se abbiamo appena cambiato formato
    
    if match and submitted_format:
        if team == 't1':
            current_target = match.format_target_for_t2
            if submitted_format != current_target:
                match.format_target_for_t2 = submitted_format
                init_cup_state(match, 't2', submitted_format)
                match.t1_format_changed = True
                db.session.commit()
                format_updated = True 
                # AGGIUNGI QUESTA RIGA:
                session['animazione_pending'] = True 

        else: # team == 't2'
            current_target = match.format_target_for_t1
            if submitted_format != current_target:
                match.format_target_for_t1 = submitted_format
                init_cup_state(match, 't1', submitted_format)
                match.t2_format_changed = True
                db.session.commit()
                format_updated = True 
                # AGGIUNGI QUESTA RIGA:
                session['animazione_pending'] = True

    # --- NUOVO CONTROLLO: SE ABBIAMO CAMBIATO FORMATO, CI FERMIAMO QUI ---
    # Se il risultato_tiro non è nel form, significa che la JS ha inviato il form solo per il formato
    if 'risultato_tiro' not in request.form:
        # Reindirizziamo l'utente alla pagina del match senza processare statistiche
        return redirect(request.referrer or '/')

    # --- LOGICA NORMALE DEL TIRO ---
    # Ora questa riga non crasha più perché se arriviamo qui, il tiro c'è per forza
    res = request.form['risultato_tiro']
    cups_for_stats = [] 

    # ... resto del tuo codice ...

    if match:
        # Applica eventuali danni precedenti
        apply_pending_damage(match, team)

        if res == 'Centro':
            # 1. Recupero dati dal form
            damage_candidates = request.form.getlist('bicchiere_colpito') # Bicchieri Rossi
            rehit_str = request.form.get('rehit_list', '')
            rehits_physically_hit = [x for x in rehit_str.split(',') if x] # Bicchieri Azzurri
            
            # 2. Potenza del tiro (n) definita dal moltiplicatore
            mult_val = request.form.get('bicchieri_multipli', '')
            mapping = {'': 1, 'Doppio': 2, 'Triplo': 3, 'Quadruplo': 4, 'Quintuplo': 5, 'Sestuplo': 6}
            shots_potency = mapping.get(mult_val, 1)

            # --- STATISTICHE DI MIRA ---
            # Uniamo le liste: gli azzurri (pending colpiti) hanno la precedenza temporale,
            # poi aggiungiamo i rossi evitando duplicati.
            all_clicked = rehits_physically_hit + [c for c in damage_candidates if c not in rehits_physically_hit]
            
            # Salviamo nelle statistiche esattamente i primi N bicchieri di questo flusso
            cups_for_stats = all_clicked[:shots_potency]

            # --- LOGICA DANNI (Funzionamento del gioco) ---
            opponent_team = 't2' if team == 't1' else 't1'
            opp_pending_list_col = f'{opponent_team}_pending_list'
            opp_pending_int_col = f'pending_damage_for_{opponent_team}'
            
            try:
                current_pending = json.loads(getattr(match, opp_pending_list_col))
                initial_count = len(current_pending)

                # Identifichiamo i bicchieri Rossi "nuovi" da aggiungere alla pending_list
                only_red = [c for c in damage_candidates if c not in rehits_physically_hit]
                
                # Aggiungiamo i rossi fino a raggiungere la potenza del tiro
                for cup in only_red:
                    if (len(current_pending) - initial_count) < shots_potency:
                        if cup not in current_pending:
                            current_pending.append(cup)
                
                # Gestione Overkill: se abbiamo fatto centro ma non ci sono (più) rossi da segnare
                punti_effettivi = len(current_pending) - initial_count
                mancanti = shots_potency - punti_effettivi
                if mancanti > 0:
                    for i in range(mancanti):
                        current_pending.append(f"Overkill_{datetime.now().timestamp()}_{i}")

                # Sincronizzazione Redemption
                if match.status.startswith('redemption'):
                    redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
                    if team == redeeming_team:
                        match.redemption_hits += shots_potency
                
                setattr(match, opp_pending_list_col, json.dumps(current_pending))
                setattr(match, opp_pending_int_col, len(current_pending))
            except Exception as e:
                print(f"Errore logica Centro: {e}")

        # Decremento tiri in redemption se Miss o Bordo (solo per chi si salva)
        if match.status.startswith('redemption'):
            redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
            if team == redeeming_team: 
                match.redemption_shots_left -= 1

        update_game_state(match)
        db.session.commit()

    # Generiamo la stringa dei colpi basandoci sulla MIRA REALE (cups_for_stats)
    # Se il risultato è Centro, usiamo la lista della mira, altrimenti "N/A"
    hit_str = ", ".join(cups_for_stats) if res == "Centro" and cups_for_stats else "N/A"
    
    # Calcolo bicchieri per storico
    curr_my_cups = 0; curr_opp_cups = 0
    if match:
        try:
            t1_c = len(json.loads(match.t1_cup_state))
            t2_c = len(json.loads(match.t2_cup_state))
            if team == 't1': curr_my_cups = t1_c; curr_opp_cups = t2_c
            else: curr_my_cups = t2_c; curr_opp_cups = t1_c
        except: pass

    new_rec = PlayerRecord(
        match_id=match.id if match else None,
        player_id=player.id,
        miss=("Sì" if res == "Miss" else "No"), 
        bordo=("Sì" if res == "Bordo" else "No"),
        centro=("Sì" if res == "Centro" else "No"),
        cups_own=curr_my_cups, 
        cups_opp=curr_opp_cups,
        bicchiere_colpito=hit_str, 
        formato=submitted_format,
        tiro_salvezza=('Sì' if match and match.status == f'redemption_{team}' else 'No'),
        postazione=request.form.get('postazione'),
        bevanda=request.form.get('bevanda', 'Birra').strip().capitalize(),
        bicchieri_multipli=request.form.get('bicchieri_multipli'),
        note=request.form.get('note', '')
    )
    db.session.add(new_rec)
    db.session.commit()

    # --- AGGIUNGI QUESTO SOTTO AL COMMIT, per l'aggiornamento ---
    if match:
        print(f"INVIO SEGNALE AGGIORNAMENTO PER MATCH {match.id}") # Debug
        socketio.emit('partita_aggiornata', {'match_id': match.id})
    
    return redirect(url_for('main.index', player_name=player_name))

# --- GESTIONE GIOCATORI ---
@bp.route('/players')
def manage_players():
    return render_template('players.html', players=Player.query.order_by(Player.name).all())

@bp.route('/add_player', methods=['POST'])
def add_player():
    pn = request.form['player_name'].strip()
    password_input = request.form['password']
    hashed_password = generate_password_hash(password_input)
    if pn and not Player.query.filter_by(name=pn).first():
        new_player = Player(name=pn, password=hashed_password)
        db.session.add(new_player)
        db.session.commit()
    return redirect(url_for('main.manage_players'))

@bp.route('/delete_player/<int:id>', methods=['POST'])
def delete_player(id):
    db.session.delete(Player.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('main.manage_players'))

@bp.route('/delete/<player_name>/<int:id>', methods=['POST'])
def delete_record(player_name, id):
    record = PlayerRecord.query.get(id)
    if record:
        # Qui potresti aggiungere la logica di "ripristino bicchieri" del vecchio file
        # se cancelli un record che era Centro. Per brevità l'ho omessa ma posso aggiungerla.
        db.session.delete(record)
        db.session.commit()
    return redirect(url_for('main.index', player_name=player_name))

