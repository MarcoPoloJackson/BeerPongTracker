from flask import render_template, flash, redirect, url_for, request, session, jsonify
from app.models import ActiveMatch, db, CUP_DEFINITIONS, Player, PlayerRecord
from app.main import bp
from datetime import datetime
from sqlalchemy import func
from werkzeug.security import generate_password_hash
import json

# --- ROTTA TEAM MODE AGGIORNATA ---
@bp.route('/team_mode/<player_name>')
def team_mode(player_name):
    # 1. Recuperiamo l'utente che sta navigando per vedere se è admin
    current_user_id = session.get('player_id')
    current_user_obj = Player.query.get(current_user_id)
    is_super_admin = current_user_obj.is_admin if current_user_obj else False

    match = None
    team = None
    
    all_active = ActiveMatch.query.filter(ActiveMatch.status != 'finished').all()
    for m in all_active:
        if player_name in [m.t1_p1, m.t1_p2]:
            match = m; team = 't1'; break
        if player_name in [m.t2_p1, m.t2_p2]:
            match = m; team = 't2'; break
    
    if not match:
        flash("Nessuna partita attiva trovata.", "warning")
        return redirect(url_for('main.index', player_name=player_name))

    if team == 't1': 
        p1 = match.t1_p1; p2 = match.t1_p2
    else: 
        p1 = match.t2_p1; p2 = match.t2_p2

    if not p1 or not p2:
        flash("Compagno di squadra non trovato.", "warning")
        return redirect(url_for('main.index', player_name=player_name))

    # --- LOGICA PRIVACY / ADMIN OVERRIDE ---
    # Identifichiamo il compagno (quello che non è player_name)
    teammate_name = p2 if p1 == player_name else p1
    teammate_obj = Player.query.filter_by(name=teammate_name).first()

    # Se l'utente NON è admin e il compagno NON ha "Condividi" attivo, blocca l'accesso
    if not is_super_admin:
        if teammate_obj and not teammate_obj.edit:
            flash(f"Il compagno {teammate_name} deve attivare 'Condividi' nella Home.", "error")
            return redirect(url_for('main.index', player_name=player_name))

    return render_template('team_view.html', p1=p1, p2=p2, match_id=match.id)


# --- ROTTE PER GESTIONE MANUALE ---

@bp.route('/match/<int:match_id>/manual')
def manual_override(match_id):
    """Mostra la pagina di gestione manuale"""
    match = ActiveMatch.query.get_or_404(match_id)
    
    # Decodifica lo stato dei bicchieri per il template
    try: match.active_cups_t1_list = json.loads(match.t1_cup_state)
    except: match.active_cups_t1_list = []
    
    try: match.active_cups_t2_list = json.loads(match.t2_cup_state)
    except: match.active_cups_t2_list = []
    
    return render_template('manuale.html', match=match, cup_definitions=CUP_DEFINITIONS)

@bp.route('/match/<int:match_id>/manual/post', methods=['POST'])
def manual_override_post(match_id):
    match = ActiveMatch.query.get_or_404(match_id)
    
    # 1. Recupera i Formati scelti
    new_format_t1 = request.form.get('t1_format')
    new_format_t2 = request.form.get('t2_format')
    
    # 2. Recupera le liste dei bicchieri (Checkbox)
    selected_cups_t1 = request.form.getlist('t1_selected_cups')
    selected_cups_t2 = request.form.getlist('t2_selected_cups')
    
    new_status = request.form.get('match_status')
    redemption_shots = int(request.form.get('redemption_shots', 0))

    # 3. Aggiorna Database
    match.t1_cup_state = json.dumps(selected_cups_t1)
    match.t2_cup_state = json.dumps(selected_cups_t2)
    
    if new_format_t1: match.format_target_for_t1 = new_format_t1
    if new_format_t2: match.format_target_for_t2 = new_format_t2
    
    # Reset Pending per evitare conflitti
    match.t1_pending_list = '[]'
    match.t2_pending_list = '[]'
    match.pending_damage_for_t1 = 0
    match.pending_damage_for_t2 = 0

    # Gestione Stato
    if new_status == 'overtime':
        match.mode = 'overtime'
        match.status = 'running' # Overtime è un modo di running
    elif new_status == 'finished':
        match.status = 'finished'
        match.end_time = datetime.now()
    else:
        match.status = new_status
        # Se torniamo a ongoing, resettiamo la mode a squadre se era overtime
        if new_status == 'ongoing':
            match.status = 'running'
            match.mode = 'squadre'
    
    # Gestione Redemption Shots
    if 'redemption' in str(new_status) or 'overtime' in str(new_status):
        match.redemption_shots_left = redemption_shots

    db.session.commit()
    flash("Configurazione salvata con successo!", "success")
    
    # CORREZIONE IMPORTANTE: Reindirizza a 'home', non 'select_player'
    return redirect(url_for('main.home')) 


# --- ALTRE ROTTE DI UTILITY ---

@bp.route('/toggle_edit', methods=['POST'])
def toggle_edit():
    if 'player_id' not in session:
        return redirect(url_for('main.login_page'))
    
    player = Player.query.get(session['player_id'])
    if player:
        player.edit = not player.edit
        db.session.commit()
    
    return redirect(url_for('main.home'))

@bp.route('/check_teammate_edit/<teammate_name>')
def check_teammate_edit(teammate_name):
    teammate = Player.query.filter_by(name=teammate_name).first()
    if teammate:
        return jsonify({'can_edit': teammate.edit})
    return jsonify({'can_edit': False})


