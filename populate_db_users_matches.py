import os
import sys
import random
import json
from faker import Faker
from werkzeug.security import generate_password_hash

# ==========================================
#               SETUP IMPORTS
# ==========================================
# Aggiunge la cartella corrente al path per trovare i moduli
sys.path.append(os.getcwd())

try:
    # 1. DA 'app' (__init__.py) importiamo SOLO create_app (e socketio se servisse)
    from app import create_app
    
    # 2. DA 'app.models' importiamo db, init_db e tutti i modelli
    from app.models import db, init_db, Player, ActiveMatch, PlayerRecord, CUP_DEFINITIONS

except ImportError as e:
    print("❌ Errore di Importazione:")
    print(f"   {e}")
    print("   Assicurati di eseguire questo script dalla cartella principale del progetto.")
    print("   Esempio: python populate_db_users_matches.py")
    sys.exit(1)

# Inizializza Faker per nomi falsi
fake = Faker('it_IT')

# ==========================================
#             HELPER FUNCTIONS
# ==========================================

def reset_database():
    """Cancella tutto il database e ricrea le tabelle vuote."""
    print("\n🧹 STEP 0: Pulizia completa del database...")
    try:
        db.drop_all()
        db.create_all()
        print("   ✅ Database resettato e tabelle ricreate.")
    except Exception as e:
        print(f"   ❌ Errore durante il reset: {e}")
        sys.exit(1)


def populate_users(num_users_to_add=50):
    """Genera utenti casuali."""
    print(f"\n👤 STEP 1: Generazione di {num_users_to_add} giocatori...")

    added_count = 0
    attempts = 0
    # Limite tentativi per evitare loop infiniti se Faker genera duplicati
    max_attempts = num_users_to_add * 5 

    # Password uguale per tutti per test (hashata)
    default_password = generate_password_hash("password123")

    while added_count < num_users_to_add and attempts < max_attempts:
        attempts += 1
        name = fake.first_name() + " " + fake.last_name()

        # Controlla duplicati
        if Player.query.filter_by(name=name).first():
            continue

        new_player = Player(
            name=name,
            password=default_password,
            edit=False
        )

        db.session.add(new_player)
        added_count += 1

    try:
        db.session.commit()
        print(f"   ✅ Aggiunti {added_count} giocatori al database.")
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Errore salvataggio giocatori: {e}")


def create_matches(num_matches=10):
    """Crea partite usando i giocatori esistenti."""
    print(f"\n🍺 STEP 2: Generazione di {num_matches} partite...")

    # 1. Recupera tutti i giocatori
    all_players = Player.query.all()
    total_players = len(all_players)

    if total_players < 4:
        print(f"   ❌ Errore: Non ci sono abbastanza giocatori ({total_players}/4 richiesti).")
        return

    # 2. Definisci i bicchieri iniziali
    # Cerca di prenderli dal modello reale, altrimenti usa un default
    if 'Piramide' in CUP_DEFINITIONS:
        cups_list = CUP_DEFINITIONS['Piramide']
    else:
        # Fallback se non trova la definizione nel modello
        cups_list = ["3 Sx", "3 Cen", "3 Dx", "2 Sx", "2 Dx", "1 Cen"]
    
    standard_cups_json = json.dumps(cups_list)
    empty_list_json = json.dumps([])
    initial_count = len(cups_list)

    count = 0
    for i in range(num_matches):
        # Sceglie 4 giocatori a caso
        participants = random.sample(all_players, 4)
        p1, p2, p3, p4 = participants

        match_name = f"Tavolo #{random.randint(100, 999)}"

        # Crea la partita
        new_match = ActiveMatch(
            match_name=match_name,
            status='running',

            # Assegnazione Giocatori
            t1_p1=p1.name, t1_p2=p2.name,
            t2_p1=p3.name, t2_p2=p4.name,

            # Stato Bicchieri
            t1_cup_state=standard_cups_json,
            t2_cup_state=standard_cups_json,
            t1_pending_list=empty_list_json,
            t2_pending_list=empty_list_json,

            # Configurazioni
            format_target_for_t1='Piramide',
            format_target_for_t2='Piramide',
            cups_target_for_t1=initial_count,
            cups_target_for_t2=initial_count,
            pending_damage_for_t1=0,
            pending_damage_for_t2=0,
            redemption_shots_left=0,
            redemption_hits=0,
            
            # Reset flag formati
            t1_format_changed=False,
            t2_format_changed=False
        )

        db.session.add(new_match)
        count += 1

    try:
        db.session.commit()
        print(f"   ✅ Create {count} partite con successo.")
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Errore salvataggio partite: {e}")


# ==========================================
#               MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    # Crea l'applicazione usando la factory reale
    # Questo assicura che DB e configurazioni siano caricate correttamente
    app = create_app()

    with app.app_context():
        # Verifica connessione DB
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'Sconosciuto')
        print(f"🚀 Connesso al DB: {db_uri}")

        # 0. WIPE DATABASE
        reset_database()

        # 1. Crea Utenti
        populate_users(num_users_to_add=60)

        # 2. Crea Partite
        create_matches(num_matches=10)

        print("\n✨ Operazioni completate.\n")