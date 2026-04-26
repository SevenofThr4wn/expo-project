import logging
from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.auth.decorators import role_required
from app.models.user import Role
from app.schemas import SettingsSchema

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings_api", __name__, url_prefix="/api")

_schema = SettingsSchema()


@settings_bp.route("/settings", methods=["POST"])
@role_required(Role.ADMIN, Role.OPERATOR)
def update_settings():
    try:
        data = _schema.load(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.messages}), 400

    if not data:
        return jsonify({"error": "No recognised settings provided"}), 400

    from app.services.recognition_service import get_recognizer
    svc = get_recognizer()
    updates = {}

    if "tolerance" in data:
        svc.tolerance = data["tolerance"]
        updates["tolerance"] = data["tolerance"]

    if "show_landmarks" in data:
        svc.show_landmarks = data["show_landmarks"]
        updates["show_landmarks"] = data["show_landmarks"]

    if "detection_scale" in data:
        svc.detection_scale = data["detection_scale"]
        updates["detection_scale"] = data["detection_scale"]

    if "log_cooldown" in data:
        svc._log_cooldown = data["log_cooldown"]
        updates["log_cooldown"] = data["log_cooldown"]

    logger.info("Settings updated: %s", updates)
    return jsonify({"message": "Settings updated.", "applied": updates})
