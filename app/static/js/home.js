/* ==========================================
   HOME JS - Logica Dashboard & Animazioni
   ========================================== */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Beer Pong Arena: Home Loaded");

    // ---------------------------------------------------------
    // 1. GESTIONE SCROLL (Resta dov'eri dopo il refresh)
    // ---------------------------------------------------------
    // Usiamo una chiave specifica per evitare conflitti con altre pagine
    const scrollPos = localStorage.getItem('homeScrollPos');
    if (scrollPos) {
        window.scrollTo(0, parseInt(scrollPos));
        // Puliamo subito per evitare che lo scroll rimanga bloccato in futuro
        localStorage.removeItem('homeScrollPos');
    }

    // Salva la posizione ogni volta che la pagina sta per essere scaricata
    window.addEventListener('beforeunload', function() {
        localStorage.setItem('homeScrollPos', window.scrollY);
    });

    // ---------------------------------------------------------
    // 2. EVIDENZIA IL MIO POSTO (Green Highlight)
    // ---------------------------------------------------------
    if (window.currentUserName) {
        // Cerchiamo specificamente il testo del nome dentro gli span dedicati
        const nameElements = document.querySelectorAll('.player-name-text');
        
        nameElements.forEach(el => {
            // Se il testo dell'elemento corrisponde esattamente al nome utente loggato
            if (el.textContent.trim() === window.currentUserName) {
                // Risaliamo alla casella contenitore (.slot-box)
                const card = el.closest('.slot-box');
                if (card) {
                    card.classList.add('my-seat');
                    console.log("Mio posto evidenziato con successo");
                }
            }
        });
    }

    // ---------------------------------------------------------
    // 3. ANIMAZIONI INGRESSO (Fade In)
    // ---------------------------------------------------------
    const animatedElements = document.querySelectorAll('.fade-in');
    if (animatedElements.length > 0) {
        animatedElements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.5s cubic-bezier(0.215, 0.610, 0.355, 1.000), transform 0.5s cubic-bezier(0.215, 0.610, 0.355, 1.000)';
            
            setTimeout(() => {
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, index * 50); // 50ms di ritardo tra ogni elemento per un effetto fluido
        });
    }
});


/* ==========================================
   LOGICA GLOBALE (FUNZIONI ONCLICK)
   ========================================== */

// Funzione helper per salvare lo scroll prima di azioni manuali
function saveCurrentScroll() {
    localStorage.setItem('homeScrollPos', window.scrollY);
}

// 1. Funzione SIEDITI SUBITO
function instantJoin(matchId, slot, playerName) {
    const form = document.getElementById('assignForm');
    if (form) {
        // Salva lo scroll prima di inviare il form
        saveCurrentScroll();
        
        document.getElementById('modalMatchId').value = matchId;
        document.getElementById('modalSlot').value = slot;
        document.getElementById('modalPlayerName').value = playerName;
        form.submit();
    }
}

// 2. Funzione APRI MODALE (Per assegnare altri)
function openModal(matchId, slot) {
    document.getElementById('modalMatchId').value = matchId;
    document.getElementById('modalSlot').value = slot;

    let teamName = slot.startsWith('t1') ? "Blu" : "Rossa";
    let slotLabel = document.getElementById('modalSlotName');
    if (slotLabel) {
        slotLabel.innerText = "Posto per Squadra " + teamName;
    }
    
    document.getElementById('modalPlayerName').value = "";
    
    // Mostra il modale
    const modal = document.getElementById('playerModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

// 3. Funzione CHIUDI MODALE
function closeModal(e) {
    // Chiude se clicchi fuori dal contenuto (sull'overlay scuro)
    if (e.target.id === 'playerModal') {
        document.getElementById('playerModal').style.display = 'none';
    }
}

// 4. Funzione INVIA SELEZIONE DAL MODALE
function submitSelection(name) {
    // Salva lo scroll prima del ricaricamento
    saveCurrentScroll();
    
    document.getElementById('modalPlayerName').value = name;
    document.getElementById('assignForm').submit();
}

// 5. LISTENER GLOBALE PER TASTI AZIONE
// Intercetta i click sui tasti "Rimuovi" (X) e "Rigioca" per salvare lo scroll
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('btn-kick') || e.target.classList.contains('btn-history-rematch')) {
        saveCurrentScroll();
    }
});

/* ==========================================
   GESTIONE MODALE KICK (RIMOZIONE)
   ========================================== */

let kickTargetUrl = ""; // Variabile globale per memorizzare l'URL di rimozione

function openKickModal(playerName, url) {
    // 1. Imposta il nome nel testo
    document.getElementById('kickPlayerName').innerText = playerName;
    
    // 2. Salva l'URL generato da Flask
    kickTargetUrl = url;
    
    // 3. Mostra il modale
    document.getElementById('kickModal').style.display = 'flex';
}

function closeKickModal(e, force = false) {
    // Chiude se clicco fuori (overlay) o se forzato dal tasto Annulla
    if (force || e.target.id === 'kickModal') {
        document.getElementById('kickModal').style.display = 'none';
    }
}

function confirmKick() {
    if (kickTargetUrl) {
        // Salva lo scroll per non tornare in cima
        saveCurrentScroll();
        // Esegue il redirect all'URL di rimozione
        window.location.href = kickTargetUrl;
    }
}

/* ==========================================
   GESTIONE MODALE ELIMINA TAVOLO
   ========================================== */

let deleteTableTargetUrl = "";

function openDeleteTableModal(matchId, url) {
    document.getElementById('delTableName').innerText = "Tavolo #" + matchId;
    deleteTableTargetUrl = url;
    document.getElementById('deleteTableModal').style.display = 'flex';
}

function closeDeleteTableModal(e, force = false) {
    if (force || e.target.id === 'deleteTableModal') {
        document.getElementById('deleteTableModal').style.display = 'none';
    }
}

function confirmTableDelete() {
    if (deleteTableTargetUrl) {
        saveCurrentScroll();
        window.location.href = deleteTableTargetUrl;
    }
}