# --- ROTTA PER MODIFICARE UN TIRO (EDIT RECORD) ---

@bp.route('/edit/<player_name>/<int:id>', methods=['GET', 'POST'])
def edit_record(player_name, id):
    # Recupera il tiro dal database
    record = PlayerRecord.query.get_or_404(id)
    
    if request.method == 'POST':
        # 1. Aggiorna Risultato (Miss, Bordo, Centro)
        res = request.form.get('risultato_tiro')
        record.miss = 'Sì' if res == 'Miss' else 'No'
        record.bordo = 'Sì' if res == 'Bordo' else 'No'
        record.centro = 'Sì' if res == 'Centro' else 'No'
        
        # 2. Aggiorna altri campi semplici
        record.numero_bicchieri = request.form.get('numero_bicchieri')
        record.formato = request.form.get('formato')
        record.bevanda = request.form.get('bevanda')
        record.note = request.form.get('note')
        record.bicchieri_multipli = request.form.get('bicchieri_multipli')
        record.postazione = request.form.get('postazione')
        
        # 3. Aggiorna Tiro Salvezza (Checkbox)
        # Se la checkbox è spuntata, request.form.get restituisce il valore (es. 'Sì'), altrimenti None
        record.tiro_salvezza = 'Sì' if request.form.get('tiro_salvezza') else 'No'
        
        # 4. Aggiorna Bicchieri Colpiti (Checkbox Multipli)
        # request.form.getlist prende tutti i valori selezionati
        colpiti_list = request.form.getlist('bicchiere_colpito')
        if colpiti_list:
            record.bicchiere_colpito = ", ".join(colpiti_list)
        else:
            # Se nessuno è selezionato e non è centro, puliamo il campo
            if res != 'Centro':
                record.bicchiere_colpito = "N/A"
            # Se è centro ma l'utente ha deselezionato tutto, lascia com'era o metti vuoto (a tua scelta)
            # Qui lasciamo vuoto se deselezionato
        
        db.session.commit()
        flash("Tiro modificato con successo!", "success")
        return redirect(url_for('main.index', player_name=player_name))
        
    # Se è GET, mostra la pagina di modifica
    return render_template('edit_record.html', record=record, player_name=player_name)


# Aggiungi questi import se mancano
from app.models import db, Player
from flask import render_template, request, redirect, url_for, session, flash

# --- ROTTA PER PAGINA SCELTA ICONA ---
@bp.route('/scegli_icona')
def icon_page():
    if 'player_id' not in session:
        return redirect(url_for('main.login_page'))
    
    player = Player.query.get(session['player_id'])
    
    return render_template('includes/icona.html', 
                           player_name=player.name, 
                           current_icon=player.icon)



@bp.route('/update_icon', methods=['POST'])
def update_icon():
    if 'player_id' not in session:
        return redirect(url_for('main.login_page'))
    
    player = Player.query.get(session['player_id'])
    if not player:
        return redirect(url_for('main.home'))

    old_name = player.name
    success_flag = True 
    specific_message_sent = False # Per evitare il doppio messaggio finale

    # --- 1. GESTIONE CAMBIO NOME ---
    if 'new_name' in request.form:
        new_name = request.form.get('new_name').strip()
        if new_name and new_name != old_name:
            RESERVED = ['CLOSED', 'NESSUNO', 'ADMIN', 'NULL', 'SCONOSCIUTO']
            if new_name.upper() in RESERVED:
                flash(f"Il nome '{new_name}' è riservato.", "error")
                success_flag = False
            else:
                existing_user = Player.query.filter(
                    func.lower(Player.name) == func.lower(new_name),
                    Player.id != player.id
                ).first()
                if existing_user:
                    flash(f"Il nome '{new_name}' è già occupato.", "error")
                    success_flag = False
                else:
                    player.name = new_name
                    # Aggiorna nomi nei match attivi
                    matches = ActiveMatch.query.filter(
                        (ActiveMatch.t1_p1 == old_name) | (ActiveMatch.t1_p2 == old_name) |
                        (ActiveMatch.t2_p1 == old_name) | (ActiveMatch.t2_p2 == old_name)
                    ).all()
                    for m in matches:
                        if m.t1_p1 == old_name: m.t1_p1 = new_name
                        if m.t1_p2 == old_name: m.t1_p2 = new_name
                        if m.t2_p1 == old_name: m.t2_p1 = new_name
                        if m.t2_p2 == old_name: m.t2_p2 = new_name
                    
                    session['player_name'] = new_name
                    flash(f"Nome cambiato in {new_name}!", "success")
                    specific_message_sent = True

    # --- 2. GESTIONE ICONA ---
    if 'icon' in request.form:
        player.icon = request.form.get('icon') or None
        # Non mettiamo specific_message_sent qui, così appare il "Profilo salvato"

    # --- 3. GESTIONE DRINK ---
    if 'fav_drink' in request.form:
        player.fav_drink = request.form.get('fav_drink', 'Birra')

    # --- 4. GESTIONE PASSWORD ---
    if 'new_password' in request.form:
        raw_password = request.form.get('new_password').strip()
        if raw_password:
            player.password = generate_password_hash(raw_password)
            flash("Password aggiornata!", "success")
            specific_message_sent = True

    # --- SALVATAGGIO FINALE (FONDAMENTALE) ---
    db.session.commit()
    
    # Mostra il messaggio generico solo se non ci sono stati errori 
    # e se non abbiamo già inviato un messaggio specifico (nome o password)
    if success_flag and not specific_message_sent:
        flash("Profilo salvato correttamente.", "success")
        
    return redirect(url_for('main.icon_page'))