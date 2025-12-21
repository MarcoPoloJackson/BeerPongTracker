def safe_division(numerator, denominator):
    """
    Equivale al SE.ERRORE(x/y; 0) di Excel.
    Se il denominatore è 0, restituisce 0.
    """
    return (numerator / denominator * 100) if denominator > 0 else 0.0

def calculate_historical_percentages(data):
    """
    Calcola le percentuali storiche basandosi sui conteggi totali già estratti.
    Corrisponde ai grafici generali.
    """
    counts = data["conteggi"]
    
    # 1. Percentuale di successo storica
    # Excel: Centri / (Miss + Bordi + Centri) -> Centri / Tiri Totali
    perc_successo = safe_division(counts["centri"], counts["tiri_totali"])
    
    # 2. Percentuale di bordi su tiri sbagliati Storica
    # Excel: Bordi / (Miss + Bordi)
    # Nota: "Miss" nel DB è il tiro completamente fuori, "Bordo" è il ferro.
    # Insieme formano i tiri che non sono entrati.
    tiri_non_entrati = counts["miss"] + counts["bordi"]
    perc_bordo_su_sbagliati = safe_division(counts["bordi"], tiri_non_entrati)

    return {
        "historical_success_rate": round(perc_successo, 2),
        "historical_rim_rate": round(perc_bordo_su_sbagliati, 2)
    }

def calculate_daily_percentages(data):
    """
    Calcola le statistiche riferite SOLO all'ultima giornata di gioco (MAX data).
    Include: Tiri, Partite giocate, Vittorie e Win Rate giornaliero.
    """
    lists = data["liste"]
    dates = lists.get("match_date", [])
    
    if not dates:
        return {
            "daily_success_rate": 0.0,
            "daily_rim_rate": 0.0,
            "last_date": None,
            "counts": { "centri": 0, "bordi": 0, "miss": 0, "totali": 0 },
            "matches": 0,
            "wins": 0,
            "win_rate": 0.0
        }

    last_date = max(dates)
    
    daily_stats = {
        "centri": 0, "bordi": 0, "miss": 0, "totali": 0
    }
    
    # Per calcolare partite e vittorie giornaliere
    daily_match_ids = set()
    daily_wins_count = 0
    processed_matches = set() # Per evitare di contare la vittoria più volte per lo stesso match

    # Recuperiamo le liste necessarie
    m_ids = lists.get("match_ids", [])
    results = lists.get("match_result", [])
    centri = lists.get("centro", [])
    bordi = lists.get("bordo", [])
    misses = lists.get("miss", [])

    for i, date_val in enumerate(dates):
        if date_val == last_date:
            # 1. Conteggio Tiri
            daily_stats["totali"] += 1
            if is_true(centri[i]): 
                daily_stats["centri"] += 1
            elif is_true(bordi[i]): 
                daily_stats["bordi"] += 1
            else: 
                daily_stats["miss"] += 1

            # 2. Conteggio Partite e Vittorie
            if i < len(m_ids):
                m_id = m_ids[i]
                daily_match_ids.add(m_id)
                
                # Se non abbiamo ancora processato questo match, controlliamo se è una vittoria
                if m_id not in processed_matches and i < len(results):
                    res = results[i]
                    if res in ["Win", "Vittoria"]:
                        daily_wins_count += 1
                    processed_matches.add(m_id)

    # Calcoli finali
    daily_matches_played = len(daily_match_ids)
    daily_win_rate = safe_division(daily_wins_count, daily_matches_played)

    perc_successo_daily = safe_division(daily_stats["centri"], daily_stats["totali"])
    tiri_non_entrati_daily = daily_stats["miss"] + daily_stats["bordi"]
    perc_bordo_daily = safe_division(daily_stats["bordi"], tiri_non_entrati_daily)

    return {
        "daily_success_rate": round(perc_successo_daily, 2),
        "daily_rim_rate": round(perc_bordo_daily, 2),
        "last_date": last_date,
        "counts": daily_stats,
        # NUOVI CAMPI PER I WIDGET
        "matches": daily_matches_played,
        "wins": daily_wins_count,
        "win_rate": round(daily_win_rate, 1)
    }


def is_true(value):
    """Helper per gestire i vari formati di vero nel DB (Sì, True, boolean)"""
    return value in ['Sì', 'Si', 'True', True, 1]

# app/main/stats_calculations.py

