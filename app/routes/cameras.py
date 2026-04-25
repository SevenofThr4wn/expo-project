from flask import Blueprint, jsonify, request

from app.auth.decorators import api_login_required, role_required
from app.models.user import Role
from app.services.camera_service import get_camera, list_cameras

cameras_bp = Blueprint("cameras_api", __name__, url_prefix="/api")


@cameras_bp.route("/cameras")
@api_login_required
def get_cameras():
    available = list_cameras()
    cam = get_camera()
    return jsonify({"cameras": available, "active": cam.index, "connected": cam.connected})


@cameras_bp.route("/cameras/select", methods=["POST"])
@role_required(Role.ADMIN, Role.OPERATOR)
def select_camera():
    data = request.get_json(silent=True) or {}
    try:
        index = int(data.get("index"))
    except (TypeError, ValueError):
        return jsonify({"error": "index must be an integer"}), 400

    success = get_camera().switch(index)
    if success:
        return jsonify({"message": f"Switched to camera {index}.", "connected": True})
    return jsonify({"error": f"Camera {index} could not be opened.", "connected": False}), 400
