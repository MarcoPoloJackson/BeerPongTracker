// ==========================================
// 1. VARIABILI GLOBALI E CONFIGURAZIONE
// ==========================================

// NOTE: activeCupsOpponent, activeCupsMe, etc. are defined in player_record.html

// Variabile per tracciare i Re-Hits (Bicchieri Azzurri cliccati)
let rehits = [];

const FORMAT_LIMITS = {
    "Piramide": { min_cups: 1, max_cups: 6 },
    "Rombo": { min_cups: 4, max_cups: 4 },
    "Triangolo": { min_cups: 3, max_cups: 3 },
    "Linea Verticale": { min_cups: 2, max_cups: 2 },
    "Linea Orizzontale": { min_cups: 2, max_cups: 2 },
    "Singolo Centrale": { min_cups: 1, max_cups: 1 }
};

const formatDisplayNames = {
    "Piramide": "Piramide 🔺",
    "Rombo": "Rombo 💠",
    "Triangolo": "Triangolo 📐",
    "Linea Verticale": "Linea Vert. ❙",
    "Linea Orizzontale": "Linea Oriz. ━",
    "Singolo Centrale": "Singolo ⏺"
};

const visualLayouts = {
    "Piramide": [ ["3 Sx", "3 Cen", "3 Dx"], ["2 Sx", "2 Dx"], ["1 Cen"] ],
    "Rombo": [ ["R3 Cen"], ["R2 Sx", "R2 Dx"], ["R1 Cen"] ],
    "Triangolo": [ ["T2 Sx", "T2 Dx"], ["T1 Cen"] ],
    "Linea Verticale": [ ["LV 2"], ["LV 1"] ],
    "Linea Orizzontale": [ ["LO Sx", "LO Dx"] ],
    "Singolo Centrale": [ ["Singolo"] ]
};

// ==========================================
// 2. STILI MODERNI (INJECTED)
// ==========================================

function injectGameStyles() {
    const styleId = 'modern-grid-styles';
    if (document.getElementById(styleId)) return;

    const css = `
        /* Container layout */
        .cups-grid-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px; /* Spacing between rows */
            padding: 15px;
            transition: all 0.3s ease;
        }

        /* Rows */
        .cup-row {
            display: flex;
            justify-content: center;
            gap: 12px; /* Spacing between cups in a row */
        }

        /* The Cup Circle */
        .cup-circle {
            width: 55px;
            height: 55px;
            border-radius: 50%;
            background: radial-gradient(circle at 30% 30%, #ff6b6b, #c0392b);
            border: 3px solid #fff;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3), inset 0 -2px 5px rgba(0,0,0,0.2);
            position: relative;
            cursor: pointer;
            transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275), filter 0.3s ease, box-shadow 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Hover Effect */
        .their-side .cup-circle:not(.eliminated):hover {
            transform: scale(1.1);
            z-index: 10;
        }

        /* Checkbox hidden but functional */
        .cup-circle input[type="checkbox"] {
            appearance: none;
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
            margin: 0;
            cursor: pointer;
            opacity: 0;
        }

        /* --- STATES --- */

        /* Eliminated (Ghost) */
        .cup-circle.eliminated {
            background: transparent;
            border-color: rgba(255,255,255,0.2);
            box-shadow: none;
            opacity: 0.4;
            pointer-events: none; /* Can't click dead cups usually */
        }
        
        /* If "Centro" is active, we might want to click eliminated cups */
        .active-target .cup-circle.eliminated {
            pointer-events: auto;
            cursor: crosshair;
        }

        /* Selected (To be hit) */
        .cup-circle.selected {
            background: radial-gradient(circle at 30% 30%, #2ecc71, #27ae60);
            box-shadow: 0 0 15px #2ecc71, 0 4px 8px rgba(0,0,0,0.3);
            transform: scale(1.15);
            border-color: #fff;
        }

        /* Pending Hit (Re-hit / Azzurro) */
        .cup-circle.pending-hit {
            background: radial-gradient(circle at 30% 30%, #3498db, #2980b9);
            box-shadow: 0 0 10px #3498db;
            animation: pulse-blue 2s infinite;
        }

        /* My Cups (Blue Theme by default) */
        #my-cups-grid .cup-circle {
            background: radial-gradient(circle at 30% 30%, #4facfe, #00f2fe);
            border-color: #fff;
        }
        #my-cups-grid .cup-circle.eliminated {
            background: transparent;
            opacity: 0.3;
        }
        #my-cups-grid .cup-circle.pending-loss {
            background: #e74c3c;
            animation: shake 0.5s;
        }

        /* Animations */
        @keyframes pulse-blue {
            0% { box-shadow: 0 0 0 0 rgba(52, 152, 219, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(52, 152, 219, 0); }
            100% { box-shadow: 0 0 0 0 rgba(52, 152, 219, 0); }
        }

        @keyframes popIn {
            from { transform: scale(0); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        
        .cup-circle {
            animation: popIn 0.4s ease-out backwards;
        }
    `;

    const styleEl = document.createElement('style');
    styleEl.id = styleId;
    styleEl.innerHTML = css;
    document.head.appendChild(styleEl);
}

