import os
from flask import Flask, render_template, session, redirect, request

from app.routes.enroll import enroll_bp
from app.routes.recognize import recognize_bp
from app.routes.auth import auth_bp
from app.routes.faces import faces_bp
from app.routes.logs import logs_bp

app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

app.register_blueprint(enroll_bp)
app.register_blueprint(recognize_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(faces_bp)
app.register_blueprint(logs_bp)

_PUBLIC = {"auth.face_login", "login", "static"}


@app.before_request
def protect_routes():
    if request.endpoint not in _PUBLIC and "user" not in session:
        return redirect("/login")


@app.route('/')
def index():
    return render_template("index.html", user=session.get("user", ""))


@app.route('/login')
def login():
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
