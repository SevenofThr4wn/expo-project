import threading
import time
import tkinter as tk
import cv2
from PIL import Image, ImageTk

from app.services.face_engine import get_faces 

STREAM_URL = 0  # webcam
TITLE = "FaceID — Live Camera"
WIN_W, WIN_H = 1280, 720
BG = "#060c1a"
_POLL_MS = 33


class CameraViewer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(TITLE)
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self.root.configure(bg=BG)

        self._label = tk.Label(
            root,
            bg=BG,
            text="Connecting to camera…",
            fg="#64748b",
            font=("Segoe UI", 14),
        )
        self._label.pack(fill=tk.BOTH, expand=True)

        self._latest_frame = None
        self._lock = threading.Lock()
        self._running = True

        threading.Thread(target=self._capture_loop, daemon=True).start()

        self.root.after(_POLL_MS, self._poll)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    # ── CAMERA THREAD ─────────────────────────────
    def _capture_loop(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if not cap.isOpened():
            print("Camera not found")
            return

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # 1. COPY ONCE (prevents OpenCV buffer corruption)
            frame = frame.copy()

            # 2. FACE DETECTION
            faces = get_faces(frame)

            for f in faces:
                x1, y1, x2, y2 = map(int, f.bbox)

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                cv2.putText(
                    frame,
                    f"Face {f.det_score:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

            # 3. SINGLE SAFE PUBLISH
            with self._lock:
                self._latest_frame = frame

        cap.release()

    # ── UI THREAD ─────────────────────────────
    def _poll(self):
        if not self._running:
            return

        with self._lock:
            frame = self._latest_frame

        if frame is not None:
            w = self._label.winfo_width()
            h = self._label.winfo_height()

            if w > 1 and h > 1:
                frame = cv2.resize(frame, (w, h))

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(image=Image.fromarray(rgb))

            self._label.configure(image=img, text="")
            self._label.image = img

        self.root.after(_POLL_MS, self._poll)

    def _close(self):
        self._running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    CameraViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()