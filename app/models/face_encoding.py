import pickle
from datetime import datetime
from app.extensions import db


class FaceEncoding(db.Model):
    __tablename__ = "face_encodings"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    encoding_blob = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def encoding(self):
        return pickle.loads(self.encoding_blob)

    @encoding.setter
    def encoding(self, value):
        self.encoding_blob = pickle.dumps(value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
        }
