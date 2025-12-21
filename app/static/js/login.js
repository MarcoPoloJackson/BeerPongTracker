document.addEventListener("DOMContentLoaded", function() {
    const mainNameInput = document.getElementById('mainNameInput');
    const ghostInput = document.getElementById('ghostInput');
    const playersDataEl = document.getElementById('playersData');
    
    const toggleBtn = document.getElementById('toggleModeBtn');
    const actionBtn = document.getElementById('mainActionBtn');
    const actionInput = document.getElementById('actionType');
    
    const delModal = document.getElementById('deleteModal');
    const delForm = document.getElementById('deleteForm');
    const delNameSpan = document.getElementById('delPlayerName');

    // Recupera lista nomi
    const playerNames = JSON.parse(playersDataEl.dataset.names || "[]");
    let isCreateMode = false;

    // --- 1. LOGICA GHOST AUTOFILL ---
    if (mainNameInput && ghostInput) {
        mainNameInput.addEventListener('input', function() {
            // Reset stato se in creazione o vuoto
            if (isCreateMode || !this.value) {
                ghostInput.value = "";
                return;
            }

            const value = this.value;
            // Cerca match (case insensitive)
            const suggestion = playerNames.find(name => 
                name.toLowerCase().startsWith(value.toLowerCase())
            );

            if (suggestion) {
                // Imposta testo fantasma
                ghostInput.value = value + suggestion.slice(value.length);
            } else {
                ghostInput.value = "";
            }
        });

        // Evento: Tasto TAB o Freccia Destra
        mainNameInput.addEventListener('keydown', function(e) {
            if ((e.key === 'Tab' || e.key === 'ArrowRight') && ghostInput.value) {
                // Se c'è un suggerimento valido e non l'abbiamo già completato
                if (this.value !== ghostInput.value) {
                    e.preventDefault(); 
                    this.value = ghostInput.value; // Completa
                    ghostInput.value = ""; // Pulisci ghost
                    document.getElementById('mainPasswordInput').focus(); // Sposta focus
                }
            }
        });
    }

    // --- 2. TOGGLE MODALITÀ (ENTRA <-> CREA) ---
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            isCreateMode = !isCreateMode;
            ghostInput.value = ""; 
            
            if(isCreateMode) {
                // CREAZIONE
                this.classList.add('create-mode');
                actionBtn.classList.add('create-mode');
                actionBtn.innerText = "Crea +";
                actionInput.value = 'create';
                mainNameInput.placeholder = "Nuovo Nome...";
            } else {
                // LOGIN
                this.classList.remove('create-mode');
                actionBtn.classList.remove('create-mode');
                actionBtn.innerText = "Entra ➔";
                actionInput.value = 'login';
                mainNameInput.placeholder = "Cerca o crea nome...";
            }
            mainNameInput.value = "";
            mainNameInput.focus();
        });
    }

    // --- 3. CLICK CARD (Riempimento veloce) ---
    window.quickFill = function(name) {
        if(!isCreateMode) {
            mainNameInput.value = name;
            ghostInput.value = ""; 
            document.getElementById('mainPasswordInput').focus();
        }
    };

    // --- 4. MODALE ELIMINAZIONE ---
    window.openDeleteModal = function(e, id, name) {
        e.stopPropagation(); 
        delForm.action = "/delete_player/" + id;
        delNameSpan.innerText = name;
        delModal.style.display = 'flex';
        setTimeout(() => {
            document.getElementById('confirmDeletePassword').focus();
        }, 100);
    };

    window.closeDeleteModal = function() {
        delModal.style.display = 'none';
        document.getElementById('confirmDeletePassword').value = '';
    };

    window.addEventListener('click', function(event) {
        if (event.target == delModal) {
            closeDeleteModal();
        }
    });
});