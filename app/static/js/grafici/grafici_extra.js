/**
 * File: static/js/grafici/grafici_extra.js
 */

// Registrazione globale del plugin (una sola volta all'avvio)
if (typeof ChartAnnotation !== 'undefined') {
    Chart.register(ChartAnnotation);
}

document.addEventListener("DOMContentLoaded", function() {
    if (window.extraData && window.extraData.rawStats) {
        renderExtraCharts(window.extraData);
    } else {
        console.error("Errore: window.extraData non trovato.");
    }
});

const drinkColorMap = {
    'acqua': '#81d4fa', 'birra': '#fbc02d', 'cerveza': '#fbc02d',
    'spritz': '#ff7043', 'aperol': '#ff7043', 'campari': '#ff7043',
    'vino': '#ad1457', 'rosso': '#ad1457', 'bianco': '#ad1457',
    'jager': '#3e2723', 'bomb': '#3e2723', 'coca': '#121212',
    'pepsi': '#121212', 'lemon': '#c6ff00', 'tonic': '#b2ebf2', 'gin': '#b2ebf2'
};

function renderExtraCharts(data) {
    const raw = data.rawStats;
    const parts = data.partnerships || { partners: { labels: [], values: [] }, enemies: { labels: [], values: [] } };
    const shots = data.shotMetrics;

    // --- 1. EFFICACIA PER NUMERO TIRO ---
    if (shots && shots.shot_number_trend) {
        renderLineChart(
            'chartShotNumSuccess', 
            shots.shot_number_trend.labels, 
            shots.shot_number_trend.values_hist,
            shots.shot_number_trend.values_today,
            shots.shot_number_trend.phase_changes 
        );

        if (shots.shot_number_trend.cup_gap) {
            renderGapChart(
                'chartCupGap',
                shots.shot_number_trend.labels,
                shots.shot_number_trend.cup_gap
            );
        }
    }

    // --- 2. ANALISI BEVANDE ---
    const drinkStats = calculateCategorySuccess(raw.bevanda, raw.centro);
    if (drinkStats.labels.length > 0) {
        const drinkColors = drinkStats.labels.map(label => getDrinkColor(label));
        renderBarChart('chartDrinkSuccess', drinkStats.labels, drinkStats.values, 'Successo %', drinkColors);
    }

    // --- 3. ANALISI POSTAZIONI (CON ORDINAMENTO FORZATO) ---
    const posStats = calculateCategorySuccess(raw.postazione, raw.centro);
    
    // Logica di ordinamento: Sinistra -> Centrale -> Destra
    const order = ["Sinistra", "Centrale", "Destra"];
    
    // Creiamo un array di oggetti per poterli ordinare mantenendo il legame label-valore
    let combinedPos = posStats.labels.map((label, i) => {
        return { label: label, value: posStats.values[i] };
    });

    combinedPos.sort((a, b) => {
        let idxA = order.findIndex(opt => a.label.includes(opt) || a.label.includes(opt.toUpperCase().substring(0,2)));
        let idxB = order.findIndex(opt => b.label.includes(opt) || b.label.includes(opt.toUpperCase().substring(0,2)));
        return idxA - idxB;
    });

    const sortedLabels = combinedPos.map(x => x.label);
    const sortedValues = combinedPos.map(x => x.value);

    if (sortedLabels.length > 0) {
        const posColors = sortedLabels.map(label => {
            if (label.includes('Sinistra') || label.includes('SX')) return '#3498db';
            if (label.includes('Centrale') || label.includes('CEN')) return '#2ecc71';
            if (label.includes('Destra') || label.includes('DX')) return '#e67e22';
            return '#95a5a6';
        });
        renderBarChart('chartPositionSuccess', sortedLabels, sortedValues, 'Successo %', posColors);
    }

    // --- 4. PARTNER E NEMICI ---
    if (parts.partners && parts.partners.labels.length > 0) {
        renderBarChart('chartPartnerWinRate', parts.partners.labels, parts.partners.values, 'Win Rate %', '#2ecc71');
    }
    if (parts.enemies && parts.enemies.labels.length > 0) {
        renderBarChart('chartEnemyLossRate', parts.enemies.labels, parts.enemies.values, 'Loss Rate %', '#e74c3c');
    }

    // --- NUOVO GRAFICO POSIZIONE VS BICCHIERI ---
    if (data.posByCups) {
        renderPosByCupsChart(
            'chartPosByCups',
            data.posByCups.labels,
            data.posByCups.sx,
            data.posByCups.cen,
            data.posByCups.dx
        );
    }
}

