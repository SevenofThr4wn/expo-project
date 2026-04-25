/**
 * Enroll page — Alpine.js component exposed as enrollApp().
 * Handles camera capture, quality assessment, multi-frame enrollment.
 */
function enrollApp() {
    return {
        name: '',
        captures: [],         // [{url, blob, quality}]
        capturing: false,
        enrolling: false,
        sessionFrames: 5,
        progress: 0,
        progressMsg: '',
        statusMsg: '',
        statusOk: true,
        lastQuality: 0,

        // ── Single capture ────────────────────────────────────────────────────
        async captureFrame() {
            this.capturing = true;
            try {
                const blob = await API.getSnapshot();
                const quality = await this._estimateQuality(blob);
                const url = URL.createObjectURL(blob);
                this.captures.push({ url, blob, quality });
                this.lastQuality = quality;

                if (quality < 30) {
                    toast('Low quality image — try better lighting.', 'error');
                } else if (quality < 60) {
                    toast('Fair quality — more varied angles improve accuracy.', 'info');
                } else {
                    toast('Good quality frame captured.', 'success');
                }
            } catch {
                toast('Snapshot failed — is the camera running?', 'error');
            } finally {
                this.capturing = false;
            }
        },

        // ── Auto-capture session ──────────────────────────────────────────────
        async captureSession() {
            if (this.captures.length > 0) {
                if (!confirm(`You have ${this.captures.length} existing capture(s). Add ${this.sessionFrames} more?`)) return;
            }
            this.capturing = true;
            const frames = parseInt(this.sessionFrames, 10) || 5;

            for (let i = 0; i < frames; i++) {
                this.progressMsg = `Capturing frame ${i + 1} of ${frames}…`;
                this.progress    = Math.round((i / frames) * 85);

                try {
                    const blob = await API.getSnapshot();
                    const quality = await this._estimateQuality(blob);
                    this.captures.push({ url: URL.createObjectURL(blob), blob, quality });
                    this.lastQuality = quality;
                } catch {
                    toast(`Frame ${i + 1} failed — skipping.`, 'error');
                }

                if (i < frames - 1) await _sleep(900);
            }

            this.progress    = 100;
            this.progressMsg = 'Done!';
            setTimeout(() => { this.capturing = false; this.progress = 0; }, 900);
        },

        removeCapture(index) {
            URL.revokeObjectURL(this.captures[index].url);
            this.captures.splice(index, 1);
        },

        // ── Enroll all captured frames ────────────────────────────────────────
        async enrollAll() {
            if (!this.name.trim() || !this.captures.length) return;
            this.enrolling  = true;
            this.statusMsg  = '';
            let ok = 0;
            let fail = 0;

            for (let i = 0; i < this.captures.length; i++) {
                try {
                    const r = await API.enroll(this.name.trim(), this.captures[i].blob);
                    if (r.error) { fail++; }
                    else         { ok++;   }
                } catch {
                    fail++;
                }
            }

            this.enrolling = false;
            if (ok > 0) {
                this.statusMsg = `${ok} frame(s) enrolled successfully${fail ? `, ${fail} failed` : ''}.`;
                this.statusOk  = true;
                // Clean up previews
                this.captures.forEach(c => URL.revokeObjectURL(c.url));
                this.captures = [];
                this.name     = '';
                this.lastQuality = 0;
                toast(`${ok} frame(s) enrolled for '${this.name || 'person'}'.`, 'success');
            } else {
                this.statusMsg = `Enrollment failed — ${fail} frame(s) had no detectable face.`;
                this.statusOk  = false;
            }
        },

        // ── Quality estimate (client-side sharpness proxy) ────────────────────
        async _estimateQuality(blob) {
            return new Promise(resolve => {
                const img = new Image();
                const url = URL.createObjectURL(blob);
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    canvas.width  = Math.min(img.width,  160);
                    canvas.height = Math.min(img.height, 120);
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);

                    // Laplacian proxy: sum absolute differences between adjacent pixels
                    let sum = 0;
                    for (let i = 0; i < data.length - 4; i += 4) {
                        const g1 = (data[i] + data[i+1] + data[i+2]) / 3;
                        const g2 = (data[i+4] + data[i+5] + data[i+6]) / 3;
                        sum += Math.abs(g1 - g2);
                    }
                    const sharpness = Math.min(sum / (canvas.width * canvas.height * 20), 1);

                    // Brightness (0=black, 1=ideal, fades at extremes)
                    let bright = 0;
                    for (let i = 0; i < data.length; i += 4) {
                        bright += (data[i] + data[i+1] + data[i+2]) / 3;
                    }
                    bright /= (data.length / 4);
                    const brightScore = 1 - Math.abs(bright - 128) / 128;

                    URL.revokeObjectURL(url);
                    resolve(Math.round((sharpness * 0.65 + brightScore * 0.35) * 100));
                };
                img.onerror = () => { URL.revokeObjectURL(url); resolve(50); };
                img.src = url;
            });
        },
    };
}

function _sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
