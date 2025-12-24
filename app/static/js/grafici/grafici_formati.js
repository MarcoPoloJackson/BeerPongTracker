/**
 * File: static/js/grafici/grafici_formati.js
 */

// DEFINIZIONE ORDINE GLOBALE
const FORMAT_ORDER = ["Piramide", "Rombo", "Triangolo", "Linea Verticale", "Linea Orizzontale"];

// COLORI SCELTI (Palette Vivace/Moderna)
const formatColors = { 
    "Piramide": "#ffe082",          // 🟡 Giallo Oro
    "Rombo": "#ce93d8",             // 🟣 Lilla Acceso
    "Triangolo": "#69f0ae",         // 🟢 Verde Neon
    "Linea Verticale": "#ffb74d",   // 🟠 Arancione
    "Linea Orizzontale": "#4fc3f7", // 🔵 Ciano/Azzurro
    "Singolo Centrale": "#ff7043"   // 🔴 Corallo Intenso
};

// Colore di fallback se il formato non è nella lista
const defaultColor = "#bdc3c7"; 

document.addEventListener("DOMContentLoaded", function() {
    if (window.formatData) {
        // 1. Processa i dati per i grafici 2D
        const stats = processRawStats(window.formatData.rawStats);
        
        // 2. Aggiorna i Widget in alto
        updateWidgets(stats);

        // 3. Disegna i grafici 2D (Chart.js) con i NUOVI COLORI
        render2DCharts(stats);

        // 4. Disegna i nuovi grafici lineari (Successo per Bicchieri)
        if (window.formatData.successByCups) {
            renderCupsCharts(window.formatData.successByCups);
        }

        // 5. Disegna i grafici 3D (ECharts)
        if (window.formatData.format3D) {
            render3DCharts(window.formatData.format3D);
        }
    } else {
        console.error("Nessun dato trovato in window.formatData");
    }
});

/* ============================================================
   SEZIONE 1: ELABORAZIONE DATI (Per Grafici 2D)
   ============================================================ */
function processRawStats(raw) {
    const formats = raw.formato || [];
    const results = raw.match_result || [];
    const hits = raw.centro || [];
    const matchIds = raw.match_ids || [];
    const agg = {};

    formats.forEach((fmt, i) => {
        if (!fmt || fmt === '-' || fmt === 'None') return;

        let cleanName = fmt;
        if (fmt === 'Altro') cleanName = 'Linea Verticale';
        if (fmt === 'LineaVerticale') cleanName = 'Linea Verticale';

        if (!agg[cleanName]) {
            agg[cleanName] = { wins: 0, total_matches: new Set(), hits: 0, total_shots: 0 };
        }

        agg[cleanName].total_matches.add(matchIds[i]);
        agg[cleanName].total_shots++;
        
        const isHit = (hits[i] === 'Sì' || hits[i] === true || hits[i] === 'True' || hits[i] === 1);
        if (isHit) agg[cleanName].hits++;
    });

    const matchOutcomeMap = {}; 
    matchIds.forEach((mid, i) => { if (results[i]) matchOutcomeMap[mid] = results[i]; });

    for (const fmt in agg) {
        let wins = 0;
        agg[fmt].total_matches.forEach(mid => {
            const res = matchOutcomeMap[mid];
            if (res === 'Win' || res === 'Vittoria') wins++;
        });
        agg[fmt].real_wins = wins;
        agg[fmt].unique_matches_count = agg[fmt].total_matches.size;
    }
    return agg;
}

function updateWidgets(stats) {
    let mostPlayed = { name: '-', count: 0 };
    let bestWinRate = { name: '-', rate: 0 };
    let bestAccuracy = { name: '-', rate: 0 };

    for (const [fmt, data] of Object.entries(stats)) {
        // --- MODIFICA: Salta se è Piramide per il calcolo del "Più Giocato" ---
        if (fmt === 'Piramide') continue; 
        // ----------------------------------------------------------------------

        const minMatches = 1; 
        if (data.unique_matches_count > mostPlayed.count) mostPlayed = { name: fmt, count: data.unique_matches_count };
        
        const wr = (data.real_wins / data.unique_matches_count) * 100;
        if (data.unique_matches_count >= minMatches && wr >= bestWinRate.rate) bestWinRate = { name: fmt, rate: wr };
        
        const acc = (data.hits / data.total_shots) * 100;
        if (data.total_shots > 5 && acc >= bestAccuracy.rate) bestAccuracy = { name: fmt, rate: acc };
    }

    document.getElementById('widget-most-played').innerText = mostPlayed.name;
    document.getElementById('widget-best-winrate').innerText = `${bestWinRate.rate.toFixed(1)}% (${bestWinRate.name})`;
    document.getElementById('widget-best-accuracy').innerText = `${bestAccuracy.rate.toFixed(1)}% (${bestAccuracy.name})`;
}