// ==========================================
// 3. FUNZIONI LOGICHE
// ==========================================

function getLayoutByFormat(fmt) { return visualLayouts[fmt] || visualLayouts["Piramide"]; }

function updateAvailableFormats() {
    let cupsVal = 1;

    // 'isMatchActive' is now global, defined in player_record.html
    if (typeof isMatchActive !== 'undefined' && isMatchActive) {
        if (activeCupsOpponent && Array.isArray(activeCupsOpponent)) cupsVal = activeCupsOpponent.length;
        else cupsVal = parseInt(serverCupsTarget) || 6;
    } else {
         const inputEl = document.getElementById('numero_bicchieri');
         if(inputEl) cupsVal = parseInt(inputEl.value) || 6;
    }

    const formatSelect = document.getElementById('formato');
    if (!formatSelect) return;

    const currentValue = formatSelect.value;
    const isLocked = formatSelect.disabled;
    formatSelect.innerHTML = '';

    let availableFormats = [];
    for (const [formatName, limits] of Object.entries(FORMAT_LIMITS)) {
        if (formatName === "Piramide") { if (cupsVal >= 1) availableFormats.push(formatName); }
        else { if (cupsVal >= limits.min_cups && cupsVal <= limits.max_cups) availableFormats.push(formatName); }
    }
    availableFormats.sort((a, b) => (a === "Piramide") ? -1 : (b === "Piramide") ? 1 : a.localeCompare(b));
    if (cupsVal === 0 && !availableFormats.includes("Piramide")) availableFormats = ["Piramide"];

    availableFormats.forEach(fmt => {
        const opt = document.createElement('option');
        opt.value = fmt; opt.text = formatDisplayNames[fmt] || fmt;
        formatSelect.appendChild(opt);
    });

    if (isLocked) {
        let found = false;
        for(let i=0; i<formatSelect.options.length; i++){ if(formatSelect.options[i].value === serverOppFormat) { formatSelect.value = serverOppFormat; found = true; } }
        if (!found) { const opt = document.createElement('option'); opt.value = serverOppFormat; opt.text = serverOppFormat; formatSelect.appendChild(opt); formatSelect.value = serverOppFormat; }
    } else {
        if (availableFormats.includes(serverOppFormat)) formatSelect.value = serverOppFormat;
        else if (availableFormats.includes(currentValue)) formatSelect.value = currentValue;
        else formatSelect.value = availableFormats[0];
    }
    updateCupsVisuals();
}

function updateCupsVisuals() {
    const formatSelect = document.getElementById('formato');
    if(!formatSelect) return;

    const selectedOppFormat = formatSelect.value;
    let listToUseOpponent = (selectedOppFormat === serverOppFormat) ? activeCupsOpponent : null;

    const theirGrid = document.getElementById('their-cups-grid');
    const myGrid = document.getElementById('my-cups-grid');

    if(theirGrid) {
        theirGrid.className = 'cups-grid-container'; // Add modern class
        renderGrid(theirGrid, selectedOppFormat, listToUseOpponent, true);
    }
    if(myGrid) {
        myGrid.className = 'cups-grid-container'; // Add modern class
        renderGrid(myGrid, serverMyFormat, activeCupsMe, false);
    }

    handleLogic();
}

