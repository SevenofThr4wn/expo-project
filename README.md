# FaceID System | Expo Project — IFB102

A real-time facial recognition and access control system with a web dashboard and headless CLI. Built with Python/Flask and designed for deployment on Raspberry Pi hardware.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?style=flat-square&logo=flask&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.13-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%2F5-A22846?style=flat-square&logo=raspberry-pi&logoColor=white)

---

- [FaceID System | Expo Project — IFB102](#faceid-system--expo-project--ifb102)
  - [Overview](#overview)
  - [Features](#features)
  - [Tech Stack](#tech-stack)
  - [Project Structure](#project-structure)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Local Setup](#local-setup)
    - [Docker (Raspberry Pi)](#docker-raspberry-pi)
  - [Usage](#usage)
    - [Web Interface](#web-interface)
    - [CLI](#cli)
  - [API Reference](#api-reference)
    - [Authentication](#authentication)
    - [Faces](#faces)
    - [Stream](#stream)
    - [Logs](#logs)
    - [Cameras](#cameras)
    - [Settings](#settings)
    - [Users](#users)
  - [Auth \& Roles](#auth--roles)
  - [Configuration](#configuration)
  - [Default Admin](#default-admin)
  - [Deployment Notes](#deployment-notes)
  - [Roadmap](#roadmap)
  - [Additional Documentation](#additional-documentation)
  - [License](#license)

---

## Overview

FaceID System is a full-stack facial recognition application for physical access control and identity verification. It lets you enroll faces, stream live video with real-time recognition overlays, manage user accounts with role-based permissions, and log every access event — all from a browser or the terminal.

The system is built to run on a Raspberry Pi with a USB webcam and is containerized for straightforward deployment.

## Features

| Feature | Description |
|---|---|
| **Username/Password Login** | Session-based login backed by bcrypt-hashed credentials in SQLite |
| **Face Login** | One-click camera authentication — matches a live frame against enrolled encodings |
| **JWT API Tokens** | Stateless Bearer tokens for CLI and headless API access |
| **Role-Based Access** | Three roles: `admin`, `operator`, `viewer` — enforced on every API route |
| **User Management** | Admins can create, update, disable, and delete user accounts |
| **Live Video Feed** | MJPEG stream with real-time bounding boxes (green = known, red = unknown) |
| **Face Enrollment** | Upload an image or capture a live snapshot to register a person by name |
| **Face Linking** | Enrolled faces can be linked to a user account by matching the name |
| **Activity Logging** | Database-backed log of every recognition event with timestamp and confidence |
| **Log Export** | Download the full recognition log as a CSV file |
| **Stats Dashboard** | Enrolled count, today's recognitions, per-hour chart, per-person breakdown |
| **Camera Selection** | Detect and hot-swap between available camera devices from the Settings panel |
| **Adjustable Tolerance** | Tune the recognition confidence threshold (0.30–0.70) at runtime |
| **Headless CLI** | Full management interface via `cli.py` — no browser required |

## Tech Stack

**Backend**
- [Flask](https://flask.palletsprojects.com/) — Web Framework and REST API
- [Flask-Bcrypt](https://flask-bcrypt.readthedocs.io/) — password encryption & hashing
- [Flask-Caching]("https://flask-caching.readthedocs.io/) — Placeholder
- [Flask-Compress](https://github.com/colour-science/flask-compress) — Placeholder
- [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/) — Bearer token authentication for API/CLI
- [Flask-Login](https://flask-login.readthedocs.io/) — Session-based authentication
- [Flask-Mail](https://flask-mail.readthedocs.io/) — Send email alerts, scheduled report delivery. Configured via .env SMTP settings.
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/) + [gevent](https://www.gevent.org) — WebSocket support
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) + [Flask-Migrate](https://flask-migrate.readthedocs.io/) — Database ORM and migrations
- [insightface](https://github.com/deepinsight/insightface) — facial encoding and matching
- [OpenCV](https://opencv.org/) — video capture and frame processing
- [NumPy](https://numpy.org/) / [Pillow](https://python-pillow.org/) — numerical and image processing
- [colorlog](https://pypi.org/project/colorlog/) — coloured console logging

**Frontend**
- Vanilla HTML5, CSS3, JavaScript
- MJPEG streaming for low-latency live video
- REST API calls to the Flask backend

**CLI**
- [Click](https://click.palletsprojects.com/) — command-line interface framework
- [Rich](https://rich.readthedocs.io/) — terminal formatting and tables

**Infrastructure**
- Docker — containerized deployment
- gunicorn + eventlet — production WSGI server
- Target hardware: Raspberry Pi 4/5 (ARM64, Debian Trixie)

## Project Structure

```
project/
├── app/
│   ├── auth/
│   │   ├── __init__.py              # Blueprint registration
│   │   ├── decorators.py            # login_required, api_login_required, role_required, admin_required
│   │   └── routes.py                # /auth/login  /auth/face-login  /auth/logout  /auth/token
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                  # User model + Role constants (admin / operator / viewer)
│   │   ├── face_encoding.py         # FaceEncoding model (numpy array stored as binary)
│   │   └── recognition_log.py       # RecognitionLog model
│   ├── routes/
│   │   ├── cameras.py               # GET /api/cameras   POST /api/cameras/select
│   │   ├── enroll.py                # POST /api/enroll
│   │   ├── faces.py                 # GET /api/faces   DELETE /api/faces/<name>
│   │   ├── logs.py                  # GET/DELETE /api/logs   GET /api/logs/export   GET /api/stats
│   │   ├── pages.py                 # HTML page routes (/, /recognition, /enroll, /faces, /logs, /users, /settings)
│   │   ├── settings.py              # POST /api/settings
│   │   ├── stream.py                # GET /api/video   /api/snapshot   /api/reload
│   │   └── users.py                 # CRUD /api/users
│   ├── services/
│   │   ├── camera_service.py        # Camera I/O and MJPEG frame generation
│   │   ├── face_service.py          # Face detection utilities
│   │   └── recognition_service.py   # Face matching, bounding-box annotation, event throttling
│   ├── static/
│   │   ├── css/styles.css           # Dark-theme design system
│   │   └── js/
│   │       ├── api.js               # Fetch-based API client
│   │       ├── dashboard.js         # Dashboard charts and stats polling
│   │       ├── enroll.js            # Enroll page logic
│   │       └── recognition.js       # Live feed and recognition UI
│   ├── templates/
│   │   ├── base.html                # Shared layout and navigation
│   │   ├── dashboard.html           # Stats and charts
│   │   ├── enroll.html              # Face enrollment
│   │   ├── faces.html               # Enrolled face management
│   │   ├── login.html               # Username/password + face login
│   │   ├── logs.html                # Recognition event log
│   │   ├── recognition.html         # Live video feed
│   │   ├── settings.html            # Tolerance, camera selection
│   │   └── users.html               # User account management (admin only)
│   ├── extensions.py                # Flask extension instances (db, login_manager, bcrypt, jwt, migrate, socketio)
│   └── __init__.py                  # Application factory (create_app)
├── cli.py                           # Headless CLI (Click + Rich)
├── run.py                           # Development server entry point
├── requirements.txt
├── Dockerfile
└── .env                             # Environment variables (gitignored)
```

## Getting Started

### Prerequisites

- Python 3.10+
- A USB or built-in webcam
- `cmake` and a C++ compiler — required by dlib
  - Windows: [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
  - Linux/macOS: `sudo apt install cmake build-essential` / `xcode-select --install`

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/SevenofThr4wn/expo-project.git
cd expo-project

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables (see Configuration section)
cp .env.example .env   # or create .env manually

# 5. Run the application
python run.py
```

The app will be available at `http://localhost:5000`. On first launch a default `admin` account is created automatically (see [Default Admin](#default-admin)).

### Docker (Raspberry Pi)

See [docs/setup.md](docs/setup.md) for the full Raspberry Pi deployment guide. Quick start:

```bash
# Pull the pre-built image
sudo docker pull johneley/johns-private-repo:latest

# Run with webcam access and persistent database storage
sudo docker run -p 5000:5000 \
  --device=/dev/video0 \
  -v faceid-data:/app/instance \
  -e FLASK_SECRET_KEY=your-secret-here \
  -e ADMIN_PASSWORD=your-admin-password \
  johneley/johns-private-repo:latest
```

## Usage

### Web Interface

| Page | URL | Access |
|---|---|---|
| Dashboard | `/` | All roles |
| Live Feed | `/recognition` | All roles |
| Enroll Face | `/enroll` | Admin, Operator |
| Enrolled Faces | `/faces` | All roles |
| Activity Log | `/logs` | All roles |
| User Management | `/users` | Admin only |
| Settings | `/settings` | Admin, Operator |

1. **Log in** — Navigate to `/auth/login` and enter your credentials, or use **Face Login** to authenticate via webcam.
2. **Enroll a face** — Go to `/enroll`, enter a name, and either upload an image or click **Capture** to grab a live frame.
3. **Live feed** — `/recognition` streams video with name labels and confidence scores overlaid on detected faces.
4. **Activity log** — `/logs` shows a timestamped history of every recognition event. Export as CSV with the download button.
5. **Manage users** — `/users` (admin only) lets you create, edit roles, disable, and delete accounts.
6. **Settings** — Adjust the recognition tolerance slider or select a different camera device.

### CLI

`cli.py` provides headless access to the API using JWT tokens — no browser needed. Useful for Raspberry Pi deployments without a display.

```bash
# Authenticate and store a token locally (~/.faceid/config.json)
python cli.py login

# Show system status
python cli.py status

# List enrolled faces
python cli.py list-faces

# Enroll a face by capturing from the camera (3 frames by default)
python cli.py enroll "Alice" --frames 5

# Delete a face
python cli.py delete-face "Alice"

# Show recent recognition logs
python cli.py logs --limit 20 --name "Alice"

# User management (admin only)
python cli.py users list
python cli.py users create
python cli.py users delete <username>

# Target a different server
python cli.py --server http://192.168.1.50:5000 status
```

## API Reference

All API endpoints are prefixed with `/api/`. Auth endpoints use `/auth/`.

Authentication is required on all endpoints unless noted as public. Use either:
- **Session cookie** — obtained via `POST /auth/login` through the browser
- **Bearer token** — obtained via `POST /auth/token`, passed as `Authorization: Bearer <token>`

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/auth/login` | Public | Render login page |
| `POST` | `/auth/login` | Public | Username/password login — sets session cookie |
| `GET` | `/auth/face-login` | Public | Authenticate via live camera frame |
| `POST` | `/auth/token` | Public | Issue a JWT for CLI/API use |
| `GET` | `/auth/logout` | Session | Invalidate session and redirect to login |

**POST /auth/login** — body: `{ "username": "...", "password": "...", "remember": false }`

**POST /auth/token** — body: `{ "username": "...", "password": "..." }` — returns `{ "access_token": "...", "user": {...} }`

### Faces

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `GET` | `/api/faces` | Any | List enrolled faces with encoding counts |
| `DELETE` | `/api/faces/<name>` | Admin, Operator | Remove all encodings for a person |

**GET /api/faces** response:
```json
{
  "faces": [
    { "name": "Alice", "count": 3 }
  ]
}
```

### Stream

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/video` | Public | MJPEG stream with recognition overlays |
| `GET` | `/api/snapshot` | Public | Single JPEG frame from the camera |
| `GET` | `/api/reload` | Public | Reload face encodings from the database |

> `/api/video` and `/api/snapshot` are intentionally public so the login page camera preview works without a session.

### Logs

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `GET` | `/api/logs` | Any | Paginated recognition event log |
| `DELETE` | `/api/logs` | Admin | Clear all log entries |
| `GET` | `/api/logs/export` | Any | Download full log as CSV |
| `GET` | `/api/stats` | Any | System statistics and chart data |

**GET /api/logs** — query params: `limit` (max 500, default 100), `offset`, `name` (filter by person)

**GET /api/stats** response:
```json
{
  "enrolled_count": 4,
  "today_recognitions": 12,
  "camera_connected": true,
  "hourly": [{ "hour": "09", "count": 3 }],
  "per_person": [{ "name": "Alice", "count": 8 }]
}
```

### Cameras

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `GET` | `/api/cameras` | Any | List available camera device indices |
| `POST` | `/api/cameras/select` | Admin, Operator | Switch the active camera |

**POST /api/cameras/select** — body: `{ "index": 0 }`

### Settings

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `POST` | `/api/settings` | Admin, Operator | Update recognition settings at runtime |

**POST /api/settings** — body (all fields optional):
```json
{
  "tolerance": 0.5,
  "show_landmarks": false
}
```

### Users

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `GET` | `/api/users` | Admin | List all user accounts |
| `POST` | `/api/users` | Admin | Create a new user |
| `PATCH` | `/api/users/<id>` | Admin | Update role, password, email, or active status |
| `DELETE` | `/api/users/<id>` | Admin | Delete a user account |

**POST /api/users** — body: `{ "username": "...", "password": "...", "role": "operator", "email": "..." }`

**PATCH /api/users/<id>** — body (all fields optional): `{ "role": "...", "password": "...", "email": "...", "is_active": true }`

## Auth & Roles

The system uses role-based access control with three roles:

| Role | Capabilities |
|---|---|
| `admin` | Full access — user management, all API endpoints, settings |
| `operator` | Enroll faces, delete faces, change camera, update settings |
| `viewer` | Read-only — view faces, logs, stats, and live feed |

Roles are enforced by decorators on every API route. A `403` is returned when a lower-privileged user attempts a restricted action.

## Configuration

Set these in a `.env` file at the project root. All values have safe defaults for development but **must be changed in production**.

| Variable | Default | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | `change-me-in-production` | Flask session signing key |
| `JWT_SECRET_KEY` | Same as `FLASK_SECRET_KEY` | JWT signing key (set separately in production) |
| `DATABASE_URL` | `sqlite:///faceid.db` | SQLAlchemy database URI |
| `ADMIN_PASSWORD` | `admin` | Password for the auto-created admin account |
| `RECOGNITION_TOLERANCE` | `0.5` | Initial recognition tolerance (0.30–0.70) |

Example `.env`:
```env
FLASK_SECRET_KEY=a-long-random-string-here
JWT_SECRET_KEY=another-long-random-string
DATABASE_URL=sqlite:///faceid.db
ADMIN_PASSWORD=changeme
RECOGNITION_TOLERANCE=0.5
```

Recognition tolerance can also be changed at runtime via `POST /api/settings` or the Settings page. Lower values require a closer match; higher values are more permissive.

## Default Admin

On first launch, if the `users` table is empty, the application automatically creates an admin account:

- **Username:** `admin`
- **Password:** value of `ADMIN_PASSWORD` env var (default: `admin`)

Change this password immediately after the first login, either through the Users page or by setting `ADMIN_PASSWORD` before the first run.

## Deployment Notes

- Tested on **Raspberry Pi 5** with 16 GB RAM and a 256 GB SD card running Debian Trixie (ARM64).
- The Docker image is built for **ARM64**. It will not run on 32-bit Raspberry Pi OS.
- A USB webcam must be connected and accessible as `/dev/video0` before starting the container.
- Use a Docker volume (`-v faceid-data:/app/instance`) to persist the SQLite database across container restarts.
- Logs are written to `logs/app.log` (rotating, 5 MB max, 5 backups). Mount a volume if you want logs to persist.
- On Windows, OpenCV uses the DirectShow backend automatically for faster camera access.
- The `SECRET_KEY` and `JWT_SECRET_KEY` environment variables **must** be set to strong random values in any production or shared deployment.

## Roadmap

- **Feature:** Protected API calls page with live demo
- **Feature:** Per-user activity history and audit trail
- **Bug Fix:** Suppress live feed when no camera is connected
- **Bug Fix:** Investigate intermittent recognition service crash
- **Optimisation:** Reduced memory footprint for Raspberry Pi 4 (4 GB)

## Additional Documentation

| Document | Description |
|---|---|
| [docs/api.md](docs/api.md) | Complete API reference — all endpoints, request/response schemas, error codes, WebSocket events |
| [docs/cli.md](docs/cli.md) | CLI command reference — all commands, options, and examples |
| [docs/setup.md](docs/setup.md) | Raspberry Pi deployment guide — Docker, environment variables, persistent storage, troubleshooting |
| [docs/development.md](docs/development.md) | Developer guide — architecture, database migrations, recognition pipeline, adding new routes |

## License

Developed as a university project (IFB102 — QUT). All rights reserved.
