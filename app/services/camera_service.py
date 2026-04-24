import cv2
import time
import platform
import logging
import numpy as np

logger = logging.getLogger(__name__)

_camera = None


def _backend():
    # DirectShow is faster on Windows; default works on Linux (Raspberry Pi)
    return cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY


def list_cameras(max_index=9):
    """Scan indices 0–max_index and return those that open successfully."""
    available = []
    backend = _backend()
    for i in range(max_index + 1):
        cap = cv2.VideoCapture(i, backend)
        if cap.isOpened():
            available.append(i)
        cap.release()
    return available


def get_camera(index=0, width=1280, height=720):
    global _camera
    if _camera is None:
        _camera = CameraService(index, width, height)
    return _camera


class CameraService:
    def __init__(self, index=0, width=1280, height=720):
        self.index     = index
        self.width     = width
        self.height    = height
        self.cap       = None
        self.connected = False

    def start(self):
        """Open the camera. Returns True on success, False if unavailable."""
        self.cap = cv2.VideoCapture(self.index, _backend())
        if not self.cap.isOpened():
            logger.warning(f"Camera {self.index} could not be opened")
            self.cap.release()
            self.cap = None
            self.connected = False
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.connected = True
        logger.info(f"Camera {self.index} started ({self.width}x{self.height})")
        return True

    def switch(self, index):
        """Hot-swap to a different camera device."""
        self.release()
        self.index = index
        return self.start()

    def read(self):
        if not self.connected or self.cap is None:
            return None
        try:
            ret, frame = self.cap.read()
        except Exception:
            self.connected = False
            return None
        if not ret:
            logger.warning(f"Camera {self.index}: frame read failed, marking disconnected")
            self.connected = False
            return None
        return frame

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.connected = False
        logger.info(f"Camera {self.index} released")

    def _no_camera_frame(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (18, 24, 38)
        cx, cy = 320, 210
        # Camera body outline
        cv2.rectangle(img, (cx - 64, cy - 40), (cx + 64, cy + 40), (55, 65, 90), 2)
        cv2.rectangle(img, (cx + 44, cy - 52), (cx + 66, cy - 28), (55, 65, 90), 2)
        cv2.circle(img, (cx, cy), 22, (55, 65, 90), 2)
        # Diagonal slash
        cv2.line(img, (cx - 82, cy - 58), (cx + 82, cy + 58), (70, 80, 110), 2)
        cv2.putText(img, "No Camera Detected", (158, 310),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (110, 120, 160), 1, cv2.LINE_AA)
        cv2.putText(img, "Go to Settings  >  Camera Device to select a device", (86, 348),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (60, 70, 100), 1, cv2.LINE_AA)
        return img

    def generate_frames(self, processor_callback):
        while True:
            frame = self.read()
            if frame is None:
                placeholder = self._no_camera_frame()
                ret, buffer = cv2.imencode(".jpg", placeholder)
                if ret:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + buffer.tobytes()
                        + b"\r\n"
                    )
                time.sleep(1.0)
                continue
            try:
                processed = processor_callback(frame)
            except Exception:
                processed = frame
            ret, buffer = cv2.imencode(".jpg", processed)
            if not ret:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )
