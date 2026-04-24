import json
import os
import threading
from collections import deque
from datetime import datetime

LOG_PATH = 'app/data/recognition_log.json'
_lock = threading.Lock()
_log = deque(maxlen=200)


def _load_from_disk():
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, 'r') as f:
                entries = json.load(f)
                _log.extend(entries[-200:])
        except Exception:
            pass


def _save_to_disk():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'w') as f:
        json.dump(list(_log), f)


_load_from_disk()


def add_event(name, confidence):
    entry = {
        "name": name,
        "confidence": confidence,
        "timestamp": datetime.now().isoformat()
    }
    with _lock:
        _log.appendleft(entry)
        _save_to_disk()


def get_events(limit=50):
    with _lock:
        return list(_log)[:limit]


def get_today_count():
    today = datetime.now().date().isoformat()
    with _lock:
        return sum(
            1 for e in _log
            if e["timestamp"].startswith(today) and e["name"] != "unknown"
        )


def clear_events():
    with _lock:
        _log.clear()
        _save_to_disk()
