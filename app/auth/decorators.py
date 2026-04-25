from functools import wraps
from flask import jsonify, redirect, url_for
from flask_login import current_user


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated


def api_login_required(f):
    """For JSON API endpoints — returns 401 instead of a redirect."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                from flask import request
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("auth.login_page"))
            if current_user.role not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    from app.models.user import Role
    return role_required(Role.ADMIN)(f)
