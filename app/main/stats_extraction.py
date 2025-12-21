from app.models import PlayerRecord, db
from sqlalchemy import func

def get_player_stats(player_id):
    """
    Restituisce i dati grezzi (liste) e i conteggi totali per un giocatore specifico.
    """
    
    # 1. Recuperiamo i record ordinati cronologicamente
    records = PlayerRecord.query.filter_by(player_id=player_id).order_by(PlayerRecord.id.asc()).all()

    # --- A. INIZIALIZZIAMO LE LISTE (Dati Grezzi) ---
    lists = {
        "ids": [],                  
        "match_ids": [],            
        "teammate_ids": [],         
        "opponent1_ids": [],        
        "opponent2_ids": [],        
        "shot_numbers": [],         
        
        # Esiti
        "miss": [],                 
        "bordo": [],                
        "centro": [],               
        "esito_label": [],          
        
        # --- CORREZIONE QUI SOTTO: DA PLURALE A SINGOLARE ---
        "bicchiere_colpito": [],    # Prima era "bicchieri_colpiti" -> ORA È CORRETTO
        
        "cups_own": [],             
        "cups_opp": [],             
        
        # Tempo
        "match_date": [],           
        "match_hour": [],           
        
        # Contesto
        "is_overtime": [],          
        "match_result": [],         
        "note": [],                 
        "tiro_salvezza": [],        
        "bicchieri_multipli": [],   
        "formato": [],              
        "postazione": [],           
        "bevanda": []               
    }

    # --- B. INIZIALIZZIAMO I CONTEGGI ---
    counts = {
        "tiri_totali": 0,
        "centri": 0,
        "bordi": 0,
        "miss": 0,
        "match_giocati_totali": 0,
        "vittorie_totali": 0       
    }

    unique_match_ids = set()

    # --- C. RIEMPIMENTO LISTE ---
    for r in records:
        # Aggiornamento Conteggi
        counts["tiri_totali"] += 1
        unique_match_ids.add(r.match_id)
        
        if r.centro == "Sì":
            counts["centri"] += 1
            lists["esito_label"].append("Centro")
        elif r.bordo == "Sì":
            counts["bordi"] += 1
            lists["esito_label"].append("Bordo")
        else:
            counts["miss"] += 1
            lists["esito_label"].append("Miss")

        # Riempimento Liste
        lists["ids"].append(r.id)
        lists["match_ids"].append(r.match_id)
        lists["teammate_ids"].append(r.teammate_id)
        lists["opponent1_ids"].append(r.opponent1_id)
        lists["opponent2_ids"].append(r.opponent2_id)
        lists["shot_numbers"].append(r.shot_number)
        
        lists["miss"].append(r.miss)
        lists["bordo"].append(r.bordo)
        lists["centro"].append(r.centro)
        
        # --- CORREZIONE ANCHE QUI ---
        lists["bicchiere_colpito"].append(r.bicchiere_colpito) 
        
        lists["cups_own"].append(r.cups_own)    
        lists["cups_opp"].append(r.cups_opp)
        
        lists["match_date"].append(r.match_date)
        lists["match_hour"].append(r.match_hour)
        
        lists["is_overtime"].append(r.is_overtime)
        lists["match_result"].append(r.match_result)
        lists["note"].append(r.note)
        lists["tiro_salvezza"].append(r.tiro_salvezza)
        lists["bicchieri_multipli"].append(r.bicchieri_multipli)
        lists["formato"].append(r.formato)
        lists["postazione"].append(r.postazione)
        lists["bevanda"].append(r.bevanda)

    # --- D. CALCOLO VITTORIE ---
    counts["match_giocati_totali"] = len(unique_match_ids)
    
    counts["vittorie_totali"] = db.session.query(func.count(func.distinct(PlayerRecord.match_id)))\
        .filter(PlayerRecord.player_id == player_id, PlayerRecord.match_result == 'Win').scalar() or 0

    return {
        "liste": lists,
        "conteggi": counts
    }