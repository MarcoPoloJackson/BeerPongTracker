import os
import sys
import random
import json
from faker import Faker
from werkzeug.security import generate_password_hash
from flask import Flask

# ==========================================
#               SETUP IMPORTS
# ==========================================
sys.path.append(os.getcwd())

try:
    # Try importing from 'app' package
    from app.models import db, Player, ActiveMatch, init_db
except ImportError:
    try:
        # Fallback for flat structure
        from models import db, Player, ActiveMatch, init_db
    except ImportError:
        print("❌ Error: Could not import 'models'. Ensure you are running this from the project root.")
        sys.exit(1)

# Initialize Faker
fake = Faker()


# ==========================================
#             HELPER FUNCTIONS
# ==========================================

def create_app_context():
    """Creates a basic Flask app instance to access the DB."""
    app = Flask(__name__)
    init_db(app)
    return app


def reset_database():
    """Drops all tables and recreates them to clear data."""
    print("\n🧹 STEP 0: Clearing entire database...")
    try:
        # Drops all tables defined in models
        db.drop_all()
        # Recreates the tables empty
        db.create_all()
        print("   ✅ Database completely wiped and tables recreated.")
    except Exception as e:
        print(f"   ❌ Error clearing database: {e}")
        # If drop_all fails (e.g. file lock), try deleting rows manually
        try:
            db.session.query(ActiveMatch).delete()
            db.session.query(Player).delete()
            db.session.commit()
            print("   ⚠️ Fallback: Deleted all rows manually.")
        except Exception as e2:
             print(f"   ❌ Critical Error: {e2}")
             sys.exit(1)


def populate_users(num_users_to_add=20):
    """Generates random users."""
    print(f"\n👤 STEP 1: Generating {num_users_to_add} new users...")

    added_count = 0
    attempts = 0
    max_attempts = num_users_to_add * 5

    while added_count < num_users_to_add and attempts < max_attempts:
        attempts += 1
        name = fake.first_name() + " " + fake.last_name()

        # Check for duplicates (though DB is empty now, good practice to keep)
        if Player.query.filter_by(name=name).first():
            continue

        new_player = Player(
            name=name,
            # Generate a standard password for testing
            password=generate_password_hash("password123", method='scrypt'),
            edit=False
        )

        db.session.add(new_player)
        added_count += 1

    try:
        db.session.commit()
        print(f"   ✅ Added {added_count} players to the database.")
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error saving players: {e}")


def create_matches(num_matches=10):
    """Creates matches using existing users in the DB."""
    print(f"\n🍺 STEP 2: Generating {num_matches} matches...")

    # 1. Fetch all available players
    all_players = Player.query.all()
    total_players = len(all_players)

    if total_players < 4:
        print(f"   ❌ Error: Not enough players (Found {total_players}, need 4+).")
        return

    # Standard 6-cup Pyramid setup
    standard_cups = json.dumps(["3 Sx", "3 Cen", "3 Dx", "2 Sx", "2 Dx", "1 Cen"])
    empty_list = json.dumps([])

    count = 0
    for i in range(num_matches):
        # 2. Pick 4 random players
        participants = random.sample(all_players, 4)
        p1, p2, p3, p4 = participants

        match_name = f"Tavolo #{random.randint(1000, 9999)}"

        # 3. Create Match
        new_match = ActiveMatch(
            match_name=match_name,
            status='running',

            # Players
            t1_p1=p1.name, t1_p2=p2.name,
            t2_p1=p3.name, t2_p2=p4.name,

            # Cup States
            t1_cup_state=standard_cups,
            t2_cup_state=standard_cups,
            t1_pending_list=empty_list,
            t2_pending_list=empty_list,

            # Configurations
            format_target_for_t1='Piramide',
            format_target_for_t2='Piramide',
            cups_target_for_t1=6,
            cups_target_for_t2=6,
            pending_damage_for_t1=0,
            pending_damage_for_t2=0,
            redemption_shots_left=0,
            redemption_hits=0
        )

        db.session.add(new_match)
        count += 1

    try:
        db.session.commit()
        print(f"   ✅ Created {count} matches successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"   ❌ Error saving matches: {e}")


# ==========================================
#               MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    app = create_app_context()

    with app.app_context():
        # Get the DB URI for confirmation
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'Unknown URI')
        print(f"🚀 Connected to: {db_uri}")

        # 0. WIPE DATABASE
        reset_database()

        # 1. Create Users
        populate_users(num_users_to_add=30)

        # 2. Create Matches (using the users we just made)
        create_matches(num_matches=10)

        print("\n✨ Operations complete.\n")