def calculate_special_metrics(data):
    """
    Calcola le metriche speciali: Serie (Storiche vs Oggi), Clutch rate e Multi-hit.
    """
    lists = data["liste"]
    dates = lists.get("match_date", [])
    last_date = max(dates) if dates else None
    
    # --- 1. CALCOLO SERIE (STREAKS) STORICHE E GIORNALIERE ---
    # Storiche
    max_c_hist = 0
    curr_c_hist = 0
    max_m_hist = 0
    curr_m_hist = 0
    
    # Giornaliere
    max_c_daily = 0
    curr_c_daily = 0
    max_m_daily = 0
    curr_m_daily = 0
    
    # Iteriamo usando l'indice per accedere contemporaneamente a esiti e date
    for i in range(len(lists["centro"])):
        is_c = is_true(lists["centro"][i])
        current_date = dates[i]
        
        # LOGICA STORICA
        if is_c:
            curr_c_hist += 1
            max_m_hist = max(max_m_hist, curr_m_hist)
            curr_m_hist = 0
        else:
            max_c_hist = max(max_c_hist, curr_c_hist)
            curr_c_hist = 0
            curr_m_hist += 1
            
        # LOGICA GIORNALIERA (Solo se il tiro è dell'ultima data)
        if last_date and current_date == last_date:
            if is_c:
                curr_c_daily += 1
                max_m_daily = max(max_m_daily, curr_m_daily)
                curr_m_daily = 0
            else:
                max_c_daily = max(max_c_daily, curr_c_daily)
                curr_c_daily = 0
                curr_m_daily += 1

    # Controllo finale per le serie che finiscono all'ultimo tiro dell'elenco
    max_c_hist = max(max_c_hist, curr_c_hist)
    max_m_hist = max(max_m_hist, curr_m_hist)
    max_c_daily = max(max_c_daily, curr_c_daily)
    max_m_daily = max(max_m_daily, curr_m_daily)

    # --- 2. PERCENTUALE SALVEZZA (CLUTCH RATE) ---
    clutch_attempts = 0
    clutch_made = 0
    if "tiro_salvezza" in lists:
        for salvezza, centro in zip(lists["tiro_salvezza"], lists["centro"]):
            if is_true(salvezza):
                clutch_attempts += 1
                if is_true(centro):
                    clutch_made += 1
    
    clutch_rate = safe_division(clutch_made, clutch_attempts)

    # --- 3. MULTI-HIT (FORZA PLURALE) ---
    multi_counts = {}
    plural_map = {
        "2": "Doppi", "3": "Tripli", "4": "Quadrupli", "5": "Quintupli", "6": "Sestupli",
        "Doppio": "Doppi", "Triplo": "Tripli", "Quadruplo": "Quadrupli", 
        "Quintuplo": "Quintupli", "Sestuplo": "Sestupli"
    }
    
    if "bicchieri_multipli" in lists:
        for val in lists["bicchieri_multipli"]:
            s_val = str(val).strip().capitalize()
            if s_val in ['-', '1', '0', 'None', '', 'False', 'Nan', 'Singolo']:
                continue

            final_label = plural_map.get(s_val)
            if not final_label and s_val.isdigit() and int(s_val) > 1:
                final_label = f"{s_val}-Hits"

            if final_label:
                multi_counts[final_label] = multi_counts.get(final_label, 0) + 1

    return {
        "longest_streak_success": max_c_hist,
        "daily_streak_success": max_c_daily,
        "longest_streak_fail": max_m_hist,
        "daily_streak_fail": max_m_daily,
        "clutch_rate": round(clutch_rate, 1),
        "clutch_attempts": clutch_attempts,
        "clutch_made": clutch_made,
        "multi_hits": multi_counts
    }


def calculate_daily_trend(data):
    """
    GRAFICO 1: Evoluzione Giornaliera.
    X: Data
    Y1: % Successo
    Y2: % Bordi (su errori)
    """
    lists = data["liste"]
    # Usiamo un dizionario per aggregare i dati per data: "YYYY-MM-DD": {centri: 0, bordi: 0, miss: 0}
    daily_agg = {}

    # 1. Aggregazione
    for date_val, centro, bordo, miss in zip(lists["match_date"], lists["centro"], lists["bordo"], lists["miss"]):
        if not date_val: continue
        
        if date_val not in daily_agg:
            daily_agg[date_val] = {"centri": 0, "bordi": 0, "miss": 0, "totali": 0}
        
        daily_agg[date_val]["totali"] += 1
        
        if is_true(centro):
            daily_agg[date_val]["centri"] += 1
        elif is_true(bordo):
            daily_agg[date_val]["bordi"] += 1
        else:
            daily_agg[date_val]["miss"] += 1

    # 2. Ordinamento per data (ascendente)
    sorted_dates = sorted(daily_agg.keys())

    # 3. Creazione Liste per il Grafico
    labels_x = []
    dataset_success = []
    dataset_rim = []

    for d in sorted_dates:
        stats = daily_agg[d]
        
        # Calcolo % Successo: Centri / Totali
        perc_succ = safe_division(stats["centri"], stats["totali"])
        
        # Calcolo % Bordi: Bordi / (Miss + Bordi) -> Bordi / (Totali - Centri)
        non_centri = stats["miss"] + stats["bordi"]
        perc_rim = safe_division(stats["bordi"], non_centri)

        from datetime import datetime
        date_obj = datetime.strptime(d, "%Y-%m-%d")
        labels_x.append(date_obj.strftime("%y-%m-%d"))
        dataset_success.append(round(perc_succ, 2))
        dataset_rim.append(round(perc_rim, 2))

    return {
        "dates": labels_x,
        "trend_success": dataset_success,
        "trend_rim": dataset_rim
    }

