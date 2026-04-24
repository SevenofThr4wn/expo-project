document.addEventListener("DOMContentLoaded", () => {

    // ── TAB NAVIGATION ──────────────────────────────────────────────────────
    const navItems  = document.querySelectorAll(".nav-item");
    const tabPanes  = document.querySelectorAll(".tab-pane");

    function switchTab(name) {
        navItems.forEach(el => el.classList.toggle("active", el.dataset.tab === name));
        tabPanes.forEach(el => el.classList.toggle("active", el.id === `tab-${name}`));
        if (name === "log")   loadLog();
        if (name === "faces") loadFaces();
        if (name === "train") loadTrainingStatus();
    }

    navItems.forEach(el => el.addEventListener("click", () => switchTab(el.dataset.tab)));


    // ── STATS ────────────────────────────────────────────────────────────────
    async function updateStats() {
        try {
            const d   = await API.getStats();
            document.getElementById("enrolledCount").textContent = d.enrolled_count ?? "—";
            document.getElementById("todayCount").textContent    = d.today_recognitions ?? "—";

            const dot   = document.getElementById("cameraDot");
            const label = document.getElementById("cameraLabel");
            if (d.camera_connected) {
                dot.className    = "stat-dot online";
                label.textContent = "Camera Online";
            } else {
                dot.className    = "stat-dot offline";
                label.textContent = "No Camera";
            }
        } catch {}
    }

    updateStats();
    setInterval(updateStats, 30_000);


    // ── RECENT RECOGNITIONS (live tab) ────────────────────────────────────────
    async function pollRecent() {
        try {
            const d = await API.getLog();
            const events = (d.events || []).slice(0, 5);
            const list   = document.getElementById("recentList");

            if (!events.length) {
                list.innerHTML = '<li class="recent-empty">No recognitions yet</li>';
                return;
            }

            list.innerHTML = events.map(e => `
                <li class="recent-item">
                    <div class="recent-avatar">${e.name[0].toUpperCase()}</div>
                    <span class="recent-name">${e.name}</span>
                    <span class="recent-conf">${e.confidence}%</span>
                </li>
            `).join("");
        } catch {}
    }

    pollRecent();
    setInterval(pollRecent, 5_000);


    // ── ACTIVITY LOG TAB ─────────────────────────────────────────────────────
    async function loadLog() {
        try {
            const d      = await API.getLog();
            const events = d.events || [];
            const tbody  = document.getElementById("logBody");

            if (!events.length) {
                tbody.innerHTML = '<tr><td colspan="3" class="empty-row">No activity logged yet</td></tr>';
                return;
            }

            tbody.innerHTML = events.map(e => {
                const ts = new Date(e.timestamp).toLocaleString();
                return `
                    <tr>
                        <td><strong>${e.name}</strong></td>
                        <td><span class="badge badge-accent">${e.confidence}%</span></td>
                        <td class="ts">${ts}</td>
                    </tr>`;
            }).join("");
        } catch {}
    }

    document.getElementById("refreshLogBtn").addEventListener("click", loadLog);


    // ── ENROLLED FACES TAB ───────────────────────────────────────────────────
    async function loadFaces() {
        try {
            const d     = await API.getFaces();
            const faces = d.faces || [];
            const grid  = document.getElementById("facesGrid");

            if (!faces.length) {
                grid.innerHTML = '<div class="faces-empty">No faces enrolled yet</div>';
                return;
            }

            grid.innerHTML = faces.map(name => `
                <div class="face-card">
                    <div class="face-avatar">${name[0].toUpperCase()}</div>
                    <div class="face-name">${name}</div>
                    <button class="face-delete" data-name="${name}">Remove</button>
                </div>
            `).join("");

            grid.querySelectorAll(".face-delete").forEach(btn => {
                btn.addEventListener("click", async () => {
                    if (!confirm(`Remove "${btn.dataset.name}" from the system?`)) return;
                    const res = await API.deleteFace(btn.dataset.name);
                    if (res.error) { alert(res.error); return; }
                    loadFaces();
                    updateStats();
                });
            });
        } catch {}
    }

    document.getElementById("refreshFacesBtn").addEventListener("click", loadFaces);


    // ── ENROLL ───────────────────────────────────────────────────────────────
    let capturedBlob = null;

    document.getElementById("captureBtn").addEventListener("click", async () => {
        const btn = document.getElementById("captureBtn");
        btn.textContent = "Capturing…";
        btn.disabled    = true;

        try {
            capturedBlob = await API.getSnapshot();
            showEnrollMsg("Snapshot captured — ready to enroll.", false);
            document.getElementById("capturePreview").style.display = "flex";
            document.getElementById("captureLabel").textContent     = "snapshot.jpg";
        } catch {
            showEnrollMsg("Snapshot failed. Is the camera running?", true);
        } finally {
            btn.textContent = "Capture";
            btn.disabled    = false;
        }
    });

    document.getElementById("clearCaptureBtn").addEventListener("click", () => {
        capturedBlob = null;
        document.getElementById("capturePreview").style.display = "none";
        showEnrollMsg("", false);
    });

    document.getElementById("enrollBtn").addEventListener("click", async () => {
        const name  = document.getElementById("nameInput").value.trim();
        const file  = document.getElementById("fileInput").files[0];
        const image = file || capturedBlob;

        if (!name)  { showEnrollMsg("Please enter a name.", true); return; }
        if (!image) { showEnrollMsg("Upload an image or use Capture.", true); return; }

        showEnrollMsg("Enrolling…", false);

        try {
            const res = await API.enroll(name, image);
            if (res.error) {
                showEnrollMsg(res.error, true);
            } else {
                showEnrollMsg(res.message, false);
                document.getElementById("nameInput").value = "";
                document.getElementById("fileInput").value = "";
                capturedBlob = null;
                document.getElementById("capturePreview").style.display = "none";
                updateStats();
            }
        } catch {
            showEnrollMsg("Request failed.", true);
        }
    });

    function showEnrollMsg(msg, isError) {
        const el   = document.getElementById("enrollStatus");
        el.textContent  = msg;
        el.style.color  = isError ? "var(--danger)" : "var(--success)";
    }


    // ── RELOAD ENCODINGS ─────────────────────────────────────────────────────
    document.getElementById("reloadBtn").addEventListener("click", async () => {
        const btn = document.getElementById("reloadBtn");
        btn.textContent = "Reloading…";
        btn.disabled    = true;

        try {
            const res = await API.reload();
            showEnrollMsg(res.message || "Reloaded.", false);
        } catch {
            showEnrollMsg("Reload failed.", true);
        } finally {
            btn.textContent = "Reload Encodings";
            btn.disabled    = false;
        }
    });


    // ── SETTINGS ─────────────────────────────────────────────────────────────
    const slider  = document.getElementById("toleranceSlider");
    const valDisp = document.getElementById("toleranceValue");

    slider.addEventListener("input", () => {
        valDisp.textContent = (slider.value / 100).toFixed(2);
    });

    document.getElementById("saveSettingsBtn").addEventListener("click", async () => {
        const tolerance = slider.value / 100;
        try {
            const res = await API.saveSettings(tolerance);
            setSettingsMsg(res.message || "Saved.", false);
        } catch {
            setSettingsMsg("Failed to save.", true);
        }
    });

    document.getElementById("clearLogBtn").addEventListener("click", async () => {
        if (!confirm("Clear all activity log entries? This cannot be undone.")) return;
        try {
            const res = await API.clearLog();
            setSettingsMsg(res.message || "Log cleared.", false);
            if (document.getElementById("tab-log").classList.contains("active")) loadLog();
        } catch {
            setSettingsMsg("Failed to clear log.", true);
        }
    });

    function setSettingsMsg(msg, isError) {
        const el   = document.getElementById("settingsStatus");
        el.textContent = msg;
        el.style.color = isError ? "var(--danger)" : "var(--success)";
    }


    // ── TRAINING ─────────────────────────────────────────────────────────────

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function loadTrainingStatus() {
        try {
            const d     = await API.getTrainingStatus();
            const faces = d.faces || [];
            const container = document.getElementById("trainStatusBody");

            if (!faces.length) {
                container.innerHTML = '<div class="faces-empty">No faces enrolled yet. Start training to see status here.</div>';
                return;
            }

            container.innerHTML = faces.map(f => {
                const quality = f.count >= 8 ? "strong" : f.count >= 4 ? "good" : f.count >= 2 ? "fair" : "weak";
                const label   = { strong: "Strong", good: "Good", fair: "Fair", weak: "Weak" }[quality];
                const barPct  = Math.min(f.count / 10 * 100, 100);
                return `
                    <div class="train-status-row">
                        <div class="ts-name">${f.name}</div>
                        <div class="ts-count">${f.count} encoding${f.count !== 1 ? "s" : ""}</div>
                        <div class="ts-bar-wrap">
                            <div class="train-bar-track">
                                <div class="train-bar-fill quality-${quality}" style="width:${barPct}%"></div>
                            </div>
                        </div>
                        <span class="quality-badge quality-${quality}">${label}</span>
                    </div>`;
            }).join("");
        } catch {}
    }

    // Bulk upload
    document.getElementById("bulkTrainBtn").addEventListener("click", async () => {
        const name  = document.getElementById("bulkName").value.trim();
        const files = document.getElementById("bulkFiles").files;

        if (!name)         { showBulkMsg("Enter a name.", true); return; }
        if (!files.length) { showBulkMsg("Select at least one image.", true); return; }

        const btn = document.getElementById("bulkTrainBtn");
        btn.disabled = true;
        showBulkMsg("Processing…", false);

        try {
            const res = await API.trainBulk(name, Array.from(files));
            showBulkMsg(res.error || res.message, !!res.error);
            if (!res.error) {
                document.getElementById("bulkFiles").value = "";
                loadTrainingStatus();
                updateStats();
            }
        } catch {
            showBulkMsg("Request failed.", true);
        } finally {
            btn.disabled = false;
        }
    });

    function showBulkMsg(msg, isError) {
        const el = document.getElementById("bulkStatus");
        el.textContent = msg;
        el.style.color = isError ? "var(--danger)" : "var(--success)";
    }

    // Live capture session
    document.getElementById("startSessionBtn").addEventListener("click", async () => {
        const name       = document.getElementById("sessionName").value.trim();
        const frameCount = parseInt(document.getElementById("frameCount").value, 10);

        if (!name) { showSessionMsg("Enter a name.", true); return; }

        const btn          = document.getElementById("startSessionBtn");
        const progress     = document.getElementById("captureProgress");
        const progressFill = document.getElementById("captureProgressFill");
        const progressText = document.getElementById("captureProgressText");

        btn.disabled = true;
        progress.style.display = "block";
        showSessionMsg("", false);

        const captured = [];

        for (let i = 0; i < frameCount; i++) {
            progressText.textContent = `Capturing frame ${i + 1} of ${frameCount}…`;
            progressFill.style.width = `${(i / frameCount) * 90}%`;

            try {
                captured.push(await API.getSnapshot());
            } catch {
                showSessionMsg("Snapshot failed. Is the camera running?", true);
                btn.disabled = false;
                progress.style.display = "none";
                return;
            }

            if (i < frameCount - 1) await sleep(1100);
        }

        progressText.textContent = "Processing encodings…";
        progressFill.style.width = "95%";

        try {
            const res = await API.trainBulk(name, captured);
            progressFill.style.width = "100%";
            showSessionMsg(res.error || res.message, !!res.error);
            if (!res.error) {
                loadTrainingStatus();
                updateStats();
            }
        } catch {
            showSessionMsg("Training request failed.", true);
        }

        btn.disabled = false;
        setTimeout(() => { progress.style.display = "none"; }, 2000);
    });

    function showSessionMsg(msg, isError) {
        const el = document.getElementById("sessionStatus");
        el.textContent = msg;
        el.style.color = isError ? "var(--danger)" : "var(--success)";
    }

    document.getElementById("refreshTrainBtn").addEventListener("click", loadTrainingStatus);


    // ── CAMERA DEVICE ────────────────────────────────────────────────────────

    document.getElementById("scanCamerasBtn").addEventListener("click", async () => {
        const btn = document.getElementById("scanCamerasBtn");
        const sel = document.getElementById("cameraSelect");
        btn.textContent = "Scanning…";
        btn.disabled    = true;
        setCameraMsg("", false);

        try {
            const d       = await API.getCameras();
            const cameras = d.cameras || [];

            sel.innerHTML = cameras.length
                ? cameras.map(i =>
                    `<option value="${i}"${i === d.active ? " selected" : ""}>` +
                    `Camera ${i}${i === d.active ? " (active)" : ""}</option>`
                  ).join("")
                : '<option value="">No cameras detected</option>';

            const dot  = document.getElementById("cameraDot2");
            const txt  = document.getElementById("cameraStatusText");
            dot.className  = d.connected ? "stat-dot online" : "stat-dot offline";
            txt.textContent = d.connected
                ? `Camera ${d.active} connected`
                : cameras.length ? "Camera found but not connected — click Apply" : "No cameras detected";

            setCameraMsg(
                cameras.length ? `Found ${cameras.length} device(s).` : "No cameras found.",
                cameras.length === 0
            );
        } catch {
            setCameraMsg("Scan failed.", true);
        } finally {
            btn.textContent = "Scan";
            btn.disabled    = false;
        }
    });

    document.getElementById("applyCameraBtn").addEventListener("click", async () => {
        const sel   = document.getElementById("cameraSelect");
        const index = parseInt(sel.value, 10);
        if (isNaN(index)) { setCameraMsg("Select a camera first.", true); return; }

        const btn = document.getElementById("applyCameraBtn");
        btn.disabled = true;
        setCameraMsg("Switching…", false);

        try {
            const res = await API.selectCamera(index);
            setCameraMsg(res.error || res.message, !!res.error);

            const dot = document.getElementById("cameraDot2");
            const txt = document.getElementById("cameraStatusText");
            dot.className  = res.connected ? "stat-dot online" : "stat-dot offline";
            txt.textContent = res.connected ? `Camera ${index} connected` : "Could not open camera";

            updateStats();
        } catch {
            setCameraMsg("Request failed.", true);
        } finally {
            btn.disabled = false;
        }
    });

    function setCameraMsg(msg, isError) {
        const el = document.getElementById("cameraMsg");
        el.textContent = msg;
        el.style.color = isError ? "var(--danger)" : "var(--success)";
    }

});
