from flask import render_template, flash, redirect, url_for, request
from app.models import ActiveMatch, db, CUP_DEFINITIONS
from app.main import bp
from datetime import datetime
import json


# MODALITA' TEAM MODE, lo so che non centra con il manuale, ma c'è troppa roba in routes
# Poi questa funzione è abbastanza a se stante
@bp.route('/team_mode/<player_name>')
def team_mode(player_name):
    # 1. Cerchiamo la partita e il team direttamente qui per evitare conflitti di importazione
    match = None
    team = None
    
    # Cerchiamo tra i match attivi quello in cui è presente il giocatore
    all_active = ActiveMatch.query.filter(ActiveMatch.status != 'finished').all()
    for m in all_active:
        if player_name in [m.t1_p1, m.t1_p2]:
            match = m
            team = 't1'
            break
        if player_name in [m.t2_p1, m.t2_p2]:
            match = m
            team = 't2'
            break
    
    if not match:
        flash("Nessuna partita attiva trovata.", "warning")
        return redirect(url_for('main.index', player_name=player_name))

    # 2. Identifica i due compagni
    if team == 't1':
        p1 = match.t1_p1
        p2 = match.t1_p2
    else:
        p1 = match.t2_p1
        p2 = match.t2_p2

    # Controllo di sicurezza se manca il compagno
    if not p1 or not p2:
        flash("Compagno di squadra non trovato.", "warning")
        return redirect(url_for('main.index', player_name=player_name))

    # 3. Carica la vista team_view.html
    return render_template('team_view.html', p1=p1, p2=p2, match_id=match.id)



# --- ROTTE PER GESTIONE MANUALE ---

@bp.route('/match/<int:match_id>/manual')
def manual_override(match_id):
    """Mostra la pagina di gestione manuale"""
    match = ActiveMatch.query.get_or_404(match_id)
    
    try:
        match.active_cups_t1_list = json.loads(match.t1_cup_state)
        match.active_cups_t2_list = json.loads(match.t2_cup_state)
    except:
        match.active_cups_t1_list = []
        match.active_cups_t2_list = []
    
    # CAMBIA QUESTA RIGA: Passiamo tutto il dizionario, non solo le chiavi
    return render_template('manuale.html', match=match, cup_definitions=CUP_DEFINITIONS)

@bp.route('/match/<int:match_id>/manual/post', methods=['POST'])
def manual_override_post(match_id):
    match = ActiveMatch.query.get_or_404(match_id)
    
    # 1. Recupera i Formati scelti
    new_format_t1 = request.form.get('t1_format')
    new_format_t2 = request.form.get('t2_format')
    
    # 2. RECUPERA LE LISTE DEI BICCHIERI SELEZIONATI (Checkbox)
    # Usiamo getlist per prendere tutti i valori spuntati nel form
    selected_cups_t1 = request.form.getlist('t1_selected_cups')
    selected_cups_t2 = request.form.getlist('t2_selected_cups')
    
    new_status = request.form.get('match_status')
    redemption_shots = int(request.form.get('redemption_shots', 0))

    # 3. AGGIORNA DATABASE (Sovrascrittura diretta)
    # Salviamo esattamente le liste ricevute, convertite in JSON
    match.t1_cup_state = json.dumps(selected_cups_t1)
    match.t2_cup_state = json.dumps(selected_cups_t2)
    
    # Aggiorna i formati target
    match.format_target_for_t1 = new_format_t1
    match.format_target_for_t2 = new_format_t2
    
    # ... resto del codice (reset pending e status) rimane uguale ...
    match.t1_pending_list = '[]'
    match.t2_pending_list = '[]'
    match.pending_damage_for_t1 = 0
    match.pending_damage_for_t2 = 0

    if new_status == 'overtime':
        match.mode = 'overtime'
        match.status = 'overtime' 
    elif new_status == 'finished':
        match.status = 'finished'
        match.end_time = datetime.now()
    else:
        match.status = new_status
        match.mode = 'standard'
    
    if 'redemption' in new_status:
        match.redemption_shots_left = redemption_shots

    db.session.commit()
    flash("Configurazione salvata con successo!", "success")
    return redirect(url_for('main.select_player'))



