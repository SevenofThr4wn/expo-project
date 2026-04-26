import json
from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Denormalised so the record survives user deletion
    actor_name = db.Column(db.String(64), nullable=True)
    # Dot-namespaced action, e.g. "user.create", "face.delete", "settings.update"
    action = db.Column(db.String(64), nullable=False, index=True)
    target_type = db.Column(db.String(32), nullable=True)   # "user" | "face" | "setting" …
    target_id = db.Column(db.String(64), nullable=True)
    detail = db.Column(db.Text, nullable=True)              # JSON blob
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def get_detail(self) -> dict:
        if self.detail:
            try:
                return json.loads(self.detail)
            except (ValueError, TypeError):
                return {}
        return {}

    def set_detail(self, data: dict) -> None:
        self.detail = json.dumps(data) if data else None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "detail": self.get_detail(),
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat(),
        }
