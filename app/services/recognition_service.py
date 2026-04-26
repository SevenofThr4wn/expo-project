import cv2
import numpy as np
import logging
import queue as _queue
import threading
import time

from app.services.face_engine import get_face_app
from app.services.face_service import draw_landmarks, COLOR_KNOWN, COLOR_UNKNOWN

logger = logging.getLogger(__name__)

_instance = None
_instance_lock = threading.Lock()
_app = None
_log_queue: _queue.Queue = _queue.Queue()


def init_recognition_service(app):
    global _app
    _app = app
    with app.app_context():
        get_recognizer().refresh_data()
    _start_log_drainer()


def _start_log_drainer():
    import gevent

    def _drain():
        while True:
            try:
                name, confidence = _log_queue.get_nowait()
                get_recognizer()._do_log_event(name, confidence)
            except _queue.Empty:
                gevent.sleep(0.1)

    gevent.spawn(_drain)


def get_recognizer():
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = RecognitionService()
    return _instance


class RecognitionService:
    def __init__(self, tolerance: float = 0.35, show_landmarks: bool = True):
        self.tolerance = tolerance
        self.show_landmarks = show_landmarks

        self._known_encodings = []
        self._known_names = []
        self._data_lock = threading.Lock()

        self._log_lock = threading.Lock()
        self._last_logged = {}
        self._log_cooldown = 8

        self._frame_count = 0
        self._process_every = 3
        self._last_results = []

        self._face_app = get_face_app()

    # ─────────────────────────────────────────────
    # DATA MANAGEMENT
    # ─────────────────────────────────────────────

    def refresh_data(self):
        ctx = _app.app_context() if _app else None
        try:
            if ctx:
                ctx.push()

            from app.models.face_encoding import FaceEncoding

            rows = FaceEncoding.query.all()

            enc = [np.array(r.encoding, dtype=np.float32) for r in rows]
            names = [r.name for r in rows]

            with self._data_lock:
                self._known_encodings = enc
                self._known_names = names

            logger.info(
                "Face data refreshed: %d encodings, %d people",
                len(enc),
                len(set(names)),
            )

        except Exception as e:
            logger.warning("Could not refresh face data: %s", e)

        finally:
            if ctx:
                try:
                    ctx.pop()
                except Exception:
                    pass

    # ─────────────────────────────────────────────
    # FRAME PROCESSING (INSIGHTFACE CORE)
    # ─────────────────────────────────────────────

    def process_frame(self, frame):
        self._frame_count += 1

        if self._frame_count % self._process_every != 0:
            return self._last_results

        faces = self._face_app.get(frame)

        if not faces:
            self._last_results = []
            return []

        # Extract InsightFace outputs
        boxes = []
        encodings = []
        landmarks = []

        for f in faces:
            boxes.append(f.bbox.astype(int))
            encodings.append(np.array(f.embedding, dtype=np.float32))
            landmarks.append(getattr(f, "kps", None))

        with self._data_lock:
            enc_snap = list(self._known_encodings)
            name_snap = list(self._known_names)

        now = time.time()
        results = []

        for i, (box, enc) in enumerate(zip(boxes, encodings)):
            name, confidence = self._match(enc, enc_snap, name_snap)

            if name != "unknown":
                with self._log_lock:
                    last = self._last_logged.get(name, 0)
                    should_log = (now - last) > self._log_cooldown
                    if should_log:
                        self._last_logged[name] = now
                if should_log:
                    self._log_event(name, confidence)

            results.append(
                {
                    "box": box,
                    "name": name,
                    "confidence": confidence,
                    "landmarks": landmarks[i] if i < len(landmarks) else None,
                }
            )

        self._last_results = results
        return results

    # ─────────────────────────────────────────────
    # MATCHING (COSINE SIMILARITY)
    # ─────────────────────────────────────────────

    def _match(self, encoding, known_encodings, known_names):
        if not known_encodings:
            return "unknown", 0

        enc = encoding / (np.linalg.norm(encoding) + 1e-10)
        known = np.array(known_encodings)

        known = known / (np.linalg.norm(known, axis=1, keepdims=True) + 1e-10)

        sims = np.dot(known, enc)
        best = int(np.argmax(sims))

        score = float(sims[best])

        if score > (1 - self.tolerance):
            return known_names[best], int(score * 100)

        return "unknown", int(score * 100)

    def match_face(self, encoding):
        with self._data_lock:
            return self._match(
                encoding,
                self._known_encodings,
                self._known_names,
            )

    # ─────────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────────

    def _log_event(self, name: str, confidence: int):
        _log_queue.put_nowait((name, confidence))

    def _do_log_event(self, name: str, confidence: int):
        ctx = _app.app_context() if _app else None
        try:
            if ctx:
                ctx.push()

            from app.extensions import db, socketio
            from app.models.recognition_log import RecognitionLog
            from app.models.user import User

            user = User.query.filter_by(username=name).first()

            entry = RecognitionLog(
                face_name=name,
                confidence=confidence,
                user_id=user.id if user else None,
            )

            db.session.add(entry)
            db.session.commit()

            socketio.emit(
                "recognition",
                {
                    "name": name,
                    "confidence": confidence,
                    "timestamp": entry.timestamp.isoformat(),
                },
            )

            logger.info("Recognition: %s (%d%%)", name, confidence)

        except Exception as e:
            logger.error("Error logging recognition event: %s", e)

        finally:
            if ctx:
                try:
                    ctx.pop()
                except Exception:
                    pass

    # ─────────────────────────────────────────────
    # DRAWING
    # ─────────────────────────────────────────────

    def draw_results(self, frame, results):
        for result in results:
            top, right, bottom, left = result["box"]

            name = result["name"]
            confidence = result["confidence"]
            color = COLOR_KNOWN if name != "unknown" else COLOR_UNKNOWN

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            label = f"{name} {confidence}%"

            (tw, th), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )

            cv2.rectangle(
                frame,
                (left, top - th - 10),
                (left + tw + 10, top),
                color,
                -1,
            )

            cv2.putText(
                frame,
                label,
                (left + 5, top - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

            # landmarks (InsightFace 5-point)
            if result.get("landmarks") is not None and self.show_landmarks:
                lm = np.array(result["landmarks"], dtype=np.int32)
                for x, y in lm:
                    cv2.circle(frame, (x, y), 2, (255, 200, 0), -1)

        return frame