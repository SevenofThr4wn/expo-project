# Setup Guide

## Prerequisites

### Hardware

| Component | Requirement |
|-----------|-------------|
| Device | Raspberry Pi 4 or 5 |
| Camera | Wired USB webcam |

### Tested Configuration

| Spec | Value |
|------|-------|
| Model | Raspberry Pi 5 |
| RAM | 16 GB |
| Storage | 256 GB SD card |
| CPU | 4-core ARM64 |

### Assumed Knowledge

- SD card already imaged with **Debian Trixie**
- Basic familiarity with the command line (CLI) and Debian commands

---

## Installation

### 1. Install Docker

If Docker is not already installed, follow the official guide:
[Docker for Raspberry Pi OS](https://docs.docker.com/engine/install/raspberry-pi-os/)

Verify the installation works:

```bash
sudo docker run hello-world
```

### 2. Start the Docker Engine

```bash
sudo systemctl start docker
```

### 3. Pull the Application Image

```bash
sudo docker pull johneley/johns-private-repo:latest
```

Wait for the image to finish downloading before continuing. The repo should be built for ARM64 architecture, if your Raspberry Pi does not support ARM64, downloading the package will not succeed.

### 4. Connect the Webcam

- Plug the USB webcam into a USB port on the Raspberry Pi
- Confirm the webcam is powered on
- If the webcam has a privacy shutter, make sure it is open

### 5. Run the Container

```bash
sudo docker run -p 5000:5000 johneley/johns-private-repo:latest
```

The application will be accessible at `http://<your-pi-ip>:5000`.