function renderGrid(container, format, activeList, isOpponent) {
    container.innerHTML = '';
    // Store format for potential specific CSS tweaks
    container.setAttribute('data-format', format);

    let layoutRows = getLayoutByFormat(format);
    // Opponent grid is usually viewed standard (pyramid base at back),
    // My grid is viewed reversed (base close to me).
    // Adjust logic depending on your specific visual preference.
    let rowsToRender = isOpponent ? layoutRows : [...layoutRows].reverse();

    rowsToRender.forEach((row, rowIndex) => {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'cup-row';

        row.forEach((cupName, cupIndex) => {
            const circle = document.createElement('div');
            circle.className = 'cup-circle';
            // Animation stagger delay
            circle.style.animationDelay = `${(rowIndex * 0.1) + (cupIndex * 0.05)}s`;

            // Check alive status
            if (activeList !== null && Array.isArray(activeList) && !activeList.includes(cupName)) {
                circle.classList.add('eliminated');
            }

            if (isOpponent) {
                // Pending Hit Logic (Blue cups)
                if (typeof pendingCups !== 'undefined' && pendingCups.includes(cupName)) {
                    circle.classList.add('pending-hit');
                    circle.setAttribute('data-pending', 'true');
                }

                circle.setAttribute('onclick', 'toggleCupSelection(this)');

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.name = 'bicchiere_colpito';
                checkbox.value = cupName;

                // Pending cups controlled by logic, not standard checkbox
                if (typeof pendingCups !== 'undefined' && pendingCups.includes(cupName)) checkbox.disabled = true;

                circle.appendChild(checkbox);
            } else {
                // My Side Logic
                if (typeof myPendingCups !== 'undefined' && myPendingCups.includes(cupName)) {
                    circle.classList.add('pending-loss');
                }
            }
            rowDiv.appendChild(circle);
        });
        container.appendChild(rowDiv);
    });
}

window.toggleCupSelection = function(circleElement) {
    const centerOpt = document.getElementById('opt_centro');
    if (!centerOpt || !centerOpt.checked) {
        alert("⚠️ SELEZIONA PRIMA 'CENTRO'!");
        return;
    }

    const checkbox = circleElement.querySelector('input');
    if (!checkbox) return;

    const isPending = circleElement.classList.contains('pending-hit');

    // --- CONTROLLO SPECIALE: TUTTI I BICCHIERI SONO PENDENTI? ---
    const totalAlive = document.querySelectorAll('.their-side .cup-circle:not(.eliminated)').length;
    const totalPending = document.querySelectorAll('.their-side .cup-circle:not(.eliminated).pending-hit').length;

    const allCupsArePending = (totalAlive > 0 && totalAlive === totalPending);
    // -------------------------------------------------------------

    // --- CASO 1: RE-HIT (Clicco su bicchiere Azzurro) ---
    if (isPending) {
        const cupName = checkbox.value;

        if (rehits.includes(cupName)) {
            rehits = rehits.filter(item => item !== cupName);
            circleElement.classList.remove('selected');
        } else {
            rehits.push(cupName);
            circleElement.classList.add('selected');

            // SE NON SONO TUTTI PENDENTI -> Chiedi sacrificio
            if (!allCupsArePending) {
                alert("🔁 RE-HIT REGISTRATO: " + cupName + "\n\nOra seleziona un bicchiere ROSSO libero da eliminare al suo posto.");
            }
        }

        checkbox.checked = false;
        const rehitInput = document.getElementById('rehit_list');
        if(rehitInput) rehitInput.value = rehits.join(",");
    }

    // --- CASO 2: COLPO NORMALE O SACRIFICIO (Clicco su bicchiere Rosso) ---
    else {
        const willBeSelected = !checkbox.checked;
        checkbox.checked = willBeSelected;
        if (willBeSelected) circleElement.classList.add('selected');
        else circleElement.classList.remove('selected');
    }

    checkAndSubmit(allCupsArePending);
};

