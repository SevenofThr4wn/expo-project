import logging
from app.services.face_engine import get_face_app
import numpy as np

from flask import Blueprint, jsonify, request

from app.auth.decorators import role_required
from app.extensions import db, cache
from app.models.face_encoding import FaceEncoding
from app.models.user import User, Role
from app.services.recognition_service import get_recognizer

logger = logging.getLogger(__name__)

enroll_bp = Blueprint("enroll_api", __name__, url_prefix="/api")


@enroll_bp.route("/enroll", methods=["POST"])
@role_required(Role.ADMIN, Role.OPERATOR)
def enroll():
    file = request.files.get("image")
    name = request.form.get("name", "").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not file:
        return jsonify({"error": "Image is required"}), 400

    # ── Load image (OpenCV format) ───────────────────
    import cv2
    import numpy as np

    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    # ── InsightFace ─────────────────────────────────
    face_app = get_face_app()
    faces = face_app.get(img)

    if not faces:
        return jsonify({
            "error": "No face detected in image. Try better lighting or a clearer angle."
        }), 400

    # ── Take best face ──────────────────────────────
    face = max(faces, key=lambda f: f.det_score)
    embedding = face.embedding

    # ── Normalise (important for cosine similarity) ─
    embedding = embedding / np.linalg.norm(embedding)

    # ── Link to user if exists ──────────────────────
    user = User.query.filter_by(username=name).first()

    fe = FaceEncoding(
        name=name,
        user_id=user.id if user else None
    )

    fe.encoding = embedding.tolist()  # store as list for DB

    db.session.add(fe)
    db.session.commit()

    # ── refresh recognition cache/system ────────────
    get_recognizer().refresh_data()
    cache.delete("api_faces_list")
    cache.delete("api_stats")

    logger.info("Enrolled face for '%s' (user_id=%s)", name, fe.user_id)

    return jsonify({"message": f"'{name}' enrolled successfully."})