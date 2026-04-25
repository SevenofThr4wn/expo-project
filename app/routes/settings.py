from flask import Blueprint, jsonify, request

from app.auth.decorators import role_required
from app.models.user import Role

settings_bp = Blueprint("settings_api", __name__, url_prefix="/api")


@settings_bp.route("/settings", methods=["POST"])
@role_required(Role.ADMIN, Role.OPERATOR)
def update_settings():
    data = request.get_json(force=True) or {}
    updates = {}

    raw_tol = data.get("tolerance")
    if raw_tol is not None:
        try:
            tolerance = float(raw_tol)
        except (TypeError, ValueError):
            return jsonify({"error": "tolerance must be a number"}), 400
        tolerance = max(0.3, min(0.7, tolerance))
        from app.services.recognition_service import get_recognizer
        get_recognizer().tolerance = tolerance
        updates["tolerance"] = tolerance

    raw_lm = data.get("show_landmarks")
    if raw_lm is not None:
        from app.services.recognition_service import get_recognizer
        get_recognizer().show_landmarks = bool(raw_lm)
        updates["show_landmarks"] = bool(raw_lm)

    if not updates:
        return jsonify({"error": "No recognised settings provided"}), 400

    return jsonify({"message": "Settings updated.", "applied": updates})
