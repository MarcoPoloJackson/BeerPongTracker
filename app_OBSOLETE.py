from flask import Flask, render_template, request, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash
import os
import json
import sqlite3
from datetime import datetime

# Importiamo tutto il necessario dal modulo databases
from app.models import (
    db,
    init_db,
    Player,
    ActiveMatch,
    get_player_db_session,
    dati_tabella_from_records,
    init_cup_state,
    get_match_info,
    apply_pending_damage,
    count_shots_in_match,
    start_overtime,
    finish_match,
    update_game_state,
    INTESTAZIONI,
    CUP_DEFINITIONS,
    get_all_db_content
)

app = Flask(__name__)

# --- CONFIGURAZIONE ---
app.config['SECRET_KEY'] = 'chiave_segretissima_beerpong'

# Inizializzazione del Database tramite la funzione importata
init_db(app)


# ==========================================
#                 ROTTE
# ==========================================

@app.route('/')
def select_player():
    # Carica giocatori e partite usando i modelli importati
    players = Player.query.order_by(Player.name).all()
    active_matches = ActiveMatch.query.all()

    matches_data = []
    busy_players = []

    for m in active_matches:
        if m.status != 'finished':
            busy_players.extend([m.t1_p1, m.t1_p2, m.t2_p1, m.t2_p2])

        stats = {
            't1_p1': count_shots_in_match(m.t1_p1, m.id),
            't1_p2': count_shots_in_match(m.t1_p2, m.id),
            't2_p1': count_shots_in_match(m.t2_p1, m.id),
            't2_p2': count_shots_in_match(m.t2_p2, m.id),
        }
        matches_data.append({'match': m, 'stats': stats})

    return render_template('home.html',
                           players=players,
                           matches_data=matches_data,
                           busy_players=busy_players)


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
        if mode == 'singolo': return redirect(url_for('main.select_player'))

        t1_p1 = request.form.get('t1_p1');
        t1_p2 = request.form.get('t1_p2')
        t2_p1 = request.form.get('t2_p1');
        t2_p2 = request.form.get('t2_p2')
        match_name = request.form.get('match_name') or f"Tavolo {db.session.query(ActiveMatch).count() + 1}"

        players_list = [p for p in [t1_p1, t1_p2, t2_p1, t2_p2] if p]
        if len(players_list) != len(set(players_list)): return "Duplicati"
        for p in players_list:
            if p in busy_players: return f"{p} occupato"

        if match:
            match.match_name = match_name;
            match.t1_p1 = t1_p1;
            match.t1_p2 = t1_p2;
            match.t2_p1 = t2_p1;
            match.t2_p2 = t2_p2
        else:
            match = ActiveMatch(match_name=match_name, t1_p1=t1_p1, t1_p2=t1_p2, t2_p1=t2_p1, t2_p2=t2_p2,
                                status='running')
            db.session.add(match)

        db.session.commit()

        if not match.t1_cup_state or match.t1_cup_state == '[]':
            init_cup_state(match, 't1', 'Piramide')
        if not match.t2_cup_state or match.t2_cup_state == '[]':
            init_cup_state(match, 't2', 'Piramide')

        return redirect(url_for('main.select_player'))

    players = Player.query.order_by(Player.name).all()
    return render_template('setup_match.html', players=players, match=match, busy_players=busy_players)


@app.route('/rematch/<int:match_id>')
def rematch(match_id):
    match = ActiveMatch.query.get_or_404(match_id)
    match.status = 'running'
    match.start_time = datetime.now()
    match.end_time = None
    match.winning_team = None

    match.cups_target_for_t1 = 6;
    match.cups_target_for_t2 = 6
    match.format_target_for_t1 = "Piramide";
    match.format_target_for_t2 = "Piramide"
    match.pending_damage_for_t1 = 0;
    match.pending_damage_for_t2 = 0
    match.redemption_shots_left = 0;
    match.redemption_hits = 0
    match.t1_format_changed = False;
    match.t2_format_changed = False

    match.t1_pending_list = '[]';
    match.t2_pending_list = '[]'
    init_cup_state(match, 't1', 'Piramide')
    init_cup_state(match, 't2', 'Piramide')

    db.session.commit()
    return redirect(url_for('main.select_player'))


