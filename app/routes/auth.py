from flask import Blueprint, session, jsonify
from app.services.camera_service import get_camera
from app.auth.face_auth import face_auth

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/face-login")
def face_login():
    camera = get_camera()
    if camera.cap is None:
        camera.start()

    frame = camera.read()
    if frame is None:
        return jsonify({"error": "Camera error"}), 500

    user = face_auth.verify(frame)
    if user:
        session["user"] = user
        return jsonify({"success": True, "user": user})

    return jsonify({"success": False})