def calculate_hourly_trend(data):
    """
    GRAFICO 2: Analisi Oraria (Storico vs Oggi).
    X: Ora (0-23)
    Y1: % Successo Storica
    Y2: % Bordi Storica
    Y3: % Successo Oggi
    Y4: % Bordi Oggi
    """
    lists = data["liste"]
    dates = lists["match_date"]
    
    # Troviamo la data di oggi (l'ultima presente nel DB)
    last_date = max(dates) if dates else None

    # Dizionario aggregazione: { 18: {hist_c:0, hist_b:0..., today_c:0...}, 19: ... }
    hourly_agg = {}

    for date_val, hour_val, centro, bordo, miss in zip(lists["match_date"], lists["match_hour"], lists["centro"], lists["bordo"], lists["miss"]):
        # Convertiamo l'ora in intero per sicurezza e ordinamento
        try:
            h = int(hour_val)
        except (ValueError, TypeError):
            continue # Salta se l'ora non è valida

        if h not in hourly_agg:
            hourly_agg[h] = {
                "hist_centri": 0, "hist_bordi": 0, "hist_miss": 0, "hist_tot": 0,
                "today_centri": 0, "today_bordi": 0, "today_miss": 0, "today_tot": 0
            }

        # --- DATI STORICI (Sempre incrementati) ---
        stats = hourly_agg[h]
        stats["hist_tot"] += 1
        
        is_c = is_true(centro)
        is_b = is_true(bordo)
        
        if is_c: stats["hist_centri"] += 1
        elif is_b: stats["hist_bordi"] += 1
        else: stats["hist_miss"] += 1

        # --- DATI OGGI (Incrementati solo se la data coincide) ---
        if last_date and date_val == last_date:
            stats["today_tot"] += 1
            if is_c: stats["today_centri"] += 1
            elif is_b: stats["today_bordi"] += 1
            else: stats["today_miss"] += 1

    # 2. Ordinamento per Ora (0, 1, ... 23)
    sorted_hours = sorted(hourly_agg.keys())

    # 3. Creazione Liste
    labels_x = []         # Ore (es. "18:00")
    hist_success = []
    hist_rim = []
    today_success = []
    today_rim = []

    for h in sorted_hours:
        # ... all'interno del ciclo for h in sorted_hours:
        s = hourly_agg[h]
    
        # --- Calcoli Storici (Rimangono invariati) ---
        h_succ = safe_division(s["hist_centri"], s["hist_tot"])
        h_non_centri = s["hist_miss"] + s["hist_bordi"]
        h_rim = safe_division(s["hist_bordi"], h_non_centri)

        # --- Calcoli Oggi (MODIFICATI PER GESTIRE I DATI MANCANTI) ---
        # Successo Oggi: se tiri totali oggi > 0 calcola, altrimenti None
        if s["today_tot"] > 0:
            t_succ = round((s["today_centri"] / s["today_tot"] * 100), 2)
        else:
            t_succ = None  # <--- Fondamentale: non manda a zero

        # Bordi Oggi: se tiri non entrati oggi > 0 calcola, altrimenti None
        t_non_centri = s["today_miss"] + s["today_bordi"]
        if t_non_centri > 0:
            t_rim = round((s["today_bordi"] / t_non_centri * 100), 2)
        else:
            t_rim = None  # <--- Fondamentale: non manda a zero

        labels_x.append(str(h))
        hist_success.append(round(h_succ, 2))
        hist_rim.append(round(h_rim, 2))
        today_success.append(t_succ)
        today_rim.append(t_rim)

    return {
        "hours": labels_x,
        "hist_success": hist_success,
        "hist_rim": hist_rim,
        "today_success": today_success,
        "today_rim": today_rim
    }

def calculate_streak_metrics(data):
    """
    Calcola le serie massime (storiche e giornaliere) per Bordi e Miss.
    Equivale alle formule ARRAYFORMULA(MAX(LUNGHEZZA(SPLIT...))) di Excel.
    """
    lists = data["liste"]
    dates = lists["match_date"]
    last_date = max(dates) if dates else None

    def get_max_streaks(outcome_list, date_filter=None):
        max_streak = 0
        current_streak = 0
        for i, val in enumerate(outcome_list):
            # Se c'è un filtro data, controlla se la data del tiro corrisponde
            if date_filter and dates[i] != date_filter:
                current_streak = 0
                continue
            
            if is_true(val):
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0
        return max_streak

    return {
        "rim_streak_hist": get_max_streaks(lists["bordo"]),
        "rim_streak_daily": get_max_streaks(lists["bordo"], last_date),
        "miss_streak_hist": get_max_streaks(lists["miss"]),
        "miss_streak_daily": get_max_streaks(lists["miss"], last_date)
    }

