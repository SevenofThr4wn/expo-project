import cv2
import logging
import time
from flask import Blueprint, Response, jsonify

from app.services.camera_service import get_camera
from app.services.recognition_service import get_recognizer

logger = logging.getLogger(__name__)

stream_bp = Blueprint("stream", __name__, url_prefix="/api")

_TARGET_FPS = 30
_FRAME_INTERVAL = 1.0 / _TARGET_FPS

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        from gevent.threadpool import ThreadPool
        _pool = ThreadPool(1)
    return _pool


def _recognise(frame):
    """Runs inside the threadpool native thread — never blocks the event loop."""
    recognizer = get_recognizer()
    results = recognizer.process_frame(frame)
    return recognizer.draw_results(frame, results)


def _generate_frames():
    camera = get_camera()
    last = 0.0

    while True:
        now = time.monotonic()
        elapsed = now - last
        if elapsed < _FRAME_INTERVAL:
            time.sleep(_FRAME_INTERVAL - elapsed) 

        frame = camera.read()
        if frame is None:
            img = camera._placeholder_frame()
            ret, buf = cv2.imencode(".jpg", img)
            if ret:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
            time.sleep(1.0)
            continue

        try:
            # Submit to native thread; this greenlet suspends here so the
            # event loop can serve other requests while recognition runs.
            frame = _get_pool().spawn(_recognise, frame).get()
        except Exception:
            pass  # fall through with the raw frame

        ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            continue

        last = time.monotonic()
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"


@stream_bp.route("/video")
def video_stream():
    """MJPEG stream — kept public so the login page camera works."""
    camera = get_camera()
    if not camera.connected:
        camera.start()
    return Response(
        _generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@stream_bp.route("/snapshot")
def snapshot():
    """Return a single JPEG frame — public for face-login flow."""
    camera = get_camera()
    if not camera.connected:
        camera.start()
    frame = camera.read()
    if frame is None:
        return "Camera unavailable", 500
    ret, buf = cv2.imencode(".jpg", frame)
    if not ret:
        return "Encode error", 500
    return Response(buf.tobytes(), mimetype="image/jpeg")


@stream_bp.route("/reload")
def reload_encodings():
    get_recognizer().refresh_data()
    return jsonify({"message": "Encodings reloaded."})
