from flask import render_template, request, redirect, url_for, session, abort, jsonify
from werkzeug.security import generate_password_hash
from datetime import datetime
import json
from app.main import bp
from app.models import (
    db, Player, ActiveMatch, PlayerRecord, CUP_DEFINITIONS, get_all_db_content
)


# ==========================================
#          HELPER: TURN LOGIC
# ==========================================
def get_current_shooter(match):
    """Calculates whose turn it is based on match.current_turn."""
    if not match: return None

    # 1. Determine rotation based on Game Status
    if match.status == 'redemption_t1':
        potential_rotation = [match.t1_p1, match.t1_p2]
    elif match.status == 'redemption_t2':
        potential_rotation = [match.t2_p1, match.t2_p2]
    else:
        potential_rotation = [match.t1_p1, match.t1_p2, match.t2_p1, match.t2_p2]

    # 2. Filter empty slots
    active_rotation = [p for p in potential_rotation if p]

    # 3. Filter deleted users
    if not active_rotation: return None
    valid_players = Player.query.filter(Player.name.in_(active_rotation)).all()
    valid_names = set(p.name for p in valid_players)
    validated_rotation = [p for p in active_rotation if p in valid_names]

    if not validated_rotation: return None

    current_index = match.current_turn % len(validated_rotation)
    return validated_rotation[current_index]


# ==========================================
#          HELPER: GAME LOGIC
# ==========================================
def init_cup_state(match, team, format_name):
    full_set = CUP_DEFINITIONS.get(format_name, [])
    if team == 't1':
        match.t1_cup_state = json.dumps(full_set)
    else:
        match.t2_cup_state = json.dumps(full_set)


def finish_match(match, winner):
    match.status = 'finished'
    match.end_time = datetime.now()
    match.winning_team = winner


def start_overtime(match):
    match.status = 'running'
    match.match_name += " (OT)"
    match.format_target_for_t1 = "Triangolo"
    match.format_target_for_t2 = "Triangolo"
    init_cup_state(match, 't1', 'Triangolo')
    init_cup_state(match, 't2', 'Triangolo')
    match.t1_pending_list = '[]'
    match.t2_pending_list = '[]'
    match.redemption_hits = 0
    match.redemption_shots_left = 0


def update_game_state_counts(match):
    try:
        t1_active = len(json.loads(match.t1_cup_state)) - len(json.loads(match.t1_pending_list))
        t2_active = len(json.loads(match.t2_cup_state)) - len(json.loads(match.t2_pending_list))
        if match.cups_target_for_t1 != t1_active: match.cups_target_for_t1 = t1_active
        if match.cups_target_for_t2 != t2_active: match.cups_target_for_t2 = t2_active
    except:
        pass


def count_player_shots(match_id, player_name):
    if not player_name: return 0
    player = Player.query.filter_by(name=player_name).first()
    if not player: return 0
    return PlayerRecord.query.filter_by(match_id=match_id, player_id=player.id).count()


# ==========================================
#                 ROUTES
# ==========================================

@bp.route('/')
def select_player():
    active_matches = ActiveMatch.query.filter(ActiveMatch.status != 'finished').all()
    matches_data = []

    for m in active_matches:
        stats = {
            't1_p1': count_player_shots(m.id, m.t1_p1), 't1_p2': count_player_shots(m.id, m.t1_p2),
            't2_p1': count_player_shots(m.id, m.t2_p1), 't2_p2': count_player_shots(m.id, m.t2_p2),
        }
        matches_data.append({'match': m, 'stats': stats})

    return render_template('home.html', matches_data=matches_data)


