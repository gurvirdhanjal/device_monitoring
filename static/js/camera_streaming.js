// static/js/camera_streaming.js
class CameraStreamingManager {
    constructor() {
        this.activeStreams = new Map();
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadCameraStatus();
    }

    bindEvents() {
        // Stream control buttons
        document.addEventListener('click', (e) => {
            // Start stream from placeholder
            if (e.target.classList.contains('start-stream-btn')) {
                const cameraId = e.target.dataset.cameraId;
                this.startStream(cameraId);
            }

            // Stream control buttons
            if (e.target.classList.contains('stream-control-btn')) {
                const cameraId = e.target.dataset.cameraId;
                const action = e.target.dataset.action;
                this.controlStream(cameraId, action);
            }

            // Retry stream
            if (e.target.classList.contains('retry-stream-btn')) {
                const cameraId = e.target.dataset.cameraId;
                this.retryStream(cameraId);
            }

            // Snapshot buttons
            if (e.target.classList.contains('snapshot-btn')) {
                const cameraId = e.target.dataset.cameraId;
                this.takeSnapshot(cameraId);
            }

            // Recording controls
            if (e.target.classList.contains('recording-control-btn')) {
                const cameraId = e.target.dataset.cameraId;
                const action = e.target.dataset.action;
                this.controlRecording(cameraId, action);
            }
        });

        // Bulk controls
        document.getElementById('startSelectedBtn').addEventListener('click', () => {
            this.controlSelectedCameras('start');
        });

        document.getElementById('stopSelectedBtn').addEventListener('click', () => {
            this.controlSelectedCameras('stop');
        });

        document.getElementById('stopAllBtn').addEventListener('click', () => {
            this.stopAllStreams();
        });

        document.getElementById('refreshStatusBtn').addEventListener('click', () => {
            this.loadCameraStatus();
        });
    }

    getStreamUrl(cameraId, isHighFps = false) {
        const fps = isHighFps ? 25 : 2; // 2 FPS for Grid, 25 FPS for Live
        return `/api/cameras/stream/${cameraId}?fps=${fps}&t=${Date.now()}`;
    }

    async startStream(cameraId) {
        const container = this.getCameraContainer(cameraId);
        if (!container) return;

        const placeholder = container.querySelector('.stream-placeholder');
        const videoContainer = container.querySelector('.video-stream-container');
        const streamImg = container.querySelector('.camera-stream');
        const overlay = container.querySelector('.stream-overlay');
        const errorDiv = container.querySelector('.stream-error');
        const startBtn = container.querySelector('.stream-control-btn[data-action="start"]');
        const stopBtn = container.querySelector('.stream-control-btn[data-action="stop"]');

        try {
            // Show loading state
            placeholder.classList.add('d-none');
            overlay.classList.remove('d-none');
            errorDiv.classList.add('d-none');

            // Set stream source (Default to Low FPS for grid)
            const streamUrl = this.getStreamUrl(cameraId, false);
            streamImg.src = streamUrl;
            this.activeStreams.set(cameraId, streamImg);

            // Wait for stream to load
            await new Promise((resolve, reject) => {
                streamImg.onload = () => {
                    console.log(`Stream loaded for camera ${cameraId}`);
                    resolve();
                };

                streamImg.onerror = () => {
                    console.error(`Stream failed to load for camera ${cameraId}`);
                    reject(new Error('Stream failed to load'));
                };

                // Timeout after 10 seconds
                setTimeout(() => {
                    reject(new Error('Stream load timeout'));
                }, 10000);
            });

            // Show video stream
            videoContainer.classList.remove('d-none');
            overlay.classList.add('d-none');

            // Update button states
            startBtn.disabled = true;
            stopBtn.disabled = false;

            this.showNotification(`Stream started for camera ${cameraId}`, 'success');
            this.loadCameraStatus();

        } catch (error) {
            console.error('Error starting stream:', error);
            this.handleStreamError(cameraId, error.message);
        }
    }

    stopStream(cameraId) {
        const container = this.getCameraContainer(cameraId);
        if (!container) return;

        const placeholder = container.querySelector('.stream-placeholder');
        const videoContainer = container.querySelector('.video-stream-container');
        const streamImg = container.querySelector('.camera-stream');
        const overlay = container.querySelector('.stream-overlay');
        const errorDiv = container.querySelector('.stream-error');
        const startBtn = container.querySelector('.stream-control-btn[data-action="start"]');
        const stopBtn = container.querySelector('.stream-control-btn[data-action="stop"]');

        // Stop the stream
        if (streamImg.src) {
            streamImg.src = '';
        }
        this.activeStreams.delete(cameraId);

        // Reset UI
        videoContainer.classList.add('d-none');
        overlay.classList.add('d-none');
        errorDiv.classList.add('d-none');
        placeholder.classList.remove('d-none');

        // Update button states
        startBtn.disabled = false;
        stopBtn.disabled = true;

        // Stop on server
        this.stopServerStream(cameraId);

        this.showNotification(`Stream stopped for camera ${cameraId}`, 'info');
        this.loadCameraStatus();
    }

    async controlStream(cameraId, action) {
        if (action === 'start') {
            await this.startStream(cameraId);
        } else if (action === 'stop') {
            this.stopStream(cameraId);
        }
    }

