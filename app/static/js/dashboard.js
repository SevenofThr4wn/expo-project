/**
 * Dashboard — stats, Chart.js charts, live Socket.IO event feed.
 */
document.addEventListener('DOMContentLoaded', () => {

    // ── Element refs ────────────────────────────────────────────────────────��─
    const dEnrolled  = document.getElementById('dEnrolled');
    const dToday     = document.getElementById('dToday');
    const dCam       = document.getElementById('dCam');
    const eventsList = document.getElementById('eventsList');
    const MAX_EVENTS = 12;

    // ── Chart.js setup ────────────────────────────────────────────────────────
    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: {
                grid:  { color: 'rgba(255,255,255,.05)' },
                ticks: { color: '#64748b', font: { size: 11 } },
            },
            y: {
                grid:  { color: 'rgba(255,255,255,.05)' },
                ticks: { color: '#64748b', font: { size: 11 }, precision: 0 },
                beginAtZero: true,
            },
        },
    };

    const hourlyCtx = document.getElementById('hourlyChart')?.getContext('2d');
    const personCtx = document.getElementById('personChart')?.getContext('2d');

    let hourlyChart = hourlyCtx ? new Chart(hourlyCtx, {
        type: 'bar',
        data: { labels: [], datasets: [{ data: [], backgroundColor: 'rgba(99,102,241,.6)', borderRadius: 4 }] },
        options: { ...chartDefaults },
    }) : null;

    let personChart = personCtx ? new Chart(personCtx, {
        type: 'doughnut',
        data: { labels: [], datasets: [{ data: [], backgroundColor: [
            'rgba(99,102,241,.7)', 'rgba(6,182,212,.7)', 'rgba(139,92,246,.7)',
            'rgba(16,185,129,.7)', 'rgba(245,158,11,.7)', 'rgba(239,68,68,.7)',
        ], borderWidth: 0 }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#94a3b8', font: { size: 11 }, boxWidth: 12 } },
            },
        },
    }) : null;

    // ── Stats + charts fetch ──────────────────────────────────────────────────
    async function refreshStats() {
        try {
            const d = await API.getStats();

            if (dEnrolled) dEnrolled.textContent = d.enrolled_count ?? '—';
            if (dToday)    dToday.textContent    = d.today_recognitions ?? '—';
            if (dCam) {
                dCam.textContent  = d.camera_connected ? 'Online' : 'Offline';
                dCam.style.color  = d.camera_connected ? 'var(--success)' : 'var(--danger)';
            }

            // Hourly bar chart (fill 0-23 hours)
            if (hourlyChart && d.hourly) {
                const byHour = {};
                d.hourly.forEach(h => { byHour[h.hour] = h.count; });
                const labels = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
                hourlyChart.data.labels = labels.map(h => `${h}:00`);
                hourlyChart.data.datasets[0].data = labels.map(h => byHour[h] || 0);
                hourlyChart.update('none');
            }

            // Per-person doughnut
            if (personChart && d.per_person && d.per_person.length) {
                personChart.data.labels = d.per_person.map(p => p.name);
                personChart.data.datasets[0].data = d.per_person.map(p => p.count);
                personChart.update('none');
            }
        } catch {}
    }

    // ── Recent events via Socket.IO ───────────────────────────────────────────
    const socket = io();

    socket.on('recognition', event => {
        const empty = eventsList.querySelector('.events-empty');
        if (empty) empty.remove();

        const ts = new Date(event.timestamp).toLocaleTimeString();
        const confClass = event.confidence >= 80 ? 'badge-success'
                        : event.confidence >= 60 ? 'badge-warn' : 'badge-danger';

        const li = document.createElement('li');
        li.innerHTML = `
            <div class="ev-avatar">${event.name[0].toUpperCase()}</div>
            <span class="ev-name">${event.name}</span>
            <span class="badge ${confClass}">${event.confidence}%</span>
            <span class="ev-time">${ts}</span>
        `;
        eventsList.prepend(li);

        while (eventsList.children.length > MAX_EVENTS) {
            eventsList.removeChild(eventsList.lastChild);
        }

        // Bump today counter
        if (dToday) {
            const cur = parseInt(dToday.textContent, 10) || 0;
            dToday.textContent = cur + 1;
        }
    });

    // ── Heatmap ───────────────────────────────────────────────────────────────
    async function renderHeatmap() {
        const grid = document.getElementById('heatmapGrid');
        if (!grid) return;

        try {
            const matrix = await API.getHeatmap();
            const days   = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            const maxVal = Math.max(1, ...matrix.flat());

            let html = '<div class="heatmap-row">'
                     + '<span class="heatmap-day-label"></span>';
            for (let h = 0; h < 24; h++) {
                html += `<span class="heatmap-hour-label">${h % 6 === 0 ? String(h).padStart(2, '0') : ''}</span>`;
            }
            html += '</div>';

            matrix.forEach((row, d) => {
                html += `<div class="heatmap-row"><span class="heatmap-day-label">${days[d]}</span>`;
                row.forEach(v => {
                    const a = v > 0 ? Math.max(0.12, (v / maxVal) * 0.85) : 0;
                    html += `<span class="heatmap-cell" style="background:rgba(99,102,241,${a.toFixed(2)})" title="${v} recognition${v !== 1 ? 's' : ''}"></span>`;
                });
                html += '</div>';
            });

            grid.innerHTML = html;
        } catch {}
    }

    // ── Boot ──────────────────────────────────────────────────────────────────
    refreshStats();
    renderHeatmap();
    setInterval(refreshStats, 30_000);
    setInterval(renderHeatmap, 60_000);
});
