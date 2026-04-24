import cv2
import logging
from flask import Blueprint, Response, jsonify
from app.services.camera_service import get_camera
from app.services.recognition_service import get_recognizer

logger = logging.getLogger(__name__)

recognize_bp = Blueprint("recognize", __name__)


def _process(frame):
    recognizer = get_recognizer()
    results = recognizer.process_frame(frame)
    return recognizer.draw_results(frame, results)


@recognize_bp.route('/video')
def video_stream():
    camera = get_camera()
    try:
        if camera.cap is None:
            camera.start()
        return Response(
            camera.generate_frames(_process),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        logger.exception(f"Video stream error: {e}")
        return "Camera error", 500


@recognize_bp.route('/snapshot')
def snapshot():
    camera = get_camera()
    try:
        if camera.cap is None:
            camera.start()
        frame = camera.read()
        if frame is None:
            return "Camera error", 500
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            return "Encode error", 500
        return Response(buffer.tobytes(), mimetype='image/jpeg')
    except Exception as e:
        logger.exception(f"Snapshot error: {e}")
        return "Error", 500


@recognize_bp.route('/reload')
def reload_encodings():
    get_recognizer().refresh_data()
    return jsonify({"message": "Encodings reloaded."})
