const API = {
    async enroll(name, image) {
        const fd = new FormData();
        fd.append("name", name);
        fd.append("image", image, image.name || "capture.jpg");
        const r = await fetch("/enroll", { method: "POST", body: fd });
        return r.json();
    },

    async reload() {
        const r = await fetch("/reload");
        return r.json();
    },

    async getSnapshot() {
        const r = await fetch("/snapshot");
        if (!r.ok) throw new Error("Snapshot failed");
        return r.blob();
    },

    async getFaces() {
        const r = await fetch("/faces");
        return r.json();
    },

    async deleteFace(name) {
        const r = await fetch(`/faces/${encodeURIComponent(name)}`, { method: "DELETE" });
        return r.json();
    },

    async getLog() {
        const r = await fetch("/log");
        return r.json();
    },

    async clearLog() {
        const r = await fetch("/log", { method: "DELETE" });
        return r.json();
    },

    async getStats() {
        const r = await fetch("/stats");
        return r.json();
    },

    async getCameras() {
        const r = await fetch("/cameras");
        return r.json();
    },

    async selectCamera(index) {
        const r = await fetch("/cameras/select", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ index }),
        });
        return r.json();
    },

    async trainBulk(name, images) {
        const fd = new FormData();
        fd.append("name", name);
        images.forEach((img, i) => fd.append("images", img, img.name || `frame_${i}.jpg`));
        const r = await fetch("/train", { method: "POST", body: fd });
        return r.json();
    },

    async getTrainingStatus() {
        const r = await fetch("/train/status");
        return r.json();
    },

    async saveSettings(tolerance) {
        const r = await fetch("/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tolerance })
        });
        return r.json();
    }
};
