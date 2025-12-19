/* ==========================================
   HOME JS - Logica Dashboard & Animazioni
   ========================================== */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Beer Pong Arena: Home Loaded");

    // 1. ANIMAZIONE INGRESSO A CASCATA
    // Seleziona sia le card delle partite live (.match-card) 
    // sia le card delle serie storiche (.series-card) grazie alla classe comune 'fade-in'
    const animatedElements = document.querySelectorAll('.fade-in');
    
    animatedElements.forEach((el, index) => {
        // Imposta stato iniziale (nascosto e spostato in basso)
        // Nota: È meglio se questo è già nel CSS, ma qui forziamo per sicurezza
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.5s cubic-bezier(0.215, 0.610, 0.355, 1.000), transform 0.5s cubic-bezier(0.215, 0.610, 0.355, 1.000)';
        
        // Ritardo progressivo (100ms * indice) per l'effetto "onda"
        setTimeout(() => {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, index * 100); 
    });

    // 2. GESTIONE EVENTUALI ERRORI IMMAGINI (Opzionale)
    // Se in futuro aggiungerai foto profilo, questo codice mette un placeholder se l'immagine non carica
    /*
    const profileImages = document.querySelectorAll('.profile-pic');
    profileImages.forEach(img => {
        img.onerror = function() {
            this.src = '/static/img/default_avatar.png'; // Percorso placeholder
        };
    });
    */



    /* Container per i bottoni nel titolo */
.action-buttons {
    display: flex;
    gap: 8px;
    margin-left: 10px;
}

/* Stile base bottoni icona */
.btn-icon {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    text-decoration: none;
    font-size: 1.1em;
    transition: transform 0.2s, background 0.2s;
}


/* NUOVO: Bottone Manuale (Ingranaggio/Strumenti) */
.btn-manual {
    background-color: #fff3e0;
    border: 1px solid #ffe0b2;
}
.btn-manual:hover {
    background-color: #ffe0b2;
    transform: scale(1.1);
}
});