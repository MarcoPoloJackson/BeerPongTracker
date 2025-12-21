import os
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from functools import wraps
# Importiamo il limiter definito nell'app principale
from app import limiter 

# Crea un Blueprint (un modulo separato di Flask)
gate_bp = Blueprint('gate', __name__)

# --- CONFIGURAZIONE PASSWORD ---
# Cerca la password nelle variabili d'ambiente, altrimenti usa quella di default
GLOBAL_SITE_PASSWORD = os.environ.get('SITE_PASSWORD', 'GiovediSir')
# --- ---- ----- ---- --- ---- ----- ---- --- ---- ----- ---- --- ---- ----- ---- 

def gate_required(view):
    """
    Decoratore personalizzato: Mettilo sopra qualsiasi rotta che vuoi proteggere.
    Se l'utente non ha inserito la password globale, viene rispedito al gate.
    """
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        # Se la chiave non è nella sessione, vai al login del sito
        if not session.get('site_access_granted'):
            return redirect(url_for('gate.site_login'))
        
        # Altrimenti, esegui la vista normale
        return view(*args, **kwargs)
    
    return wrapped_view

@gate_bp.route('/site_login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Blocca l'IP dopo 5 tentativi errati in un minuto
def site_login():
    """
    La pagina che chiede la password globale.
    """
    if request.method == 'POST':
        pwd = request.form.get('site_password')
        
        if pwd == GLOBAL_SITE_PASSWORD:
            # Password corretta: salviamo il "pass" nella sessione
            session['site_access_granted'] = True
            flash("Accesso consentito.", "success")
            
            # Reindirizza alla pagina di login dei giocatori
            return redirect(url_for('main.login_page'))
        else:
            # Messaggio di errore categorizzato per il template
            flash("Password errata. Riprova.", "error")
    
    # Se è già loggato tramite sessione, non mostrare il form e vai avanti
    if session.get('site_access_granted'):
        return redirect(url_for('main.login_page'))

    return render_template('site_gate.html')

@gate_bp.route('/site_logout')
def site_logout():
    """Rimuove l'accesso globale al sito (torna a chiedere la password)"""
    session.pop('site_access_granted', None)
    flash("Sessione chiusa. Sito bloccato.", "info")
    return redirect(url_for('gate.site_login'))