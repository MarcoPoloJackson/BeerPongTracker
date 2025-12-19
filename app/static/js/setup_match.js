/* ==========================================
   SETUP MATCH JS - Logica Bidirezionale
   ========================================== */

let activeSlotId = null;       // Se ho cliccato prima uno slot
let selectedPlayerName = null; // Se ho cliccato prima un giocatore

// Inizializza la pagina
document.addEventListener("DOMContentLoaded", function() {
    // Sincronizza input nascosti con UI (per Modifica Partita)
    const fields = ['t1_p1', 't1_p2', 't2_p1', 't2_p2'];
    fields.forEach(f => {
        const inputEl = document.getElementById('input_' + f);
        if (inputEl) {
            const val = inputEl.value;
            if (val) {
                updateSlotVisuals(f, val);
                markChipUsed(val, true);
            }
        }
    });
});

// --- GESTIONE CLICK ---

// 1. CLICK SU UNO SLOT
function selectSlot(slotKey) {
    // CASO A: Ho già un giocatore "in mano" (selezionato prima)?
    if (selectedPlayerName) {
        // Assegnalo subito a questo slot!
        performAssignment(slotKey, selectedPlayerName);
        resetSelectionState(); // Pulisci tutto
    } 
    // CASO B: Non ho giocatori selezionati, attivo lo slot
    else {
        // Disattiva altri slot
        document.querySelectorAll('.slot-card').forEach(el => el.classList.remove('active-slot'));
        
        // Attiva questo
        const slotEl = document.getElementById('slot_' + slotKey);
        slotEl.classList.add('active-slot');
        activeSlotId = slotKey;
    }
}

// 2. CLICK SU UN GIOCATORE
function assignPlayer(playerName) {
    // CASO A: Ho già uno slot attivo (selezionato prima)?
    if (activeSlotId) {
        // Assegna questo giocatore allo slot attivo
        performAssignment(activeSlotId, playerName);
        resetSelectionState(); // Pulisci tutto
    }
    // CASO B: Non ho slot attivi, seleziono il giocatore ("lo prendo in mano")
    else {
        // Se clicco lo stesso giocatore due volte, deseleziono
        if (selectedPlayerName === playerName) {
            resetSelectionState();
            return;
        }

        // Rimuovi evidenziazione da altri giocatori
        document.querySelectorAll('.player-chip').forEach(el => el.classList.remove('active-chip'));
        
        // Evidenzia questo giocatore
        const safeId = "chip_" + playerName.replace(/ /g, '_');
        const chip = document.getElementById(safeId);
        if (chip) chip.classList.add('active-chip');
        
        selectedPlayerName = playerName;
    }
}

// --- LOGICA DI ASSEGNAZIONE ---

function performAssignment(slotKey, playerName) {
    // Se lo slot aveva già un giocatore, liberalo prima
    const currentVal = document.getElementById('input_' + slotKey).value;
    if (currentVal) {
        markChipUsed(currentVal, false);
    }

    // Aggiorna Input Nascosto
    document.getElementById('input_' + slotKey).value = playerName;
    
    // Aggiorna Grafica Slot
    updateSlotVisuals(slotKey, playerName);
    
    // Segna Chip come "Usato" (grigio)
    markChipUsed(playerName, true);
}

// 3. PULSANTE X PER RIMUOVERE
function clearSlot(slotKey, event) {
    event.stopPropagation(); // Evita di attivare lo slot
    const val = document.getElementById('input_' + slotKey).value;
    if (val) {
        markChipUsed(val, false); // Rendi di nuovo disponibile
        
        // Resetta valori slot
        document.getElementById('input_' + slotKey).value = "";
        const nameEl = document.getElementById('name_' + slotKey);
        nameEl.innerText = "EMPTY";
        nameEl.style.color = "rgba(255,255,255,0.2)";
        document.getElementById('slot_' + slotKey).classList.remove('filled');
    }
}

// --- HELPERS ---

function resetSelectionState() {
    activeSlotId = null;
    selectedPlayerName = null;
    document.querySelectorAll('.slot-card').forEach(el => el.classList.remove('active-slot'));
    document.querySelectorAll('.player-chip').forEach(el => el.classList.remove('active-chip'));
}

function updateSlotVisuals(slotKey, name) {
    const nameEl = document.getElementById('name_' + slotKey);
    const cardEl = document.getElementById('slot_' + slotKey);
    
    nameEl.innerText = name;
    nameEl.style.color = "#111"; // Testo scuro su sfondo chiaro
    cardEl.classList.add('filled');
}

function markChipUsed(name, isUsed) {
    const safeId = "chip_" + name.replace(/ /g, '_');
    const chip = document.getElementById(safeId);
    if (chip) {
        if (isUsed) {
            chip.classList.add('used');
            chip.classList.remove('active-chip'); // Rimuovi eventuale stato attivo
        } else {
            chip.classList.remove('used');
        }
    }
}

function submitGame() {
    const uiName = document.getElementById('ui_match_name').value;
    document.getElementById('hidden_match_name').value = uiName;
    
    const inputs = ['t1_p1', 't1_p2', 't2_p1', 't2_p2'];
    for (let id of inputs) {
        if (!document.getElementById('input_' + id).value) {
            alert("⚠️ Devi riempire tutti i 4 slot prima di iniziare!");
            return;
        }
    }
    
    document.getElementById('realForm').submit();
}