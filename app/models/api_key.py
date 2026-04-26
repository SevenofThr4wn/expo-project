import hashlib
import secrets
from datetime import datetime
from app.extensions import db


class APIKey(db.Model):
    __tablename__ = "api_keys"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(64), nullable=False)
    key_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    prefix = db.Column(db.String(12), nullable=False)   # first chars shown in UI
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def generate():
        """Return (raw_key, key_hash, prefix). Store hash; show raw_key once."""
        raw = "fid_" + secrets.token_urlsafe(32)
        h = hashlib.sha256(raw.encode()).hexdigest()
        prefix = raw[:12]
        return raw, h, prefix

    @staticmethod
    def hash_key(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "prefix": self.prefix,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