@bp.route('/setup_match', defaults={'match_id': None}, methods=['GET', 'POST'])
@bp.route('/setup_match/<int:match_id>', methods=['GET', 'POST'])
def setup_match(match_id):
    match = None
    if match_id: match = ActiveMatch.query.get_or_404(match_id)
    players = Player.query.order_by(Player.name).all()

    if request.method == 'POST':
        t1_p1 = request.form.get('t1_p1');
        t1_p2 = request.form.get('t1_p2')
        t2_p1 = request.form.get('t2_p1');
        t2_p2 = request.form.get('t2_p2')
        match_name = request.form.get('match_name') or f"Tavolo {ActiveMatch.query.count() + 1}"

        # Check duplicates
        selected = [p for p in [t1_p1, t1_p2, t2_p1, t2_p2] if p]
        if len(selected) != len(set(selected)): return "❌ Errore: Giocatori duplicati.", 400

        if match:
            match.match_name = match_name
            match.t1_p1 = t1_p1;
            match.t1_p2 = t1_p2
            match.t2_p1 = t2_p1;
            match.t2_p2 = t2_p2
            if request.form.get('status'): match.status = request.form.get('status')
        else:
            match = ActiveMatch(match_name=match_name, status='running', current_turn=0,
                                t1_p1=t1_p1, t1_p2=t1_p2, t2_p1=t2_p1, t2_p2=t2_p2)
            db.session.add(match)
            init_cup_state(match, 't1', 'Piramide')
            init_cup_state(match, 't2', 'Piramide')

        db.session.commit()
        return redirect(url_for('main.select_player'))

    return render_template('setup_match.html', players=players, match=match)


# --- CHANGED: URL NOW INCLUDES MATCH ID ---
@bp.route('/match/<int:match_id>/play/<player_name>')
def index(match_id, player_name):
    # 1. LOAD SPECIFIC MATCH
    match = ActiveMatch.query.get_or_404(match_id)
    player = Player.query.filter_by(name=player_name).first()

    if not player: return "Giocatore non trovato", 404

    # 2. VERIFY PLAYER BELONGS TO THIS MATCH
    team = None
    if player_name in [match.t1_p1, match.t1_p2]:
        team = 't1'
    elif player_name in [match.t2_p1, match.t2_p2]:
        team = 't2'

    if not team: return f"Il giocatore {player_name} non è in questa partita!", 403

    # 3. GET RECORDS
    records_obj = PlayerRecord.query.filter_by(match_id=match.id, player_id=player.id).order_by(
        PlayerRecord.id.desc()).all()
    clean_records = []
    for r in records_obj:
        clean_records.append({
            "ID": r.id, "Giocatore": r.player.name,
            "Miss": r.miss, "Bordo": r.bordo, "Centro": r.centro,
            "Noi": r.cups_own, "Loro": r.cups_opp,
            "Colpiti": r.bicchiere_colpito, "Data": r.timestamp.strftime("%H:%M"),
            "Note": r.note, "Multipli": r.bicchieri_multipli
        })

    # 4. GAME STATE UI
    update_game_state_counts(match)
    current_shooter = None
    if match.status == 'running' or match.status.startswith('redemption'):
        current_shooter = get_current_shooter(match)

    game_result = 'win' if match.status == 'finished' and match.winning_team == team else (
        'loss' if match.status == 'finished' else None)

    # Determine Active Cups
    try:
        if team == 't1':
            my_active = json.loads(match.t1_cup_state);
            opp_active = json.loads(match.t2_cup_state)
            opp_pending = json.loads(match.t2_pending_list);
            my_pending = json.loads(match.t1_pending_list)
            pending_dmg = match.pending_damage_for_t1
        else:
            my_active = json.loads(match.t2_cup_state);
            opp_active = json.loads(match.t1_cup_state)
            opp_pending = json.loads(match.t1_pending_list);
            my_pending = json.loads(match.t2_pending_list)
            pending_dmg = match.pending_damage_for_t2
    except:
        my_active = [];
        opp_active = [];
        opp_pending = [];
        my_pending = [];
        pending_dmg = 0

    # Redemption UI
    redemption_info = None
    if match.status.startswith('redemption'):
        is_my_team = (match.status == f'redemption_{team}')
        redemption_info = {'active': True, 'shots_left': match.redemption_shots_left, 'is_me': is_my_team}

    teammate = ""
    if team == 't1':
        teammate = match.t1_p2 if match.t1_p1 == player_name else match.t1_p1
    else:
        teammate = match.t2_p2 if match.t2_p1 == player_name else match.t2_p1

    defaults = {
        'match_id': match.id,
        'opp_active_cups': opp_active, 'opp_pending_cups': opp_pending,
        'formato': match.format_target_for_t2 if team == 't1' else match.format_target_for_t1
    }

    return render_template('player_record.html',
                           dati=clean_records, defaults=defaults, player_name=player_name,
                           match_id=match.id,  # Pass explicit match ID
                           teammate=teammate, pending_damage=pending_dmg,
                           match_status=match.status, redemption_info=redemption_info,
                           game_result=game_result, current_shooter=current_shooter)


