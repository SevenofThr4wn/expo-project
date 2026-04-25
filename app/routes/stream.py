import cv2
import logging
from flask import Blueprint, Response, jsonify

from app.services.camera_service import get_camera
from app.services.recognition_service import get_recognizer

logger = logging.getLogger(__name__)

stream_bp = Blueprint("stream", __name__, url_prefix="/api")


def _process(frame):
    recognizer = get_recognizer()
    results = recognizer.process_frame(frame)
    return recognizer.draw_results(frame, results)


@stream_bp.route("/video")
def video_stream():
    """MJPEG stream — kept public so the login page camera works."""
    camera = get_camera()
    if not camera.connected:
        camera.start()
    return Response(
        camera.generate_frames(_process),
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