def calculate_partnership_metrics(data, name_map):
    lists = data["liste"]
    teammate_stats = {}
    opponent_stats = {}

    t_list = lists.get("teammate_ids", [])
    o_list = lists.get("opponent1_ids", [])
    res_list = lists.get("match_result", [])

    for compagno, risultato in zip(t_list, res_list):
        c_id = str(compagno).strip()
        if c_id in ["-", "None", "0", "nan", "[]"] or not c_id:
            continue
            
        # Traduci ID in Nome usando la mappa
        nome_reale = name_map.get(c_id, f"Player {c_id}")
        
        if nome_reale not in teammate_stats:
            teammate_stats[nome_reale] = {"totali": 0, "vittorie": 0}
        
        teammate_stats[nome_reale]["totali"] += 1
        if risultato == "Win":
            teammate_stats[nome_reale]["vittorie"] += 1

    for avversario, risultato in zip(o_list, res_list):
        a_id = str(avversario).strip()
        if a_id in ["-", "None", "0", "nan", "[]"] or not a_id:
            continue
            
        nome_reale = name_map.get(a_id, f"Player {a_id}")
            
        if nome_reale not in opponent_stats:
            opponent_stats[nome_reale] = {"totali": 0, "sconfitte": 0}
        
        opponent_stats[nome_reale]["totali"] += 1
        if risultato == "Loss":
            opponent_stats[nome_reale]["sconfitte"] += 1

    # Formattazione per il frontend (ordinata)
    win_rate_teammate = sorted(
        [{"nome": n, "percentuale": round(safe_division(s["vittorie"], s["totali"]), 1)} 
         for n, s in teammate_stats.items()],
        key=lambda x: x["percentuale"], reverse=True
    )

    loss_rate_opponent = sorted(
        [{"nome": n, "percentuale": round(safe_division(s["sconfitte"], s["totali"]), 1)} 
         for n, s in opponent_stats.items()],
        key=lambda x: x["percentuale"], reverse=True
    )

    return {
        "partners": {
            "labels": [x["nome"] for x in win_rate_teammate],
            "values": [x["percentuale"] for x in win_rate_teammate]
        },
        "enemies": {
            "labels": [x["nome"] for x in loss_rate_opponent],
            "values": [x["percentuale"] for x in loss_rate_opponent]
        }
    }