# --- CHANGED: API NOW REQUIRES MATCH ID ---
@bp.route('/api/match/<int:match_id>/status/<player_name>')
def get_match_status(match_id, player_name):
    match = ActiveMatch.query.get(match_id)
    if not match or match.status == 'finished':
        return jsonify({'active': False, 'status': 'finished'})

    team = 't1' if player_name in [match.t1_p1, match.t1_p2] else 't2'

    if team == 't1':
        my_active = match.t1_cup_state;
        opp_active = match.t2_cup_state
        opp_pending = match.t2_pending_list;
        my_pending = match.t1_pending_list
    else:
        my_active = match.t2_cup_state;
        opp_active = match.t1_cup_state
        opp_pending = match.t1_pending_list;
        my_pending = match.t2_pending_list

    current_shooter = get_current_shooter(match)
    is_my_turn = (current_shooter == player_name)

    state_signature = f"{my_active}|{opp_active}|{opp_pending}|{my_pending}|{match.status}|{current_shooter}|{match.current_turn}"

    return jsonify({
        'active': True,
        'state_signature': state_signature,
        'opp_active_cups': json.loads(opp_active),
        'opp_pending_cups': json.loads(opp_pending),
        'status': match.status,
        'current_shooter': current_shooter,
        'is_my_turn': is_my_turn
    })


