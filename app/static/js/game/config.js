/* ==========================================
   CONFIG.JS - Configurazioni e Costanti
   ========================================== */

const FORMAT_LIMITS = {
    "Piramide": { min_cups: 1, max_cups: 6 },
    "Rombo": { min_cups: 4, max_cups: 4 },
    "Triangolo": { min_cups: 3, max_cups: 3 },
    "Linea Verticale": { min_cups: 2, max_cups: 2 },
    "Linea Orizzontale": { min_cups: 2, max_cups: 2 },
    "Singolo Centrale": { min_cups: 1, max_cups: 1 }
};

const formatDisplayNames = { 
    "Piramide": "Piramide", 
    "Rombo": "Rombo",
    "Triangolo": "Triangolo",
    "Linea Verticale": "Linea Verticale",
    "Linea Orizzontale": "Linea Orizzontale",
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

// COLORI SCELTI (Palette Vivace/Moderna)
const formatColors = { 
    "Piramide": "#ffe082",          // 🟡 Giallo Oro (Classico)
    "Rombo": "#ce93d8",             // 🟣 Lilla Acceso
    "Triangolo": "#69f0ae",         // 🟢 Verde Neon
    "Linea Verticale": "#ffb74d",   // 🟠 Arancione
    "Linea Orizzontale": "#4fc3f7", // 🔵 Ciano/Azzurro
    "Singolo Centrale": "#ff7043"   // 🔴 Corallo Intenso (Molto meglio del grigio)
};