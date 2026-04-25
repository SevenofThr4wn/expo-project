import csv
import io
import logging
from datetime import date

from flask import Blueprint, jsonify, make_response, request

from app.auth.decorators import api_login_required, role_required
from app.extensions import db
from app.models.face_encoding import FaceEncoding
from app.models.recognition_log import RecognitionLog
from app.models.user import Role
from app.services.camera_service import get_camera

logger = logging.getLogger(__name__)

logs_bp = Blueprint("logs_api", __name__, url_prefix="/api")


@logs_bp.route("/logs")
@api_login_required
def get_logs():
    limit = min(int(request.args.get("limit", 100)), 500)
    offset = int(request.args.get("offset", 0))
    name_filter = request.args.get("name", "").strip()

    q = RecognitionLog.query.order_by(RecognitionLog.timestamp.desc())
    if name_filter:
        q = q.filter(RecognitionLog.face_name.ilike(f"%{name_filter}%"))

    total = q.count()
    events = q.offset(offset).limit(limit).all()
    return jsonify({"events": [e.to_dict() for e in events], "total": total})


@logs_bp.route("/logs", methods=["DELETE"])
@role_required(Role.ADMIN)
def clear_logs():
    count = RecognitionLog.query.delete()
    db.session.commit()
    logger.info("Cleared %d recognition log entries", count)
    return jsonify({"message": f"Cleared {count} log entries."})


@logs_bp.route("/logs/export")
@api_login_required
def export_logs():
    events = RecognitionLog.query.order_by(RecognitionLog.timestamp.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "confidence", "timestamp"])
    for e in events:
        writer.writerow([e.id, e.face_name, e.confidence, e.timestamp.isoformat()])
    resp = make_response(output.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=recognition_log.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp


@logs_bp.route("/stats")
@api_login_required
def get_stats():
    cam = get_camera()
    today = date.today()
    today_count = RecognitionLog.query.filter(
        db.func.date(RecognitionLog.timestamp) == today
    ).count()
    enrolled = db.session.query(
        db.func.count(db.distinct(FaceEncoding.name))
    ).scalar()

    # Per-hour counts for the last 24 h (SQLite-compatible)
    hourly = db.session.execute(
        db.text(
            "SELECT strftime('%H', timestamp) as hour, COUNT(*) as cnt "
            "FROM recognition_logs "
            "WHERE timestamp >= datetime('now', '-24 hours') "
            "GROUP BY hour ORDER BY hour"
        )
    ).fetchall()

    # Per-person counts for chart
    per_person = (
        db.session.query(RecognitionLog.face_name, db.func.count().label("cnt"))
        .group_by(RecognitionLog.face_name)
        .order_by(db.func.count().desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "enrolled_count": enrolled,
        "today_recognitions": today_count,
        "camera_connected": cam.connected,
        "hourly": [{"hour": r[0], "count": r[1]} for r in hourly],
        "per_person": [{"name": r[0], "count": r[1]} for r in per_person],
    })
