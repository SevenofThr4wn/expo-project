import logging
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import current_user
from marshmallow import ValidationError

from app.auth.decorators import role_required
from app.extensions import db
from app.models.settings_profile import SettingsProfile
from app.models.user import Role
from app.schemas import SettingsProfileSchema

logger = logging.getLogger(__name__)

profiles_bp = Blueprint("profiles_api", __name__, url_prefix="/api")

_schema = SettingsProfileSchema()


@profiles_bp.route("/profiles")
@role_required(Role.ADMIN, Role.OPERATOR)
def list_profiles():
    profiles = SettingsProfile.query.order_by(SettingsProfile.name).all()
    return jsonify({"profiles": [p.to_dict() for p in profiles]})


@profiles_bp.route("/profiles", methods=["POST"])
@role_required(Role.ADMIN, Role.OPERATOR)
def create_profile():
    try:
        data = _schema.load(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.messages}), 400

    if SettingsProfile.query.filter_by(name=data["name"]).first():
        return jsonify({"error": "A profile with that name already exists"}), 409

    from app.services.recognition_service import get_recognizer
    svc = get_recognizer()

    profile = SettingsProfile(name=data["name"])
    profile.set_config({
        "tolerance": svc.tolerance,
        "show_landmarks": svc.show_landmarks,
        "detection_scale": svc.detection_scale,
        "log_cooldown": svc._log_cooldown,
        **data.get("config", {}),
    })
    db.session.add(profile)
    db.session.commit()
    logger.info("Settings profile '%s' created by '%s'", profile.name, current_user.username)
    return jsonify({"message": "Profile created.", "profile": profile.to_dict()}), 201


@profiles_bp.route("/profiles/<int:profile_id>", methods=["DELETE"])
@role_required(Role.ADMIN, Role.OPERATOR)
def delete_profile(profile_id):
    profile = SettingsProfile.query.get_or_404(profile_id)
    name = profile.name
    db.session.delete(profile)
    db.session.commit()
    logger.info("Settings profile '%s' deleted by '%s'", name, current_user.username)
    return jsonify({"message": f"Profile '{name}' deleted."})


@profiles_bp.route("/profiles/<int:profile_id>/apply", methods=["POST"])
@role_required(Role.ADMIN, Role.OPERATOR)
def apply_profile(profile_id):
    profile = SettingsProfile.query.get_or_404(profile_id)
    cfg = profile.get_config()

    from app.services.recognition_service import get_recognizer
    svc = get_recognizer()
    applied = {}

    if "tolerance" in cfg:
        svc.tolerance = float(cfg["tolerance"])
        applied["tolerance"] = svc.tolerance
    if "show_landmarks" in cfg:
        svc.show_landmarks = bool(cfg["show_landmarks"])
        applied["show_landmarks"] = svc.show_landmarks
    if "detection_scale" in cfg:
        svc.detection_scale = float(cfg["detection_scale"])
        applied["detection_scale"] = svc.detection_scale
    if "log_cooldown" in cfg:
        svc._log_cooldown = int(cfg["log_cooldown"])
        applied["log_cooldown"] = svc._log_cooldown

    profile.is_active = True
    SettingsProfile.query.filter(SettingsProfile.id != profile_id).update({"is_active": False})
    db.session.commit()

    logger.info("Profile '%s' applied by '%s': %s", profile.name, current_user.username, applied)
    return jsonify({"message": f"Profile '{profile.name}' applied.", "applied": applied})