@app.route('/end_match/<int:match_id>')
def end_match(match_id):
    db.session.delete(ActiveMatch.query.get_or_404(match_id));
    db.session.commit()
    return redirect(url_for('main.select_player'))


@app.route('/tracker/<player_name>')
def index(player_name):
    dbsession, PlayerRecord = get_player_db_session(player_name)
    records_obj = dbsession.query(PlayerRecord).order_by(PlayerRecord.id.desc()).all()
    clean_records = dati_tabella_from_records(records_obj)
    ultimo_record = dbsession.query(PlayerRecord).order_by(PlayerRecord.id.desc()).first()

    defaults = {'numero_bicchieri': '6', 'formato': 'Piramide', 'postazione': '', 'bevanda': 'Birra',
                'giocatore': player_name, 'my_formato': 'Piramide', 'match_id': 0}
    match, team = get_match_info(player_name)

    pending_damage_for_me = 0;
    pending_damage_for_them = 0
    match_status = None;
    redemption_info = None
    format_locked = False;
    game_result = None

    my_active_cups = CUP_DEFINITIONS['Piramide']
    opp_active_cups = CUP_DEFINITIONS['Piramide']
    opp_pending_cups = [];
    my_pending_cups = []
    my_cups_count = 6;
    opp_cups_count = 6

    if match:
        defaults['match_id'] = match.id
        update_game_state(match)
        match_status = match.status

        if match.status == 'finished':
            game_result = 'win' if match.winning_team == team else 'loss'

        try:
            if team == 't1':
                my_active_cups = json.loads(match.t1_cup_state);
                opp_active_cups = json.loads(match.t2_cup_state)
                opp_pending_cups = json.loads(match.t2_pending_list);
                my_pending_cups = json.loads(match.t1_pending_list)
                defaults['my_formato'] = match.format_target_for_t1;
                defaults['formato'] = match.format_target_for_t2
                format_locked = match.t1_format_changed
                pending_damage_for_me = match.pending_damage_for_t1;
                pending_damage_for_them = match.pending_damage_for_t2
            else:
                my_active_cups = json.loads(match.t2_cup_state);
                opp_active_cups = json.loads(match.t1_cup_state)
                opp_pending_cups = json.loads(match.t1_pending_list);
                my_pending_cups = json.loads(match.t2_pending_list)
                defaults['my_formato'] = match.format_target_for_t2;
                defaults['formato'] = match.format_target_for_t1
                format_locked = match.t2_format_changed
                pending_damage_for_me = match.pending_damage_for_t2;
                pending_damage_for_them = match.pending_damage_for_t1

            my_cups_count = len(my_active_cups) - len(my_pending_cups)
            opp_cups_count = len(opp_active_cups)
        except Exception as e:
            print(f"Errore caricamento stato bicchieri: {e}")

    display_opp_cups = str(opp_cups_count)
    if match and match.status.startswith('redemption'):
        is_my_team_redeeming = (match.status == f'redemption_{team}')
        redemption_info = {'active': True, 'shots_left': match.redemption_shots_left, 'is_me': is_my_team_redeeming}
        if is_my_team_redeeming:
            display_opp_cups = f"{opp_cups_count} - {match.redemption_hits}"

    defaults['numero_bicchieri'] = display_opp_cups
    defaults['opp_active_cups'] = opp_active_cups;
    defaults['my_active_cups'] = my_active_cups
    defaults['opp_pending_cups'] = opp_pending_cups;
    defaults['my_pending_cups'] = my_pending_cups

    if ultimo_record:
        if not match:
            defaults['postazione'] = ultimo_record.postazione;
            defaults['bevanda'] = ultimo_record.bevanda
            defaults['numero_bicchieri'] = str(ultimo_record.numero_bicchieri)
        elif player_name == match.t1_p1 or player_name == match.t2_p1:
            defaults['postazione'] = 'Sinistra'
        elif player_name == match.t1_p2 or player_name == match.t2_p2:
            defaults['postazione'] = 'Destra'
        if ultimo_record.bevanda: defaults['bevanda'] = ultimo_record.bevanda

    dbsession.close()

    teammate = ""
    if match:
        if team == 't1':
            teammate = match.t1_p2 if match.t1_p1 == player_name else match.t1_p1
        else:
            teammate = match.t2_p2 if match.t2_p1 == player_name else match.t2_p1

    return render_template('player_record.html', intestazioni=INTESTAZIONI, dati=clean_records,
                           titolo=f"Tracker - {player_name}", defaults=defaults, player_name=player_name,
                           is_match=bool(match), teammate=teammate,
                           pending_damage=pending_damage_for_me, waiting_for_opponent=pending_damage_for_them,
                           match_status=match_status, redemption_info=redemption_info,
                           my_cups=my_cups_count, opp_cups=opp_cups_count, format_locked=format_locked,
                           game_result=game_result)


