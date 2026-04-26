import cv2
import time
import platform
import threading
import logging

logger = logging.getLogger(__name__)

_camera = None
_camera_lock = threading.Lock()

_TARGET_FPS = 30
_FRAME_INTERVAL = 1.0 / _TARGET_FPS


def _backend_list():
    system = platform.system()

    if system == "Windows":
        # MSMF is usually the ONLY reliable one for webcams now
        return [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]

    if system == "Linux":
        return [cv2.CAP_V4L2, cv2.CAP_ANY]

    return [cv2.CAP_ANY]


def list_cameras(max_index: int = 5) -> list:
    available = []

    for i in range(max_index + 1):
        for backend in _backend_list():
            cap = cv2.VideoCapture(0, backend)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    available.append(i)
                    break

    return available

def get_camera(index: int = 0, width: int = 1280, height: int = 720):
    global _camera

    if _camera is None:
        with _camera_lock:
            if _camera is None:
                _camera = CameraService(index, width, height)
                _camera.start()

    return _camera


def camera_is_connected() -> bool:
    return _camera is not None and _camera.connected


# ─────────────────────────────────────────────────────────────
# CAMERA SERVICE
# ─────────────────────────────────────────────────────────────

class CameraService:
    def __init__(self, index=0, width=1280, height=720):
        self.index = index
        self.width = width
        self.height = height

        self.cap = None
        self.connected = False

        self._lock = threading.Lock()
        self._reconnect_thread = None
        self._stop = threading.Event()

    # ───────────────── OPEN CAMERA ─────────────────

    def start(self):
        with self._lock:
            if self.connected:
                return True

            self.cap = None
            self.connected = False

            for backend in _backend_list():
                logger.info("Opening camera %d (backend=%s)...", self.index, backend)

                cap = cv2.VideoCapture(self.index, backend)

                if not cap.isOpened():
                    cap.release()
                    continue

                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

                # warmup (IMPORTANT for webcams)
                time.sleep(0.3)

                ret, frame = cap.read()
                if not ret or frame is None:
                    cap.release()
                    continue

                self.cap = cap
                self.connected = True
                self._stop.set()

                logger.info("Camera %d started", self.index)
                return True

            logger.warning("Camera %d failed to open on all backends", self.index)
            self._schedule_reconnect()
            return False

    # ───────────────── SWITCH ─────────────────

    def switch(self, index: int):
        self.release()
        self.index = index
        return self.start()

    # ───────────────── RELEASE ─────────────────

    def release(self):
        self._stop.set()

        with self._lock:
            if self.cap:
                self.cap.release()
                self.cap = None

            self.connected = False

        logger.info("Camera %d released", self.index)

    # ───────────────── READ FRAME ─────────────────

    def read(self):
        if not self.connected or self.cap is None:
            return None

        with self._lock:
            ret, frame = self.cap.read()

        if not ret:
            self._handle_disconnect()
            return None

        return frame

    # ───────────────── DISCONNECT ─────────────────

    def _handle_disconnect(self):
        logger.warning("Camera %d disconnected", self.index)
        self.connected = False

        if self.cap:
            self.cap.release()
            self.cap = None

        self._schedule_reconnect()

    # ───────────────── RECONNECT ─────────────────

    def _schedule_reconnect(self):
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        self._stop.clear()
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            daemon=True
        )
        self._reconnect_thread.start()

    def _reconnect_loop(self):
        delay = 2

        while not self._stop.is_set():
            logger.info("Camera %d reconnecting in %ds...", self.index, delay)
            time.sleep(delay)

            if self.start():
                logger.info("Camera %d reconnected", self.index)
                return

            delay = min(delay * 2, 10)

    # ───────────────── MJPEG STREAM ─────────────────

    def generate_frames(self, processor=None):
        last = 0

        while True:
            now = time.time()

            if now - last < _FRAME_INTERVAL:
                time.sleep(_FRAME_INTERVAL)

            frame = self.read()

            if frame is None:
                continue

            if processor:
                try:
                    frame = processor(frame)
                except Exception:
                    pass

            _, buf = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, 85]
            )

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                buf.tobytes() +
                b"\r\n"
            )

            last = time.time()