/* ============================================================
   SEZIONE 2: RENDER GRAFICI 2D (Chart.js)
   ============================================================ */
function render2DCharts(stats) {
    // Ordiniamo le labels in base all'ordine preferito
    const labels = Object.keys(stats).sort((a, b) => {
        let idxA = FORMAT_ORDER.indexOf(a);
        let idxB = FORMAT_ORDER.indexOf(b);
        if (idxA === -1) idxA = 999;
        if (idxB === -1) idxB = 999;
        return idxA - idxB;
    });

    // --- 1. Mappatura Colori per Istogrammi ---
    const barColors = labels.map(l => formatColors[l] || defaultColor);

    const winRates = labels.map(l => ((stats[l].real_wins / stats[l].unique_matches_count) * 100).toFixed(1));
    const accuracies = labels.map(l => ((stats[l].hits / stats[l].total_shots) * 100).toFixed(1));
    
    // --- 2. Dati specifici per la Torta (Esclusa Piramide) ---
    const pieLabels = labels.filter(l => l !== 'Piramide');
    const pieUsages = pieLabels.map(l => stats[l].unique_matches_count);
    const pieColors = pieLabels.map(l => formatColors[l] || defaultColor);
    // ---------------------------------------------------------

    // Passiamo i colori dinamici
    createBarChart('chartFormatWinRate', labels, winRates, 'Win Rate', barColors);
    createBarChart('chartFormatAccuracy', labels, accuracies, 'Precisione', barColors);
    
    // Passiamo i dati filtrati e i colori dinamici alla torta
    createPieChart('chartFormatUsage', pieLabels, pieUsages, pieColors);
}

function createBarChart(ctxId, labels, values, label, colors) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;
    if (Chart.getChart(ctx)) Chart.getChart(ctx).destroy();

    new Chart(ctx, {
        type: 'bar',
        data: { 
            labels: labels, 
            datasets: [{ 
                label: label, 
                data: values, 
                backgroundColor: colors, // Usa l'array di colori
                borderRadius: 6 
            }] 
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { 
                y: { 
                    beginAtZero: true, 
                    // Rimosso max: 100 per dinamicità
                    ticks: { callback: v => v + "%" } 
                } 
            },
            plugins: { legend: { display: false } }
        }
    });
}

function createPieChart(ctxId, labels, values, colors) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;
    if (Chart.getChart(ctx)) Chart.getChart(ctx).destroy();

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{ 
                data: values, 
                backgroundColor: colors, // Usa l'array di colori filtrato
                borderWidth: 2 
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
    });
}

/* ============================================================
   SEZIONE 3: GRAFICI 3D - FIX MOUSE OVERLAY + ORDINAMENTO
   ============================================================ */
