from flask import render_template, session, redirect, url_for, flash
from app.main import bp
from app.models import Player, PlayerRecord  # Aggiunto PlayerRecord
from app.main.stats_extraction import get_player_stats 
from app.main.stats_calculations import (
    calculate_historical_percentages, 
    calculate_daily_percentages, 
    calculate_special_metrics,
    calculate_daily_trend,  
    calculate_hourly_trend,
    calculate_streak_metrics,
    calculate_partnership_metrics,
    calculate_shot_performance_metrics,
    calculate_insights,
    calculate_position_by_cups,
    calculate_format_heatmaps,
    calculate_success_by_opp_cups,
    calculate_comeback_and_flops,
    calculate_overtime_metrics
)
import json

# =============================================
# HELPER: FILTRO GIOCATORI INVALIDI
# =============================================
def get_valid_players():
    """Restituisce solo i giocatori reali, escludendo None/Nessuno."""
    all_players = Player.query.order_by(Player.name).all()
    return [p for p in all_players if p.name not in ['None', 'Nessuno', 'CLOSED'] 
            and 'admin' not in p.name.lower()]

# =============================================
# 1. GRAFICI PRINCIPALI (HOME)
# =============================================
@bp.route('/grafici')
def grafici_home():
    current_id = session.get('player_id')
    if not current_id:
        flash("Devi effettuare il login per vedere le statistiche.", "warning")
        return redirect(url_for('main.home'))

    player = Player.query.get(current_id)
    if not player:
        flash("Giocatore non trovato.", "danger")
        return redirect(url_for('main.home'))
        
    real_name = player.name
    dati_grezzi = get_player_stats(current_id)
    players = get_valid_players()

    historical_metrics = calculate_historical_percentages(dati_grezzi)
    daily_metrics = calculate_daily_percentages(dati_grezzi)
    special_metrics = calculate_special_metrics(dati_grezzi)
    trend_daily = calculate_daily_trend(dati_grezzi)
    trend_hourly = calculate_hourly_trend(dati_grezzi)

    return render_template('grafici/grafici_home.html', 
                           player_name=real_name, 
                           players=players,
                           stats_data=dati_grezzi["liste"],
                           counts=dati_grezzi["conteggi"],
                           historical=historical_metrics,
                           daily=daily_metrics,
                           special=special_metrics,
                           trend_daily=trend_daily,
                           trend_hourly=trend_hourly)

# =============================================
# 2. GRAFICI EXTRA (Curiosità e Analisi)
# =============================================
@bp.route('/grafici/extra')
def grafici_extra():
    current_id = session.get('player_id')
    if not current_id:
        return redirect(url_for('main.home'))
        
    dati_grezzi = get_player_stats(current_id) 
    players_list = get_valid_players()
    
    all_players_full = Player.query.all()
    all_players_dict = {str(p.id): p.name for p in all_players_full}
    all_players_dict.update({'0': '-', 'None': '-', 'None': 'Nessuno'})

    streaks = calculate_streak_metrics(dati_grezzi)
    partnerships = calculate_partnership_metrics(dati_grezzi, all_players_dict)
    
    keys_to_remove = ['None', 'Nessuno', '-', 'CLOSED']
    for key in keys_to_remove:
        if key in partnerships:
            del partnerships[key]

    shot_metrics = calculate_shot_performance_metrics(dati_grezzi)
    insights = calculate_insights(dati_grezzi, partnerships, shot_metrics)
    pos_by_cups = calculate_position_by_cups(dati_grezzi)
    comeback_flop_data = calculate_comeback_and_flops(dati_grezzi, all_players_dict)
    ot_metrics = calculate_overtime_metrics(dati_grezzi)

    hist = calculate_historical_percentages(dati_grezzi)
    daily = calculate_daily_percentages(dati_grezzi)

    delta_success = daily["daily_success_rate"] - hist["historical_success_rate"] if daily["matches"] > 0 else 0
    delta_rim = daily["daily_rim_rate"] - hist["historical_rim_rate"] if daily["matches"] > 0 else 0

    comparison = {
        "delta_success": round(delta_success, 1),
        "delta_rim": round(delta_rim, 1),
        "played_today": daily["matches"] > 0
    }

    return render_template('grafici/grafici_extra.html', 
                           player_name=session.get('player_name'),
                           players=players_list, 
                           stats_data=dati_grezzi["liste"],
                           counts=dati_grezzi["conteggi"],
                           streaks=streaks,
                           comebacks=comeback_flop_data["comebacks"],
                           flops=comeback_flop_data["flops"],
                           partnerships=partnerships,
                           ot_metrics=ot_metrics,
                           shot_metrics=shot_metrics,
                           pos_by_cups=pos_by_cups,
                           insights=insights,
                           comparison=comparison)

# =============================================
# 3. GRAFICI FORMATI (Heatmaps)
# =============================================
@bp.route('/grafici/formati')
def grafici_formati():
    current_id = session.get('player_id')
    if not current_id:
        return redirect(url_for('main.home'))
    
    dati_grezzi = get_player_stats(current_id)
    players = get_valid_players()
    
    success_by_cups = calculate_success_by_opp_cups(dati_grezzi)
    format_3d_data = calculate_format_heatmaps(dati_grezzi)
    
    return render_template('grafici/grafici_formati.html', 
                           player_name=session.get('player_name'),
                           players=players,
                           stats_data=dati_grezzi["liste"],
                           success_by_cups=success_by_cups,
                           format_3d_data=format_3d_data)

# =============================================
# 4. NOTE E DIARIO
# =============================================
@bp.route('/grafici/note/<player_name>')
def note_giocatore(player_name):
    if 'player_id' not in session:
        return redirect(url_for('main.login_page'))
    
    player_target = Player.query.filter_by(name=player_name).first_or_404()
    
    # IMPORTANTE: Usiamo PlayerRecord e ActiveMatch (nomi corretti dal tuo models.py)
    from app.models import PlayerRecord, ActiveMatch 
    
    # Recuperiamo i tiri con note
    note_records = PlayerRecord.query.filter(
        PlayerRecord.player_id == player_target.id,
        PlayerRecord.note != None,
        PlayerRecord.note != ""
    ).order_by(PlayerRecord.timestamp.desc()).all()
    
    # Mappa veloce per trasformare gli ID in nomi
    all_players_map = {p.id: p.name for p in Player.query.all()}
    all_players_map[None] = "-"

    enriched_notes = []
    for rec in note_records:
        # Recuperiamo i nomi usando gli ID salvati nel record (più sicuro e veloce)
        compagno = all_players_map.get(rec.teammate_id, "-")
        
        # Gestione avversari (potevano essere 1 o 2)
        opp1 = all_players_map.get(rec.opponent1_id, "-")
        opp2 = all_players_map.get(rec.opponent2_id, "-")
        
        if opp2 != "-":
            avversari = f"{opp1} & {opp2}"
        else:
            avversari = opp1

        enriched_notes.append({
            'rec': rec,
            'compagno': compagno,
            'avversari': avversari,
            'colpiti_list': rec.bicchiere_colpito.split(',') if rec.bicchiere_colpito else []
        })
    
    players = get_valid_players()

    return render_template('grafici/note.html', 
                           player_name=player_name, 
                           notes=enriched_notes,
                           players=players)