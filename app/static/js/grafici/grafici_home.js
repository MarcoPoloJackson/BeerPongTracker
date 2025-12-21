function createTrendChart(ctxId, labels, dataStorica, dataOggi, labelPrincipale, color) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;
    
    if (Chart.getChart(ctx)) Chart.getChart(ctx).destroy();

    const datasets = [{
        label: 'Storico ' + labelPrincipale,
        data: dataStorica,
        borderColor: color,
        backgroundColor: color.replace('1)', '0.1)'),
        fill: true,
        tension: 0.4,
        pointRadius: 3
    }];

    if (dataOggi && dataOggi.length > 0) {
        datasets.push({
            label: 'Oggi ' + labelPrincipale,
            data: dataOggi,
            borderColor: '#e74c3c',
            backgroundColor: 'rgba(231, 76, 60, 0.2)',
            fill: true,
            tension: 0.4,
            pointStyle: 'star',
            pointRadius: 6,
            spanGaps: false
        });
    }

    new Chart(ctx, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { 
                    display: true, 
                    position: 'top',
                    labels: { boxWidth: 12, font: { size: 11 } }
                },
                tooltip: { 
                    callbacks: { 
                        label: (c) => ` ${c.dataset.label}: ${c.parsed.y}%` 
                    } 
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        autoSkip: true,
                        maxRotation: 45,
                        minRotation: 0,
                        font: { size: 10 }
                    }
                },
                y: { 
                    // 1. beginAtZero: false permette all'asse di non partire da 0 
                    // se i dati sono tutti molto alti (es. tra 80% e 90%)
                    beginAtZero: false, 
                    
                    ticks: { 
                        callback: (v) => v + "%",
                        font: { size: 10 }
                    },
                    grid: { color: 'rgba(0, 0, 0, 0.05)' }
                }
            }
        }
    });
}

