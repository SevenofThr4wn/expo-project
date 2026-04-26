from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

from app.auth.decorators import login_required
from app.models.user import Role

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")


@pages_bp.route("/recognition")
@login_required
def recognition():
    return render_template("recognition.html")


@pages_bp.route("/enroll")
@login_required
def enroll_page():
    return render_template("enroll.html")

@pages_bp.route("/faces")
@login_required
def faces_page():
    return render_template("faces.html")


@pages_bp.route("/logs")
@login_required
def logs_page():
    return render_template("logs.html")


@pages_bp.route("/users")
@login_required
def users_page():
    if current_user.role != Role.ADMIN:
        return redirect(url_for("pages.dashboard"))
    return render_template("users.html")


@pages_bp.route("/settings")
@login_required
def settings_page():
    return render_template("settings.html")


@pages_bp.route("/groups")
@login_required
def groups_page():
    return render_template("groups.html")


@pages_bp.route("/notifications")
@login_required
def notifications_page():
    return render_template("notifications.html")


@pages_bp.route("/audit")
@login_required
def audit_page():
    if current_user.role != Role.ADMIN:
        return redirect(url_for("pages.dashboard"))
    return render_template("audit.html")


@pages_bp.route("/api-keys")
@login_required
def api_keys_page():
    return render_template("api_keys.html")


@pages_bp.route("/health")
@login_required
def health_page():
    if current_user.role not in (Role.ADMIN, Role.OPERATOR):
        return redirect(url_for("pages.dashboard"))
    return render_template("health.html")


@pages_bp.route("/person/<name>")
@login_required
def person_page(name):
    return render_template("person.html")
