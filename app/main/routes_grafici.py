from flask import render_template, session, redirect, url_for, flash
from app.main import bp
from app.models import Player
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
    calculate_success_by_opp_cups
)
import json

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

    # --- LISTA GIOCATORI (Per le icone nell'header) ---
    players = Player.query.all()

    # Calcoli Esistenti
    historical_metrics = calculate_historical_percentages(dati_grezzi)
    daily_metrics = calculate_daily_percentages(dati_grezzi)
    special_metrics = calculate_special_metrics(dati_grezzi)

    # Trend Temporali
    trend_daily = calculate_daily_trend(dati_grezzi)
    trend_hourly = calculate_hourly_trend(dati_grezzi)

    raw_lists = dati_grezzi["liste"]

    return render_template('grafici/grafici_home.html', 
                           player_name=real_name, 
                           # --- PASSAGGIO LISTA GIOCATORI ---
                           players=players,
                           # ---------------------------------
                           stats_data=raw_lists,
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
    
    # --- LISTA GIOCATORI (Per le icone nell'header) ---
    players_list = Player.query.all()
    
    # Creiamo il dizionario per i calcoli statistici
    all_players_dict = {str(p.id): p.name for p in players_list}
    all_players_dict.update({'0': '-', 'None': '-'})

    # Calcoli Avanzati
    streaks = calculate_streak_metrics(dati_grezzi)
    partnerships = calculate_partnership_metrics(dati_grezzi, all_players_dict)
    shot_metrics = calculate_shot_performance_metrics(dati_grezzi)
    insights = calculate_insights(dati_grezzi, partnerships, shot_metrics)
    pos_by_cups = calculate_position_by_cups(dati_grezzi)

    # Calcolo Delta (Oggi vs Storico)
    hist = calculate_historical_percentages(dati_grezzi)
    daily = calculate_daily_percentages(dati_grezzi)

    if daily["matches"] > 0:
        delta_success = daily["daily_success_rate"] - hist["historical_success_rate"]
        delta_rim = daily["daily_rim_rate"] - hist["historical_rim_rate"]
    else:
        delta_success = 0
        delta_rim = 0

    comparison = {
        "delta_success": round(delta_success, 1),
        "delta_rim": round(delta_rim, 1),
        "played_today": daily["matches"] > 0
    }

    return render_template('grafici/grafici_extra.html', 
                           player_name=session.get('player_name'),
                           # --- PASSAGGIO LISTA GIOCATORI ---
                           players=players_list, 
                           # ---------------------------------
                           stats_data=dati_grezzi["liste"],
                           counts=dati_grezzi["conteggi"],
                           streaks=streaks,
                           partnerships=partnerships,
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
    
    # --- LISTA GIOCATORI (Per le icone nell'header) ---
    players = Player.query.all()
    
    # Calcoli Formati
    success_by_cups = calculate_success_by_opp_cups(dati_grezzi)
    format_3d_data = calculate_format_heatmaps(dati_grezzi)
    
    return render_template('grafici/grafici_formati.html', 
                           player_name=session.get('player_name'),
                           # --- PASSAGGIO LISTA GIOCATORI ---
                           players=players,
                           # ---------------------------------
                           stats_data=dati_grezzi["liste"],
                           success_by_cups=success_by_cups,
                           format_3d_data=format_3d_data)