function render3DCharts(format3DData) {
    console.log("Dati 3D ricevuti (Mouse Fix + Sorted):", format3DData);

    // 1. Convertiamo in array di [key, value] e ordiniamo
    const sortedEntries = Object.entries(format3DData).sort((a, b) => {
        let idxA = FORMAT_ORDER.indexOf(a[0]);
        let idxB = FORMAT_ORDER.indexOf(b[0]);
        if (idxA === -1) idxA = 999;
        if (idxB === -1) idxB = 999;
        return idxA - idxB;
    });

    // 2. Iteriamo sull'array ordinato
    for (const [fmtName, dataPoints] of sortedEntries) {
        
        if (fmtName === 'Singolo Centrale') {
            const safeId = fmtName.replace(/ /g, '-');
            const domId = `heatmap-${safeId}`;
            const chartDom = document.getElementById(domId);
            if (chartDom) {
                const card = chartDom.closest('.chart-card');
                if (card) card.style.display = 'none';
            }
            continue;
        }

        const safeId = fmtName.replace(/ /g, '-');
        const domId = `heatmap-${safeId}`;
        const chartDom = document.getElementById(domId);
        
        if (chartDom) {
            if (echarts.getInstanceByDom(chartDom)) echarts.dispose(chartDom);
            
            chartDom.addEventListener('wheel', (e) => {
                e.stopPropagation();
            }, { capture: true, passive: true });

            const myChart = echarts.init(chartDom, null, { renderer: 'canvas' });
            
            // --- 1. CALCOLI (NORMALIZZAZIONE ASSI PER IL MOUSE) ---
            const xVals = dataPoints.map(d => d.x);
            const yVals = dataPoints.map(d => d.y);
            
            const rawMinX = Math.min(...xVals);
            const rawMaxX = Math.max(...xVals);
            const rawMinY = Math.min(...yVals);
            const rawMaxY = Math.max(...yVals);
            
            const midX = (rawMinX + rawMaxX) / 2;
            const midY = (rawMinY + rawMaxY) / 2;
            
            const spreadX = rawMaxX - rawMinX;
            const spreadY = rawMaxY - rawMinY;
            
            const maxDimension = Math.max(spreadX, spreadY);
            const halfSpan = (maxDimension / 2) + 0.8; 
            
            const finalMinX = midX - halfSpan;
            const finalMaxX = midX + halfSpan;
            const finalMinY = midY - halfSpan;
            const finalMaxY = midY + halfSpan;

            // --- 2. RANGE ---
            const zVals = dataPoints.map(d => d.z);
            const minZ = Math.min(...zVals);
            let maxZ = Math.max(...zVals);
            if (maxZ === minZ) maxZ = minZ + 1; 

            // --- 3. POSIZIONAMENTO ---
            // Se lo schermo è piccolo, aggiungiamo 60 alla distanza per zoommare fuori
            const isMobile = window.innerWidth < 600;
            const dynamicDistance = 100 + (maxDimension * 10) + (isMobile ? 0 : 0);
            let topOffset = 20 - (spreadY * 5);
            if (isMobile) {
                topOffset += -10; // Aumenta questo numero per spingere il tavolo più in basso
                }   

            const seriesData = dataPoints.map(item => ({
                value: [item.x, item.y, item.z],
                cupName: item.cup,
                hits: item.hits,
                total: item.total
            }));

            const option = {
                backgroundColor: 'transparent',

                tooltip: {
                    show: true,
                    trigger: 'item',
                    backgroundColor: 'rgba(42, 27, 21, 0.95)',
                    borderColor: '#8d6e63',
                    borderWidth: 1,
                    textStyle: { color: '#f8fafc', fontSize: 13 },
                    formatter: (p) => {
                        const relativePercent = (p.value[2] - minZ) / (maxZ - minZ);
                        let valColor = '#3b82f6'; 
                        if(relativePercent > 0.4) valColor = '#a855f7';
                        if(relativePercent > 0.8) valColor = '#ef4444';

                        return `<div style="text-align:center; padding: 4px;">
                                  <b style="font-size:1.1em">${p.data.cupName}</b><br/>
                                  <span style="color:${valColor}; font-size:1.4em; font-weight:900;">${p.value[2]}%</span><br/>
                                  <small style="color:#cbd5e1;">${p.data.hits} su ${p.data.total} colpi</small>
                                </div>`;
                    }
                },
                
                visualMap: {
                    min: minZ,
                    max: maxZ,
                    inRange: { 
                        color: ['#1e3a8a', '#6d28d9', '#be185d', '#f43f5e'],
                        colorAlpha: [1, 1] 
                    },
                    show: false
                },
                
                xAxis3D: { type: 'value', show: false, min: finalMinX, max: finalMaxX },
                yAxis3D: { type: 'value', show: false, min: finalMinY, max: finalMaxY },
                
                // Rimosso max: 100 anche qui per coerenza
                zAxis3D: { type: 'value', show: false, min: 0 },
                
                grid3D: {
                    boxWidth: 110, 
                    boxDepth: 110, 
                    boxHeight: 40,
                    show: false, 

                    groundPlane: { show: true, color: 'transparent' },
                    
                    top: topOffset + '%', 
                    
                    viewControl: {
                        projection: 'perspective',
                        autoRotate: false,       
                        rotateSensitivity: 0,   
                        zoomSensitivity: 0,      
                        panSensitivity: 0,       
                        alpha: 35,               
                        beta: 0,                 
                        distance: dynamicDistance 
                    },
                    
                    light: {
                        main: { 
                            shadow: true,
                            shadowQuality: 'high',
                            intensity: 0.7,      
                            alpha: 30,           
                            beta: 15             
                        },
                        ambient: { intensity: 0.6 } 
                    }
                },
                series: [{
                    type: 'bar3D',
                    data: seriesData,
                    shading: 'lambert', 
                    
                    bevelSize: 0.5, 
                    bevelSmoothness: 20, 
                    barSize: 20, 
                    
                    itemStyle: { opacity: 1 },
                    label: {
                        show: true, 
                        distance: 5,
                        formatter: (p) => p.value[2] > 0 ? p.value[2] + '%' : '',
                        textStyle: {
                            color: '#ffffff',
                            fontSize: 16,
                            fontWeight: '800',
                            fontFamily: 'Inter, sans-serif',
                            backgroundColor: 'rgba(0,0,0,0.6)',
                            padding: [4, 8],
                            borderRadius: 6
                        }
                    },
                    emphasis: {
                        label: { show: true },
                        itemStyle: { color: '#fbbf24' } 
                    }
                }]
            };

            myChart.setOption(option);
            window.addEventListener('resize', () => myChart.resize());
        }
    }
}

