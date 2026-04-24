from flask import Blueprint, request, jsonify
from app.services.camera_service import get_camera, list_cameras

cameras_bp = Blueprint("cameras", __name__)


@cameras_bp.route('/cameras', methods=['GET'])
def get_cameras():
    available = list_cameras()
    cam = get_camera()
    return jsonify({
        "cameras": available,
        "active": cam.index,
        "connected": cam.connected,
    })


@cameras_bp.route('/cameras/select', methods=['POST'])
def select_camera():
    data = request.get_json(silent=True) or {}
    raw  = data.get("index")

    if raw is None:
        return jsonify({"error": "index is required."}), 400
    try:
        index = int(raw)
    except (TypeError, ValueError):
        return jsonify({"error": "index must be an integer."}), 400

    success = get_camera().switch(index)
    if success:
        return jsonify({"message": f"Switched to camera {index}.", "connected": True})
    return jsonify({"error": f"Camera {index} could not be opened.", "connected": False}), 400
