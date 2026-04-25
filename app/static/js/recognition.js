/**
 * Live Recognition page — Socket.IO driven event feed.
 */
document.addEventListener('DOMContentLoaded', () => {

    const recentEl     = document.getElementById('recentEvents');
    const sessionCount = document.getElementById('sessionCount');
    const lastSeenEl   = document.getElementById('lastSeen');
    const camStatusEl  = document.getElementById('camStatus');
    const reloadBtn    = document.getElementById('reloadBtn');

    let count = 0;
    const MAX_EVENTS = 20;

    // ── Socket.IO ─────────────────────────────────────────────────────────────
    const socket = io();

    socket.on('connect',    () => updateCamStatus(true));
    socket.on('disconnect', () => updateCamStatus(false));

    socket.on('recognition', event => {
        count++;
        sessionCount.textContent = count;
        lastSeenEl.textContent   = event.name;

        // Remove "waiting" placeholder
        const empty = recentEl.querySelector('.recent-empty');
        if (empty) empty.remove();

        // Build list item
        const li = document.createElement('li');
        li.className = 'recent-item';
        const ts = new Date(event.timestamp).toLocaleTimeString();
        const confClass = event.confidence >= 80 ? 'badge-success'
                        : event.confidence >= 60 ? 'badge-warn'
                        : 'badge-danger';
        li.innerHTML = `
            <div class="recent-avatar">${event.name[0].toUpperCase()}</div>
            <span class="recent-name">${event.name}</span>
            <span class="badge ${confClass}">${event.confidence}%</span>
            <span class="recent-conf">${ts}</span>
        `;

        recentEl.prepend(li);

        // Cap list length
        while (recentEl.children.length > MAX_EVENTS) {
            recentEl.removeChild(recentEl.lastChild);
        }
    });

    // ── Camera status ─────────────────────────────────────────────────────────
    async function updateCamStatus() {
        try {
            const d = await API.getStats();
            if (camStatusEl) {
                camStatusEl.textContent  = d.camera_connected ? 'Online' : 'Offline';
                camStatusEl.style.color  = d.camera_connected ? 'var(--success)' : 'var(--danger)';
            }
        } catch {}
    }

    updateCamStatus();

    // ── Reload encodings ──────────────────────────────────────────────────────
    reloadBtn.addEventListener('click', async () => {
        reloadBtn.disabled    = true;
        reloadBtn.textContent = 'Reloading…';
        try {
            const r = await API.reloadEncodings();
            toast(r.message || 'Reloaded.', 'success');
        } catch {
            toast('Reload failed.', 'error');
        } finally {
            reloadBtn.disabled    = false;
            reloadBtn.innerHTML   = `
                <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/></svg>
                Reload Encodings`;
        }
    });
});
