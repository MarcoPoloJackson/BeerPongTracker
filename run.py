from app import create_app
from app import socketio # <-- IMPORTA L'OGGETTO CHE ABBIAMO CREATO PRIMA

app = create_app()

if __name__ == '__main__':
    # Usiamo socketio.run invece di app.run
    # allow_unsafe_werkzeug=True serve se usi l'ambiente di sviluppo base
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)