@app.route('/force_update/<player_name>', methods=['POST'])
def force_update(player_name):
    match, team = get_match_info(player_name)
    if match and match.status == 'running':
        opponent_team = 't2' if team == 't1' else 't1'
        apply_pending_damage(match, opponent_team)
        update_game_state(match)
        db.session.commit()
    return redirect(url_for('main.index', player_name=player_name))


@app.route('/add/<player_name>', methods=['POST'])
def add_record(player_name):
    dbsession, PlayerRecord = get_player_db_session(player_name)
    match, team = get_match_info(player_name)

    submitted_format = request.form.get('formato')
    final_format = submitted_format
    if match:
        target_format_db = match.format_target_for_t2 if team == 't1' else match.format_target_for_t1
        if submitted_format and submitted_format != target_format_db:
            already_changed = match.t1_format_changed if team == 't1' else match.t2_format_changed
            if not already_changed:
                if team == 't1':
                    match.format_target_for_t2 = submitted_format;
                    match.t1_format_changed = True
                    init_cup_state(match, 't2', submitted_format)
                else:
                    match.format_target_for_t1 = submitted_format;
                    match.t2_format_changed = True
                    init_cup_state(match, 't1', submitted_format)
                db.session.commit()
            else:
                final_format = target_format_db

    res = request.form['risultato_tiro']
    cups_for_stats = []

    if match:
        apply_pending_damage(match, team)

        if res == 'Centro':
            damage_candidates = request.form.getlist('bicchiere_colpito')
            rehit_str = request.form.get('rehit_list', '')
            rehits = [x for x in rehit_str.split(',') if x]
            cups_for_stats = rehits + damage_candidates

            if match.status.startswith('redemption'):
                redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'

                if team == redeeming_team:
                    try:
                        # --- [MODIFICA 1: SALVIAMO I BICCHIERI PENDENTI] ---
                        opponent_team = 't2' if team == 't1' else 't1'
                        opp_pending_list_col = f'{opponent_team}_pending_list'

                        # 1. Carichiamo la lista attuale
                        current_pending = json.loads(getattr(match, opp_pending_list_col))

                        # 2. Aggiungiamo i bicchieri (anche duplicati per balls back)
                        for c in cups_for_stats:
                            current_pending.append(c)

                        # 3. Salviamo nel DB (Ora diventeranno AZZURRI nel frontend)
                        setattr(match, opp_pending_list_col, json.dumps(current_pending))
                        # ---------------------------------------------------

                        # Aggiorniamo le statistiche
                        match.redemption_hits += len(cups_for_stats)
                        match.redemption_shots_left -= 1

                        # Nota: Il controllo vittoria ora lo farà update_game_state in models.py
                        # usando i bicchieri reali aggiornati qui sopra.

                    except Exception as e:
                        print(f"Redemption calc error: {e}")
            else:
                opponent_team = 't2' if team == 't1' else 't1'
                opp_pending_list_col = f'{opponent_team}_pending_list'
                opp_pending_int_col = f'pending_damage_for_{opponent_team}'
                opp_active_col = f'{opponent_team}_cup_state'

                try:
                    current_pending = json.loads(getattr(match, opp_pending_list_col))
                    current_active_cups = json.loads(getattr(match, opp_active_col))
                    effective_new_hits = len(damage_candidates)
                    if effective_new_hits == 0 and len(rehits) > 0: effective_new_hits = len(rehits)

                    balance = len(current_active_cups) - len(current_pending) - effective_new_hits

                    if balance < 0:
                        finish_match(match, winner=team)
                        new_rec = PlayerRecord(
                            match_id=match.id, miss="No", bordo="No", centro="Sì",
                            numero_bicchieri="VITTORIA (Overkill)", bicchiere_colpito=", ".join(cups_for_stats),
                            giocatore=player_name, data=datetime.now().strftime("%d/%m/%Y"),
                            ora=datetime.now().strftime("%H:%M")
                        )
                        dbsession.add(new_rec);
                        db.session.commit()
                        return redirect(url_for('index', player_name=player_name))
                    else:
                        for c in damage_candidates:
                            # Aggiungiamo SEMPRE, anche se c'è già.
                            # Così pending_list diventa es: ["3 Cen", "3 Cen"]
                            current_pending.append(c)
                        setattr(match, opp_pending_list_col, json.dumps(current_pending))
                        setattr(match, opp_pending_int_col, len(current_pending))
                except Exception as e:
                    print(f"Errore logica normale: {e}")

        if match.status.startswith('redemption'):
            redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
            if team == redeeming_team and res != 'Centro': match.redemption_shots_left -= 1

        update_game_state(match)
        db.session.commit()

    hit_str = ", ".join(cups_for_stats) if res == "Centro" else "N/A"
    post = request.form.get('postazione')
    if not post and match: post = 'Sinistra' if player_name in [match.t1_p1, match.t2_p1] else 'Destra'

    curr_my_cups = 0;
    curr_opp_cups = 0
    if match:
        try:
            t1_c = len(json.loads(match.t1_cup_state));
            t2_c = len(json.loads(match.t2_cup_state))
            if team == 't1':
                curr_my_cups = t1_c; curr_opp_cups = t2_c
            else:
                curr_my_cups = t2_c; curr_opp_cups = t1_c
        except:
            pass
    adesso = datetime.now()

    new_rec = PlayerRecord(
        match_id=match.id if match else None,
        miss=("Sì" if res == "Miss" else "No"), bordo=("Sì" if res == "Bordo" else "No"),
        centro=("Sì" if res == "Centro" else "No"),
        cups_own=curr_my_cups, cups_opp=curr_opp_cups,
        numero_bicchieri=str(curr_opp_cups), bicchiere_colpito=hit_str, formato=final_format,
        tiro_salvezza=('Sì' if 'tiro_salvezza' in request.form else 'No'), postazione=post,
        bevanda=request.form['bevanda'].strip().capitalize(),
        giocatore=player_name, bicchieri_multipli=request.form.get('bicchieri_multipli'),
        data=adesso.strftime("%d/%m/%Y"), ora=adesso.strftime("%H:%M"), note=request.form['note']
    )
    dbsession.add(new_rec);
    dbsession.commit();
    dbsession.close()
    return redirect(url_for('main.index', player_name=player_name))


