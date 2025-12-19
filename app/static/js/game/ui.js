/* ==========================================
   2. UI.JS - Gestione Interfaccia e Griglia
   ========================================== */

// Helper interno per ottenere il layout visivo (definito in config.js)
function getLayoutByFormat(fmt) { 
    return visualLayouts[fmt] || visualLayouts["Piramide"]; 
}

// --- FUNZIONE 1: GESTIONE CARICAMENTO E COLORI MENU ---
window.updateAvailableFormats = function() {
    let cupsVal = 1;

    // 1. Calcolo numero bicchieri attuali
    if (typeof isMatchActive !== 'undefined' && isMatchActive) {
        if (typeof activeCupsOpponent !== 'undefined' && Array.isArray(activeCupsOpponent)) {
            cupsVal = activeCupsOpponent.length;
        } else {
            cupsVal = parseInt(serverCupsTarget) || 6;
        }
    } else {
         const inputEl = document.getElementById('numero_bicchieri');
         if(inputEl) cupsVal = parseInt(inputEl.value) || 6;
    }

    const formatSelect = document.getElementById('formato');
    if (!formatSelect) return;

    // --- CONDIZIONI DI BLOCCO ---
    
    // A. C'è un bicchiere colpito in sospeso (pending)?
    const hasPendingOpponent = (typeof pendingCups !== 'undefined' && pendingCups.length > 0);
    
    // B. Il formato è già stato cambiato in precedenza (Server lock)?
    const isServerLocked = (typeof serverOppFormat !== 'undefined' && serverOppFormat && serverOppFormat !== "Piramide");
    
    // C. NUOVA REGOLA: Blocca se ci sono 6 o 5 bicchieri
    const isCountLocked = (cupsVal === 6 || cupsVal === 5);

    // --- APPLICAZIONE DEL BLOCCO ---
    // Se una qualsiasi delle condizioni è vera, disabilita il menu
    if (isServerLocked || hasPendingOpponent || isCountLocked) {
        formatSelect.disabled = true;
        
        // Opzionale: Se è bloccato per la regola dei 6/5 bicchieri, 
        // assicurati che visivamente mostri "Piramide" se non è stato cambiato altro.
        if (isCountLocked && !isServerLocked) {
             // Questo fa sì che se sei a 6 bicchieri, il menu resti fisso su Piramide
             // senza permettere di cambiarlo.
        }
    } else {
        formatSelect.disabled = false;
    }

    // --- GENERAZIONE OPZIONI (Resto del codice invariato) ---
    const currentValue = formatSelect.value;
    const isLocked = formatSelect.disabled; // Rileggiamo lo stato appena calcolato
    formatSelect.innerHTML = '';

    let availableFormats = [];
    for (const [formatName, limits] of Object.entries(FORMAT_LIMITS)) {
        if (formatName === "Piramide") { 
            if (cupsVal >= 1) availableFormats.push(formatName); 
        } else { 
            if (cupsVal >= limits.min_cups && cupsVal <= limits.max_cups) availableFormats.push(formatName); 
        }
    }

    availableFormats.sort((a, b) => (a === "Piramide") ? -1 : (b === "Piramide") ? 1 : a.localeCompare(b));
    if (cupsVal === 0 && !availableFormats.includes("Piramide")) availableFormats = ["Piramide"];

    availableFormats.forEach(fmt => {
        const opt = document.createElement('option');
        opt.value = fmt; 
        opt.text = formatDisplayNames[fmt] || fmt;
        
        if (typeof formatColors !== 'undefined' && formatColors[fmt]) {
            opt.style.backgroundColor = formatColors[fmt];
            opt.style.color = "#333"; 
        }
        
        formatSelect.appendChild(opt);
    });

    if (isLocked) {
        let found = false;
        // Determina quale valore mostrare nel menu bloccato
        // Se è bloccato dal server, usa quello del server.
        // Se è bloccato dal conteggio (6 o 5), usa quello corrente (che sarà Piramide di default)
        const targetLockedValue = serverOppFormat || currentValue || "Piramide";

        for(let i=0; i<formatSelect.options.length; i++){ 
            if(formatSelect.options[i].value === targetLockedValue) { 
                formatSelect.value = targetLockedValue; 
                found = true; 
            } 
        }
        if (!found) { 
            const opt = document.createElement('option'); 
            opt.value = targetLockedValue; 
            opt.text = formatDisplayNames[targetLockedValue] || targetLockedValue; 
            
            if (typeof formatColors !== 'undefined' && formatColors[targetLockedValue]) {
                opt.style.backgroundColor = formatColors[targetLockedValue];
                opt.style.color = "#333";
            }

            formatSelect.appendChild(opt); 
            formatSelect.value = targetLockedValue; 
        }
    } else {
        if (availableFormats.includes(serverOppFormat)) formatSelect.value = serverOppFormat;
        else if (availableFormats.includes(currentValue)) formatSelect.value = currentValue;
        else formatSelect.value = availableFormats[0];
    }
    
    if (typeof window.updateFormatColor === 'function') {
        window.updateFormatColor();
    }
}

