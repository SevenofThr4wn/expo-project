from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_caching import Cache
from flask_compress import Compress
from flask_mail import Mail

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()
socketio = SocketIO()
cache = Cache()
compress = Compress()
mail = Mail()

login_manager.login_view = "auth.login_page"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return User.query.get(int(user_id))
