# ── Builder ───────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt


# ── Runtime ───────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# install Dart Sass
ENV SASS_VERSION=1.77.8
RUN ARCH=$(uname -m) && \
    curl -fL https://github.com/sass/dart-sass/releases/download/${SASS_VERSION}/dart-sass-${SASS_VERSION}-linux-arm64.tar.gz \
    -o sass.tar.gz && \
    tar -xzf sass.tar.gz && \
    mv dart-sass /opt/dart-sass && \
    ln -s /opt/dart-sass/sass /usr/local/bin/sass && \
    rm sass.tar.gz

# copy prebuilt python packages
COPY --from=builder /install /usr/local

COPY . .

RUN sass app/static/scss/styles.scss app/static/css/styles.css --style=compressed

RUN useradd -m appuser
USER appuser

CMD ["gunicorn", "-w", "1", "-k", "eventlet", "--worker-connections", "100", "-b", "0.0.0.0:5000", "run:app"]
