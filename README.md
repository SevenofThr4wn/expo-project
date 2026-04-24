# FaceID System

A real-time facial recognition and access control system with a web-based dashboard. Built with Python/Flask and designed for deployment on Raspberry Pi hardware.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?style=flat-square&logo=flask&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.13-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%2F5-A22846?style=flat-square&logo=raspberry-pi&logoColor=white)

---

## Overview

FaceID System is a full-stack facial recognition application that lets you enroll faces, stream live video with real-time recognition, and log access events — all from a browser. It is built to run on a Raspberry Pi with a USB webcam, making it suitable for physical access control or identity verification scenarios.

## Features

| Feature | Description |
|---|---|
| **Live Video Feed** | MJPEG stream with real-time bounding boxes (green = known, red = unknown) |
| **Face Enrollment** | Upload an image to register a new person by name |
| **Face Authentication** | Session-based face-login that validates identity against enrolled encodings |
| **Activity Logging** | Persistent JSON log of every recognition event with timestamp and confidence score |
| **Face Management** | View, list, and delete enrolled faces from the dashboard |
| **Adjustable Tolerance** | Tune the recognition confidence threshold (0.3–0.7) via the settings panel |
| **Statistics** | Live count of enrolled faces, recognitions today, and system status |

## Tech Stack

**Backend**
- [Flask](https://flask.palletsprojects.com/) — web framework and REST API
- [face_recognition](https://github.com/ageitgey/face_recognition) — facial encoding and matching
- [OpenCV](https://opencv.org/) — video capture and frame processing
- [dlib](http://dlib.net/) — face detection backbone
- [NumPy](https://numpy.org/) / [Pillow](https://python-pillow.org/) — numerical and image processing

**Frontend**
- Vanilla HTML5, CSS3, JavaScript
- MJPEG streaming for low-latency video
- REST API calls to the Flask backend

**Infrastructure**
- Docker — containerized deployment
- Target hardware: Raspberry Pi 4/5 (ARM64, Debian Trixie)

## Project Structure

```
project/
├── app/
│   ├── __init__.py              # App factory and blueprint registration
│   ├── auth/
│   │   └── face_auth.py         # Authentication logic
│   ├── routes/
│   │   ├── auth.py              # POST /face-login
│   │   ├── enroll.py            # POST /enroll
│   │   ├── recognize.py         # GET  /video, /snapshot, /reload
│   │   ├── faces.py             # GET/DELETE /faces
│   │   └── logs.py              # GET /log, /stats, /settings
│   ├── services/
│   │   ├── camera_service.py    # Camera I/O and frame streaming
│   │   ├── recognition_service.py # Face matching and annotation
│   │   └── face_service.py      # Face detection utilities
│   ├── stores/
│   │   ├── face_store.py        # Pickle-based face encoding persistence
│   │   └── log_store.py         # JSON-based recognition event log
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/
│   │       ├── api.js           # API client wrapper
│   │       └── main.js          # Dashboard logic and tab navigation
│   ├── templates/
│   │   ├── index.html           # Main dashboard
│   │   └── login.html           # Face login screen
│   └── data/                    # Runtime data (gitignored)
│       ├── encodings.pkl
│       ├── recognition_log.json
│       └── authorized_faces/
├── docs/
│   └── setup.md                 # Raspberry Pi deployment guide
├── run.py                       # Flask entry point
├── requirements.txt
└── Dockerfile
```

## Getting Started

### Prerequisites

- Python 3.8+
- A webcam (USB or built-in)
- `cmake` and a C++ compiler (required by dlib)

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/SevenofThr4wn/expo-project.git
cd expo-project

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your secret key (optional — defaults to a dev key)
echo "SECRET_KEY=your-secret-key-here" > .env

# 5. Run the application
python run.py
```

The app will be available at `http://localhost:5000`.

### Docker (Raspberry Pi)

See [docs/setup.md](docs/setup.md) for the full Raspberry Pi deployment guide. Quick start:

```bash
# Pull the pre-built image
sudo docker pull johneley/johns-private-repo:latest

# Run with webcam access (on Raspberry Pi)
sudo docker run -p 5000:5000 --device=/dev/video0 johneley/johns-private-repo:latest
```

## Usage

1. **Login** — Navigate to `http://<device-ip>:5000`. You will be prompted for face authentication.
2. **Enroll a face** — Go to the **Enroll** panel, enter a name, upload a clear photo, and submit.
3. **Live feed** — The **Live Feed** tab streams real-time video with name labels and confidence scores.
4. **Activity log** — The **Activity Log** tab shows a timestamped history of every recognition event.
5. **Manage faces** — The **Enrolled Faces** tab lets you view and delete registered people.
6. **Settings** — Adjust the recognition tolerance slider to trade off precision vs. recall.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/face-login` | Authenticate via uploaded image |
| `POST` | `/enroll` | Enroll a new face |
| `GET` | `/video` | MJPEG video stream |
| `GET` | `/snapshot` | Capture a single frame |
| `GET` | `/reload` | Reload face encodings from disk |
| `GET` | `/faces` | List all enrolled faces |
| `DELETE` | `/faces/<name>` | Remove an enrolled face |
| `GET` | `/log` | Retrieve recognition log |
| `GET` | `/stats` | System statistics |
| `POST` | `/settings` | Update recognition settings |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-in-prod` | Flask session secret — **change in production** |

Recognition tolerance can also be adjusted at runtime via the Settings tab in the dashboard (stored in `app/data/`).

## Deployment Notes

- Tested on **Raspberry Pi 5** with 16 GB RAM and a 256 GB SD card running Debian Trixie (ARM64).
- A USB webcam must be connected and accessible as `/dev/video0` before starting the container.
- Activity logs are written to `app/data/recognition_log.json` and capped at 200 events in memory.

## License

This project was developed as a university project. All rights reserved.
