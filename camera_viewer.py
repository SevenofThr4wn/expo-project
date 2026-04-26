"""
FaceID — standalone desktop camera viewer.

Loads face encodings directly from the SQLite database (no Flask context
required), runs InsightFace detection + ArcFace matching on every 3rd frame,
and draws the same overlay as the web stream.

Hotkeys:
  R — reload encodings from DB
  Q — quit
"""

import os
import pickle
import sqlite3
import threading
import time
import tkinter as tk

import cv2
import numpy as np
from dotenv import load_dotenv
from PIL import Image, ImageTk

from app.services.face_engine import get_face_app

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
STREAM_URL = 0
TITLE      = "FaceID — Live Camera"
WIN_W      = 1280
WIN_H      = 720
BG         = "#060c1a"
_POLL_MS   = 33
_PROCESS_EVERY = 3 

TOLERANCE = float(os.getenv("RECOGNITION_TOLERANCE", "0.6"))

_raw_db = os.getenv("DATABASE_URL", "sqlite:///faceid.db")
if _raw_db.startswith("sqlite:///"):
    _rel = _raw_db[len("sqlite:///"):]
    _DB_PATH = (
        _rel if os.path.isabs(_rel)
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", os.path.basename(_rel))
    )
else:
    _DB_PATH = _raw_db

COLOR_KNOWN   = (0, 220, 100)   # BGR green  — recognised person
COLOR_UNKNOWN = (60,  60, 220)  # BGR red    — unknown face

# 68-point landmark connectivity (ibug/300W convention — same ordering as dlib)
# Each sub-list is drawn as a polyline.
_LM68_GROUPS = [
    list(range(0,  17)),          # jaw line
    list(range(17, 22)),          # left eyebrow
    list(range(22, 27)),          # right eyebrow
    list(range(27, 31)),          # nose bridge
    list(range(30, 36)),          # nose bottom
    list(range(36, 42)) + [36],   # left eye  (closed)
    list(range(42, 48)) + [42],   # right eye (closed)
    list(range(48, 60)) + [48],   # outer lip (closed)
    list(range(60, 68)) + [60],   # inner lip (closed)
]


# ── Encoding store ───────────────────────────────────
_enc_lock  = threading.Lock()
_encodings: list[np.ndarray] = []
_names:     list[str]        = []


def load_encodings() -> None:
    """Read all face encodings from the SQLite DB without a Flask app context."""
    global _encodings, _names
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=5)
        cur  = conn.cursor()
        cur.execute("SELECT name, encoding_blob FROM face_encodings")
        rows = cur.fetchall()
        conn.close()

        enc   = [np.array(pickle.loads(blob), dtype=np.float32) for _, blob in rows]
        names = [name for name, _ in rows]

        with _enc_lock:
            _encodings = enc
            _names     = names

        print(f"[FaceID] Loaded {len(enc)} encodings ({len(set(names))} people)")
    except Exception as exc:
        print(f"[FaceID] Could not load encodings: {exc}")


# ── Cosine-similarity matching ────────────────────────────────────────────────
def _match(embedding: np.ndarray) -> tuple[str, int]:
    with _enc_lock:
        enc_snap  = list(_encodings)
        name_snap = list(_names)

    if not enc_snap:
        return "unknown", 0

    enc   = embedding / (np.linalg.norm(embedding) + 1e-10)
    known = np.array(enc_snap)
    known = known / (np.linalg.norm(known, axis=1, keepdims=True) + 1e-10)

    sims  = np.dot(known, enc)
    best  = int(np.argmax(sims))
    score = float(sims[best])

    if score > (1 - TOLERANCE):
        return name_snap[best], int(score * 100)
    return "unknown", int(score * 100)


