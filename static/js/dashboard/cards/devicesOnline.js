/**
 * Card Component: Devices Online
 */
import { formatPercent, checkStale, animateValue } from '../utils.js';

export function renderDevicesOnline(data, timestamp) {
    const cardId = 'card-devices-online';
    const container = document.getElementById(cardId);
    if (!container) return;

    const body = container.querySelector('.card-body');
    if (!data || !data.devices) {
        if (body) body.innerHTML = '<div class="text-secondary">No Data</div>';
        return;
    }

    const devices = data.devices || {};
    const total = devices.total ?? 0;
    const online = devices.online ?? devices.up ?? 0;
    const degraded = devices.degraded ?? 0;
    const healthy = devices.healthy ?? Math.max(0, online - degraded);
    const offline = devices.offline ?? devices.down ?? 0;
    const unknown = devices.unknown ?? Math.max(0, total - online - offline);
    const onlinePercent = devices.online_percent ?? devices.up_percent ?? 0;

    // Main Value (Animated)
    const valueEl = document.getElementById('val-devices-online');
    if (valueEl) {
        let onlineEl = valueEl.querySelector('.anim-online');
        let totalEl = valueEl.querySelector('.anim-total');

        if (!onlineEl) {
            valueEl.innerHTML = `<span class="anim-online">${online}</span>/<span class="anim-total">${total}</span>`;
        } else {
            const currentOnline = parseInt(onlineEl.textContent, 10) || 0;
            const currentTotal = parseInt(totalEl.textContent, 10) || 0;
            animateValue(onlineEl, currentOnline, online);
            animateValue(totalEl, currentTotal, total);
        }
    }

    // Sub Info (Breakdown) - WITH LABELS for clarity
    const breakdownEl = document.getElementById('sub-devices-online');
    if (breakdownEl) {
        const parts = [];

        // Always show healthy if > 0
        if (healthy > 0) {
            parts.push(`<span class="tactical-text-success">Healthy: ${healthy}</span>`);
        }

        // Show degraded if > 0
        if (degraded > 0) {
            parts.push(`<span class="tactical-text-warning">Degraded: ${degraded}</span>`);
        }

        // Always show offline
        parts.push(`<span class="tactical-text-danger">Offline: ${offline}</span>`);

        // Show unknown if > 0
        if (unknown > 0) {
            parts.push(`<span class="tactical-text-muted">Unknown: ${unknown}</span>`);
        }

        // Create flex container for cleaner layout
        const listHtml = parts.join(' <span style="color: var(--tactical-border); margin: 0 0.5rem">|</span> ');
        const percentHtml = `<div class="tactical-text-accent" style="font-weight: 700;">${formatPercent(onlinePercent)} Up</div>`;

        breakdownEl.innerHTML = `
            <div class="stat-subinfo" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                <div>${listHtml}</div>
                ${percentHtml}
            </div>
        `;
    }

    // Stale Check
    checkStale(timestamp, cardId);
}
