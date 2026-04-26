import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from colorlog import ColoredFormatter

from app.extensions import db, login_manager, bcrypt, jwt, migrate, socketio, cache, compress, mail


def _setup_logging():
    fmt = "%(log_color)s[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter(fmt))

    file_fmt = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=5_000_000, backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(file_fmt))
    file_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    for noisy in ("werkzeug", "socketio", "engineio", "insightface", "onnxruntime"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _ensure_default_admin(app):
    from app.models import User, Role

    with app.app_context():
        if User.query.count() == 0:
            admin = User(username="admin", role=Role.ADMIN, is_active=True)
            admin.set_password(os.getenv("ADMIN_PASSWORD", "admin"))
            db.session.add(admin)
            db.session.commit()
            logging.getLogger(__name__).info(
                "Default admin user created (username: admin)"
            )


def _configure_sqlite_pragmas(app):
    """Enable WAL mode and performance pragmas for SQLite connections."""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if "sqlite" not in uri:
        return
    from sqlalchemy import event

    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def _set_pragmas(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")      # concurrent readers + one writer
            cur.execute("PRAGMA cache_size=-64000")     # 64 MB page cache
            cur.execute("PRAGMA synchronous=NORMAL")    # safe + faster than FULL
            cur.execute("PRAGMA busy_timeout=10000")    # 10 s before SQLITE_BUSY
            cur.close()

    logging.getLogger(__name__).info("SQLite WAL mode + pragmas configured")


def _compile_scss(app):
    """Compile SCSS only in development using Dart Sass."""
    if not app.debug:
        return

    import subprocess
    import os

    scss_entry = os.path.join(app.static_folder, "scss", "styles.scss")
    css_output = os.path.join(app.static_folder, "css", "styles.css")

    try:
        subprocess.run(
            ["sass", scss_entry, css_output],
            check=True
        )
    except Exception as exc:
        print(f"SCSS compile failed: {exc}")


def create_app():
    from dotenv import load_dotenv

    load_dotenv()
    _setup_logging()

    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Core config ───────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///faceid.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", app.config["SECRET_KEY"])
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False
    app.config["FACE_RECOGNITION_THRESHOLD"] = float(
        os.getenv("FACE_RECOGNITION_THRESHOLD", 0.6)
    )

    # ── Flask-Caching ─────────────────────────────────────────────────────────
    app.config["CACHE_TYPE"] = "SimpleCache"
    app.config["CACHE_DEFAULT_TIMEOUT"] = 30

    # ── Flask-Compress ────────────────────────────────────────────────────────
    app.config["COMPRESS_REGISTER"] = True
    app.config["COMPRESS_LEVEL"] = 6          # gzip level 1-9
    app.config["COMPRESS_MIN_SIZE"] = 500     # bytes before compressing

    # ── Flask-Mail ────────────────────────────────────────────────────────────
    app.config["MAIL_SERVER"]   = os.getenv("MAIL_SERVER", "")
    app.config["MAIL_PORT"]     = int(os.getenv("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"]  = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", "faceid@localhost")

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="gevent")
    cache.init_app(app)
    compress.init_app(app)
    mail.init_app(app)

    # ── SQLite performance pragmas ─────────────────────────────────────────────
    _configure_sqlite_pragmas(app)

    # ── Register ALL models so Alembic/SQLAlchemy sees them ───────────────────
    from app.models import (  # noqa: F401
        User, FaceEncoding, RecognitionLog,
        FaceGroup, FaceGroupMember,
        Notification, AuditLog, APIKey, SettingsProfile,
    )

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.auth import auth_bp
    from app.routes.pages import pages_bp
    from app.routes.stream import stream_bp
    from app.routes.faces import faces_bp
    from app.routes.enroll import enroll_bp
    from app.routes.logs import logs_bp
    from app.routes.cameras import cameras_bp
    from app.routes.settings import settings_bp
    from app.routes.users import users_bp
    from app.routes.groups import groups_bp
    from app.routes.notifications import notifications_bp
    from app.routes.audit import audit_bp
    from app.routes.api_keys import api_keys_bp
    from app.routes.health import health_bp
    from app.routes.profiles import profiles_bp

    for bp in [
        auth_bp, pages_bp, stream_bp, faces_bp, enroll_bp,
        logs_bp, cameras_bp, settings_bp, users_bp,
        groups_bp, notifications_bp, audit_bp, api_keys_bp,
        health_bp, profiles_bp,
    ]:
        app.register_blueprint(bp)

    with app.app_context():
        db.create_all()

    _ensure_default_admin(app)

    # ── SCSS → CSS ────────────────────────────────────────────────────────────
    _compile_scss(app)

    # ── Recognition service ───────────────────────────────────────────────────
    from app.services.recognition_service import init_recognition_service
    init_recognition_service(app)

    # ── Scheduler ─────────────────────────────────────────────────────────────
    from app.services.scheduler_service import init_scheduler
    init_scheduler(app)

    return app
