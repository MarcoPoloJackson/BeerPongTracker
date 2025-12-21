import os
import sys
import random
import json
from datetime import datetime, timedelta
from faker import Faker
from werkzeug.security import generate_password_hash

# ==========================================
#               SETUP IMPORTS
# ==========================================
sys.path.append(os.getcwd())

try:
    from app import create_app
    from app.models import db, Player, ActiveMatch, PlayerRecord, CUP_DEFINITIONS
except ImportError as e:
    print("❌ Errore di Importazione:")
    print(f"   {e}")
    sys.exit(1)

fake = Faker('it_IT')

# ==========================================
#             CONFIGURAZIONE
# ==========================================
ADMINS_CONFIG = ["admin1", "admin2", "admin3", "admin4"]
COMMON_PASSWORD = "1234"
TARGET_SHOTS_PER_ADMIN = 1000

# Definizioni bicchieri per coerenza
CUPS_BY_FORMAT = {
    'Piramide': ["1", "2 Sx", "2 Dx", "3 Sx", "3 Cen", "3 Dx", "4 Sx", "4 Dx", "5 Cen", "6"],
    'Altro': ["Base 1", "Base 2", "Centro", "Ala Sx", "Ala Dx", "Jolly"]
}

# ==========================================
#             HELPER FUNCTIONS
# ==========================================

def reset_database():
    """Cancella tutto e ricrea le tabelle."""
    print("\n🧹 STEP 0: Pulizia completa del database...")
    try:
        db.drop_all()
        db.create_all()
        print("   ✅ Database resettato.")
    except Exception as e:
        print(f"   ❌ Errore reset: {e}")
        sys.exit(1)

def get_weighted_choice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]

def boolean_choice(probability):
    """Restituisce True con una probabilità di 1/probability"""
    return random.randint(1, probability) == 1

def generate_admins_and_npcs():
    print(f"\n👤 STEP 1: Creazione Admin e Giocatori NPC...")
    
    admins = []
    # 1. Crea Admin
    hashed_pw = generate_password_hash(COMMON_PASSWORD)
    for name in ADMINS_CONFIG:
        adm = Player(name=name, password=hashed_pw, edit=True)
        db.session.add(adm)
        admins.append(adm)
    
    # 2. Crea NPC (Opponents/Teammates)
    npcs = []
    for _ in range(20):
        npc_name = fake.first_name() + " " + fake.last_name()
        # Evita duplicati
        if npc_name not in ADMINS_CONFIG:
            npc = Player(name=npc_name, password=hashed_pw, edit=False)
            db.session.add(npc)
            npcs.append(npc)
            
    db.session.commit()
    print(f"   ✅ Creati 4 Admin e {len(npcs)} NPC.")
    
    # Ricarichiamo gli oggetti dal DB per avere gli ID
    all_admins = Player.query.filter(Player.name.in_(ADMINS_CONFIG)).all()
    all_npcs = Player.query.filter(~Player.name.in_(ADMINS_CONFIG)).all()
    
    return all_admins, all_npcs