@app.route('/edit/<player_name>/<int:id>', methods=['GET', 'POST'])
def edit_record(player_name, id):
    dbsession, PlayerRecord = get_player_db_session(player_name)
    record = dbsession.query(PlayerRecord).get(id)
    if not record: dbsession.close(); abort(404)
    match, team = get_match_info(player_name)

    if request.method == 'POST':
        if match and match.status != 'finished' and record.centro == 'Sì':
            try:
                old_cups = [c.strip() for c in record.bicchiere_colpito.split(',')]
                target_col = 't2_cup_state' if team == 't1' else 't1_cup_state'
                current_list = json.loads(getattr(match, target_col))
                for c in old_cups:
                    if c not in current_list: current_list.append(c)
                setattr(match, target_col, json.dumps(current_list))
                if match.status.startswith('redemption'):
                    redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
                    if team == redeeming_team: match.redemption_hits -= len(old_cups); match.redemption_shots_left += 1
            except:
                pass

        res = request.form['risultato_tiro']
        record.miss = "Sì" if res == "Miss" else "No"
        record.bordo = "Sì" if res == "Bordo" else "No"
        record.centro = "Sì" if res == "Centro" else "No"
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

        if match and match.status != 'finished' and res == 'Centro':
            try:
                target_col = 't2_cup_state' if team == 't1' else 't1_cup_state'
                current_list = json.loads(getattr(match, target_col))
                updated_list = [c for c in current_list if c not in hit_list]
                setattr(match, target_col, json.dumps(updated_list))
                if match.status.startswith('redemption'):
                    redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
                    if team == redeeming_team: match.redemption_hits += len(hit_list); match.redemption_shots_left -= 1
            except:
                pass

        if match: update_game_state(match)
        dbsession.commit();
        dbsession.close()
        return redirect(url_for('main.index', player_name=player_name))

    return render_template('edit_record.html', record=record, player_name=player_name)


