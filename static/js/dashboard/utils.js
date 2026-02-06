/**
 * Utility functions for Dashboard
 */

// Format timestamp to "X mins ago"
export function timeAgo(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Invalid Date';

    const seconds = Math.floor((new Date() - date) / 1000);

    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";

    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";

    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";

    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";

    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " mins ago";

    return Math.floor(seconds) + " seconds ago";
}

// Format numbers (e.g. 1200 -> 1.2k)
export function formatNumber(num) {
    if (num === null || num === undefined) return '-';
    return new Intl.NumberFormat('en-US', { notation: "compact", compactDisplay: "short" }).format(num);
}

// Format percentage
export function formatPercent(num) {
    if (num === null || num === undefined) return '-';
    return `${Number(num).toFixed(1)}%`;
}

// Add Stale indicator to a card
export function checkStale(lastUpdatedStr, elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const diffMs = new Date() - new Date(lastUpdatedStr);
    const fiveMinutes = 5 * 60 * 1000;

    if (diffMs > fiveMinutes) {
        el.classList.add('card-stale');
        el.setAttribute('title', `Data stale. Last updated: ${timeAgo(lastUpdatedStr)}`);
    } else {
        el.classList.remove('card-stale');
        el.removeAttribute('title');
    }
}

/**
 * Animate a numeric value change
 * @param {HTMLElement} element - The element to update
 * @param {number} start - Starting value
 * @param {number} end - Ending value
 * @param {number} duration - Animation duration in ms
 */
export function animateValue(element, start, end, duration = 500) {
    if (!element) return;
    // Ensure numbers
    start = parseInt(start) || 0;
    end = parseInt(end) || 0;

    if (start === end) {
        element.textContent = end;
        return;
    }

    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);

        // Easing function (easeOutQuad)
        const easeProgress = 1 - (1 - progress) * (1 - progress);

        const current = Math.floor(easeProgress * (end - start) + start);
        element.textContent = current;

        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            element.textContent = end;
        }
    };
    window.requestAnimationFrame(step);
}
