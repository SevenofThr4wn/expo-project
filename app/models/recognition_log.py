from datetime import datetime
from app.extensions import db


class RecognitionLog(db.Model):
    __tablename__ = "recognition_logs"

    id = db.Column(db.Integer, primary_key=True)
    face_name = db.Column(db.String(64), nullable=False, index=True)
    confidence = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.face_name,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
        }