/* ============================================================
   SEZIONE 4: NUOVI GRAFICI (FIX VISIBILITÀ ETICHETTE)
   ============================================================ */
function renderCupsCharts(data) {
    const labels = data.labels; 

    // --- GRAFICO 1: GENERALE (Istogramma) ---
    const ctxGen = document.getElementById('chartCupsGeneral');
    if (ctxGen) {
        if (Chart.getChart(ctxGen)) Chart.getChart(ctxGen).destroy();

        new Chart(ctxGen, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '% Successo',
                    data: data.general,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: '#3b82f6',
                    borderWidth: 1,
                    borderRadius: 4,
                    barPercentage: 0.75,
                }]
            },
            plugins: [{
                // PLUGIN CUSTOM PER I NUMERI SOPRA LE BARRE
                id: 'barLabels',
                afterDatasetsDraw(chart) {
                    const { ctx, scales: { y } } = chart;
                    chart.data.datasets.forEach((dataset, i) => {
                        const meta = chart.getDatasetMeta(i);
                        meta.data.forEach((bar, index) => {
                            const value = dataset.data[index];
                            if(value != null) {
                                ctx.fillStyle = '#1e293b'; // Colore Scuro
                                ctx.font = '800 13px Inter'; // Font più grassetto e grande
                                ctx.textAlign = 'center';
                                ctx.textBaseline = 'bottom';
                                // Scrive il valore 5px sopra la barra
                                ctx.fillText(value + '%', bar.x, bar.y - 5);
                            }
                        });
                    });
                }
            }],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: { top: 20 } // Un po' di margine extra di sicurezza
                },
                scales: {
                    x: { 
                        title: { display: true, text: 'Bicchieri Rimasti' },
                        grid: { display: false } // Rimuove griglia verticale per pulizia
                    },
                    y: { 
                        beginAtZero: true, 
                        // --- LA CHIAVE È QUI ---
                        grace: '10%', // Aggiunge il 10% di spazio vuoto sopra la barra più alta
                        ticks: { callback: v => v + '%' },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    }
                },
                plugins: { 
                    legend: { display: false },
                    tooltip: { enabled: false } // Disabilita il tooltip standard (ridondante)
                }
            }
        });
    }

    // --- GRAFICO 2: PER FORMATO (Linee Logaritmiche) ---
    const ctxFmt = document.getElementById('chartCupsByFormat');
    if (ctxFmt) {
        if (Chart.getChart(ctxFmt)) Chart.getChart(ctxFmt).destroy();

        const datasets = [];
        const sortedFormats = Object.keys(data.by_format).sort((a, b) => {
            let idxA = FORMAT_ORDER.indexOf(a);
            let idxB = FORMAT_ORDER.indexOf(b);
            if (idxA === -1) idxA = 999;
            if (idxB === -1) idxB = 999;
            return idxA - idxB;
        });

        sortedFormats.forEach(fmt => {
            const values = data.by_format[fmt];
            const color = formatColors[fmt] || defaultColor;
            datasets.push({
                label: fmt,
                data: values,
                borderColor: color,
                backgroundColor: color,
                borderWidth: 2,
                tension: 0.3,
                pointRadius: 3,
                fill: false 
            });
        });

        new Chart(ctxFmt, {
            type: 'line',
            data: { labels: labels, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        type: 'logarithmic',
                        title: { display: true, text: 'Bicchieri Rimasti (Scala Log)' },
                        min: 1, max: 6, reverse: true,
                        ticks: { callback: v => [1,2,3,4,5,6].includes(v) ? v : null },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    },
                    y: { 
                        beginAtZero: false, 
                        // Anche qui niente max, si adatta da solo
                        ticks: { callback: v => v + '%' } 
                    }
                },
                plugins: {
                    legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } }
                }
            }
        });
    }
}