def generate_stats_for_admin(admin_player, all_players_pool):
    """
    Genera partite e tiri specifici per UN admin finché non arriva a 1000 tiri.
    """
    current_shots = 0
    match_counter = 0
    
    print(f"   🎲 Generazione statistiche per {admin_player.name}...")

    while current_shots < TARGET_SHOTS_PER_ADMIN:
        match_counter += 1
        
        # --- 1. SETUP PARTITA ---
        # Seleziona compagno e avversari casuali
        others = [p for p in all_players_pool if p.id != admin_player.id]
        participants = random.sample(others, 3)
        teammate = participants[0]
        opponent1 = participants[1]
        opponent2 = participants[2]
        
        # Parametri Match
        match_date_obj = datetime.now() - timedelta(days=random.randint(0, 365)) # Ultimo anno
        match_date_str = match_date_obj.strftime("%Y-%m-%d")
        match_hour = random.randint(18, 23) # Orario serale verosimile
        
        # Formato (70% Piramide, 30% Altro)
        formato = get_weighted_choice(['Piramide', 'Altro'], [70, 30])
        initial_cups = 10 if formato == 'Piramide' else 6
        
        # Overtime (1/80)
        is_overtime = boolean_choice(80)
        
        # Risultato Match (Win/Loss random 50/50 per variare)
        match_result = random.choice(["Win", "Loss"])
        winning_team = "t1" if match_result == "Win" else "t2"
        
        # Creiamo l'oggetto Match nel DB
        # NOTA: Rimosso 'created_at' che causava errore
        match_db = ActiveMatch(
            match_name=f"Match simulato {admin_player.name} #{match_counter}",
            status='finished',
            mode='squadre',
            t1_p1=admin_player.name, t1_p2=teammate.name,
            t2_p1=opponent1.name, t2_p2=opponent2.name,
            winning_team=winning_team,
            format_target_for_t1=formato,
            format_target_for_t2=formato,
            cups_target_for_t1=initial_cups,
            cups_target_for_t2=initial_cups
        )
        db.session.add(match_db)
        db.session.flush() # Per ottenere l'ID
        
        # --- 2. SETUP TIRI ---
        # Tiri random tra 15 e 40
        shots_in_this_match = random.randint(15, 40)
        
        # Se superiamo i 1000, tronchiamo all'esatto necessario
        if current_shots + shots_in_this_match > TARGET_SHOTS_PER_ADMIN:
            shots_in_this_match = TARGET_SHOTS_PER_ADMIN - current_shots

        # --- 3. GENERAZIONE RECORD TIRI ---
        for shot_idx in range(1, shots_in_this_match + 1):
            
            # -- Logica Esiti (Miss, Bordo, Centro) --
            # Definiamo probabilità base realistiche per variare
            # Es: 40% Miss, 20% Bordo, 40% Centro
            outcome = get_weighted_choice(['miss', 'bordo', 'centro'], [40, 20, 40])
            
            miss_val, bordo_val, centro_val = "No", "No", "No"
            bicchiere_colpito = None
            
            if outcome == 'miss':
                miss_val = "Sì"
            elif outcome == 'bordo':
                bordo_val = "Sì"
            else:
                centro_val = "Sì"
                # Se è centro, colpisce un bicchiere coerente col formato
                possible_cups = CUPS_BY_FORMAT.get(formato, ["Generico"])
                bicchiere_colpito = random.choice(possible_cups)

            # -- Logica Bicchieri Multipli (1/100 Doppio, 1/1000 Triplo) --
            multiplo = "-"
            # Nota: deve essere centro per fare multi hit? Tecnicamente sì nel gioco reale,
            # ma qui seguiamo la statistica pura. Lo mettiamo solo se è centro.
            if centro_val == "Sì":
                if boolean_choice(1000):
                    multiplo = "Triplo" # 3
                elif boolean_choice(100):
                    multiplo = "Doppio" # 2
            
            # -- Tiro Salvezza (1/20) --
            is_salvezza = boolean_choice(20)
            salvezza_val = "Sì" if is_salvezza else "No"

            # -- Note (1/100) --
            nota_text = ""
            if boolean_choice(100):
                nota_text = random.choice(["Tiro fortunato", "Scivolato", "Distratto", "MVP"])
            
            # -- Postazione (90% Lati, 10% Centro) --
            postazione = get_weighted_choice(
                ['Destra', 'Sinistra', 'Centrale'], 
                [45, 45, 10]
            )

            # -- Bevanda (50% Birra, altri 10% ciascuno) --
            bevanda = get_weighted_choice(
                ['Birra', 'Vino', 'Coca', 'Spritz', 'JagerBomb', 'GinTonic'],
                [50, 10, 10, 10, 10, 10]
            )

            # -- Cups Own / Opp (Random 1-6) --
            c_own = random.randint(1, 6)
            c_opp = random.randint(1, 6)

            # CREAZIONE RECORD
            record = PlayerRecord(
                match_id=match_db.id,
                player_id=admin_player.id,
                
                shot_number=shot_idx,
                
                teammate_id=teammate.id,
                opponent1_id=opponent1.id,
                opponent2_id=opponent2.id,
                
                match_date=match_date_str,  # Col L (Questa è quella che conta per i grafici)
                match_hour=match_hour,      # Col M
                
                match_result=match_result,
                is_overtime=is_overtime,    # Prob 1/80
                note=nota_text,             # Prob 1/100
                
                tiro_salvezza=salvezza_val,     # Col G (1/20)
                bicchieri_multipli=multiplo,    # Col J-K (1/100, 1/1000)
                
                formato=formato,            # Col F (70/30)
                postazione=postazione,      # Col H (90/10)
                bevanda=bevanda,            # Col I (50/others)
                
                # Esiti
                miss=miss_val,              # Col A
                bordo=bordo_val,            # Col B
                centro=centro_val,          # Col C
                bicchiere_colpito=bicchiere_colpito, # Col E
                
                cups_own=c_own,
                cups_opp=c_opp,
                
                timestamp=datetime.now()
            )
            db.session.add(record)
            current_shots += 1

    print(f"   ✅ {admin_player.name}: Raggiunti {current_shots} tiri.")
    db.session.commit()


# ==========================================
#               MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        print(f"🚀 Avvio popolamento mirato alle statistiche...")

        # 1. Reset
        reset_database()

        # 2. Creazione Utenti
        admins_list, npcs_list = generate_admins_and_npcs()
        all_players_pool = admins_list + npcs_list

        # 3. Loop Statistiche per ogni Admin
        print(f"\n📊 STEP 2: Generazione 1000 tiri per ciascuno dei 4 admin...")
        
        for admin in admins_list:
            generate_stats_for_admin(admin, all_players_pool)

        print("\n✨ Finito! Ora hai 4 Admin con 1000 tiri esatti e statistiche realistiche.")