function renderComparisonCharts(data) {
    // 1. DEBUG: Stampa i dati precisi nella console per vedere cosa arriva
    console.log("Trend Giornaliero:", data.trendDaily);
    console.log("Trend Orario:", data.trendHourly);
    console.log("--- DEBUG DATI GRAFICI ---");
    console.log("Storico:", data.historical);
    console.log("Giornaliero:", data.daily);
    console.log("Liste Grezze:", data.rawStats);
    console.log("--------------------------");

    // 2. CONFIGURAZIONE ESTETICA COMUNE (Per i grafici a barre)
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false, // Importante per adattarsi al wrapper CSS
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return context.parsed.y + '%';
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true, // Per i grafici a barre è meglio partire da 0 solitamente

                ticks: { callback: function(value) { return value + "%" } }
            }
        }
    };

    // Label dinamica per la data
    const dailyLabel = data.daily.last_date ? `Ultima Giornata (${data.daily.last_date})` : "Ultima Giornata";

    // ============================================================
    // 1. GRAFICO SUCCESSO (Storico vs Oggi)
    // ============================================================
    const ctxSuccess = document.getElementById('chartSuccess');
    if (ctxSuccess) {
        // Distruggi vecchio grafico se esiste
        if (Chart.getChart(ctxSuccess)) Chart.getChart(ctxSuccess).destroy();

        const valStorico = data.historical.historical_success_rate || 0;
        const valOggi = data.daily.daily_success_rate || 0;

        new Chart(ctxSuccess, {
            type: 'bar',
            data: {
                labels: ['Media Storica', dailyLabel],
                datasets: [{
                    label: 'Percentuale Successo',
                    data: [valStorico, valOggi],
                    backgroundColor: ['rgba(52, 73, 94, 0.7)', 'rgba(46, 204, 113, 0.7)'],
                    borderColor: ['rgba(52, 73, 94, 1)', 'rgba(46, 204, 113, 1)'],
                    borderWidth: 1,
                    barPercentage: 0.6
                }]
            },
            options: commonOptions
        });
    }

    // ============================================================
    // 2. GRAFICO BORDI (Storico vs Oggi)
    // ============================================================
    const ctxRim = document.getElementById('chartRim');
    if (ctxRim) {
        if (Chart.getChart(ctxRim)) Chart.getChart(ctxRim).destroy();

        const valStoricoRim = data.historical.historical_rim_rate || 0;
        const valOggiRim = data.daily.daily_rim_rate || 0;

        new Chart(ctxRim, {
            type: 'bar',
            data: {
                labels: ['Media Storica', dailyLabel],
                datasets: [{
                    label: 'Percentuale Bordi',
                    data: [valStoricoRim, valOggiRim],
                    backgroundColor: ['rgba(149, 165, 166, 0.7)', 'rgba(243, 156, 18, 0.7)'],
                    borderColor: ['rgba(149, 165, 166, 1)', 'rgba(243, 156, 18, 1)'],
                    borderWidth: 1,
                    barPercentage: 0.6
                }]
            },
            options: commonOptions
        });
    }

    // ============================================================
    // 3. GRAFICO A TORTA (Distribuzione Tiri TOTALE STORICA)
    // ============================================================
    const ctxPie = document.getElementById('chartDistribution');
    
    if (ctxPie && data.rawStats && data.rawStats.centro) {
        if (Chart.getChart(ctxPie)) Chart.getChart(ctxPie).destroy();

        // Filtriamo le liste grezze totali
        const countCentri = data.rawStats.centro.filter(v => v === 'Sì' || v === true || v === 'True').length;
        const countBordi  = data.rawStats.bordo.filter(v => v === 'Sì' || v === true || v === 'True').length;
        const countMiss   = data.rawStats.miss.filter(v => v === 'Sì' || v === true || v === 'True').length;

        if (countCentri + countBordi + countMiss > 0) {
            new Chart(ctxPie, {
                type: 'pie',
                data: {
                    labels: ['Centri', 'Bordi', 'Miss'],
                    datasets: [{
                        data: [countCentri, countBordi, countMiss],
                        backgroundColor: [
                            'rgba(46, 204, 113, 0.8)', // Verde
                            'rgba(243, 156, 18, 0.8)', // Arancione
                            'rgba(231, 76, 60, 0.8)'   // Rosso
                        ],
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'bottom' },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.label || '';
                                    let value = context.raw;
                                    let total = context.chart._metasets[context.datasetIndex].total;
                                    let percentage = ((value / total) * 100).toFixed(1) + "%";
                                    return `${label}: ${value} (${percentage})`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    // ============================================================
    // 4. GRAFICO A TORTA (Distribuzione Tiri GIORNALIERA)
    // ============================================================
    const ctxPieDaily = document.getElementById('chartDailyDistribution');
    
    // Controlliamo se 'counts' esiste dentro 'data.daily'
    if (ctxPieDaily && data.daily && data.daily.counts) {
        if (Chart.getChart(ctxPieDaily)) Chart.getChart(ctxPieDaily).destroy();

        const dCounts = data.daily.counts; 
        const totalDaily = dCounts.centri + dCounts.bordi + dCounts.miss;

        if (totalDaily > 0) {
            new Chart(ctxPieDaily, {
                type: 'pie',
                data: {
                    labels: ['Centri', 'Bordi', 'Miss'],
                    datasets: [{
                        data: [dCounts.centri, dCounts.bordi, dCounts.miss],
                        backgroundColor: [
                            'rgba(46, 204, 113, 0.8)', // Verde
                            'rgba(243, 156, 18, 0.8)', // Arancione
                            'rgba(231, 76, 60, 0.8)'   // Rosso
                        ],
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'bottom' },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.label || '';
                                    let value = context.raw;
                                    let total = context.chart._metasets[context.datasetIndex].total;
                                    let percentage = ((value / total) * 100).toFixed(1) + "%";
                                    return `${label}: ${value} (${percentage})`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    // ============================================================
    // ANALISI TREND (NUOVI GRAFICI) - INCOLLA QUI
    // ============================================================
    if (data.trendDaily && data.trendHourly) {
        // 1. Successo su Data -> TRUE (Ruota)
    createTrendChart('chartSuccessTrend', data.trendDaily.dates, data.trendDaily.trend_success, null, 'Successo', 'rgba(52, 152, 219, 1)', true);

    // 2. Successo su Ora -> FALSE (Dritto)
    createTrendChart('chartSuccessHourly', data.trendHourly.hours, data.trendHourly.hist_success, data.trendHourly.today_success, 'Successo', 'rgba(52, 152, 219, 1)', false);

    // 3. Bordi su Data -> TRUE (Ruota)
    createTrendChart('chartRimTrend', data.trendDaily.dates, data.trendDaily.trend_rim, null, 'Bordi', 'rgba(243, 156, 18, 1)', true);

    // 4. Bordi su Ora -> FALSE (Dritto)
    createTrendChart('chartRimHourly', data.trendHourly.hours, data.trendHourly.hist_rim, data.trendHourly.today_rim, 'Bordi', 'rgba(243, 156, 18, 1)', false);
    }

}

