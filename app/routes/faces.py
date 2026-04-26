import logging
from flask import Blueprint, jsonify

from app.auth.decorators import api_login_required, role_required
from app.extensions import db, cache
from app.models.face_encoding import FaceEncoding
from app.models.user import Role
from app.services.recognition_service import get_recognizer

logger = logging.getLogger(__name__)

faces_bp = Blueprint("faces_api", __name__, url_prefix="/api")

FACES_CACHE_KEY = "api_faces_list"


@faces_bp.route("/faces")
@api_login_required
@cache.cached(timeout=30, key_prefix=FACES_CACHE_KEY)
def list_faces():
    rows = (
        db.session.query(FaceEncoding.name, db.func.count(FaceEncoding.id).label("count"))
        .group_by(FaceEncoding.name)
        .all()
    )
    return jsonify({"faces": [{"name": r.name, "count": r.count} for r in rows]})


@faces_bp.route("/faces/<name>", methods=["DELETE"])
@role_required(Role.ADMIN, Role.OPERATOR)
def delete_face(name):
    deleted = FaceEncoding.query.filter_by(name=name).delete()
    if not deleted:
        return jsonify({"error": f"No encodings found for '{name}'"}), 404
    db.session.commit()
    get_recognizer().refresh_data()
    cache.delete(FACES_CACHE_KEY)
    cache.delete("api_stats")
    logger.info("Deleted %d encodings for '%s'", deleted, name)
    return jsonify({"message": f"'{name}' removed ({deleted} encodings deleted)"})
