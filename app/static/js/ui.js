const UI = {
    setStatus(text) {
        document.getElementById("systemStatus").innerText = "Status: " + text;
    },
    showEnrollMessage(msg, isError = false) {
        const el = document.getElementById("enrollStatus");
        el.innerText = msg;
        el.style.color = isError ? "red" : "lightgreen";
    },

    setOnline(isOnline) {
        const dot = document.getElementById("statusDot");
        dot.style.background = isOnline ? "lime" : "red";
    }
};