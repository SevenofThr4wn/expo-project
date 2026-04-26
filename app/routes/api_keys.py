import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user
from marshmallow import ValidationError

from app.auth.decorators import api_login_required
from app.extensions import db
from app.models.api_key import APIKey
from app.schemas import CreateAPIKeySchema

logger = logging.getLogger(__name__)

api_keys_bp = Blueprint("api_keys_api", __name__, url_prefix="/api")

_schema = CreateAPIKeySchema()


@api_keys_bp.route("/keys")
@api_login_required
def list_keys():
    keys = APIKey.query.filter_by(user_id=current_user.id).order_by(APIKey.created_at.desc()).all()
    return jsonify({"keys": [k.to_dict() for k in keys]})


@api_keys_bp.route("/keys", methods=["POST"])
@api_login_required
def create_key():
    try:
        data = _schema.load(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.messages}), 400

    raw_key, key_hash, prefix = APIKey.generate()
    key = APIKey(
        user_id=current_user.id,
        name=data["name"],
        key_hash=key_hash,
        prefix=prefix,
    )
    db.session.add(key)
    db.session.commit()
    logger.info("API key '%s' created for user '%s'", data["name"], current_user.username)

    result = key.to_dict()
    result["raw_key"] = raw_key
    return jsonify({
        "message": "Key created. Save it now — it will not be shown again.",
        "key": result,
    }), 201


@api_keys_bp.route("/keys/<int:key_id>/toggle", methods=["PATCH"])
@api_login_required
def toggle_key(key_id):
    key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first_or_404()
    key.is_active = not key.is_active
    db.session.commit()
    state = "activated" if key.is_active else "deactivated"
    return jsonify({"message": f"Key {state}.", "key": key.to_dict()})


@api_keys_bp.route("/keys/<int:key_id>", methods=["DELETE"])
@api_login_required
def delete_key(key_id):
    key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first_or_404()
    name = key.name
    db.session.delete(key)
    db.session.commit()
    logger.info("API key '%s' revoked by user '%s'", name, current_user.username)
    return jsonify({"message": f"Key '{name}' revoked."})