function checkAndSubmit(isSpecialMode = false) {
    const baseLimit = getCurrentLimit();
    const activeCheckboxes = document.querySelectorAll('input[name="bicchiere_colpito"]:checked').length;
    const rehitCount = rehits.length;
    const totalActions = activeCheckboxes + rehitCount;

    const targetTotal = isSpecialMode ? baseLimit : (baseLimit + rehitCount);

    if (totalActions > targetTotal) {
        alert("Troppe selezioni! Hai selezionato " + totalActions + ".");
        return;
    }

    // SE IL NUMERO E' CORRETTO -> INVIA IL FORM
    if (totalActions === targetTotal && totalActions > 0) {
        setTimeout(() => {
            const form = document.getElementById('gameForm');
            if(form) form.submit();
        }, 300);
    }
}

function getCurrentLimit() {
    const double = document.getElementById('multi_doppio');
    if (double && double.checked) return 2;

    const triple = document.getElementById('multi_triplo');
    if (triple && triple.checked) return 3;

    const quad = document.getElementById('multi_quadruplo');
    if (quad && quad.checked) return 4;

    const quint = document.getElementById('multi_quintuplo');
    if (quint && quint.checked) return 5;

    const sext = document.getElementById('multi_sestuplo');
    if (sext && sext.checked) return 6;

    return 1;
}

window.handleResultClick = function(value) {
    handleLogic();

    if (value !== 'Centro') {
        const form = document.getElementById('gameForm');
        if(!form) return;

        const radioBtn = document.querySelector(`input[name="risultato_tiro"][value="${value}"]`);
        const label = radioBtn ? radioBtn.nextElementSibling : null;

        document.body.classList.add('animating-submit');

        if (label) {
            if (value === 'Miss') {
                label.classList.add('animate-miss-trigger');
                setTimeout(() => { form.submit(); }, 700);
            } else if (value === 'Bordo') {
                label.classList.add('animate-bordo-trigger');
                setTimeout(() => { form.submit(); }, 600);
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

    if (centerOpt && centerOpt.checked) {
        if(dynamicSection) dynamicSection.style.display = 'block';
        if(theirContainerOuter) theirContainerOuter.classList.add('active-target');
        if(instr) { instr.innerText = "TOCCA IL BICCHIERE ELIMINATO"; instr.style.color = "#2ecc71"; instr.style.fontWeight = "bold"; }
    } else {
        if(dynamicSection) dynamicSection.style.display = 'none';
        if(theirContainerOuter) theirContainerOuter.classList.remove('active-target');
        if(instr) { instr.innerText = "Seleziona 'Centro' per interagire"; instr.style.color = "#999"; instr.style.fontWeight = "normal"; }
        resetMultipli();
    }
};

function resetMultipli() {
    const noneOpt = document.getElementById('multi_none');
    if(noneOpt) noneOpt.checked = true;

    rehits = [];
    const rehitInput = document.getElementById('rehit_list');
    if(rehitInput) rehitInput.value = "";

    const circles = document.querySelectorAll('.their-side .cup-circle');
    circles.forEach(c => {
        c.classList.remove('selected');
        const cb = c.querySelector('input');
        if(cb) cb.checked = false;
    });
}

document.addEventListener('DOMContentLoaded', function() {
    injectGameStyles(); // Inietta CSS moderni
    updateAvailableFormats();
    const fmtSelect = document.getElementById('formato');
    if(fmtSelect && typeof serverOppFormat !== 'undefined' && fmtSelect.value !== serverOppFormat && !fmtSelect.disabled) {
         let isValidFmt = false;
         for(let i=0; i<fmtSelect.options.length; i++){ if(fmtSelect.options[i].value === serverOppFormat) isValidFmt = true; }
         if(isValidFmt) { fmtSelect.value = serverOppFormat; }
    }
    updateCupsVisuals();
    handleLogic();
});