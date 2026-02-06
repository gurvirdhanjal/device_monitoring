/**
 * Connection Status Indicator Component
 * 
 * Displays real-time connection status with visual feedback:
 * - 🟢 Green dot + "Live" when connected
 * - 🟡 Yellow dot + "Reconnecting..." when connecting
 * - 🔴 Red dot + "Offline - Polling" when disconnected
 */

import { ConnectionStatus } from './sseClient.js';

/**
 * Render the connection status indicator.
 * 
 * @param {string} status Current connection status
 */
export function renderConnectionIndicator(status) {
    const container = document.getElementById('connection-indicator');
    if (!container) {
        console.warn('[ConnectionIndicator] Container #connection-indicator not found');
        return;
    }

    const configs = {
        [ConnectionStatus.CONNECTED]: {
            dotClass: 'indicator-dot--connected',
            text: 'Live',
            title: 'Real-time updates active'
        },
        [ConnectionStatus.CONNECTING]: {
            dotClass: 'indicator-dot--connecting',
            text: 'Reconnecting...',
            title: 'Attempting to reconnect'
        },
        [ConnectionStatus.DISCONNECTED]: {
            dotClass: 'indicator-dot--disconnected',
            text: 'Polling',
            title: 'Using polling fallback (30s refresh)'
        }
    };

    const config = configs[status] || configs[ConnectionStatus.DISCONNECTED];

    container.innerHTML = `
        <div class="connection-indicator" title="${config.title}">
            <span class="indicator-dot ${config.dotClass}"></span>
            <span class="indicator-text">${config.text}</span>
        </div>
    `;
}

/**
 * Initialize the connection indicator with default disconnected state.
 */
export function initConnectionIndicator() {
    renderConnectionIndicator(ConnectionStatus.DISCONNECTED);
}
