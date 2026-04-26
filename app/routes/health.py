import logging
import os
from datetime import datetime

import psutil
from flask import Blueprint, jsonify

from app.auth.decorators import role_required
from app.extensions import db
from app.models.user import Role

logger = logging.getLogger(__name__)

health_bp = Blueprint("health_api", __name__, url_prefix="/api")

_start_time = datetime.utcnow()


@health_bp.route("/health")
@role_required(Role.ADMIN, Role.OPERATOR)
def get_health():
    proc = psutil.Process(os.getpid())

    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    proc_mem = proc.memory_info().rss / 1024 / 1024  # MB
    uptime_s = int((datetime.utcnow() - _start_time).total_seconds())

    # DB row counts
    try:
        from app.models.recognition_log import RecognitionLog
        from app.models.face_encoding import FaceEncoding
        log_count = RecognitionLog.query.count()
        encoding_count = FaceEncoding.query.count()
    except Exception:
        log_count = encoding_count = -1

    # Camera status
    try:
        from app.services.camera_service import camera_is_connected
        cam_ok = camera_is_connected()
    except Exception:
        cam_ok = False

    # Scheduler status
    sched_running = False
    try:
        from app.services.scheduler_service import get_scheduler
        s = get_scheduler()
        sched_running = s is not None and s.running
    except Exception:
        pass

    return jsonify({
        "uptime_seconds": uptime_s,
        "cpu_percent": cpu,
        "memory": {
            "total_mb": round(mem.total / 1024 / 1024),
            "used_mb": round(mem.used / 1024 / 1024),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
            "used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
            "percent": disk.percent,
        },
        "process_mem_mb": round(proc_mem, 1),
        "camera_connected": cam_ok,
        "scheduler_running": sched_running,
        "db": {
            "recognition_logs": log_count,
            "face_encodings": encoding_count,
        },
    })
