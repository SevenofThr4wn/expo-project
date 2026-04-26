import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.auth.decorators import admin_required
from app.extensions import db
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

audit_bp = Blueprint("audit_api", __name__, url_prefix="/api")


def record_audit(action: str, actor_name: str = None, actor_id: int = None,
                 target_type: str = None, target_id=None, detail: dict = None, ip: str = None):
    """Write one audit log row. Silently swallows errors to avoid breaking callers."""
    try:
        entry = AuditLog(
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            ip_address=ip,
        )
        if detail:
            entry.set_detail(detail)
        db.session.add(entry)
        db.session.commit()
    except Exception as exc:
        logger.error("Audit log write failed: %s", exc)
        try:
            db.session.rollback()
        except Exception:
            pass


@audit_bp.route("/audit")
@admin_required
def list_audit():
    limit = min(int(request.args.get("limit", 100)), 500)
    offset = int(request.args.get("offset", 0))
    action_filter = request.args.get("action", "").strip()
    actor_filter = request.args.get("actor", "").strip()

    q = AuditLog.query.order_by(AuditLog.timestamp.desc())
    if action_filter:
        q = q.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    if actor_filter:
        q = q.filter(AuditLog.actor_name.ilike(f"%{actor_filter}%"))

    total = q.count()
    entries = q.offset(offset).limit(limit).all()
    return jsonify({"entries": [e.to_dict() for e in entries], "total": total})


@audit_bp.route("/audit", methods=["DELETE"])
@admin_required
def clear_audit():
    count = AuditLog.query.delete()
    db.session.commit()
    logger.info("Audit log cleared (%d entries) by '%s'", count, current_user.username)
    return jsonify({"message": f"Cleared {count} audit entries."})
