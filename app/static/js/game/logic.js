/* ==========================================
   3. LOGIC.JS - Logica di Gioco e Eventi
   ========================================== */

// Helper per ottenere il limite attuale (Doppio, Triplo, ecc.)
function getCurrentLimit() {
    if (document.getElementById('multi_doppio').checked) return 2;
    if (document.getElementById('multi_triplo').checked) return 3;
    if (document.getElementById('multi_quadruplo').checked) return 4;
    if (document.getElementById('multi_quintuplo').checked) return 5;
    if (document.getElementById('multi_sestuplo').checked) return 6;
    return 1; // Default per multi_none
}

window.toggleCupSelection = function(circleElement) {
    const centerOpt = document.getElementById('opt_centro');
    // Blocco di sicurezza: se non hai selezionato "Centro", non fa nulla
    if (!centerOpt || !centerOpt.checked) {
        alert("⚠️ SELEZIONA PRIMA 'CENTRO'!");
        return;
    }

    const checkbox = circleElement.querySelector('input');
    if (!checkbox) return;

    const isPending = circleElement.classList.contains('pending-hit');
    const isAlreadySelected = circleElement.classList.contains('selected');

    // Recuperiamo i dati attuali
    const limit = getCurrentLimit(); // es. 2 se è Doppio
    // Conta solo i bicchieri rossi attualmente selezionati
    const activeCheckboxes = document.querySelectorAll('input[name="bicchiere_colpito"]:checked').length;
    
    // --- A. LOGICA DI BLOCCO (Preventiva) ---
    if (!isAlreadySelected) {
        // Se sto provando a selezionare un bicchiere NUOVO (Rosso)
        if (!isPending) {
            // Il limite dinamico è: Potenza del tiro + Numero di Rehits attivi
            // Esempio: Doppio(2) + 1 Rehit = Posso selezionare 3 cose in totale (ma activeCheckboxes conta solo i rossi)
            // Quindi: se ho già selezionato i rossi necessari, mi fermo.
            // Nota: rehits.length mi da il "bonus".
            if (activeCheckboxes >= (limit + rehits.length)) {
                // Feedback visivo che hai finito i colpi
                const instr = document.getElementById('multi-instruction');
                if(instr) {
                    let oldText = instr.innerText;
                    instr.innerText = "LIMITE RAGGIUNTO!";
                    instr.style.color = "red";
                    setTimeout(() => { 
                        instr.innerText = oldText; 
                        updateInstructionText(); // Ripristina testo corretto
                    }, 800);
                }
                return; // BLOCCO: Non fa selezionare
            }
        }
    }

    // --- B. ESECUZIONE DEL CLICK ---
    if (isPending) {
        // Gestione Rehit (Azzurro)
        const cupName = checkbox.value;
        if (rehits.includes(cupName)) {
            // Deseleziono
            rehits = rehits.filter(item => item !== cupName);
            circleElement.classList.remove('selected');
        } else {
            // Seleziono
            rehits.push(cupName);
            circleElement.classList.add('selected');
        }
        
        // Sincronizzo l'input hidden per il backend
        const rehitInput = document.getElementById('rehit_list');
        if(rehitInput) rehitInput.value = rehits.join(',');
        
        // I pending NON devono essere "checked" nel form standard dei bicchieri rossi
        checkbox.checked = false; 

    } else {
        // Gestione Normale (Rosso)
        const willBeSelected = !checkbox.checked;
        checkbox.checked = willBeSelected;
        
        if (willBeSelected) circleElement.classList.add('selected');
        else circleElement.classList.remove('selected');
    }

    // --- C. AGGIORNAMENTI UI E CONTROLLO INVIO ---
    updateInstructionText(); // Aggiorna "Segna ancora X bicchieri"
    checkAndSubmit();        // Controlla se il turno è finito
};

