import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user
from marshmallow import ValidationError

from app.auth.decorators import admin_required
from app.extensions import db
from app.models.user import User, Role
from app.schemas import CreateUserSchema, UpdateUserSchema

logger = logging.getLogger(__name__)

users_bp = Blueprint("users_api", __name__, url_prefix="/api")

_create_schema = CreateUserSchema()
_update_schema = UpdateUserSchema()


@users_bp.route("/users")
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [u.to_dict() for u in users]})


@users_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    try:
        data = _create_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.messages}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 409

    user = User(username=data["username"], role=data["role"], email=data.get("email"))
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    logger.info("Admin '%s' created user '%s'", current_user.username, data["username"])
    return jsonify({"message": f"User '{data['username']}' created.", "user": user.to_dict()}), 201


@users_bp.route("/users/<int:user_id>", methods=["PATCH"])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        data = _update_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.messages}), 400

    if not data:
        return jsonify({"error": "No valid fields provided"}), 400

    if "role" in data:
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = data["is_active"]
    if "password" in data:
        user.set_password(data["password"])
    if "email" in data:
        user.email = data["email"]

    db.session.commit()
    logger.info("Admin '%s' updated user '%s'", current_user.username, user.username)
    return jsonify({"message": "User updated.", "user": user.to_dict()})


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({"error": "Cannot delete your own account"}), 400

    username = user.username
    db.session.delete(user)
    db.session.commit()
    logger.info("Admin '%s' deleted user '%s'", current_user.username, username)
    return jsonify({"message": f"User '{username}' deleted."})
