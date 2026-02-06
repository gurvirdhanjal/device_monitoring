/**
 * Card Component: Active Alerts
 */
import { checkStale, animateValue } from '../utils.js';

export function renderActiveAlerts(data, timestamp) {
    const cardId = 'card-active-alerts';
    const container = document.getElementById(cardId);
    if (!container) return;

    const body = container.querySelector('.card-body');
    if (!data || !data.active_alerts) {
        if (body) body.innerHTML = '<div class="text-secondary">No Data</div>';
        return;
    }

    const { critical, warning, info } = data.active_alerts;
    const total = critical + warning + info;

    // Main Value (Show CRITICAL count prominently if exists, else total)
    const valueEl = document.getElementById('val-active-alerts');
    if (valueEl) {
        const endVal = critical > 0 ? critical : total;
        const currentVal = parseInt(valueEl.textContent, 10) || 0;

        // Animate if changed
        if (currentVal !== endVal) {
            animateValue(valueEl, currentVal, endVal);
        }

        // Color code based on severity
        if (critical > 0) {
            valueEl.className = 'metric-value tactical-text-danger';
        } else {
            valueEl.className = 'metric-value ' + (warning > 0 ? 'tactical-text-warning' : 'tactical-text-success');
        }
    }

    // Sub Info - WITH LABELS
    const breakdownEl = document.getElementById('sub-active-alerts');
    if (breakdownEl) {
        const parts = [];

        if (critical > 0) {
            parts.push(`<span class="tactical-text-danger"><strong>Critical: ${critical}</strong></span>`);
        }
        if (warning > 0) {
            parts.push(`<span class="tactical-text-warning">Warning: ${warning}</span>`);
        }
        if (info > 0) {
            parts.push(`<span class="tactical-text-accent">Info: ${info}</span>`);
        }

        // Show total
        if (parts.length > 1) {
            parts.push(`<span class="tactical-text-muted" style="margin-left:auto; font-weight:600">Total: ${total}</span>`);
        }

        if (parts.length === 0) {
            breakdownEl.innerHTML = '<div class="stat-subinfo"><span class="tactical-text-success"><i class="fas fa-check-circle"></i> All Clear</span></div>';
        } else {
            breakdownEl.innerHTML = `<div class="stat-subinfo">${parts.join(' <span style="color: var(--tactical-border); margin: 0 0.5rem">|</span> ')}</div>`;
        }
    }

    checkStale(timestamp, cardId);

    // Interaction
    if (container.dataset.interactive !== 'true') {
        container.style.cursor = 'pointer';
        container.addEventListener('click', () => {
            // Navigate to alerts page (assuming /alerts or /monitoring#alerts)
            // For now, alerting user functionality is coming
            alert("Navigate to Alerts Detail Page (Coming Soon)");
        });
        container.dataset.interactive = 'true';
    }
}
