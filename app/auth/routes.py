import logging
from datetime import datetime

import numpy as np
from app.services.face_engine import get_face_app
from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from flask_login import login_user, logout_user, current_user
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.user import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        logger.warning("Failed login attempt for '%s'", username)
        return jsonify({"error": "Invalid username or password"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is disabled"}), 403

    login_user(user, remember=bool(data.get("remember", False)))
    user.last_login = datetime.utcnow()
    db.session.commit()

    logger.info("User '%s' logged in", username)
    return jsonify({"success": True, "user": user.to_dict()})


@auth_bp.route("/face-login", methods=["GET"])
def face_login():
    """Match a live camera frame against enrolled face encodings."""
    
    from app.services.camera_service import get_camera
    from app.models.face_encoding import FaceEncoding

    camera = get_camera()
    if not camera.connected:
        camera.start()
    
    frame = camera.read()
    if frame is None:
        return jsonify({"error": "Camera unavailable"}, 500)
    
    face_app = get_face_app()
    faces = face_app.get(frame)

    if not faces:
        return jsonify({"success": False, "message": "no face detected"})
    
    rows = FaceEncoding.query.all()
    if not rows:
        return jsonify({"success": False, "message": "No faces enrolled"})
    
    known_embeddings = np.array([r.encoding for r in rows])

    query_emb = faces[0].embedding

    query_emb = query_emb / np.linalg.norm(query_emb)
    known_embeddings = known_embeddings / np.linalg.norm(known_embeddings, axis=1, keepdims=True)

    similarities = np.dot(known_embeddings, query_emb)

    best_idx = int(np.argmax(similarities))
    best_score = float(similarities([best_idx]))

    if best_score > 0.5:
        matched = rows[best_idx]

        if matched.user_id:
            user = User.query.get(matched.user_id)

            if user and user.is_active:
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()

                logger.info("Face Login %s (%.3f)", user.username, best_score)
                return jsonify({
                    "success": True,
                    "user": user.to_dict()
                })
        logger.info("Face login (unlinked): %s", matched.name)
        return jsonify({
            "success": True,
            "name": matched.name
        })
    return jsonify({
        "success": False,
        "message": "Face not recognised"
    })

@auth_bp.route("/logout")
def logout():
    username = current_user.username if current_user.is_authenticated else "unknown"
    logout_user()
    logger.info("User '%s' logged out", username)
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/token", methods=["POST"])
def get_token():
    """Issue a JWT for CLI / API key usage."""
    data = request.get_json(silent=True) or {}
    user = User.query.filter_by(username=data.get("username", "").strip()).first()

    if not user or not user.check_password(data.get("password", "")):
        return jsonify({"error": "Invalid credentials"}), 401
    if not user.is_active:
        return jsonify({"error": "Account disabled"}), 403

    token = create_access_token(
        identity=str(user.id), additional_claims={"role": user.role}
    )
    return jsonify({"access_token": token, "user": user.to_dict()})
