import csv
import io
import logging
from datetime import date

import openpyxl
from flask import Blueprint, jsonify, make_response, request

from app.auth.decorators import api_login_required, role_required
from app.extensions import db, cache
from app.models.face_encoding import FaceEncoding
from app.models.recognition_log import RecognitionLog
from app.models.user import Role
from app.services.camera_service import camera_is_connected

logger = logging.getLogger(__name__)

logs_bp = Blueprint("logs_api", __name__, url_prefix="/api")

STATS_CACHE_KEY = "api_stats"


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
    cache.delete(STATS_CACHE_KEY)
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


@logs_bp.route("/person/<name>")
@api_login_required
def person_stats(name):
    from app.models.face_encoding import FaceEncoding

    q = RecognitionLog.query.filter_by(face_name=name)
    total = q.count()
    if not total:
        return jsonify({"error": f"No recognition history found for '{name}'"}), 404

    avg_conf = db.session.query(
        db.func.avg(RecognitionLog.confidence)
    ).filter_by(face_name=name).scalar() or 0

    first = (
        RecognitionLog.query.filter_by(face_name=name)
        .order_by(RecognitionLog.timestamp.asc())
        .first()
    )
    last = q.order_by(RecognitionLog.timestamp.desc()).first()
    encoding_count = FaceEncoding.query.filter_by(name=name).count()
    recent = q.order_by(RecognitionLog.timestamp.desc()).limit(20).all()

    return jsonify({
        "name": name,
        "total_recognitions": total,
        "avg_confidence": round(float(avg_conf), 1),
        "encoding_count": encoding_count,
        "first_seen": first.timestamp.isoformat(),
        "last_seen": last.timestamp.isoformat(),
        "recent_events": [e.to_dict() for e in recent],
    })


@logs_bp.route("/stats/heatmap")
@api_login_required
@cache.cached(timeout=60, key_prefix="api_heatmap")
def get_heatmap():
    """7×24 matrix of recognition count by (day_of_week, hour) over the last 30 days."""
    rows = db.session.execute(
        db.text(
            "SELECT strftime('%w', timestamp) as dow, strftime('%H', timestamp) as hour, COUNT(*) as cnt "
            "FROM recognition_logs "
            "WHERE timestamp >= datetime('now', '-30 days') "
            "GROUP BY dow, hour"
        )
    ).fetchall()
    matrix = [[0] * 24 for _ in range(7)]
    for r in rows:
        matrix[int(r[0])][int(r[1])] = r[2]
    return jsonify({"matrix": matrix, "days": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]})


@logs_bp.route("/logs/export/xlsx")
@api_login_required
def export_logs_xlsx():
    events = RecognitionLog.query.order_by(RecognitionLog.timestamp.desc()).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Recognition Log"
    ws.append(["ID", "Name", "Confidence (%)", "Timestamp"])
    for e in events:
        ws.append([e.id, e.face_name, e.confidence, e.timestamp.isoformat()])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = make_response(buf.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=recognition_log.xlsx"
    resp.headers["Content-Type"] = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return resp


@logs_bp.route("/stats")
@api_login_required
@cache.cached(timeout=10, key_prefix=STATS_CACHE_KEY)
def get_stats():
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
        "camera_connected": camera_is_connected(),
        "hourly": [{"hour": r[0], "count": r[1]} for r in hourly],
        "per_person": [{"name": r[0], "count": r[1]} for r in per_person],
    })
