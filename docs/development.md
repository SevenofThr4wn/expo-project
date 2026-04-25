# Development Guide

How to run, extend, and understand the FaceID codebase.

---

- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Application Structure](#application-structure)
  - [Application Factory](#application-factory)
  - [Extensions](#extensions)
  - [Blueprints](#blueprints)
  - [Services](#services)
- [Database](#database)
  - [Models](#models)
  - [Migrations](#migrations)
- [Authentication System](#authentication-system)
  - [Session Auth](#session-auth)
  - [JWT Auth](#jwt-auth)
  - [Route Decorators](#route-decorators)
- [Recognition Pipeline](#recognition-pipeline)
  - [Camera Service](#camera-service)
  - [Recognition Service](#recognition-service)
  - [Event Throttling](#event-throttling)
- [Logging](#logging)
- [Adding a New API Route](#adding-a-new-api-route)
- [Running in Production](#running-in-production)

---

## Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/SevenofThr4wn/expo-project.git
cd expo-project

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux / macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file
cp .env.example .env           # or create it manually — see next section

# 5. Initialise the database (first time only)
flask db upgrade               # or let create_app() call db.create_all()

# 6. Start the development server
python run.py
```

The development server starts with `debug=True` via `socketio.run()`, which enables the Werkzeug reloader and detailed error pages.

---

## Environment Variables

Create a `.env` file in the project root. `python-dotenv` loads it automatically via `create_app()`.

| Variable | Default | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | `change-me-in-production` | Signs session cookies |
| `JWT_SECRET_KEY` | Same as `FLASK_SECRET_KEY` | Signs JWT tokens |
| `DATABASE_URL` | `sqlite:///faceid.db` | SQLAlchemy connection string |
| `ADMIN_PASSWORD` | `admin` | Password for the auto-created admin account |
| `RECOGNITION_TOLERANCE` | `0.5` | Initial face match threshold (0.30–0.70) |

Example `.env`:

```env
FLASK_SECRET_KEY=dev-secret-key-change-me
JWT_SECRET_KEY=dev-jwt-key-change-me
DATABASE_URL=sqlite:///faceid.db
ADMIN_PASSWORD=admin
RECOGNITION_TOLERANCE=0.5
```

---

## Application Structure

### Application Factory

`app/__init__.py` exports `create_app()`. It:

1. Loads `.env` with `python-dotenv`
2. Configures logging (console + rotating file)
3. Creates and configures the Flask app
4. Initialises all extensions
5. Imports models so SQLAlchemy/Alembic sees them
6. Registers all blueprints
7. Calls `db.create_all()` to create tables if they don't exist
8. Calls `_ensure_default_admin()` to seed the first admin account
9. Calls `init_recognition_service(app)` to load face encodings from the DB into memory

```python
from app import create_app
app = create_app()
```

### Extensions

All Flask extension instances live in `app/extensions.py` as module-level singletons. This breaks the circular import that would occur if they were defined in `__init__.py`.

```python
from app.extensions import db, login_manager, bcrypt, jwt, migrate, socketio
```

### Blueprints

Each area of the app is a Flask Blueprint registered in `create_app()`:

| Blueprint variable | URL prefix | File |
|---|---|---|
| `auth_bp` | `/auth` | `app/auth/routes.py` |
| `pages_bp` | (none) | `app/routes/pages.py` |
| `stream_bp` | `/api` | `app/routes/stream.py` |
| `faces_bp` | `/api` | `app/routes/faces.py` |
| `enroll_bp` | `/api` | `app/routes/enroll.py` |
| `logs_bp` | `/api` | `app/routes/logs.py` |
| `cameras_bp` | `/api` | `app/routes/cameras.py` |
| `settings_bp` | `/api` | `app/routes/settings.py` |
| `users_bp` | `/api` | `app/routes/users.py` |

### Services

`app/services/` contains long-lived singleton objects that manage shared resources. They are **not** Flask extensions — they are plain Python classes managed with module-level globals and `threading.Lock`.

| Service | Singleton accessor | Responsibility |
|---|---|---|
| `CameraService` | `get_camera()` | OpenCV capture, MJPEG generation, auto-reconnect |
| `RecognitionService` | `get_recognizer()` | Face matching, bounding-box drawing, recognition logging |

Both singletons are thread-safe. Do not instantiate them directly — always use the accessor functions.

---

## Database

### Models

All models live in `app/models/` and are imported into `app/models/__init__.py`:

| Model | Table | Description |
|---|---|---|
| `User` | `users` | User accounts, bcrypt-hashed passwords, role |
| `FaceEncoding` | `face_encodings` | 128-dimensional face encoding stored as a pickle blob |
| `RecognitionLog` | `recognition_logs` | Recognition events with confidence and timestamp |

**Relationships:**
- `User` → `FaceEncoding`: one-to-many (`cascade="all, delete-orphan"`)
- `FaceEncoding.user_id`: nullable FK to `users.id` (`ON DELETE SET NULL`)
- `RecognitionLog.user_id`: nullable FK to `users.id` (`ON DELETE SET NULL`)

The `FaceEncoding.encoding` property serialises/deserialises the numpy array via `pickle`:

```python
fe = FaceEncoding(name="Alice")
fe.encoding = encodings[0]   # numpy array — serialised to blob automatically
db.session.add(fe)
db.session.commit()
```

### Migrations

Database migrations are managed with Flask-Migrate (Alembic wrapper).

```bash
# Initialise the migrations directory (first time only — already done)
flask db init

# Generate a migration after changing a model
flask db migrate -m "add email to users"

# Apply pending migrations
flask db upgrade

# Roll back the last migration
flask db downgrade
```

The migration scripts live in `migrations/versions/`. Commit them alongside model changes.

> On first run, `create_app()` calls `db.create_all()` as a fallback if no migration history exists. For production, always use `flask db upgrade` so the schema history is tracked.

---

## Authentication System

### Session Auth

Flask-Login manages the session cookie. `app/extensions.py` registers the user loader:

```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

`login_manager.login_view = "auth.login_page"` means unauthenticated users are redirected to `/auth/login` by the standard `@login_required` decorator.

### JWT Auth

Flask-JWT-Extended issues tokens at `POST /auth/token`. Tokens contain the user ID and role as claims:

```python
token = create_access_token(
    identity=str(user.id),
    additional_claims={"role": user.role}
)
```

`JWT_ACCESS_TOKEN_EXPIRES = False` means tokens never expire. Change this to a `timedelta` for production deployments where token rotation matters.

### Route Decorators

All auth decorators live in `app/auth/decorators.py`:

| Decorator | Behaviour when unauthenticated | Behaviour when wrong role |
|---|---|---|
| `@login_required` | Redirect to login page | N/A |
| `@api_login_required` | Return `401 JSON` | N/A |
| `@role_required(*roles)` | Redirect or `401 JSON` (detects API vs browser) | `403 JSON` |
| `@admin_required` | Same as `role_required(Role.ADMIN)` | `403 JSON` |

Use `@api_login_required` on JSON endpoints where a redirect would be wrong. Use `@login_required` only on page routes.

---

## Recognition Pipeline

### Camera Service

`CameraService` (`app/services/camera_service.py`) wraps an OpenCV `VideoCapture` object:

- Targets **30 FPS** (`_TARGET_FPS = 30`, enforced in `generate_frames()`)
- Captures at **1280×720** by default
- On Windows, uses `cv2.CAP_MSMF` (Media Foundation) for lower latency; everywhere else uses `cv2.CAP_ANY`
- If the camera disconnects, `_mark_disconnected()` triggers `_reconnect_loop()` — a daemon thread that retries with exponential back-off (3 s → 6 s → 12 s → … capped at 30 s)
- When no camera frame is available, `generate_frames()` yields a placeholder image rather than blocking

### Recognition Service

`RecognitionService` (`app/services/recognition_service.py`) holds the enrolled encodings in memory and processes camera frames:

1. **`refresh_data()`** — queries `FaceEncoding.query.all()` and replaces `_known_encodings` / `_known_names` under a lock. Called on startup and after any enroll or delete.
2. **`process_frame(frame)`** — runs face detection and matching every **2nd frame** (`_process_every = 2`), reusing the previous results on skipped frames to reduce CPU load.
3. **`_match(encoding, ...)`** — uses `face_recognition.face_distance()` and compares the best distance against `self.tolerance`. Returns `(name, confidence)` where confidence is `int((1 - distance) * 100)`.
4. **`draw_results(frame, results)`** — draws bounding boxes, corner accents, label pills, confidence bars, and optional landmarks onto the frame using OpenCV.

`RecognitionService` is a singleton initialised in `create_app()` via `init_recognition_service(app)`. The `_app` reference allows the background logging thread to push its own Flask app context when writing to the database.

### Event Throttling

To avoid flooding the database and the WebSocket channel, each recognised person is logged at most once every **8 seconds** (`_log_cooldown`). The cooldown is tracked per-name in `_last_logged`, a `dict[str, float]` keyed by name with the last log timestamp.

When a recognition event does pass the cooldown:

1. A `RecognitionLog` row is inserted into the database.
2. A `recognition` WebSocket event is emitted to all connected clients.

---

## Logging

Logging is configured in `_setup_logging()` inside `app/__init__.py`:

- **Console handler** — coloured output via `colorlog.ColoredFormatter`
- **File handler** — `logs/app.log`, rotating at 5 MB, keeping 5 backups

The root logger is set to `INFO`. Noisy libraries (`werkzeug`, `socketio`, `engineio`, `face_recognition_models`) are silenced to `WARNING`.

In every module, get a named logger at the top:

```python
import logging
logger = logging.getLogger(__name__)
```

Use `logger.info()`, `logger.warning()`, `logger.error()` — never `print()`.

---

## Adding a New API Route

1. **Create or pick a blueprint file** in `app/routes/`.

2. **Define the route:**

```python
import logging
from flask import Blueprint, jsonify
from app.auth.decorators import api_login_required

logger = logging.getLogger(__name__)

example_bp = Blueprint("example_api", __name__, url_prefix="/api")

@example_bp.route("/example")
@api_login_required
def example():
    return jsonify({"message": "Hello"})
```

3. **Register the blueprint** in `app/__init__.py`:

```python
from app.routes.example import example_bp
# add example_bp to the list passed to app.register_blueprint(bp)
```

4. **Add the decorator** appropriate for the required role:
   - Any authenticated user: `@api_login_required`
   - Specific roles: `@role_required(Role.ADMIN, Role.OPERATOR)`
   - Admin only: `@admin_required`

---

## Running in Production

The Dockerfile uses **gunicorn** with the **eventlet** worker, which is required for Flask-SocketIO:

```bash
gunicorn -w 1 -k eventlet --worker-connections 100 -b 0.0.0.0:5000 run:app
```

**Important constraints:**
- Use exactly **1 worker** (`-w 1`) — the camera and recognition services are in-process singletons; multiple workers would create multiple independent instances competing for the same camera device.
- The eventlet worker handles concurrent WebSocket and HTTP connections via cooperative multi-tasking, so a single worker can serve many clients simultaneously.
- Set `FLASK_SECRET_KEY`, `JWT_SECRET_KEY`, and `ADMIN_PASSWORD` to strong random values via environment variables before the first run.
- Mount a Docker volume at `/app/instance` to persist the SQLite database, and at `/app/logs` to persist log files.
