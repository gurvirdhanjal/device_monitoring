/**
 * Card Component: Network Performance
 * Shows Latency and Packet Loss as main KPIs
 */
import { checkStale, animateValue } from '../utils.js';

export function renderNetworkPerformance(data, timestamp) {
    const cardId = 'card-network-perf';
    const container = document.getElementById(cardId);
    if (!container) return;

    const body = container.querySelector('.card-body');
    if (!data || !data.network_health) {
        if (body) body.innerHTML = '<div class="text-secondary">No Data</div>';
        return;
    }

    const { avg_latency_ms, avg_packet_loss_pct, packet_loss } = data.network_health;
    const packetLoss = packet_loss ?? avg_packet_loss_pct ?? 0;

    // Main Value (Latency)
    const valueEl = document.getElementById('val-latency');
    if (valueEl) {
        const latVal = parseInt(avg_latency_ms ?? 0, 10);
        let latEl = valueEl.querySelector('.anim-lat');

        if (!latEl) {
            valueEl.innerHTML = `<span class="anim-lat">${latVal}</span> ms`;
        } else {
            const currentLat = parseInt(latEl.textContent, 10) || 0;
            animateValue(latEl, currentLat, latVal);
        }
        // Color based on threshold
        valueEl.className = 'metric-value';
        if (avg_latency_ms > 200) valueEl.classList.add('tactical-text-danger');
        else if (avg_latency_ms > 100) valueEl.classList.add('tactical-text-warning');
        else if (avg_latency_ms > 0) valueEl.classList.add('tactical-text-success');
    }

    // Sub Info (Packet Loss + Quality Rating)
    const subEl = document.getElementById('sub-packet-loss');
    if (subEl) {
        const lossClass = packetLoss > 5 ? 'tactical-text-danger' : packetLoss > 1 ? 'tactical-text-warning' : 'tactical-text-success';
        const qualityLabel = packetLoss === 0 && avg_latency_ms < 50 ? 'Excellent' :
            packetLoss < 1 && avg_latency_ms < 100 ? 'Good' :
                packetLoss < 5 && avg_latency_ms < 200 ? 'Fair' : 'Poor';

        subEl.innerHTML = `
            <div class="stat-subinfo">
                <span class="${lossClass}">Packet Loss: ${packetLoss.toFixed(2)}%</span>
                <span style="color: var(--tactical-border); margin: 0 0.5rem">|</span>
                <span class="tactical-text-muted">Quality: ${qualityLabel}</span>
            </div>
        `;
    }

    checkStale(timestamp, cardId);
}
