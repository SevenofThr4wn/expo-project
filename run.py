import os
import logging
import colorlog
from flask import Flask, render_template, session, redirect, request

from app.routes.enroll import enroll_bp
from app.routes.recognize import recognize_bp
from app.routes.auth import auth_bp
from app.routes.faces import faces_bp
from app.routes.logs import logs_bp
from app.routes.train import train_bp
from app.routes.cameras import cameras_bp

LOG_FORMAT = "%(log_color)s [%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"

handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    LOG_FORMAT))

logger = logging.getLogger(__name__)
logger.addHandler(handler)

# Configures werkzeug logger
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.addHandler(handler)
werkzeug_logger.setLevel(logging.INFO)
werkzeug_logger.handlers
werkzeug_logger.propagate = False


app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
logger.info("App Init: Flask App Initialized")

# Configures other loggers
fr_models_logger = logging.getLogger("face_recognition_models")
fr_models_logger.setLevel(logging.WARNING)



# Registers all Flask route blueprints
app.register_blueprint(enroll_bp)
app.register_blueprint(recognize_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(faces_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(train_bp)
app.register_blueprint(cameras_bp)

_PUBLIC = {"auth.face_login", "login", "static"}
_AUTHORIZED_PATH = "app/data/authorized_faces"


def _has_authorized_faces():
    """Return True only if at least one image exists inside authorized_faces/."""
    if not os.path.isdir(_AUTHORIZED_PATH):
        return False
    for entry in os.listdir(_AUTHORIZED_PATH):
        person_dir = os.path.join(_AUTHORIZED_PATH, entry)
        if os.path.isdir(person_dir):
            for f in os.listdir(person_dir):
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    return True
    return False


@app.before_request
def protect_routes():
    if request.endpoint not in _PUBLIC and "user" not in session:
        if not _has_authorized_faces():
            session["user"] = "admin"
            return
        return redirect("/login")


@app.route('/')
def index():
    return render_template("index.html", user=session.get("user", ""))


@app.route('/login')
def login():
    if not _has_authorized_faces():
        session["user"] = "admin"
        return redirect("/")
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
    logger.info("Debug Mode Active")