def calculate_shot_performance_metrics(data):
    lists = data["liste"]
    dates = lists.get("match_date", [])
    match_ids = lists.get("match_ids", [])
    
    last_date = max(dates) if dates else None

    # --- 1. CONTEGGIO TIRI PER PARTITA ---
    shots_per_match = {}      # {match_id: numero_tiri}
    match_date_map = {}       # {match_id: data_partita}

    # Iteriamo su tutti i tiri per contarli raggruppandoli per Match ID
    for i, m_id in enumerate(match_ids):
        if not m_id: continue
        
        if m_id not in shots_per_match:
            shots_per_match[m_id] = 0
            if i < len(dates):
                match_date_map[m_id] = dates[i]
        
        shots_per_match[m_id] += 1

    # --- 2. CALCOLO RECORD (MAX TIRI) ---
    # Storico
    max_shots_hist = 0
    if shots_per_match:
        max_shots_hist = max(shots_per_match.values())

    # Giornaliero
    max_shots_daily = 0
    if last_date:
        # Filtriamo solo i conteggi delle partite giocate nell'ultima data
        daily_counts = [
            count for m_id, count in shots_per_match.items() 
            if match_date_map.get(m_id) == last_date
        ]
        if daily_counts:
            max_shots_daily = max(daily_counts)

    # --- 3. LOGICA ESISTENTE (Shot Trend & Medie) ---
    # (Questa parte rimane invariata per alimentare il grafico e la media)
    shot_agg = {}
    c_own_list = lists.get("cups_own", [])
    c_opp_list = lists.get("cups_opp", [])

    for i in range(len(lists.get("shot_numbers", []))):
        sn = lists["shot_numbers"][i]
        if sn is None or sn > 30: continue
        sn = int(sn)
        if sn not in shot_agg:
            shot_agg[sn] = {"h_c": 0, "h_t": 0, "t_c": 0, "t_t": 0, "cups": [], "gaps": []}
        
        is_c = is_true(lists["centro"][i])
        shot_agg[sn]["h_t"] += 1
        if is_c: shot_agg[sn]["h_c"] += 1
        
        if c_opp_list[i] is not None:
            shot_agg[sn]["cups"].append(int(c_opp_list[i]))
            
        if dates[i] == last_date:
            shot_agg[sn]["t_t"] += 1
            if is_c: shot_agg[sn]["t_c"] += 1

        if c_own_list[i] is not None and c_opp_list[i] is not None:
            try:
                gap = int(c_own_list[i]) - int(c_opp_list[i])
                shot_agg[sn]["gaps"].append(gap)
            except: pass

    sorted_nums = sorted(shot_agg.keys())
    
    gap_values = []
    for n in sorted_nums:
        if shot_agg[n]["gaps"]:
            avg_gap = sum(shot_agg[n]["gaps"]) / len(shot_agg[n]["gaps"])
            gap_values.append(round(avg_gap, 2))
        else:
            gap_values.append(0)
    
    labels = [f"{n}°" for n in sorted_nums]
    values_hist = [round(safe_division(shot_agg[n]["h_c"], shot_agg[n]["h_t"]), 1) for n in sorted_nums]
    
    values_today = []
    phase_changes = []
    last_rounded_cups = None

    for n in sorted_nums:
        if shot_agg[n]["t_t"] > 0:
            values_today.append(round(safe_division(shot_agg[n]["t_c"], shot_agg[n]["t_t"]), 1))
        else:
            values_today.append(None)
        
        if shot_agg[n]["cups"]:
            avg_cups = sum(shot_agg[n]["cups"]) / len(shot_agg[n]["cups"])
            current_rounded = round(avg_cups)
            if last_rounded_cups is not None and current_rounded != last_rounded_cups:
                phase_changes.append({"shot": n, "label": f"{current_rounded} cups"})
            last_rounded_cups = current_rounded

    unique_m_hist = len(set(match_ids))
    avg_hist = round(len(lists.get("match_ids", [])) / unique_m_hist, 1) if unique_m_hist > 0 else 0
    
    daily_shots_idx = [i for i, d in enumerate(dates) if d == last_date]
    daily_m_ids = [match_ids[i] for i in daily_shots_idx]
    unique_m_daily = len(set(daily_m_ids)) if daily_m_ids else 0
    avg_daily = round(len(daily_shots_idx) / unique_m_daily, 1) if unique_m_daily > 0 else 0

    return {
        "avg_shots_per_match": avg_hist,
        "avg_shots_daily": avg_daily,
        
        # --- NUOVI CAMPI AGGIUNTI ---
        "max_shots_match_hist": max_shots_hist,
        "max_shots_match_daily": max_shots_daily,
        # ----------------------------

        "shot_number_trend": {
            "labels": labels,
            "values_hist": values_hist,
            "values_today": values_today,
            "phase_changes": phase_changes,
            "cup_gap": gap_values
        }
    }

