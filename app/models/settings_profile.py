import json
from datetime import datetime
from app.extensions import db


class SettingsProfile(db.Model):
    __tablename__ = "settings_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    config = db.Column(db.Text, nullable=False, default="{}")  # JSON
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def get_config(self) -> dict:
        try:
            return json.loads(self.config) if self.config else {}
        except (ValueError, TypeError):
            return {}

    def set_config(self, data: dict) -> None:
        self.config = json.dumps(data)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "config": self.get_config(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
