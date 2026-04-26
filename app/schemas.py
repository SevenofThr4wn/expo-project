"""
Marshmallow schemas for request validation and response serialisation.
All schemas use EXCLUDE so unknown fields are silently ignored.
"""
from marshmallow import Schema, fields, validate, EXCLUDE


class _Base(Schema):
    class Meta:
        unknown = EXCLUDE


class LoginSchema(_Base):
    username = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    password = fields.Str(required=True, validate=validate.Length(min=1))
    remember = fields.Bool(load_default=False)


class CreateUserSchema(_Base):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=64))
    password = fields.Str(required=True, validate=validate.Length(min=6))
    role = fields.Str(
        load_default="operator",
        validate=validate.OneOf(["admin", "operator", "viewer"]),
    )
    email = fields.Email(load_default=None, allow_none=True)


class UpdateUserSchema(_Base):
    role = fields.Str(validate=validate.OneOf(["admin", "operator", "viewer"]))
    password = fields.Str(validate=validate.Length(min=6))
    email = fields.Email(allow_none=True)
    is_active = fields.Bool()


class SettingsSchema(_Base):
    tolerance = fields.Float(validate=validate.Range(min=0.3, max=0.7))
    show_landmarks = fields.Bool()
    detection_scale = fields.Float(validate=validate.Range(min=0.25, max=1.0))
    log_cooldown = fields.Int(validate=validate.Range(min=1, max=300))


class CameraSelectSchema(_Base):
    index = fields.Int(required=True, validate=validate.Range(min=0, max=9))


class LogFilterSchema(_Base):
    limit = fields.Int(load_default=100, validate=validate.Range(min=1, max=500))
    offset = fields.Int(load_default=0, validate=validate.Range(min=0))
    name = fields.Str(load_default="")


class FaceGroupSchema(_Base):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    colour = fields.Str(load_default="#6366f1", validate=validate.Regexp(r"^#[0-9a-fA-F]{6}$"))


class CreateAPIKeySchema(_Base):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=64))


class SettingsProfileSchema(_Base):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    config = fields.Dict(load_default=dict)