def calculate_insights(data, partnerships, shot_metrics):
    """
    Calcola i 'Fun Facts' o consigli tattici basati sui dati.
    Gestisce i pareggi unendo i nomi con ' / '.
    """
    lists = data["liste"]
    
    # --- HELPER INTERNO PER TROVARE I MIGLIORI ---
    def get_best_category(category_list, outcome_list, min_attempts=2):
        stats = {}
        for cat, outcome in zip(category_list, outcome_list):
            if str(cat) in ['-', 'None', 'nan', '']: continue
            
            if cat not in stats: stats[cat] = {'made': 0, 'total': 0}
            stats[cat]['total'] += 1
            if is_true(outcome): stats[cat]['made'] += 1
            
        # Troviamo il max rate
        max_rate = -1
        best_names = []
        
        for cat, s in stats.items():
            if s['total'] < min_attempts: continue # Ignora se ha tirato solo 1 volta
            rate = (s['made'] / s['total']) * 100
            
            if rate > max_rate:
                max_rate = rate
                best_names = [cat]
            elif rate == max_rate:
                best_names.append(cat)
                
        if not best_names: return "-", 0
        return " / ".join(best_names), round(max_rate, 1)

    # 1. MIGLIOR POSTAZIONE (Winrate inteso come % tiro)
    best_pos_name, best_pos_rate = get_best_category(lists.get("postazione", []), lists.get("centro", []))

    # 2. MIGLIOR DRINK (Winrate inteso come % tiro)
    best_drink_name, best_drink_rate = get_best_category(lists.get("bevanda", []), lists.get("centro", []))

    # 3. MIGLIOR COMPAGNO (Match Winrate)
    # Usiamo i dati già calcolati in partnerships
    best_partner_name = "-"
    best_partner_rate = 0
    if partnerships["partners"]["values"]:
        max_val = max(partnerships["partners"]["values"])
        winners = [
            label for label, val in zip(partnerships["partners"]["labels"], partnerships["partners"]["values"]) 
            if val == max_val
        ]
        best_partner_name = " / ".join(winners)
        best_partner_rate = max_val

    # 4. PEGGIOR NEMICO (Match Loss Rate)
    worst_enemy_name = "-"
    worst_enemy_rate = 0
    if partnerships["enemies"]["values"]:
        max_val = max(partnerships["enemies"]["values"])
        losers = [
            label for label, val in zip(partnerships["enemies"]["labels"], partnerships["enemies"]["values"]) 
            if val == max_val
        ]
        worst_enemy_name = " / ".join(losers)
        worst_enemy_rate = max_val

    # 5. MIGLIOR TIRO (Shot Number Success)
    best_shot_num = "-"
    best_shot_rate = 0
    # Usiamo shot_metrics['shot_number_trend']
    trend = shot_metrics.get("shot_number_trend", {})
    if trend and trend.get("values_hist"):
        # values_hist è una lista di float. Troviamo il max.
        # labels sono ["1°", "2°"...]
        valid_values = [v for v in trend["values_hist"] if v is not None]
        if valid_values:
            max_val = max(valid_values)
            winners = []
            for i, val in enumerate(trend["values_hist"]):
                if val == max_val:
                    # Estraiamo il numero dalla label "1°" -> "1"
                    lbl = trend["labels"][i].replace("°", "")
                    winners.append(lbl)
            
            best_shot_num = " / ".join(winners)
            best_shot_rate = max_val

    # 6. PRIMO TIRO (Shot #1 Success)
    first_shot_rate = 0
    if trend and trend.get("values_hist") and len(trend["values_hist"]) > 0:
        first_shot_rate = trend["values_hist"][0] # Il primo elemento è il tiro 1

    # --- 7. GIORNATA MIGLIORE (Best Day) ---
    dates = lists.get("match_date", [])
    outcomes = lists.get("centro", [])
    
    day_stats = {}
    for d, out in zip(dates, outcomes):
        if not d: continue
        if d not in day_stats: day_stats[d] = {'made': 0, 'total': 0}
        day_stats[d]['total'] += 1
        if is_true(out): day_stats[d]['made'] += 1
        
    best_day_date = "-"
    best_day_rate = 0
    
    for d, s in day_stats.items():
        # Filtro: almeno 5 tiri per considerare la giornata valida statistica
        if s['total'] < 5: continue 
        
        rate = (s['made'] / s['total']) * 100
        
        # Cerchiamo la % più alta. 
        # In caso di pareggio, vince quella più recente (o la prima trovata dipendendo dall'ordine)
        if rate > best_day_rate:
            best_day_rate = rate
            best_day_date = d
            
    # Formattazione Data (da YYYY-MM-DD a DD/MM/YYYY)
    if best_day_date != "-":
        try:
            from datetime import datetime
            dt_obj = datetime.strptime(best_day_date, "%Y-%m-%d")
            best_day_date = dt_obj.strftime("%d/%m/%Y")
        except:
            pass # Se fallisce, lascia il formato originale

    return {
        "best_pos": best_pos_name,
        "best_pos_rate": best_pos_rate,
        "best_drink": best_drink_name,
        "best_drink_rate": best_drink_rate,
        "best_partner": best_partner_name,
        "best_partner_rate": best_partner_rate,
        "worst_enemy": worst_enemy_name,
        "worst_enemy_rate": worst_enemy_rate,
        "best_shot_num": best_shot_num,
        "best_shot_rate": best_shot_rate,
        "first_shot_rate": first_shot_rate,
        "best_day_date": best_day_date,
        "best_day_rate": round(best_day_rate, 1)
    }

