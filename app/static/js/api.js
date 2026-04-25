/**
 * FaceID REST API client
 * All methods return the parsed JSON response (or throw on network error).
 */
const API = {

    // ── Auth ──────────────────────────────────────────────────────────────────
    async login(username, password, remember = false) {
        return _post('/auth/login', { username, password, remember });
    },

    // ── Faces ─────────────────────────────────────────────────────────────────
    async getFaces() {
        return _get('/api/faces');
    },
    async deleteFace(name) {
        const r = await fetch(`/api/faces/${encodeURIComponent(name)}`, { method: 'DELETE' });
        return r.json();
    },

    // ── Enroll ────────────────────────────────────────────────────────────────
    async enroll(name, imageBlob) {
        const fd = new FormData();
        fd.append('name', name);
        fd.append('image', imageBlob, imageBlob.name || 'capture.jpg');
        const r = await fetch('/api/enroll', { method: 'POST', body: fd });
        return r.json();
    },

    // ── Stream ────────────────────────────────────────────────────────────────
    async getSnapshot() {
        const r = await fetch('/api/snapshot');
        if (!r.ok) throw new Error('Snapshot failed');
        return r.blob();
    },
    async reloadEncodings() {
        return _get('/api/reload');
    },

    // ── Logs ──────────────────────────────────────────────────────────────────
    async getLogs({ limit = 100, offset = 0, name = '' } = {}) {
        const p = new URLSearchParams({ limit, offset });
        if (name) p.set('name', name);
        return _get(`/api/logs?${p}`);
    },
    async clearLogs() {
        const r = await fetch('/api/logs', { method: 'DELETE' });
        return r.json();
    },

    // ── Stats ─────────────────────────────────────────────────────────────────
    async getStats() {
        return _get('/api/stats');
    },

    // ── Cameras ───────────────────────────────────────────────────────────────
    async getCameras() {
        return _get('/api/cameras');
    },
    async selectCamera(index) {
        return _post('/api/cameras/select', { index });
    },

    // ── Settings ──────────────────────────────────────────────────────────────
    async saveSettings(payload) {
        return _post('/api/settings', payload);
    },

    // ── Users (admin) ─────────────────────────────────────────────────────────
    async getUsers() {
        return _get('/api/users');
    },
    async createUser(data) {
        return _post('/api/users', data);
    },
    async updateUser(id, data) {
        const r = await fetch(`/api/users/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return r.json();
    },
    async deleteUser(id) {
        const r = await fetch(`/api/users/${id}`, { method: 'DELETE' });
        return r.json();
    },
};

// ── Helpers ───────────────────────────────────────────────────────────────────
async function _get(url) {
    const r = await fetch(url);
    return r.json();
}

async function _post(url, body) {
    const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return r.json();
}
