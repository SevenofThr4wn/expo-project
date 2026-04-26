FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV SASS_VERSION=1.77.8

WORKDIR /app

# ── System deps ─────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Sass ─────────────────────────────────────────────────────
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then ARCH="x64"; \
    elif [ "$ARCH" = "aarch64" ]; then ARCH="arm64"; \
    else echo "Unsupported arch: $ARCH" && exit 1; fi && \
    curl -fL https://github.com/sass/dart-sass/releases/download/${SASS_VERSION}/dart-sass-${SASS_VERSION}-linux-${ARCH}.tar.gz \
    -o dart-sass.tar.gz && \
    tar -xzf dart-sass.tar.gz && \
    mv dart-sass /opt/dart-sass && \
    ln -s /opt/dart-sass/sass /usr/local/bin/sass && \
    rm dart-sass.tar.gz

# ── Python deps (CACHED) ────────────────────────────────────
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ── App ──────────────────────────────────────────────────────
COPY . .

RUN sass app/static/scss/styles.scss app/static/css/styles.css --style=compressed

# ── Runtime user ────────────────────────────────────────────
RUN useradd -m appuser
USER appuser

CMD ["gunicorn", "-w", "1", "-k", "eventlet", "--worker-connections", "100", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "run:app"]