import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.auth.decorators import api_login_required, admin_required
from app.extensions import db
from app.models.notification import Notification

logger = logging.getLogger(__name__)

notifications_bp = Blueprint("notifications_api", __name__, url_prefix="/api")


@notifications_bp.route("/notifications")
@api_login_required
def list_notifications():
    limit = min(int(request.args.get("limit", 50)), 200)
    q = Notification.query.filter(
        db.or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None),
        )
    ).order_by(Notification.is_read.asc(), Notification.created_at.desc())

    total = q.count()
    unread = Notification.query.filter(
        db.or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None),
        ),
        Notification.is_read == False,
    ).count()
    items = q.limit(limit).all()
    return jsonify({"notifications": [n.to_dict() for n in items], "total": total, "unread": unread})


@notifications_bp.route("/notifications/<int:notif_id>/read", methods=["PATCH"])
@api_login_required
def mark_read(notif_id):
    notif = Notification.query.filter(
        Notification.id == notif_id,
        db.or_(Notification.user_id == current_user.id, Notification.user_id.is_(None)),
    ).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({"message": "Marked as read."})


@notifications_bp.route("/notifications/read-all", methods=["POST"])
@api_login_required
def mark_all_read():
    Notification.query.filter(
        db.or_(Notification.user_id == current_user.id, Notification.user_id.is_(None)),
        Notification.is_read == False,
    ).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"message": "All notifications marked as read."})


@notifications_bp.route("/notifications", methods=["DELETE"])
@api_login_required
def clear_notifications():
    count = Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"message": f"Cleared {count} notifications."})


@notifications_bp.route("/notifications", methods=["POST"])
@admin_required
def create_notification():
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    body = (data.get("body") or "").strip() or None
    ntype = data.get("type", "info")
    if ntype not in ("info", "success", "warn", "alert"):
        ntype = "info"
    user_id = data.get("user_id") or None

    notif = Notification(title=title, body=body, type=ntype, user_id=user_id)
    db.session.add(notif)
    db.session.commit()
    logger.info("Notification '%s' created by '%s'", title, current_user.username)
    return jsonify({"message": "Notification created.", "notification": notif.to_dict()}), 201
