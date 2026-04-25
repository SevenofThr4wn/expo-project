import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.auth.decorators import admin_required
from app.extensions import db
from app.models.user import User, Role

logger = logging.getLogger(__name__)

users_bp = Blueprint("users_api", __name__, url_prefix="/api")


@users_bp.route("/users")
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [u.to_dict() for u in users]})


@users_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", Role.OPERATOR)
    email = data.get("email", "").strip() or None

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if role not in Role.ALL:
        return jsonify({"error": f"Role must be one of: {', '.join(Role.ALL)}"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    user = User(username=username, role=role, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    logger.info("Admin '%s' created user '%s'", current_user.username, username)
    return jsonify({"message": f"User '{username}' created.", "user": user.to_dict()}), 201


@users_bp.route("/users/<int:user_id>", methods=["PATCH"])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if "role" in data:
        if data["role"] not in Role.ALL:
            return jsonify({"error": "Invalid role"}), 400
        user.role = data["role"]
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "password" in data and data["password"]:
        user.set_password(data["password"])
    if "email" in data:
        user.email = data["email"] or None

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
