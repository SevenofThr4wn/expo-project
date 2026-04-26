import re
import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user
from marshmallow import ValidationError

from app.auth.decorators import api_login_required, role_required
from app.extensions import db
from app.models.face_group import FaceGroup, FaceGroupMember
from app.models.user import Role
from app.schemas import FaceGroupSchema

logger = logging.getLogger(__name__)

groups_bp = Blueprint("groups_api", __name__, url_prefix="/api")

_schema = FaceGroupSchema()


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")[:80]


def _unique_slug(base: str, exclude_id: int = None) -> str:
    slug = base
    n = 1
    while True:
        q = FaceGroup.query.filter_by(slug=slug)
        if exclude_id:
            q = q.filter(FaceGroup.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{base}-{n}"
        n += 1


@groups_bp.route("/groups")
@api_login_required
def list_groups():
    groups = FaceGroup.query.order_by(FaceGroup.name).all()
    return jsonify({"groups": [g.to_dict() for g in groups]})


@groups_bp.route("/groups", methods=["POST"])
@role_required(Role.ADMIN, Role.OPERATOR)
def create_group():
    try:
        data = _schema.load(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.messages}), 400

    if FaceGroup.query.filter_by(name=data["name"]).first():
        return jsonify({"error": "A group with that name already exists"}), 409

    slug = _unique_slug(_slugify(data["name"]))
    group = FaceGroup(name=data["name"], slug=slug, colour=data.get("colour", "#6366f1"))
    db.session.add(group)
    db.session.commit()
    logger.info("Group '%s' created by '%s'", group.name, current_user.username)
    return jsonify({"message": "Group created.", "group": group.to_dict()}), 201


@groups_bp.route("/groups/<int:group_id>", methods=["PATCH"])
@role_required(Role.ADMIN, Role.OPERATOR)
def update_group(group_id):
    group = FaceGroup.query.get_or_404(group_id)
    try:
        data = _schema.load(request.get_json(force=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.messages}), 400

    if "name" in data and data["name"] != group.name:
        if FaceGroup.query.filter(FaceGroup.name == data["name"], FaceGroup.id != group_id).first():
            return jsonify({"error": "Name already in use"}), 409
        group.name = data["name"]
        group.slug = _unique_slug(_slugify(data["name"]), exclude_id=group_id)

    if "colour" in data:
        group.colour = data["colour"]

    db.session.commit()
    return jsonify({"message": "Group updated.", "group": group.to_dict()})


@groups_bp.route("/groups/<int:group_id>", methods=["DELETE"])
@role_required(Role.ADMIN, Role.OPERATOR)
def delete_group(group_id):
    group = FaceGroup.query.get_or_404(group_id)
    name = group.name
    db.session.delete(group)
    db.session.commit()
    logger.info("Group '%s' deleted by '%s'", name, current_user.username)
    return jsonify({"message": f"Group '{name}' deleted."})


@groups_bp.route("/groups/<int:group_id>/members")
@api_login_required
def list_members(group_id):
    group = FaceGroup.query.get_or_404(group_id)
    members = group.members.all()
    return jsonify({"members": [m.to_dict() for m in members]})


@groups_bp.route("/groups/<int:group_id>/members", methods=["POST"])
@role_required(Role.ADMIN, Role.OPERATOR)
def add_member(group_id):
    group = FaceGroup.query.get_or_404(group_id)
    data = request.get_json(force=True) or {}
    face_name = (data.get("face_name") or "").strip()
    if not face_name:
        return jsonify({"error": "face_name is required"}), 400

    if FaceGroupMember.query.filter_by(group_id=group_id, face_name=face_name).first():
        return jsonify({"error": f"'{face_name}' is already in this group"}), 409

    member = FaceGroupMember(group_id=group_id, face_name=face_name)
    db.session.add(member)
    db.session.commit()
    return jsonify({"message": f"'{face_name}' added to '{group.name}'.", "member": member.to_dict()}), 201


@groups_bp.route("/groups/<int:group_id>/members/<face_name>", methods=["DELETE"])
@role_required(Role.ADMIN, Role.OPERATOR)
def remove_member(group_id, face_name):
    member = FaceGroupMember.query.filter_by(group_id=group_id, face_name=face_name).first_or_404()
    db.session.delete(member)
    db.session.commit()
    return jsonify({"message": f"'{face_name}' removed from group."})