/* ==========================================
   2. UI.JS - Gestione Interfaccia e Griglia
   ========================================== */

// Helper interno per ottenere il layout visivo
function getLayoutByFormat(fmt) { 
    return visualLayouts[fmt] || visualLayouts["Piramide"]; 
}

// ... [La funzione updateAvailableFormats RIMANE UGUALE A PRIMA] ...
// (Per brevità non la ricopio tutta, lasciala com'era nel tuo codice)


// --- NUOVA FUNZIONE EVENTO CAMBIO FORMATO ---
window.handleFormatChange = function(selectElement) {
    // 1. Aggiorna l'input nascosto
    const hiddenInput = document.getElementById('hidden_formato');
    if (hiddenInput) {
        hiddenInput.value = selectElement.value;
    }

    // 2. Deseleziona i radio dei tiri
    document.querySelectorAll('input[name="risultato_tiro"]').forEach(rb => {
        rb.checked = false;
    });

    // 3. NUOVA ANIMAZIONE (Forma + Testo)
    const formatName = selectElement.value;
    triggerFormatOverlay(formatName);

    // 4. Disabilita select
    selectElement.disabled = true;

    // 5. Invia il form
    setTimeout(() => {
        const form = document.getElementById('gameForm');
        if (form) form.submit();
    }, 1200); // Aumentato leggermente il tempo per godersi l'animazione (era 300)
};

// --- NUOVA FUNZIONE: LOGICA ANIMAZIONE OVERLAY ---
function triggerFormatOverlay(formatName) {
    const overlayWrapper = document.querySelector('.format-content-wrapper');
    const shapeEl = document.getElementById('format-shape');
    const textEl = document.getElementById('format-text');

    if (!overlayWrapper || !shapeEl || !textEl) return;

    // 1. Imposta il testo
    // Usa formatDisplayNames da config.js se esiste, altrimenti il valore grezzo
    const displayText = (typeof formatDisplayNames !== 'undefined' && formatDisplayNames[formatName]) 
                        ? formatDisplayNames[formatName] 
                        : formatName;
    textEl.innerText = displayText;

    // 2. Scegli la forma CSS in base al nome
    // Rimuovi tutte le classi di forma precedenti
    shapeEl.className = 'format-shape';

    // Logica di assegnazione forma AGGIORNATA
    const lowerName = formatName.toLowerCase();
    
    if (lowerName.includes('piramide') || lowerName.includes('triangolo')) {
        if(lowerName.includes('mini')) shapeEl.classList.add('shape-minipiramide');
        else shapeEl.classList.add('shape-piramide');
    } 
    else if (lowerName.includes('rombo') || lowerName.includes('diamante')) {
        shapeEl.classList.add('shape-rombo');
    }
    else if (lowerName.includes('casa')) {
        shapeEl.classList.add('shape-casa');
    }
    else if (lowerName.includes('albero')) {
        shapeEl.classList.add('shape-albero');
    }
    // --- NUOVI CONTROLLI ---
    else if (lowerName.includes('singolo')) {
        shapeEl.classList.add('shape-singolo'); // Diventa cerchio
    }
    else if (lowerName.includes('verticale')) {
        shapeEl.classList.add('shape-linea-verticale'); // Diventa barra verticale
    }
    else if (lowerName.includes('orizzontale') || lowerName.includes('linea')) {
        // "linea" generico lo mandiamo su orizzontale se non è specificato verticale
        shapeEl.classList.add('shape-linea-orizzontale'); // Diventa barra orizzontale
    }
    else {
        // Default (es. 4x4, Quadrato, Nido)
        shapeEl.classList.add('shape-box');
    }

    // 3. Fai partire l'animazione
    overlayWrapper.classList.remove('animate-format-popup');
    void overlayWrapper.offsetWidth; // Force Reflow
    overlayWrapper.classList.add('animate-format-popup');
}




// --- GESTIONE COLORI ---
window.updateFormatColor = function() {
    const sel = document.getElementById('formato');
    
    // Controlliamo che config.js sia caricato e ci siano i colori
    if(sel && typeof formatColors !== 'undefined') {
        const selectedValue = sel.value;
        const color = formatColors[selectedValue] || "#ffffff";
        
        // Applichiamo il colore direttamente allo stile inline
        // Questo vince sul CSS (ora che abbiamo tolto !important dal CSS)
        sel.style.backgroundColor = color;
        
        // Assicuriamo che il testo sia leggibile (Scuro)
        sel.style.color = "#212121"; 
    }
}