function checkAndSubmit() {
    // 1. Potenza del tiro (Singolo=1, Doppio=2, ecc.)
    const baseLimit = getCurrentLimit(); 
    
    // 2. Click effettuati
    const selectedRehits = rehits.length; // Bicchieri Blu (Pending colpiti)
    const selectedNew = document.querySelectorAll('input[name="bicchiere_colpito"]:checked').length; // Bicchieri Rossi (Nuovi colpiti)

    // 3. Analisi del Tavolo Avversario
    const allTheirCups = document.querySelectorAll('.their-side .cup-circle:not(.eliminated)');
    const allTheirPending = document.querySelectorAll('.their-side .cup-circle.pending-hit:not(.eliminated)');
    
    // VERIFICA SPECIALE: Tutti i bicchieri rimasti sono pending?
    const areAllCupsPending = (allTheirCups.length > 0 && allTheirCups.length === allTheirPending.length);

    // 4. Calcolo del budget di click necessari
    let budgetNecessarioDiRossi;

    if (areAllCupsPending) {
        // --- CASO SPECIALE: TUTTI I BICCHIERI SONO PENDING ---
        // In questo caso, il Rehit (blu) vale come un colpo normale (rosso) perché non c'è altro da colpire.
        // Quindi non chiediamo rossi extra. Il limite è semplicemente la potenza del tiro.
        // E i click totali validi sono (Rossi + Blu).
        
        const totalClicks = selectedNew + selectedRehits;
        
        // Se ho cliccato abbastanza cose (tra blu e rossi) per soddisfare il limite
        if (totalClicks >= baseLimit) {
            setTimeout(() => {
                const form = document.getElementById('gameForm');
                if(form) form.submit();
            }, 300);
            return;
        }
        
    } else {
        // --- CASO NORMALE ---
        // Ogni Rehit (azzurro) è un "bonus" che richiede un rosso extra.
        // Quindi il numero di rossi che devo cliccare è il limite base.
        // (Il sistema attuale ti lascia selezionare Rehit illimitati, ma devi pareggiare i Rossi).
        budgetNecessarioDiRossi = baseLimit; 
        
        // A. Hai completato i click richiesti sui bicchieri rossi
        const budgetSoddisfatto = selectedNew >= budgetNecessarioDiRossi;
        
        // B. NON CI SONO PIÙ BICCHIERI CLICCABILI (Rossi) DA CLICCARE
        // (Es. ho un Triplo, ma sul tavolo sono rimasti solo 2 bicchieri rossi)
        const bicchieriRossiDisponibili = document.querySelectorAll('.their-side .cup-circle:not(.eliminated):not(.pending-hit)').length;
        // Se ho selezionato tutti i rossi che potevo
        const hoPresoTuttiIRossi = selectedNew >= bicchieriRossiDisponibili;

        // Se hai fatto almeno un click...
        if (selectedNew + selectedRehits > 0) {
            // ...e hai finito i click necessari OPPURE hai finito fisicamente i bicchieri rossi
            if (budgetSoddisfatto || hoPresoTuttiIRossi) {
                setTimeout(() => {
                    const form = document.getElementById('gameForm');
                    if(form) form.submit();
                }, 300);
            }
        }
    }
}
// Helper per contare i click totali fatti in questo turno
function totalSelected() {
    return document.querySelectorAll('input[name="bicchiere_colpito"]:checked').length + rehits.length;
}


// Aggiungi questa funzione helper per l'animazione
function triggerMultiplierAnimation(label) {
    const textEl = document.getElementById('multiplier-text');
    if (!textEl) return;

    // Imposta il testo
    textEl.innerText = label;
    
    // Rimuovi la classe se esiste già per poterla riattivare
    textEl.classList.remove('animate-multiplier');
    
    // "Force reflow" - trucco per riavviare l'animazione CSS
    void textEl.offsetWidth; 
    
    // Aggiungi la classe che fa partire l'animazione
    textEl.classList.add('animate-multiplier');
}

