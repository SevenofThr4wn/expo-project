import cv2
import logging

logger = logging.getLogger(__name__)

_camera = None


def get_camera(index=0, width=1280, height=720):
    global _camera
    if _camera is None:
        _camera = CameraService(index, width, height)
    return _camera


class CameraService:
    def __init__(self, index=0, width=1280, height=720):
        self.index  = index
        self.width  = width
        self.height = height
        self.cap    = None

    def start(self):
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            logger.error("Camera could not be accessed")
            raise RuntimeError("Camera not accessible")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        logger.info(f"Camera started ({self.width}x{self.height})")

    def read(self):
        if self.cap is None:
            raise RuntimeError("Camera not initialized")
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Failed to read frame")
            return None
        return frame

    def release(self):
        if self.cap:
            self.cap.release()
            logger.info("Camera released")

    def generate_frames(self, processor_callback):
        while True:
            frame = self.read()
            if frame is None:
                break
            processed = processor_callback(frame)
            ret, buffer = cv2.imencode(".jpg", processed)
            if not ret:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buffer.tobytes()
                + b"\r\n"
            )
