from datetime import datetime
from sqlalchemy import UniqueConstraint
from app.extensions import db


class FaceGroup(db.Model):
    __tablename__ = "face_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    slug = db.Column(db.String(80), nullable=False, unique=True, index=True)
    colour = db.Column(db.String(7), nullable=False, default="#6366f1")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    members = db.relationship(
        "FaceGroupMember",
        backref="group",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "colour": self.colour,
            "created_at": self.created_at.isoformat(),
            "member_count": self.members.count(),
        }


class FaceGroupMember(db.Model):
    __tablename__ = "face_group_members"

    id = db.Column(db.Integer, primary_key=True)
    face_name = db.Column(db.String(64), nullable=False, index=True)
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("face_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    added_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("face_name", "group_id", name="uq_face_group_member"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "face_name": self.face_name,
            "group_id": self.group_id,
            "added_at": self.added_at.isoformat(),
        }