# --- CHANGED: ADD RECORD NOW REQUIRES MATCH ID ---
@bp.route('/match/<int:match_id>/add/<player_name>', methods=['POST'])
def add_record(match_id, player_name):
    match = ActiveMatch.query.get_or_404(match_id)
    player = Player.query.filter_by(name=player_name).first()

    # Determine Team
    team = None
    if player_name in [match.t1_p1, match.t1_p2]:
        team = 't1'
    elif player_name in [match.t2_p1, match.t2_p2]:
        team = 't2'

    if not team: abort(403)

    # 1. SECURITY
    if match.status == 'running' or match.status.startswith('redemption'):
        actual_shooter = get_current_shooter(match)
        if actual_shooter and actual_shooter != player_name:
            return "❌ Non è il tuo turno!", 403

    # 2. GAMEPLAY LOGIC (Same as before, simplified for brevity)
    res = request.form.get('risultato_tiro')
    bicchieri_colpiti = request.form.getlist('bicchiere_colpito')
    hit_str = ", ".join(bicchieri_colpiti) if res == "Centro" else "N/A"
    note_msg = ""

    my_team_str = team
    opp_team_str = 't2' if team == 't1' else 't1'
    opp_pending_col = f'{opp_team_str}_pending_list'
    opp_cup_state_col = f'{opp_team_str}_cup_state'

    current_pending = json.loads(getattr(match, opp_pending_col))
    teammate_hit_previously = (len(current_pending) > 0)
    is_second_shot = (match.current_turn % 2 != 0) if match.status == 'running' else False

    # Register Hit
    if res == 'Centro':
        for cup in bicchieri_colpiti:
            if cup not in current_pending: current_pending.append(cup)
        setattr(match, opp_pending_col, json.dumps(current_pending))

    # Apply Damage / End Turn
    should_apply_damage = is_second_shot or match.status.startswith('redemption')
    if should_apply_damage:
        current_active = json.loads(getattr(match, opp_cup_state_col))
        new_active = [c for c in current_active if c not in current_pending]
        setattr(match, opp_cup_state_col, json.dumps(new_active))
        if match.status == 'running' and teammate_hit_previously and (res == 'Centro'): note_msg = " [BALLS BACK! 🔥]"
        setattr(match, opp_pending_col, '[]')
    else:
        note_msg = " (Attesa compagno...)"

    # Status & Win Logic
    t1_s = json.loads(match.t1_cup_state);
    t2_s = json.loads(match.t2_cup_state)

    if match.status == 'running':
        if len(t1_s) == 0:
            match.status = 'redemption_t1'; match.redemption_shots_left = 2; note_msg += " [T1 REDEMPTION]"
        elif len(t2_s) == 0:
            match.status = 'redemption_t2'; match.redemption_shots_left = 2; note_msg += " [T2 REDEMPTION]"
        match.current_turn += 1

    elif match.status.startswith('redemption'):
        redeeming_team = match.status.split('_')[1]
        if res != 'Centro': match.redemption_shots_left -= 1

        target_cups = t1_s if redeeming_team == 't1' else t2_s
        if len(target_cups) == 0:
            start_overtime(match); note_msg += " [OVERTIME]"
        elif match.redemption_shots_left <= 0:
            finish_match(match, 't2' if redeeming_team == 't1' else 't1'); note_msg += " [FINITO]"

    update_game_state_counts(match)

    # Save Record
    new_rec = PlayerRecord(
        match_id=match.id, player_id=player.id,
        miss=("Sì" if res == "Miss" else "No"), bordo=("Sì" if res == "Bordo" else "No"),
        centro=("Sì" if res == "Centro" else "No"),
        bicchiere_colpito=hit_str, cups_own=len(t1_s) if team == 't1' else len(t2_s),
        cups_opp=len(t2_s) if team == 't1' else len(t1_s),
        note=note_msg, bicchieri_multipli=request.form.get('bicchieri_multipli'),
        formato=request.form.get('formato'), postazione=request.form.get('postazione'),
        bevanda=request.form.get('bevanda'),
        tiro_salvezza=('Sì' if 'tiro_salvezza' in request.form else 'No')
    )
    db.session.add(new_rec)
    db.session.commit()

    return redirect(url_for('main.index', match_id=match.id, player_name=player_name))


# --- MANAGEMENT ROUTES ---
@bp.route('/players')
def manage_players():
    return render_template('players.html', players=Player.query.order_by(Player.name).all())


@bp.route('/add_player', methods=['POST'])
def add_player():
    pn = request.form.get('player_name', '').strip()
    pwd = request.form.get('password')
    if pn and pwd and not Player.query.filter_by(name=pn).first():
        db.session.add(Player(name=pn, password=generate_password_hash(pwd)))
        db.session.commit()
    return redirect(url_for('main.manage_players'))


@bp.route('/delete_player/<int:id>', methods=['POST'])
def delete_player(id):
    db.session.delete(Player.query.get_or_404(id));
    db.session.commit()
    return redirect(url_for('main.manage_players'))


@bp.route('/edit/<player_name>/<int:id>', methods=['GET', 'POST'])
def edit_record(player_name, id):
    # NOTE: Ideally this should also take match_id, but we can look it up from the record
    record = PlayerRecord.query.get_or_404(id)
    return render_template('edit_record.html', record=record, player_name=player_name)  # simplified for brevity


@bp.route('/delete/<player_name>/<int:id>', methods=['POST'])
def delete_record(player_name, id):
    record = PlayerRecord.query.get_or_404(id)
    match_id = record.match_id
    db.session.delete(record)
    db.session.commit()
    return redirect(url_for('main.index', match_id=match_id, player_name=player_name))


@bp.route('/database-viewer')
def database_viewer():
    return render_template('admin_db.html', full_db=get_all_db_content())