function getDrinkColor(label) {
    const lowerLabel = label.toLowerCase();
    for (let key in drinkColorMap) {
        if (lowerLabel.includes(key)) return drinkColorMap[key];
    }
    return 'rgba(149, 165, 166, 0.7)';
}

function calculateCategorySuccess(categoryList, centerList) {
    let stats = {};
    categoryList.forEach((cat, index) => {
        if (!cat || cat === '-' || cat === 'None') return;
        if (!stats[cat]) stats[cat] = { total: 0, made: 0 };
        stats[cat].total += 1;
        const isCenter = centerList[index] === 'Sì' || centerList[index] === true || centerList[index] === 'True' || centerList[index] === 1;
        if (isCenter) stats[cat].made += 1;
    });
    const labels = Object.keys(stats);
    const values = labels.map(l => ((stats[l].made / stats[l].total) * 100).toFixed(1));
    return { labels, values };
}

// --------------------------------------------------------
// FUNZIONE PER GRAFICI A BARRE (Assi Dinamici)
// --------------------------------------------------------
function renderBarChart(ctxId, labels, values, datasetLabel, colors) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;
    if (Chart.getChart(ctx)) Chart.getChart(ctx).destroy();

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: datasetLabel,
                data: values,
                backgroundColor: colors,
                borderRadius: 8,
                barPercentage: 0.6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { maxRotation: 45, minRotation: 0 } }, // Rotazione automatica
                y: { 
                    beginAtZero: true, 
                    // Rimosso max: 100. L'asse si adatterà al valore più alto (es. 60%)
                    ticks: { callback: (v) => v + "%" } 
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.y}%` } }
            }
        }
    });
}

// --------------------------------------------------------
// FUNZIONE PER GRAFICI A LINEE (Assi Dinamici + Legenda Fasi)
// --------------------------------------------------------
function renderLineChart(ctxId, labels, valuesHist, valuesToday, phaseChanges) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;
    if (Chart.getChart(ctx)) Chart.getChart(ctx).destroy();

    // 1. GENERAZIONE DELLA LEGENDA (Se ci sono fasi)
    if (phaseChanges && phaseChanges.length > 0) {
        renderPhaseLegend(ctxId);
    }

    const annotations = {};
    if (phaseChanges && phaseChanges.length > 0) {
        // Colori in ordine di fase: Inizio -> Metà -> Fine
        const zoneColors = [
            'rgba(46, 204, 113, 0.15)', // Verde (6 Bicchieri)
            'rgba(241, 196, 15, 0.15)', // Giallo (5-4 Bicchieri)
            'rgba(52, 152, 219, 0.15)', // Blu (3-2 Bicchieri)
            'rgba(155, 89, 182, 0.15)'  // Viola (1 Bicchiere)
        ];

        let lastIndex = 0;
        phaseChanges.forEach((change, i) => {
            let xIndex = labels.indexOf(change.shot + "°");
            if (xIndex !== -1) {
                annotations['zone' + i] = {
                    type: 'box',
                    xMin: lastIndex,
                    xMax: xIndex,
                    backgroundColor: zoneColors[i % zoneColors.length],
                    borderWidth: 0,
                };
                lastIndex = xIndex;
            }
        });

        // Ultima zona (spesso la chiusura)
        annotations['zone_final'] = {
            type: 'box',
            xMin: lastIndex,
            xMax: labels.length - 1,
            backgroundColor: 'rgba(231, 76, 60, 0.15)', // Rosso (Finale)
            borderWidth: 0
        };
    }

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Media Storica',
                    data: valuesHist,
                    borderColor: 'rgba(52, 152, 219, 0.95)',
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Oggi',
                    data: valuesToday,
                    borderColor: '#ff5e57',
                    borderWidth: 4,
                    pointBackgroundColor: '#ff5e57',
                    pointRadius: 4,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // FONDAMENTALE PER ALLUNGARE IL GRAFICO
            plugins: {
                annotation: { annotations: annotations },
                legend: { display: true, position: 'top', align: 'end' }
            },
            scales: {
                y: { 
                    beginAtZero: false, 
                    display: true,
                    title: { display: true, text: 'Successo %', color: '#7f8c8d' },
                    ticks: { callback: v => v + "%", color: '#7f8c8d', font: { size: 12, weight: 'bold' } },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                },
                x: { grid: { display: false }, ticks: { color: '#7f8c8d' } }
            }
        }
    });
}

// --------------------------------------------------------
// NUOVA FUNZIONE: CREA LA LEGENDA SOTTO IL GRAFICO
// --------------------------------------------------------
function renderPhaseLegend(ctxId) {
    const canvas = document.getElementById(ctxId);
    if (!canvas) return;

    const wrapper = canvas.parentElement; 
    const card = wrapper.parentElement;
    
    // Evita di creare la legenda due volte se ricarichi la pagina
    if (card.querySelector('.phase-legend')) return;

    // Questa legenda spiega i colori definiti in zoneColors sopra.
    // Ordine logico: 6 -> 5/4 -> 3/2 -> 1
    const legendHtml = `
        <div class="phase-legend">
            <span class="legend-title">Fasi Partita (Bicchieri):</span>
            <div class="legend-item">
                <span class="dot" style="background: rgba(46, 204, 113, 0.8)"></span> 6
            </div>
            <div class="legend-item">
                <span class="dot" style="background: rgba(241, 196, 15, 0.8)"></span> 5-4
            </div>
            <div class="legend-item">
                <span class="dot" style="background: rgba(52, 152, 219, 0.8)"></span> 3-2
            </div>
            <div class="legend-item">
                <span class="dot" style="background: rgba(155, 89, 182, 0.8)"></span> 1
            </div>
            <div class="legend-item">
                <span class="dot" style="background: rgba(231, 76, 60, 0.8)"></span> 0
            </div>
        </div>
    `;

    // Inserisce l'HTML dopo il contenitore del grafico
    wrapper.insertAdjacentHTML('afterend', legendHtml);
}

function renderGapChart(ctxId, labels, values) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;
    if (Chart.getChart(ctx)) Chart.getChart(ctx).destroy();

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Gap Bicchieri (Tu - Avversario)',
                data: values,
                borderColor: '#9b59b6', 
                backgroundColor: (context) => {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    if (!chartArea) return null;
                    const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                    
                    gradient.addColorStop(0, 'rgba(46, 204, 113, 0.5)');   
                    gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0)');
                    gradient.addColorStop(1, 'rgba(231, 76, 60, 0.5)');    
                    return gradient;
                },
                fill: true,
                tension: 0.4,
                borderWidth: 3,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    display: true,
                    title: { display: true, text: 'Vantaggio/Svantaggio', color: '#7f8c8d' },
                    // Gap è un valore assoluto (-3, +2), non percentuale. 
                    // Non serve toccare max qui, si adatta già da solo.
                    grid: {
                        color: (context) => context.tick.value === 0 ? '#2c3e50' : 'rgba(0,0,0,0.05)',
                        lineWidth: (context) => context.tick.value === 0 ? 2 : 1
                    },
                    ticks: { color: '#7f8c8d' }
                },
                x: { grid: { display: false }, ticks: { color: '#7f8c8d' } }
            },
            plugins: {
                legend: { display: false },
                tooltip: { 
                    mode: 'index', 
                    intersect: false,
                    callbacks: {
                        label: (c) => `Gap: ${c.parsed.y > 0 ? '+' : ''}${c.parsed.y} bicchieri`
                    }
                }
            }
        }
    });
}

// --------------------------------------------------------
// FUNZIONE PER GRAFICI POSIZIONE (Assi Dinamici)
// --------------------------------------------------------
function renderPosByCupsChart(ctxId, labels, dataSx, dataCen, dataDx) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;
    if (Chart.getChart(ctx)) Chart.getChart(ctx).destroy();

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Sinistra',
                    data: dataSx,
                    borderColor: '#3498db',
                    backgroundColor: '#3498db',
                    tension: 0.3,
                    pointRadius: 4,
                    spanGaps: true 
                },
                {
                    label: 'Centrale',
                    data: dataCen,
                    borderColor: '#2ecc71',
                    backgroundColor: '#2ecc71',
                    tension: 0.3,
                    pointRadius: 4,
                    spanGaps: true
                },
                {
                    label: 'Destra',
                    data: dataDx,
                    borderColor: '#e67e22',
                    backgroundColor: '#e67e22',
                    tension: 0.3,
                    pointRadius: 4,
                    spanGaps: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: (c) => `${c.dataset.label}: ${c.parsed.y}%`
                    }
                }
            },
            scales: {
                y: { 
                    beginAtZero: false, 
                    // Rimosso max: 100
                    ticks: { callback: (v) => v + "%" }
                }
            }
        }
    });
}


