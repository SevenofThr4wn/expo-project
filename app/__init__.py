import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from colorlog import ColoredFormatter

from app.extensions import db, login_manager, bcrypt, jwt, migrate, socketio


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

    for noisy in ("werkzeug", "face_recognition_models", "socketio", "engineio"):
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


def create_app():
    from dotenv import load_dotenv

    load_dotenv()
    _setup_logging()

    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///faceid.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", app.config["SECRET_KEY"])
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False
    app.config["RECOGNITION_TOLERANCE"] = float(
        os.getenv("RECOGNITION_TOLERANCE", 0.5)
    )

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")

    # Register models so Alembic/SQLAlchemy sees them
    from app.models import User, FaceEncoding, RecognitionLog  # noqa: F401

    # Blueprints
    from app.auth import auth_bp
    from app.routes.pages import pages_bp
    from app.routes.stream import stream_bp
    from app.routes.faces import faces_bp
    from app.routes.enroll import enroll_bp
    from app.routes.logs import logs_bp
    from app.routes.cameras import cameras_bp
    from app.routes.settings import settings_bp
    from app.routes.users import users_bp

    for bp in [
        auth_bp, pages_bp, stream_bp, faces_bp, enroll_bp,
        logs_bp, cameras_bp, settings_bp, users_bp,
    ]:
        app.register_blueprint(bp)

    with app.app_context():
        db.create_all()

    _ensure_default_admin(app)

    # Pass app reference to recognition service for background-thread DB access
    from app.services.recognition_service import init_recognition_service
    init_recognition_service(app)

    return app
