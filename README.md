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

On first launch with no data, the system skips authentication entirely and opens the dashboard directly so you can enroll faces straight away.

## Features

| Feature | Description |
|---|---|
| **First-run bypass** | No login required when no authorized faces are enrolled — opens the dashboard immediately |
| **Live Video Feed** | MJPEG stream with real-time bounding boxes (green = known, red = unknown) |
| **Face Enrollment** | Upload an image or capture directly from the live webcam feed to register a person by name |
| **Webcam Snapshot** | One-click capture from the live feed for enrollment — no separate photo needed |
| **Face Authentication** | Session-based face-login that validates identity against enrolled encodings |
| **Activity Logging** | Persistent JSON log of every recognition event with timestamp and confidence score |
| **Face Management** | View, list, and delete enrolled faces from the dashboard |
| **Bulk Training** | Upload multiple images at once to improve recognition accuracy for a person |
| **Camera Selection** | Detect and hot-swap between available camera devices from the Settings panel |
| **Adjustable Tolerance** | Tune the recognition confidence threshold (0.3–0.7) via the Settings panel |
| **Statistics** | Live count of enrolled faces, recognitions today, and camera connection status |

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
│   ├── auth/
│   │   └── face_auth.py             # Session authentication against authorized_faces/
│   ├── routes/
│   │   ├── auth.py                  # GET  /face-login
│   │   ├── cameras.py               # GET  /cameras, POST /cameras/select
│   │   ├── enroll.py                # POST /enroll
│   │   ├── faces.py                 # GET/DELETE /faces, /faces/<name>
│   │   ├── logs.py                  # GET /log, /stats — DELETE /log — POST /settings
│   │   ├── recognize.py             # GET  /video, /snapshot, /reload
│   │   └── train.py                 # POST /train — GET /train/status
│   ├── services/
│   │   ├── camera_service.py        # Camera I/O, frame streaming, placeholder frame
│   │   ├── face_service.py          # Face detection utilities
│   │   ├── recognition_service.py   # Face matching, annotation, event throttling
│   │   └── training_service.py      # Bulk image processing for training
│   ├── stores/
│   │   ├── face_store.py            # Pickle-based face encoding persistence
│   │   └── log_store.py             # Thread-safe JSON recognition event log
│   ├── static/
│   │   ├── css/styles.css           # Dark theme design system
│   │   └── js/
│   │       ├── api.js               # Fetch-based API client
│   │       └── main.js              # Tab navigation, polling, all UI handlers
│   ├── templates/
│   │   ├── index.html               # Main dashboard (Live / Log / Faces / Training / Settings)
│   │   └── login.html               # Face authentication screen
│   └── data/                        # Runtime data (gitignored)
│       ├── encodings.pkl            # Enrolled face encodings
│       ├── recognition_log.json     # Persisted activity log
│       └── authorized_faces/        # Images used for login (organised by person name)
├── run.py                           # Flask entry point
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

1. **First launch** — If no authorized faces are enrolled, the dashboard opens immediately with no login prompt. Use this opportunity to enroll faces.
2. **Enroll a face** — On the **Live Feed** tab, enter a name and either upload a photo or click **Capture** to grab a frame from the webcam, then click **Enroll Face**.
3. **Improve accuracy** — Use the **Training** tab to upload multiple images of the same person and build a richer encoding set.
4. **Live feed** — The **Live Feed** tab streams real-time video with name labels and confidence scores overlaid on each detected face.
5. **Activity log** — The **Activity Log** tab shows a timestamped history of every recognition event (deduplicated to once per 8 seconds per person).
6. **Manage faces** — The **Enrolled Faces** tab lets you view and remove registered people.
7. **Settings** — Adjust the recognition tolerance slider, select a camera device, or clear the activity log.
8. **Login (once faces are enrolled)** — Place authorized face images in `app/data/authorized_faces/<name>/` and restart. From then on, the system requires face authentication on every visit.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/face-login` | Authenticate the current camera frame against authorized faces |
| `POST` | `/enroll` | Enroll a new face (`name` + `image` form fields) |
| `GET` | `/video` | MJPEG video stream with recognition overlays |
| `GET` | `/snapshot` | Capture a single JPEG frame from the camera |
| `GET` | `/reload` | Reload face encodings from disk into memory |
| `GET` | `/faces` | List all enrolled face names |
| `DELETE` | `/faces/<name>` | Remove all encodings for a person |
| `GET` | `/log` | Retrieve the recognition event log (last 50 entries) |
| `DELETE` | `/log` | Clear all log entries |
| `GET` | `/stats` | System statistics (enrolled count, today's recognitions, camera status) |
| `POST` | `/settings` | Update recognition tolerance at runtime |
| `GET` | `/cameras` | List available camera device indices |
| `POST` | `/cameras/select` | Switch the active camera device |
| `POST` | `/train` | Submit multiple images for bulk training |
| `GET` | `/train/status` | Check the status of an in-progress training job |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-in-prod` | Flask session secret — **change in production** |

Recognition tolerance can be adjusted at runtime via the Settings tab (range 0.30–0.70, default 0.50). Lower values require a closer match; higher values are more permissive.

## First-Run Behaviour

The system checks for images inside `app/data/authorized_faces/` on every request. While that directory is empty:

- All routes are accessible without a login session.
- The session user is set to `"admin"` automatically.
- The `/login` page redirects straight to the dashboard.

Once you add at least one image to `authorized_faces/`, the login gate activates on the next request.

## Deployment Notes

- Tested on **Raspberry Pi 5** with 16 GB RAM and a 256 GB SD card running Debian Trixie (ARM64).
- A USB webcam must be connected and accessible as `/dev/video0` before starting the container.
- Activity logs are written to `app/data/recognition_log.json` and capped at 200 events in memory.
- On Windows, OpenCV uses the DirectShow backend automatically for faster camera access.

## License

This project was developed as a university project. All rights reserved.