// --- MODIFICA LA TUA FUNZIONE ESISTENTE toggleMultiBtn ---
window.toggleMultiBtn = function(targetRadioId) {
    const targetRadio = document.getElementById(targetRadioId);
    const noneRadio = document.getElementById('multi_none');

    if (!targetRadio || !noneRadio) return;

    // Mappa ID radio -> Testo da mostrare
    const labels = {
        'multi_doppio': 'DOPPIO!',
        'multi_triplo': 'TRIPLO!',
        'multi_quadruplo': 'QUADRUPLO!',
        'multi_quintuplo': 'QUINTUPLO!',
        'multi_sestuplo': 'SESTUPLO!'
    };

    // Logica Toggle
    if (targetRadio.checked) {
        noneRadio.checked = true; // Spegni
        // Non mostriamo animazione se spegniamo
    } else {
        targetRadio.checked = true; // Accendi
        
        // --- QUI PARTE L'ANIMAZIONE ---
        if (labels[targetRadioId]) {
            triggerMultiplierAnimation(labels[targetRadioId]);
        }
    }

    // Resetta selezione e aggiorna UI
    resetSelezioneBicchieri();
    handleLogic();
};


// Gestione click tasti principali (Miss, Bordo, Centro)
window.handleResultClick = function(value) {
    handleLogic(); // Aggiorna UI

    if (value !== 'Centro') {
        const form = document.getElementById('gameForm');
        if(!form) return;

        const radioBtn = document.querySelector(`input[name="risultato_tiro"][value="${value}"]`);
        const label = radioBtn ? radioBtn.nextElementSibling : null;

        document.body.classList.add('animating-submit');

        if (label) {
            if (value === 'Miss') {
                label.classList.add('animate-miss-trigger');
                setTimeout(() => { form.submit(); }, 500);
            } else if (value === 'Bordo') {
                label.classList.add('animate-bordo-trigger');
                setTimeout(() => { form.submit(); }, 500);
            } else {
                form.submit();
            }
        } else {
             form.submit();
        }
    }
};

window.handleLogic = function() {
    const centerOpt = document.getElementById('opt_centro');
    const dynamicSection = document.getElementById('dynamic-hit-section');
    const theirContainerOuter = document.getElementById('their-cups-container');
    const instr = document.getElementById('instruction-text');

    // Se "Centro" è selezionato
    if (centerOpt && centerOpt.checked) {
        // 1. Mostra la sezione dei moltiplicatori
        if(dynamicSection) dynamicSection.style.display = 'block';
        
        // 2. Attiva l'effetto glow sui bicchieri avversari
        if(theirContainerOuter) theirContainerOuter.classList.add('active-target');
        
        // 3. Sincronizza i bottoni grafici con i radio button nascosti
        const buttons = {
            'multi_doppio': 'btn_doppio', 
            'multi_triplo': 'btn_triplo',
            'multi_quadruplo': 'btn_quad', 
            'multi_quintuplo': 'btn_quint',
            'multi_sestuplo': 'btn_sest'
        };

        for (let [radioId, btnId] of Object.entries(buttons)) {
            const btn = document.getElementById(btnId);
            const radio = document.getElementById(radioId);
            if(btn && radio) {
                if(radio.checked) btn.classList.add('active');
                else btn.classList.remove('active');
            }
        }
        
        // 4. Aggiorna il testo istruzioni (importante chiamarlo qui!)
        updateInstructionText();
        
        // 5. Aggiorna il testo principale in alto
        if(instr) { 
            instr.innerText = "TOCCA IL BICCHIERE ELIMINATO"; 
            instr.style.color = "#2ecc71"; 
            instr.style.fontWeight = "bold"; 
        }

    } else {
        // Se "Centro" NON è selezionato (es. hai cliccato Miss o Reset)
        if(dynamicSection) dynamicSection.style.display = 'none';
        if(theirContainerOuter) theirContainerOuter.classList.remove('active-target');
        
        if(instr) { 
            instr.innerText = "Seleziona 'Centro' per interagire"; 
            instr.style.color = "#999"; 
            instr.style.fontWeight = "normal"; 
        }
        
        // Reset completo (pulisce moltiplicatori e bicchieri)
        resetMultipli();
    }
};