def calculate_position_by_cups(data):
    """
    Calcola la % di successo per ogni postazione (SX, CEN, DX) 
    in base al numero di bicchieri avversari rimasti (10, 9... 1).
    """
    lists = data["liste"]
    
    # Dizionario di appoggio: { numero_bicchieri: { 'Sinistra': {made, total}, ... } }
    stats = {}
    
    # Mappa per normalizzare i nomi delle postazioni
    pos_map = {
        "Sinistra": "Sinistra", "SX": "Sinistra", "Sx": "Sinistra",
        "Destra": "Destra", "DX": "Destra", "Dx": "Destra",
        "Centrale": "Centrale", "Centro": "Centrale", "CEN": "Centrale"
    }

    cups_list = lists.get("cups_opp", [])
    pos_list = lists.get("postazione", [])
    hit_list = lists.get("centro", [])

    # 1. Aggregazione dati
    for cups, pos, hit in zip(cups_list, pos_list, hit_list):
        # Filtri di validità
        if not cups or str(cups) in ['-', 'None']: continue
        if not pos or str(pos) in ['-', 'None']: continue
        
        try:
            c_num = int(cups)
        except:
            continue
            
        # Ignoriamo casi strani (es. 20 bicchieri) per pulizia grafico
        if c_num > 10 or c_num < 1: continue

        # Normalizza postazione
        clean_pos = pos_map.get(str(pos).strip(), None)
        if not clean_pos: continue

        # Inizializza struttura se manca
        if c_num not in stats:
            stats[c_num] = {
                "Sinistra": {"m": 0, "t": 0},
                "Centrale": {"m": 0, "t": 0},
                "Destra": {"m": 0, "t": 0}
            }
        
        stats[c_num][clean_pos]["t"] += 1
        if is_true(hit):
            stats[c_num][clean_pos]["m"] += 1

    # 2. Preparazione dati per Chart.js
    # Ordiniamo i bicchieri da 10 a 1 (scendendo, come in partita)
    sorted_cups = sorted(stats.keys(), reverse=True) 
    
    data_sx = []
    data_cen = []
    data_dx = []

    for c in sorted_cups:
        row = stats[c]
        
        # Helper per calcolare % o mettere None se 0 tiri
        def get_perc(p_key):
            if row[p_key]["t"] > 0:
                return round((row[p_key]["m"] / row[p_key]["t"]) * 100, 1)
            return None # None non disegna il punto nel grafico

        data_sx.append(get_perc("Sinistra"))
        data_cen.append(get_perc("Centrale"))
        data_dx.append(get_perc("Destra"))

    return {
        "labels": sorted_cups, # Asse X (10, 9, 8...)
        "sx": data_sx,
        "cen": data_cen,
        "dx": data_dx
    }

def calculate_format_heatmaps(data):
    """
    Calcola le percentuali per i grafici 3D.
    - COORDINATE CORRETTE: Y=0 è la parte bassa (vicino al giocatore).
    - EXCLUDE: Singolo Centrale.
    - FIX: Alias per Linea Verticale.
    - ORDER: Piramide, Rombo, Triangolo, Linea Verticale, Linea Orizzontale.
    """
    lists = data.get("liste", {})
    
    # 1. DEFINIZIONE LAYOUT
    layout_coords = {
        "Piramide": {
            "1 Cen": [1, 0],
            "2 Sx": [0.5, 1], "2 Dx": [1.5, 1], 
            "3 Sx": [0, 2], "3 Cen": [1, 2], "3 Dx": [2, 2]
        },
        "Rombo": {
            "R1 Cen": [1, 0], 
            "R2 Sx": [0, 1], "R2 Dx": [2, 1], 
            "R3 Cen": [1, 2]
        },
        "Triangolo": {
            "T1 Cen": [1, 0], 
            "T2 Sx": [0.5, 1], "T2 Dx": [1.5, 1]
        },
        "Linea Verticale": { 
            "LV 1": [0, 0], 
            "LV 2": [0, 1] 
        },
        "Linea Orizzontale": { 
            "LO Sx": [0, 0], "LO Dx": [1, 0] 
        }
    }

    # 2. NORMALIZZAZIONE
    normalized_layouts = {}
    for fmt_key, cups_map in layout_coords.items():
        fmt_low = fmt_key.lower().strip()
        normalized_layouts[fmt_low] = {
            "real_name": fmt_key,
            "cups": {c.lower().replace(" ", ""): c for c in cups_map.keys()}
        }
    
    # --- ALIAS E FIX ---
    if "linea verticale" in normalized_layouts:
        normalized_layouts["altro"] = normalized_layouts["linea verticale"]
        normalized_layouts["lineaverticale"] = normalized_layouts["linea verticale"]
        target = normalized_layouts["linea verticale"]["cups"]
        target["1"] = "LV 1"; target["2"] = "LV 2"; target["lv1"] = "LV 1"; target["lv2"] = "LV 2"

    if "piramide" in normalized_layouts:
        normalized_layouts["piramide"]["cups"]["1"] = "1 Cen"

    # 3. RECUPERO DATI
    formats_list = lists.get("formato", []) or []
    hits_list = lists.get("bicchiere_colpito", []) or []

    stats = {}
    format_totals = {}

    # 4. CICLO ELABORAZIONE
    for fmt, hit_str in zip(formats_list, hits_list):
        if not fmt or str(fmt) in ['-', 'None', '']: continue
        if not hit_str or str(hit_str) in ['-', 'None', 'N/A', '', '[]']: continue

        fmt_clean = str(fmt).lower().strip()
        if fmt_clean == 'altro':
            if '1' in str(hit_str) or '2' in str(hit_str): fmt_clean = 'linea verticale'

        if fmt_clean in normalized_layouts:
            real_fmt = normalized_layouts[fmt_clean]["real_name"]
            cups_hit = [c.strip() for c in str(hit_str).split(',') if c.strip()]
            
            for cup in cups_hit:
                cup_clean = cup.lower().replace(" ", "")
                target_cups_map = normalized_layouts[fmt_clean]["cups"]
                
                if cup_clean in target_cups_map:
                    real_cup_name = target_cups_map[cup_clean]
                    if real_fmt not in stats:
                        stats[real_fmt] = {}; format_totals[real_fmt] = 0
                    stats[real_fmt][real_cup_name] = stats[real_fmt].get(real_cup_name, 0) + 1
                    format_totals[real_fmt] += 1

    # 5. OUTPUT ORDINATO
    # Definiamo l'ordine esatto richiesto
    desired_order = ["Piramide", "Rombo", "Triangolo", "Linea Verticale", "Linea Orizzontale"]
    result = {}

    # Iteriamo sulla lista ordinata. Se il formato esiste nei dati (stats), lo aggiungiamo.
    for fmt in desired_order:
        if fmt in stats:
            cup_counts = stats[fmt]
            coords_map = layout_coords.get(fmt)
            total_hits = format_totals.get(fmt, 0)
            chart_data = []
            
            for cup_name, (x, y) in coords_map.items():
                hits = cup_counts.get(cup_name, 0)
                percentage = round((hits / total_hits * 100), 1) if total_hits > 0 else 0
                
                chart_data.append({
                    "x": x, "y": y, "z": percentage,
                    "cup": cup_name, "hits": hits, "total": total_hits
                })
            result[fmt] = chart_data

    return result