// Aggiorna le griglie (Loro e Noi)
window.updateCupsVisuals = function() {
    // Prima di tutto aggiorna lo stato di disponibilità del menu
    window.updateAvailableFormats();
    const formatSelect = document.getElementById('formato');
    if(!formatSelect) return;

    const selectedOppFormat = formatSelect.value;
    let listToUseOpponent = (selectedOppFormat === serverOppFormat) ? activeCupsOpponent : null;

    const theirGrid = document.getElementById('their-cups-grid');
    const myGrid = document.getElementById('my-cups-grid');

    if(theirGrid) {
        theirGrid.className = 'cups-grid-container'; 
        renderGrid(theirGrid, selectedOppFormat, listToUseOpponent, true);
    }
    if(myGrid) {
        myGrid.className = 'cups-grid-container'; 
        renderGrid(myGrid, serverMyFormat, activeCupsMe, false);
    }

    if (typeof window.handleLogic === 'function') window.handleLogic();
    if (typeof window.updateFormatColor === 'function') window.updateFormatColor();

}

// Funzione interna per disegnare i cerchi dei bicchieri
function renderGrid(container, format, activeList, isOpponent) {
    container.innerHTML = '';
    container.setAttribute('data-format', format);

    let layoutRows = getLayoutByFormat(format);
    let rowsToRender = isOpponent ? layoutRows : [...layoutRows].reverse();

    rowsToRender.forEach((row, rowIndex) => {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'cup-row';

        row.forEach((cupName, cupIndex) => {
            const circle = document.createElement('div');
            circle.className = 'cup-circle';
            // Animazione ingresso a cascata
            circle.style.animationDelay = `${(rowIndex * 0.1) + (cupIndex * 0.05)}s`;

            // Controlla se è eliminato
            if (activeList !== null && Array.isArray(activeList) && !activeList.includes(cupName)) {
                circle.classList.add('eliminated');
            }

            if (isOpponent) {
                // Logica "Loro" (Bersagli)
                if (typeof pendingCups !== 'undefined' && pendingCups.includes(cupName)) {
                    circle.classList.add('pending-hit');
                    circle.setAttribute('data-pending', 'true');
                }

                // Qui colleghiamo l'evento click (definito in logic.js)
                circle.setAttribute('onclick', 'toggleCupSelection(this)');

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.name = 'bicchiere_colpito';
                checkbox.value = cupName;

                // I bicchieri "pending" non si possono selezionare come nuovi colpi
                if (typeof pendingCups !== 'undefined' && pendingCups.includes(cupName)) {
                    checkbox.disabled = true;
                }

                circle.appendChild(checkbox);
            } else {
                // Logica "Noi" (Solo visualizzazione)
                if (typeof myPendingCups !== 'undefined' && myPendingCups.includes(cupName)) {
                    circle.classList.add('pending-loss');
                }
            }
            rowDiv.appendChild(circle);
        });
        container.appendChild(rowDiv);
    });
}


// In fondo a ui.js
document.addEventListener('DOMContentLoaded', function() {
    
    // 1. Popola menu e blocca se necessario
    if (typeof updateAvailableFormats === 'function') updateAvailableFormats();
    
    // 2. Disegna il tavolo
    if (typeof updateCupsVisuals === 'function') updateCupsVisuals();
    
    // 3. Gestisce la UI dei colpi (Centro/Miss)
    if (typeof handleLogic === 'function') handleLogic();

    // 4. Applica il colore iniziale al box formato
    if (typeof updateFormatColor === 'function') updateFormatColor();
});



// OVERTIME 

function playFormatAnimation(formatName) {
    const overlay = document.getElementById('format-overlay');
    const shape = document.getElementById('format-shape');
    const text = document.getElementById('format-text');

    if (!overlay || !shape || !text) return;

    // 1. Imposta il testo e la classe per l'icona
    text.innerText = formatName.toUpperCase(); // Es: "PIRAMIDE"
    
    // Rimuovi vecchie classi e aggiungi quella nuova (es. class="format-shape piramide")
    shape.className = 'format-shape ' + formatName.toLowerCase(); 

    // 2. Mostra l'overlay
    overlay.classList.add('active');

    // 3. Nascondi dopo 2.5 secondi (durata animazione)
    setTimeout(() => {
        overlay.classList.remove('active');
    }, 2500);
}