// AGGIORNATA: Pulisce tutto, inclusi i bottoni grafici
function resetMultipli() {
    const noneOpt = document.getElementById('multi_none');
    if(noneOpt) noneOpt.checked = true;

    resetSelezioneBicchieri(); // Pulisce rehits e cerchi selezionati
    
    // Rimuove la classe active da tutti i bottoni grafici
    document.querySelectorAll('.multi-btn').forEach(btn => btn.classList.remove('active'));
    
    // Ripristina testo istruzione
    const instrEl = document.getElementById('multi-instruction');
    if(instrEl) instrEl.innerText = "Seleziona i bicchieri";
}



// Nuova funzione per pulire solo i bicchieri senza resettare il moltiplicatore
function resetSelezioneBicchieri() {
    rehits = [];
    const rehitInput = document.getElementById('rehit_list');
    if(rehitInput) rehitInput.value = "";
    document.querySelectorAll('.their-side .cup-circle').forEach(c => {
        c.classList.remove('selected');
        const cb = c.querySelector('input');
        if(cb) cb.checked = false;
    });
}

function updateInstructionText() {
    const instrEl = document.getElementById('multi-instruction');
    if (!instrEl) return;

    // 1. Recupero le variabili
    const limit = getCurrentLimit(); // Potenza del tiro (es. 2 per doppio)
    const numRehits = rehits.length; // Numero rehit fatti (azzurri)
    const numReds = document.querySelectorAll('input[name="bicchiere_colpito"]:checked').length; // Rossi cliccati

    // 2. Controllo Caso Speciale: TUTTI i bicchieri avversari sono pending?
    const allTheirCups = document.querySelectorAll('.their-side .cup-circle:not(.eliminated)');
    const allTheirPending = document.querySelectorAll('.their-side .cup-circle.pending-hit:not(.eliminated)');
    const areAllCupsPending = (allTheirCups.length > 0 && allTheirCups.length === allTheirPending.length);

    // 3. CALCOLO DINAMICO DI "clickRimanenti"
    let clickRimanenti;

    if (areAllCupsPending) {
        // CASO SPECIALE: Se sono tutti pending, i rehit (blu) VALGONO come hit per finire il turno.
        // Quindi sottraiamo sia i rossi che i blu dal limite.
        // Esempio: Doppio (2). Clicco 1 blu, 1 rosso. (2 - 2) = 0 -> Invia.
        clickRimanenti = limit - (numReds + numRehits);
    } else {
        // CASO NORMALE: I rehit (blu) sono bonus che richiedono un rosso extra.
        // Quindi contiamo solo i rossi per vedere quanto manca al limite base.
        // Esempio: Doppio (2). Clicco 1 blu. (2 - 0) = 2 -> "Segna ancora 2".
        clickRimanenti = limit - numReds;
    }

    // 4. Gestione Testi (La tua logica originale)
    if (clickRimanenti <= 0) {
        // Se abbiamo finito i colpi (o siamo andati oltre in overkill), non scrive nulla.
        // Questo risolve il problema che vedevi prima.
        instrEl.innerText = ""; 
    } 
    else {
        instrEl.style.color = "#e67e22"; 

        // CASO 1: 1 click rimasto, 0 rehit
        if (clickRimanenti === 1 && numRehits === 0) {
            instrEl.innerText = "Segna 1 bicchiere";
        }
        // CASO 2: 1 click rimasto, almeno 1 rehit
        else if (clickRimanenti === 1 && numRehits >= 1) {
            instrEl.innerText = "Segna ancora 1 bicchiere";
        }
        // CASO 3: Più click rimasti, 0 rehit
        else if (clickRimanenti > 1 && numRehits === 0) {
            instrEl.innerText = `Segna ${clickRimanenti} bicchieri`;
        }
        // CASO 4: Più click rimasti, almeno 1 rehit
        else if (clickRimanenti > 1 && numRehits >= 1) {
            instrEl.innerText = `Segna ancora ${clickRimanenti} bicchieri`;
        }
    }
}
