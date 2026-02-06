/**
 * Network Discovery UI Handler
 */

export function initDiscovery() {
    const startBtn = document.getElementById('btn-start-discovery');
    const seedInput = document.getElementById('seed-ip');
    const statusEl = document.getElementById('discovery-status');

    if (!startBtn || !seedInput || !statusEl) return;

    startBtn.addEventListener('click', async () => {
        const seedIp = seedInput.value.trim();
        if (!seedIp) {
            showDiscoveryStatus("Please enter a seed IP", "text-danger");
            return;
        }

        resetResults();

        startBtn.disabled = true;
        startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Initializing...';
        showDiscoveryStatus("Inquiry sent. Discovery process started in background...", "text-info");

        try {
            const response = await fetch('/api/discovery/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ seed_ip: seedIp })
            });

            const data = await response.json();
            if (data.success) {
                showDiscoveryStatus("Discovery running. This can take a few minutes...", "text-info");
                if (data.job_id) {
                    pollStatus(data.job_id);
                } else {
                    showDiscoveryStatus("Discovery started. Check device inventory for updates.", "text-success");
                }
            } else {
                showDiscoveryStatus("Error: " + (data.error || "Unknown error"), "text-danger");
            }
        } catch (err) {
            console.error("Discovery Error:", err);
            showDiscoveryStatus("Failed to initiate discovery", "text-danger");
        } finally {
            startBtn.disabled = false;
            startBtn.innerHTML = 'Start Mapping';
        }
    });

    function resetResults() {
        const resultsEl = document.getElementById('discovery-results');
        const switchesBody = document.getElementById('discovery-switches-body');
        const devicesBody = document.getElementById('discovery-devices-body');
        if (resultsEl) resultsEl.style.display = 'none';
        if (switchesBody) {
            switchesBody.innerHTML = '<tr><td colspan="4" class="text-center p-3">No results yet.</td></tr>';
        }
        if (devicesBody) {
            devicesBody.innerHTML = '<tr><td colspan="4" class="text-center p-3">No results yet.</td></tr>';
        }
    }

    async function pollStatus(jobId) {
        const maxPolls = 60; // ~3 minutes at 3s interval
        let count = 0;
        const interval = setInterval(async () => {
            count += 1;
            if (count > maxPolls) {
                clearInterval(interval);
                showDiscoveryStatus("Discovery still running in background. You can check later.", "text-warning");
                return;
            }
            try {
                const res = await fetch(`/api/discovery/status/${jobId}`);
                const job = await res.json();
                if (job.error) {
                    clearInterval(interval);
                    showDiscoveryStatus("Discovery error: " + job.error, "text-danger");
                    return;
                }
                if (job.status === 'completed') {
                    clearInterval(interval);
                    const msg = `Completed. Switches: ${job.switch_count || 0}, Devices: ${job.device_count || 0}`;
                    showDiscoveryStatus(msg, "text-success");
                    if (job.switches) {
                        renderResults(job.switches);
                    }
                } else if (job.status === 'running') {
                    const msg = `Running... switches found: ${job.switch_count || 0}`;
                    showDiscoveryStatus(msg, "text-info");
                }
            } catch (e) {
                clearInterval(interval);
                showDiscoveryStatus("Discovery status check failed.", "text-danger");
            }
        }, 3000);
    }

    function renderResults(switches) {
        const resultsEl = document.getElementById('discovery-results');
        const switchesBody = document.getElementById('discovery-switches-body');
        const devicesBody = document.getElementById('discovery-devices-body');

        if (!resultsEl || !switchesBody || !devicesBody) return;

        if (!switches || switches.length === 0) {
            switchesBody.innerHTML = '<tr><td colspan="4" class="text-center p-3">No switches discovered.</td></tr>';
            devicesBody.innerHTML = '<tr><td colspan="4" class="text-center p-3">No devices discovered.</td></tr>';
            resultsEl.style.display = 'block';
            return;
        }

        switchesBody.innerHTML = switches.map(sw => {
            const neighbors = (sw.neighbors || []).length;
            const devices = (sw.devices || []).length;
            const errors = (sw.errors || []).length;
            const ip = sw.ip || 'Unknown';
            return `
                <tr>
                    <td>${ip}</td>
                    <td>${neighbors}</td>
                    <td>${devices}</td>
                    <td>${errors}</td>
                </tr>
            `;
        }).join('');

        const deviceRows = [];
        switches.forEach(sw => {
            const swIp = sw.ip || 'Unknown';
            (sw.devices || []).forEach(dev => {
                deviceRows.push({
                    switch_ip: swIp,
                    ip: dev.ip || '',
                    mac: dev.mac || '',
                    port: dev.interface || ''
                });
            });
        });

        if (deviceRows.length === 0) {
            devicesBody.innerHTML = '<tr><td colspan="4" class="text-center p-3">No devices discovered.</td></tr>';
        } else {
            devicesBody.innerHTML = deviceRows.map(d => `
                <tr>
                    <td>${d.switch_ip}</td>
                    <td>${d.ip || '-'}</td>
                    <td>${d.mac || '-'}</td>
                    <td>${d.port || '-'}</td>
                </tr>
            `).join('');
        }

        resultsEl.style.display = 'block';
    }

    function showDiscoveryStatus(msg, className) {
        statusEl.textContent = msg;
        statusEl.className = `small mt-2 p-2 rounded ${className}`;
        statusEl.style.display = 'block';
        statusEl.style.background = 'rgba(255,255,255,0.05)';
    }
}
