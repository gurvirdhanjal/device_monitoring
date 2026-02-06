/**
 * Card Component: Network Availability
 */
import { formatPercent, checkStale } from '../utils.js';

let chartInstance = null;

export function renderNetworkAvailability(data, trendsData) {
    const cardId = 'card-network-avail';
    const container = document.getElementById(cardId);
    if (!container) return;

    // 1. Update Metrics
    if (data && data.devices) {
        const { online_percent, up_percent } = data.devices;
        const percentValue = online_percent ?? up_percent ?? 0;
        const valueEl = document.getElementById('val-availability');
        if (valueEl) valueEl.textContent = formatPercent(percentValue);

        // Color
        if (valueEl) {
            valueEl.className = 'metric-value ' + (percentValue >= 99 ? 'tactical-text-success' : (percentValue >= 95 ? 'tactical-text-warning' : 'tactical-text-danger'));
        }
    }

    // 2. Update Sparkline (if trend data available)
    if (trendsData && trendsData.availability_trend) {
        renderSparkline(trendsData.availability_trend);
    }
}

function renderSparkline(trendData) {
    const canvas = document.getElementById('chart-availability-spark');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = trendData.map(d => d.time);
    const values = trendData.map(d => d.value);

    // Destroy previous instance if needed
    if (chartInstance) {
        chartInstance.data.labels = labels;
        chartInstance.data.datasets[0].data = values;
        chartInstance.update('none'); // Update without full animation
        return;
    }

    // Create new Chart
    // @ts-ignore
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                borderColor: '#2ecc71',
                borderWidth: 2,
                backgroundColor: 'rgba(46, 204, 113, 0.1)',
                fill: true,
                pointRadius: 0,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: {
                x: { display: false },
                y: { display: false, min: 0, max: 100 }
            },
            animation: false
        }
    });
}