    retryStream(cameraId) {
        const container = this.getCameraContainer(cameraId);
        const errorDiv = container.querySelector('.stream-error');
        errorDiv.classList.add('d-none');

        this.startStream(cameraId);
    }

    async stopServerStream(cameraId) {
        try {
            await fetch('/api/cameras/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'stop',
                    camera_ids: [cameraId]
                })
            });
        } catch (error) {
            console.error('Error stopping server stream:', error);
        }
    }

    handleStreamError(cameraId, errorMessage) {
        const container = this.getCameraContainer(cameraId);
        if (!container) return;

        const videoContainer = container.querySelector('.video-stream-container');
        const overlay = container.querySelector('.stream-overlay');
        const errorDiv = container.querySelector('.stream-error');
        const startBtn = container.querySelector('.stream-control-btn[data-action="start"]');
        const stopBtn = container.querySelector('.stream-control-btn[data-action="stop"]');

        // Reset stream
        const streamImg = container.querySelector('.camera-stream');
        if (streamImg.src) {
            streamImg.src = '';
        }
        this.activeStreams.delete(cameraId);

        // Show error state
        videoContainer.classList.add('d-none');
        overlay.classList.add('d-none');
        errorDiv.classList.remove('d-none');

        // Update button states
        startBtn.disabled = false;
        stopBtn.disabled = true;

        this.showNotification(`Stream error: ${errorMessage}`, 'error');
        this.loadCameraStatus();
    }

    getCameraContainer(cameraId) {
        return document.querySelector(`[data-camera-id="${cameraId}"]`);
    }

    async loadCameraStatus() {
        try {
            const response = await fetch('/api/cameras/status');
            const data = await response.json();

            if (data.success) {
                this.updateCameraStatus(data.cameras);
            }
        } catch (error) {
            console.error('Error loading camera status:', error);
        }
    }

    updateCameraStatus(cameras) {
        const statusContainer = document.getElementById('cameraStatus');
        let html = '<div class="row">';

        cameras.forEach(camera => {
            const streamingBadge = camera.is_streaming ?
                '<span class="tactical-badge tactical-badge-success">Live</span>' :
                '<span class="tactical-badge tactical-badge-secondary">Offline</span>';

            const recordingBadge = camera.is_recording ?
                '<span class="tactical-badge tactical-badge-danger ms-1">Recording</span>' : '';

            html += `
                <div class="col-md-3 mb-2">
                    <div class="d-flex justify-content-between align-items-center p-2 border rounded" style="background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1) !important;">
                        <span class="text-white">${camera.device_name}</span>
                        <div>
                            ${streamingBadge}
                            ${recordingBadge}
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        statusContainer.innerHTML = html;
    }

    async takeSnapshot(cameraId) {
        try {
            const response = await fetch(`/api/cameras/snapshot/${cameraId}`);
            const data = await response.json();

            if (data.success) {
                this.showNotification('Snapshot taken successfully!', 'success');
                // Open snapshot in new tab
                window.open(data.filepath, '_blank');
            } else {
                this.showNotification('Failed to take snapshot: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error taking snapshot:', error);
            this.showNotification('Error taking snapshot', 'error');
        }
    }

    async controlRecording(cameraId, action) {
        try {
            const endpoint = action === 'start' ?
                `/api/cameras/start-recording/${cameraId}` :
                `/api/cameras/stop-recording/${cameraId}`;

            const response = await fetch(endpoint);
            const data = await response.json();

            if (data.success) {
                this.showNotification(data.message, 'success');
                this.loadCameraStatus();
            } else {
                this.showNotification('Recording error: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Error controlling recording:', error);
            this.showNotification('Error controlling recording', 'error');
        }
    }

    async controlSelectedCameras(action) {
        const select = document.getElementById('cameraSelector');
        const selectedCameras = Array.from(select.selectedOptions).map(opt => opt.value);

        if (selectedCameras.length === 0) {
            this.showNotification('Please select at least one camera', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/cameras/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: action,
                    camera_ids: selectedCameras
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(`Action ${action} completed for selected cameras`, 'success');
                this.loadCameraStatus();

                // Start streams locally if action was start
                if (action === 'start') {
                    selectedCameras.forEach(cameraId => {
                        setTimeout(() => this.startStream(cameraId), 100);
                    });
                }
            }
        } catch (error) {
            console.error('Error controlling cameras:', error);
            this.showNotification('Error controlling cameras', 'error');
        }
    }

    async stopAllStreams() {
        const cameras = document.querySelectorAll('.camera-stream-container');
        const cameraIds = Array.from(cameras).map(container => container.dataset.cameraId);

        try {
            const response = await fetch('/api/cameras/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'stop',
                    camera_ids: cameraIds
                })
            });

            const data = await response.json();

            if (data.success) {
                // Stop all local streams
                cameraIds.forEach(cameraId => {
                    this.stopStream(cameraId);
                });

                this.showNotification('All camera streams stopped', 'success');
                this.loadCameraStatus();
            }
        } catch (error) {
            console.error('Error stopping all streams:', error);
            this.showNotification('Error stopping streams', 'error');
        }
    }

    showNotification(message, type = 'info') {
        // Simple notification implementation
        const alertClass = type === 'error' ? 'alert-danger' :
            type === 'success' ? 'alert-success' :
                type === 'warning' ? 'alert-warning' : 'alert-info';

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alertDiv);

        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 5000);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function () {
    window.cameraManager = new CameraStreamingManager();
});