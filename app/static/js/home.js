/* ==========================================
   HOME JS - Logica Dashboard & Animazioni
   ========================================== */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Beer Pong Arena: Home Loaded");

    // 1. GESTIONE SCROLL (Resta dov'eri dopo il refresh)
    const scrollPos = localStorage.getItem('homeScrollPos');
    if (scrollPos) {
        window.scrollTo(0, parseInt(scrollPos));
        localStorage.removeItem('homeScrollPos');
    }

    // Salva scroll prima di lasciare la pagina
    window.addEventListener('beforeunload', function() {
        localStorage.setItem('homeScrollPos', window.scrollY);
    });

    // 2. EVIDENZIA IL MIO POSTO
    if (typeof window.currentUserName !== 'undefined' && window.currentUserName) {
        const nameElements = document.querySelectorAll('.player-name-text');
        nameElements.forEach(el => {
            if (el.textContent.trim() === window.currentUserName) {
                const card = el.closest('.slot-box');
                if (card) card.classList.add('my-seat');
            }
        });
    }

    // 3. ANIMAZIONI INGRESSO
    const animatedElements = document.querySelectorAll('.fade-in');
    if (animatedElements.length > 0) {
        animatedElements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.5s cubic-bezier(0.215, 0.610, 0.355, 1.000), transform 0.5s cubic-bezier(0.215, 0.610, 0.355, 1.000)';
            setTimeout(() => {
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, index * 50);
        });
    }

    // 4. AGGIORNAMENTO REAL-TIME (SOCKET.IO) - "SURGICAL UPDATE"
    if (typeof io !== 'undefined') {
        const socket = io();
        
        socket.on('partita_aggiornata', function(data) {
            console.log("⚡ Aggiornamento tavolo #" + data.match_id);
            
            // 1. Identifichiamo il tavolo che è cambiato
            const matchId = data.match_id;
            const cardElement = document.getElementById(`table-card-${matchId}`);

            if (cardElement) {
                // 2. Chiediamo al server SOLO l'HTML aggiornato di questo tavolo
                // Nota: Devi creare questa rotta in Python (vedi punto 3 sotto)
                fetch(`/api/render_table/${matchId}`)
                    .then(response => {
                        if (!response.ok) throw new Error("Errore network");
                        return response.text();
                    })
                    .then(html => {
                        // 3. Sostituiamo il vecchio HTML con quello nuovo
                        cardElement.outerHTML = html;
                        
                        // 4. Ri-applichiamo eventuali evidenziazioni (il "mio posto")
                        if (window.currentUserName) {
                            // Cerchiamo nel NUOVO elemento appena inserito
                            const newCard = document.getElementById(`table-card-${matchId}`);
                            const nameElements = newCard.querySelectorAll('.player-name-text');
                            nameElements.forEach(el => {
                                if (el.textContent.trim() === window.currentUserName) {
                                    el.closest('.slot-box').classList.add('my-seat');
                                }
                            });
                        }
                        console.log(`✅ Tavolo #${matchId} aggiornato senza reload.`);
                    })
                    .catch(err => {
                        console.error("Errore update parziale, fallback su reload:", err);
                        // Se qualcosa va storto, ricarichiamo la pagina per sicurezza
                        location.reload();
                    });
            } else {
                // Se non troviamo il tavolo (es. nuovo tavolo creato), ricarichiamo tutto
                location.reload();
            }
        });
    }
});


/* ==========================================
   LOGICA GLOBALE (FUNZIONI ONCLICK)
   ========================================== */

function saveCurrentScroll() {
    localStorage.setItem('homeScrollPos', window.scrollY);
}

// 1. Funzione SIEDITI SUBITO (Click diretto sul posto vuoto)
window.instantJoin = function(matchId, slot, playerName) {
    console.log("Tentativo ingresso:", matchId, slot, playerName); // Debug
    const form = document.getElementById('assignForm');
    if (form) {
        saveCurrentScroll();
        document.getElementById('modalMatchId').value = matchId;
        document.getElementById('modalSlot').value = slot;
        document.getElementById('modalPlayerName').value = playerName;
        form.submit();
    } else {
        console.error("Form di assegnazione non trovato!");
    }
};

// 2. Funzione APRI MODALE (Per assegnare altri)
window.openModal = function(matchId, slot) {
    document.getElementById('modalMatchId').value = matchId;
    document.getElementById('modalSlot').value = slot;

    let teamName = slot.startsWith('t1') ? "Blu" : "Rossa";
    let slotLabel = document.getElementById('modalSlotName');
    if (slotLabel) {
        slotLabel.innerText = "Posto per Squadra " + teamName;
    }
    
    // Resetta il campo nome
    document.getElementById('modalPlayerName').value = "";
    
    const modal = document.getElementById('playerModal');
    if (modal) {
        modal.style.display = 'flex';
    }
};

// 3. Funzione CHIUDI MODALE
window.closeModal = function(e) {
    if (e.target.id === 'playerModal') {
        document.getElementById('playerModal').style.display = 'none';
    }
};

// 4. Funzione INVIA SELEZIONE DAL MODALE
window.submitSelection = function(name) {
    saveCurrentScroll();
    document.getElementById('modalPlayerName').value = name;
    document.getElementById('assignForm').submit();
};

// 5. LISTENER GLOBALE PER TASTI AZIONE (Kick e Rematch)
document.addEventListener('click', function(e) {
    // Gestione delegata per elementi dinamici
    if (e.target.closest('.btn-kick') || e.target.closest('.btn-history-rematch')) {
        saveCurrentScroll();
    }
});

/* ==========================================
   GESTIONE MODALE KICK (RIMOZIONE)
   ========================================== */
let kickTargetUrl = ""; 

window.openKickModal = function(playerName, url) {
    const nameSpan = document.getElementById('kickPlayerName');
    if(nameSpan) nameSpan.innerText = playerName;
    
    kickTargetUrl = url;
    
    const modal = document.getElementById('kickModal');
    if(modal) modal.style.display = 'flex';
};

window.closeKickModal = function(e, force = false) {
    if (force || e.target.id === 'kickModal') {
        document.getElementById('kickModal').style.display = 'none';
    }
};

window.confirmKick = function() {
    if (kickTargetUrl) {
        saveCurrentScroll();
        window.location.href = kickTargetUrl;
    }
};

/* ==========================================
   GESTIONE MODALE ELIMINA TAVOLO
   ========================================== */
let deleteTableTargetUrl = "";

window.openDeleteTableModal = function(matchId, url) {
    const tName = document.getElementById('delTableName');
    if(tName) tName.innerText = "Tavolo #" + matchId;
    
    deleteTableTargetUrl = url;
    
    const modal = document.getElementById('deleteTableModal');
    if(modal) modal.style.display = 'flex';
};

window.closeDeleteTableModal = function(e, force = false) {
    if (force || e.target.id === 'deleteTableModal') {
        document.getElementById('deleteTableModal').style.display = 'none';
    }
};

window.confirmTableDelete = function() {
    if (deleteTableTargetUrl) {
        saveCurrentScroll();
        window.location.href = deleteTableTargetUrl;
    }
};