def calculate_success_by_opp_cups(data):
    """
    Calcola la % di successo in base al numero di bicchieri avversari presenti (1-6).
    - RANGE: Solo 1-6.
    - ORDINE: Decrescente (da 6 a 1) per l'asse X.
    """
    lists = data["liste"]
    
    # Recuperiamo le liste
    c_opp_list = lists.get("cups_opp", [])
    hit_list = lists.get("centro", [])
    fmt_list = lists.get("formato", [])
    
    # 1. STRUTTURE DATI (Solo per 1-6)
    # Generale: { 1: {m:0, t:0}, ... 6: {m:0, t:0} }
    general_stats = {i: {"m": 0, "t": 0} for i in range(1, 7)}
    
    # Per Formato
    format_stats = {} 

    # 2. ITERAZIONE
    for i in range(len(c_opp_list)):
        # Validazione Bicchieri
        raw_cups = c_opp_list[i]
        if raw_cups is None or str(raw_cups) in ['-', 'None', 'nan']: continue
        try:
            cups = int(raw_cups)
        except: continue
        
        # FILTRO: Consideriamo solo da 1 a 6 bicchieri
        if cups < 1 or cups > 6: continue

        # Validazione Colpo
        is_hit = is_true(hit_list[i])

        # --- A. AGGIORNAMENTO GENERALE ---
        general_stats[cups]["t"] += 1
        if is_hit:
            general_stats[cups]["m"] += 1

        # --- B. AGGIORNAMENTO PER FORMATO ---
        raw_fmt = fmt_list[i]
        if not raw_fmt or str(raw_fmt) in ['-', 'None', 'nan', '']: continue
        
        fmt_clean = str(raw_fmt).strip()
        if fmt_clean == 'Altro': fmt_clean = 'Linea Verticale'
        if fmt_clean == 'LineaVerticale': fmt_clean = 'Linea Verticale'
        
        if fmt_clean not in format_stats:
            format_stats[fmt_clean] = {k: {"m": 0, "t": 0} for k in range(1, 7)}
        
        format_stats[fmt_clean][cups]["t"] += 1
        if is_hit:
            format_stats[fmt_clean][cups]["m"] += 1

    # 3. PREPARAZIONE OUTPUT (ORDINATO 6 -> 1)
    # Creiamo la lista labels invertita: [6, 5, 4, 3, 2, 1]
    labels = list(range(6, 0, -1)) 
    
    # Dataset Generale (seguiamo l'ordine di labels)
    general_data = []
    for c in labels:
        stat = general_stats[c]
        if stat["t"] > 0:
            general_data.append(round((stat["m"] / stat["t"]) * 100, 1))
        else:
            general_data.append(None)

    # Dataset Formati
    formats_data = {}
    for fmt_name, cup_dict in format_stats.items():
        series = []
        has_data = False
        
        for c in labels: # Seguiamo l'ordine 6 -> 1
            stat = cup_dict[c]
            if stat["t"] > 0:
                series.append(round((stat["m"] / stat["t"]) * 100, 1))
                has_data = True
            else:
                series.append(None)
        
        if has_data:
            formats_data[fmt_name] = series

    return {
        "labels": labels,          # [6, 5, 4, 3, 2, 1]
        "general": general_data,   
        "by_format": formats_data  
    }