import cv2
import time
import platform
import threading
import logging
import numpy as np

logger = logging.getLogger(__name__)

_camera = None
_camera_lock = threading.Lock()

_TARGET_FPS = 30
_FRAME_INTERVAL = 1.0 / _TARGET_FPS


def _backend():
    return cv2.CAP_MSMF if platform.system() == "Windows" else cv2.CAP_ANY


def list_cameras(max_index: int = 9) -> list:
    """Return indices of camera devices that open successfully."""
    available = []
    prev = cv2.getLogLevel() if hasattr(cv2, "getLogLevel") else None
    if prev is not None:
        cv2.setLogLevel(0)
    try:
        for i in range(max_index + 1):
            cap = cv2.VideoCapture(i, cv2.CAP_ANY)
            if cap.isOpened():
                available.append(i)
            cap.release()
    finally:
        if prev is not None:
            cv2.setLogLevel(prev)
    return available


def get_camera(index: int = 0, width: int = 1280, height: int = 720):
    global _camera
    if _camera is None:
        with _camera_lock:
            if _camera is None:
                _camera = CameraService(index, width, height)
                _camera.start()
    return _camera


class CameraService:
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720):
        self.index = index
        self.width = width
        self.height = height
        self.cap = None
        self.connected = False
        self._lock = threading.Lock()
        self._reconnect_thread: threading.Thread | None = None
        self._stop_reconnect = threading.Event()

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> bool:
        with self._lock:
            self.cap = cv2.VideoCapture(self.index, _backend())
            if not self.cap.isOpened():
                logger.warning("Camera %d could not be opened", self.index)
                self.cap.release()
                self.cap = None
                self.connected = False
                self._schedule_reconnect()
                return False
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.connected = True
            self._stop_reconnect.set()   # cancel any pending reconnect
        logger.info("Camera %d started (%dx%d)", self.index, self.width, self.height)
        return True

    def switch(self, index: int) -> bool:
        self.release()
        self.index = index
        return self.start()

    def release(self):
        self._stop_reconnect.set()
        with self._lock:
            if self.cap:
                self.cap.release()
                self.cap = None
            self.connected = False
        logger.info("Camera %d released", self.index)

    # ── Reading ────────────────────────────────────────────────────────────────

    def read(self):
        if not self.connected or self.cap is None:
            return None
        with self._lock:
            if not self.connected or self.cap is None:
                return None
            try:
                ret, frame = self.cap.read()
            except Exception:
                self._mark_disconnected()
                return None
            if not ret:
                self._mark_disconnected()
                return None
            return frame

    def _mark_disconnected(self):
        """Called while holding self._lock."""
        self.connected = False
        logger.warning("Camera %d disconnected", self.index)
        self._schedule_reconnect()

    # ── Auto-reconnect ─────────────────────────────────────────────────────────

    def _schedule_reconnect(self):
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return
        self._stop_reconnect.clear()
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop, daemon=True
        )
        self._reconnect_thread.start()

    def _reconnect_loop(self):
        delay = 3
        while not self._stop_reconnect.is_set():
            logger.info("Camera %d: attempting reconnect in %ds…", self.index, delay)
            self._stop_reconnect.wait(delay)
            if self._stop_reconnect.is_set():
                break
            if self.start():
                logger.info("Camera %d reconnected", self.index)
                break
            delay = min(delay * 2, 30)

    # ── MJPEG generation ───────────────────────────────────────────────────────

    def _placeholder_frame(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (18, 24, 38)
        cx, cy = 320, 210
        cv2.rectangle(img, (cx - 64, cy - 40), (cx + 64, cy + 40), (55, 65, 90), 2)
        cv2.rectangle(img, (cx + 44, cy - 52), (cx + 66, cy - 28), (55, 65, 90), 2)
        cv2.circle(img, (cx, cy), 22, (55, 65, 90), 2)
        cv2.line(img, (cx - 82, cy - 58), (cx + 82, cy + 58), (70, 80, 110), 2)
        cv2.putText(img, "No Camera Detected", (148, 310),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (110, 120, 160), 1, cv2.LINE_AA)
        cv2.putText(img, "Settings > Camera Device to select a device", (90, 348),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (60, 70, 100), 1, cv2.LINE_AA)
        return img

    def generate_frames(self, processor=None):
        last_frame_time = 0.0
        while True:
            now = time.monotonic()
            elapsed = now - last_frame_time
            if elapsed < _FRAME_INTERVAL:
                time.sleep(_FRAME_INTERVAL - elapsed)

            frame = self.read()
            if frame is None:
                img = self._placeholder_frame()
                ret, buf = cv2.imencode(".jpg", img)
                if ret:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
                time.sleep(1.0)
                continue

            try:
                processed = processor(frame) if processor else frame
            except Exception:
                processed = frame

            ret, buf = cv2.imencode(".jpg", processed, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                continue

            last_frame_time = time.monotonic()
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
