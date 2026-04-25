import logging
import face_recognition as fr
from flask import Blueprint, jsonify, request

from app.auth.decorators import role_required
from app.extensions import db
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

    img = fr.load_image_file(file)
    encodings = fr.face_encodings(img)

    if not encodings:
        return jsonify({"error": "No face detected in image. Try better lighting or a clearer angle."}), 400

    # Link to a user account if name matches a username
    user = User.query.filter_by(username=name).first()

    fe = FaceEncoding(name=name, user_id=user.id if user else None)
    fe.encoding = encodings[0]
    db.session.add(fe)
    db.session.commit()

    get_recognizer().refresh_data()
    logger.info("Enrolled face for '%s' (user_id=%s)", name, fe.user_id)
    return jsonify({"message": f"'{name}' enrolled successfully."})