@app.route('/delete/<player_name>/<int:id>', methods=['POST'])
def delete_record(player_name, id):
    dbsession, PlayerRecord = get_player_db_session(player_name)
    r = dbsession.query(PlayerRecord).get(id)

    if r:
        match, team = get_match_info(player_name)
        if match and match.status != 'finished' and r.centro == 'Sì':
            try:
                cups_to_restore = [c.strip() for c in r.bicchiere_colpito.split(',')]
                target_col = 't2_cup_state' if team == 't1' else 't1_cup_state'
                current_cups = json.loads(getattr(match, target_col))
                for cup in cups_to_restore:
                    if cup not in current_cups: current_cups.append(cup)
                setattr(match, target_col, json.dumps(current_cups))
                update_game_state(match)
                if match.status.startswith('redemption'):
                    redeeming_team = 't1' if match.status == 'redemption_t1' else 't2'
                    if team == redeeming_team: match.redemption_hits -= len(
                        cups_to_restore); match.redemption_shots_left += 1
            except Exception as e:
                print(f"Errore ripristino bicchieri: {e}")

        dbsession.delete(r);
        dbsession.commit()
    dbsession.close()
    return redirect(url_for('main.index', player_name=player_name))


@app.route('/players')
def manage_players():
    return render_template('players.html', players=Player.query.order_by(Player.name).all())


@app.route('/add_player', methods=['POST'])
def add_player():
    pn = request.form['player_name'].strip()
    password_input = request.form['password']
    hashed_password = generate_password_hash(password_input)
    if pn and not Player.query.filter_by(name=pn).first():
        new_player = Player(name=pn, password=hashed_password, edit=False)
        db.session.add(new_player);
        db.session.commit()
    return redirect(url_for('manage_players'))


@app.route('/delete_player/<int:id>', methods=['POST'])
def delete_player(id):
    db.session.delete(Player.query.get_or_404(id));
    db.session.commit()
    return redirect(url_for('manage_players'))


@app.route('/database-viewer')
def database_viewer():
    # Tutta la logica complessa è ora delegata a models.py
    full_content = get_all_db_content()
    return render_template('admin_db.html', full_db=full_content)


if __name__ == '__main__':
    app.run(debug=True)