# ── Drawing ────────────────────────
def _draw_results(frame: np.ndarray, results: list[dict]) -> np.ndarray:
    for r in results:
        left, top, right, bottom = (int(v) for v in r["box"])
        name       = r["name"]
        confidence = r["confidence"]
        color      = COLOR_KNOWN if name != "unknown" else COLOR_UNKNOWN

        # Bounding box
        cv2.rectangle(frame, (left, top), (right, bottom), color, 1, cv2.LINE_AA)

        # Corner accent marks
        cl, ct = 14, 2
        for ox, oy, hx, vy in [
            (left,  top,    left  + cl, top    + cl),
            (right, top,    right - cl, top    + cl),
            (left,  bottom, left  + cl, bottom - cl),
            (right, bottom, right - cl, bottom - cl),
        ]:
            cv2.line(frame, (ox, oy), (hx, oy), color, ct, cv2.LINE_AA)
            cv2.line(frame, (ox, oy), (ox, vy), color, ct, cv2.LINE_AA)

        # Label pill
        label = f"{name}  {confidence}%"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
        ly = top - 10 if top > 34 else bottom + th + 10
        cv2.rectangle(frame, (left, ly - th - 6), (left + tw + 10, ly + 2), color, -1)
        cv2.putText(
            frame, label, (left + 5, ly - 1),
            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA,
        )

        # Confidence bar
        bar_w  = tw + 10
        filled = int(bar_w * confidence / 100)
        cv2.rectangle(frame, (left, ly + 3), (left + bar_w, ly + 6), (40, 40, 40), -1)
        cv2.rectangle(frame, (left, ly + 3), (left + filled, ly + 6), color, -1)

        # 68-point 3D landmarks (x, y, z — drop z for drawing)
        lm68 = r.get("landmark_3d_68")
        if lm68 is not None:
            pts = np.array(lm68, dtype=np.int32)[:, :2]  # (68, 2)
            for group in _LM68_GROUPS:
                cv2.polylines(
                    frame,
                    [pts[group]],
                    isClosed=False,
                    color=(255, 200, 0),
                    thickness=1,
                    lineType=cv2.LINE_AA,
                )
        elif r.get("kps") is not None:
            # Fallback: 5-point kps if 1k3d68 model isn't present
            for x, y in np.array(r["kps"], dtype=np.int32):
                cv2.circle(frame, (x, y), 2, (255, 200, 0), -1, cv2.LINE_AA)

    return frame


# ── Main viewer ───────────────────────────────────────────────────────────────
class CameraViewer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(TITLE)
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self.root.configure(bg=BG)

        self._feed = tk.Label(root, bg=BG, text="Connecting to camera…",
                              fg="#64748b", font=("Segoe UI", 14))
        self._feed.pack(fill=tk.BOTH, expand=True)

        self._bar = tk.Label(
            root, bg="#0b1224", fg="#64748b", font=("Consolas", 10),
            text=f"R — reload encodings  |  Q — quit  |  DB: {_DB_PATH}",
            anchor="w", padx=10, pady=4,
        )
        self._bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._latest_frame: np.ndarray | None = None
        self._frame_lock   = threading.Lock()
        self._running      = True
        self._face_app     = get_face_app()

        # FPS tracking
        self._fps           = 0.0
        self._fps_frames    = 0
        self._fps_ts        = time.monotonic()

        threading.Thread(target=self._capture_loop, daemon=True).start()

        self.root.after(_POLL_MS, self._poll)
        self.root.bind("<q>", lambda _: self._close())
        self.root.bind("<Q>", lambda _: self._close())
        self.root.bind("<r>", lambda _: threading.Thread(target=load_encodings, daemon=True).start())
        self.root.bind("<R>", lambda _: threading.Thread(target=load_encodings, daemon=True).start())
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    # ── Camera thread ────────────────────────────────────
    def _capture_loop(self) -> None:
        cap = cv2.VideoCapture(STREAM_URL, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[FaceID] Camera not found")
            return

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        n            = 0
        last_results: list[dict] = []

        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            frame = frame.copy()
            n    += 1

            if n % _PROCESS_EVERY == 0:
                faces        = self._face_app.get(frame)
                last_results = []
                for f in faces:
                    name, conf = _match(np.array(f.embedding, dtype=np.float32))
                    last_results.append({
                        "box":             f.bbox,
                        "name":            name,
                        "confidence":      conf,
                        "kps":             getattr(f, "kps", None),
                        "landmark_3d_68":  getattr(f, "landmark_3d_68", None),
                    })

            _draw_results(frame, last_results)

            # FPS counter (top-left)
            self._fps_frames += 1
            now = time.monotonic()
            if now - self._fps_ts >= 1.0:
                self._fps      = self._fps_frames / (now - self._fps_ts)
                self._fps_ts   = now
                self._fps_frames = 0
            cv2.putText(
                frame, f"{self._fps:.0f} fps", (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 80), 1, cv2.LINE_AA,
            )

            with self._frame_lock:
                self._latest_frame = frame

        cap.release()

    # ── UI thread poll (Tk main thread) ───────────────────────────────────────
    def _poll(self) -> None:
        if not self._running:
            return

        with self._frame_lock:
            frame = self._latest_frame

        if frame is not None:
            w = self._feed.winfo_width()
            h = self._feed.winfo_height()
            if w > 1 and h > 1:
                frame = cv2.resize(frame, (w, h))

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(image=Image.fromarray(rgb))
            self._feed.configure(image=img, text="")
            self._feed.image = img

        self.root.after(_POLL_MS, self._poll)

    def _close(self) -> None:
        self._running = False
        self.root.destroy()


def main() -> None:
    load_encodings()
    root = tk.Tk()
    CameraViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
