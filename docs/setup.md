# Raspberry Pi Deployment Guide

This guide covers deploying the FaceID System on a Raspberry Pi using Docker.

---

- [Hardware Requirements](#hardware-requirements)
- [Prerequisites](#prerequisites)
- [Step 1 — Install Docker](#step-1--install-docker)
- [Step 2 — Connect the Webcam](#step-2--connect-the-webcam)
- [Step 3 — Configure Environment Variables](#step-3--configure-environment-variables)
- [Step 4 — Pull the Image](#step-4--pull-the-image)
- [Step 5 — Run the Container](#step-5--run-the-container)
- [Step 6 — First Login](#step-6--first-login)
- [Persistent Storage](#persistent-storage)
- [Running on Startup](#running-on-startup)
- [CLI Access (No Browser)](#cli-access-no-browser)
- [Updating the Image](#updating-the-image)
- [Troubleshooting](#troubleshooting)

---

## Hardware Requirements

| Component | Requirement |
|---|---|
| Device | Raspberry Pi 4 or 5 |
| Camera | Wired USB webcam |
| RAM | 4 GB minimum, 8 GB+ recommended |
| Storage | 32 GB SD card minimum |

**Tested configuration:**

| Spec | Value |
|---|---|
| Model | Raspberry Pi 5 |
| RAM | 16 GB |
| Storage | 256 GB SD card |
| OS | Debian Trixie (ARM64) |

## Prerequisites

- SD card imaged with **Debian Trixie** (64-bit / ARM64)
- Basic familiarity with the Linux command line
- Internet connection on the Pi during setup

> The Docker image is built for **ARM64 only**. It will not run on 32-bit Raspberry Pi OS.

---

## Step 1 — Install Docker

If Docker is not already installed, follow the [official guide for Raspberry Pi OS](https://docs.docker.com/engine/install/raspberry-pi-os/).

Verify the installation:

```bash
sudo docker run hello-world
```

Start the Docker engine if it isn't running:

```bash
sudo systemctl enable --now docker
```

---

## Step 2 — Connect the Webcam

1. Plug the USB webcam into a USB port on the Raspberry Pi.
2. Confirm it is powered on and the privacy shutter (if any) is open.
3. Verify the device appears:

```bash
ls /dev/video*
```

You should see at least `/dev/video0`. If the webcam exposes multiple device files, use the lowest-numbered one.

---

## Step 3 — Configure Environment Variables

Create an environment file that the container will read at startup. Store it somewhere safe on the Pi:

```bash
mkdir -p ~/faceid
nano ~/faceid/.env
```

Paste and edit the following:

```env
FLASK_SECRET_KEY=replace-with-a-long-random-string
JWT_SECRET_KEY=replace-with-another-long-random-string
ADMIN_PASSWORD=replace-with-a-strong-password
DATABASE_URL=sqlite:///faceid.db
RECOGNITION_TOLERANCE=0.5
```

> Generate strong secrets with: `python3 -c "import secrets; print(secrets.token_hex(32))"`

---

## Step 4 — Pull the Image

```bash
sudo docker pull johneley/johns-private-repo:latest
```

Wait for the download to complete before continuing. Image size is several hundred MB due to dlib and OpenCV.

---

## Step 5 — Run the Container

```bash
sudo docker run -d \
  --name faceid \
  -p 5000:5000 \
  --device=/dev/video0 \
  -v faceid-db:/app/instance \
  -v faceid-logs:/app/logs \
  --env-file ~/faceid/.env \
  --restart unless-stopped \
  johneley/johns-private-repo:latest
```

**Flag breakdown:**

| Flag | Purpose |
|---|---|
| `-d` | Run in the background |
| `--name faceid` | Give the container a memorable name |
| `-p 5000:5000` | Expose the web interface on port 5000 |
| `--device=/dev/video0` | Pass the webcam through to the container |
| `-v faceid-db:/app/instance` | Persist the SQLite database across restarts |
| `-v faceid-logs:/app/logs` | Persist application logs across restarts |
| `--env-file ~/faceid/.env` | Load environment variables from the file you created |
| `--restart unless-stopped` | Automatically restart on reboot or crash |

Check that the container started successfully:

```bash
sudo docker logs faceid
```

You should see log lines ending with the server starting on `0.0.0.0:5000`.

---

## Step 6 — First Login

Find your Pi's IP address:

```bash
hostname -I
```

Open a browser on any device on the same network and navigate to:

```
http://<your-pi-ip>:5000
```

Log in with:
- **Username:** `admin`
- **Password:** the value of `ADMIN_PASSWORD` you set in the `.env` file

> Change the admin password immediately after the first login via the Users page.

---

## Persistent Storage

The two Docker volumes used above keep your data safe across container restarts and image updates:

| Volume | Contents |
|---|---|
| `faceid-db` | SQLite database — user accounts, face encodings, recognition logs |
| `faceid-logs` | Application log files |

To inspect volume locations on disk:

```bash
sudo docker volume inspect faceid-db
```

To back up the database:

```bash
sudo docker cp faceid:/app/instance/faceid.db ~/faceid/faceid.db.bak
```

---

## Running on Startup

The `--restart unless-stopped` flag in the run command means the container starts automatically when Docker starts. Because Docker itself is enabled as a systemd service (`systemctl enable docker`), the FaceID container will start on every boot without any additional configuration.

To verify:

```bash
sudo docker ps --filter "name=faceid"
```

---

## CLI Access (No Browser)

If the Pi has no display, you can manage the system from its terminal using the CLI.

Install the CLI dependencies on the Pi (outside Docker):

```bash
pip3 install click requests rich
```

Clone or copy `cli.py` to the Pi, then:

```bash
# Log in (stores JWT in ~/.faceid/config.json)
python3 cli.py login

# Check system status
python3 cli.py status

# Enroll a face from the camera
python3 cli.py enroll "Alice" --frames 5

# View recent recognition events
python3 cli.py logs --limit 20
```

If the server is running on the same Pi, the default `http://localhost:5000` works. For a remote Pi:

```bash
python3 cli.py --server http://192.168.1.50:5000 status
```

---

## Updating the Image

```bash
# Pull the latest image
sudo docker pull johneley/johns-private-repo:latest

# Stop and remove the old container (data is safe in volumes)
sudo docker stop faceid && sudo docker rm faceid

# Start a new container with the same run command as Step 5
sudo docker run -d \
  --name faceid \
  -p 5000:5000 \
  --device=/dev/video0 \
  -v faceid-db:/app/instance \
  -v faceid-logs:/app/logs \
  --env-file ~/faceid/.env \
  --restart unless-stopped \
  johneley/johns-private-repo:latest
```

---

## Troubleshooting

**Container exits immediately**

```bash
sudo docker logs faceid
```

Check for missing environment variables or a database permission error. Ensure the `.env` file path is correct and readable.

**Webcam not detected inside the container**

Confirm the device exists on the host:
```bash
ls -la /dev/video*
```

If the webcam appears as `/dev/video1` or higher, update the `--device` flag accordingly:
```bash
--device=/dev/video1
```

**Can't connect to the web interface**

- Confirm the container is running: `sudo docker ps`
- Confirm port 5000 is not blocked by a firewall: `sudo ufw status`
- Check the Pi's IP with `hostname -I` — use the first address shown

**Face login not working**

- Enroll at least one face via the web interface or CLI before attempting face login.
- Ensure the webcam shutter is open and the face is well-lit.
- Try lowering the recognition tolerance in Settings if matches are being rejected.

**Recognition service crashes**

```bash
sudo docker restart faceid
```

Check `sudo docker logs faceid` for a Python traceback. This is a known intermittent issue under investigation.
