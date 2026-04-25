import cv2
import face_recognition
import numpy as np
import logging
import threading
import time

from app.services.face_service import get_landmarks, draw_landmarks, COLOR_KNOWN, COLOR_UNKNOWN

logger = logging.getLogger(__name__)

_instance = None
_instance_lock = threading.Lock()
_app = None  # stored so background threads can push an app context


def init_recognition_service(app):
    global _app
    _app = app
    with app.app_context():
        get_recognizer().refresh_data()


def get_recognizer():
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = RecognitionService()
    return _instance


class RecognitionService:
    def __init__(self, tolerance: float = 0.5, show_landmarks: bool = True):
        self.tolerance = tolerance
        self.show_landmarks = show_landmarks

        self._known_encodings: list = []
        self._known_names: list = []
        self._data_lock = threading.Lock()

        self._log_lock = threading.Lock()
        self._last_logged: dict = {}
        self._log_cooldown = 8  # seconds between duplicate log entries

        self._frame_count = 0
        self._process_every = 2   # run recognition every N frames, display all
        self._last_results: list = []

    # ── Data management ────────────────────────────────────────────────────────

    def refresh_data(self):
        """Reload face encodings from the database."""
        ctx = _app.app_context() if _app else None
        try:
            if ctx:
                ctx.push()
            from app.models.face_encoding import FaceEncoding
            rows = FaceEncoding.query.all()
            enc = [r.encoding for r in rows]
            names = [r.name for r in rows]
            with self._data_lock:
                self._known_encodings = enc
                self._known_names = names
            logger.info(
                "Face data refreshed: %d encodings, %d people",
                len(enc), len(set(names)),
            )
        except Exception as e:
            logger.warning("Could not refresh face data: %s", e)
        finally:
            if ctx:
                try:
                    ctx.pop()
                except Exception:
                    pass

    # ── Per-frame processing ───────────────────────────────────────────────────

    def process_frame(self, frame):
        self._frame_count += 1

        # Only run the expensive recognition every Nth frame
        if self._frame_count % self._process_every != 0:
            return self._last_results

        rgb = frame[:, :, ::-1]
        boxes = face_recognition.face_locations(rgb)
        if not boxes:
            self._last_results = []
            return []

        encodings = face_recognition.face_encodings(rgb, boxes)
        landmarks = get_landmarks(frame, boxes) if self.show_landmarks else []

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

            results.append({
                "box": box,
                "name": name,
                "confidence": confidence,
                "landmarks": landmarks[i] if i < len(landmarks) else {},
            })

        self._last_results = results
        return results

    def _match(self, encoding, known_encodings, known_names):
        if not known_encodings:
            return "unknown", 0
        distances = face_recognition.face_distance(known_encodings, encoding)
        best = int(np.argmin(distances))
        if distances[best] < self.tolerance:
            return known_names[best], int((1 - distances[best]) * 100)
        return "unknown", int((1 - distances[best]) * 100)

    def match_face(self, encoding):
        with self._data_lock:
            return self._match(encoding, self._known_encodings, self._known_names)

    # ── Logging ────────────────────────────────────────────────────────────────

    def _log_event(self, name: str, confidence: int):
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

            socketio.emit("recognition", {
                "name": name,
                "confidence": confidence,
                "timestamp": entry.timestamp.isoformat(),
            })
            logger.info("Recognition: %s (%d%%)", name, confidence)
        except Exception as e:
            logger.error("Error logging recognition event: %s", e)
        finally:
            if ctx:
                try:
                    ctx.pop()
                except Exception:
                    pass

    # ── Drawing ────────────────────────────────────────────────────────────────

    def draw_results(self, frame, results):
        for result in results:
            top, right, bottom, left = result["box"]
            name = result["name"]
            confidence = result["confidence"]
            is_known = name != "unknown"
            color = COLOR_KNOWN if is_known else COLOR_UNKNOWN

            # Outer bounding box (thin, 50 % alpha emulated with line width)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 1, cv2.LINE_AA)

            # Corner accent marks
            cl = 14
            ct = 2
            for ox, oy, hx, vy in [
                (left,  top,    left + cl, top + cl),
                (right, top,    right - cl, top + cl),
                (left,  bottom, left + cl, bottom - cl),
                (right, bottom, right - cl, bottom - cl),
            ]:
                cv2.line(frame, (ox, oy), (hx, oy), color, ct, cv2.LINE_AA)
                cv2.line(frame, (ox, oy), (ox, vy), color, ct, cv2.LINE_AA)

            # Label pill
            label = f"{name}  {confidence}%"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
            ly = top - 10 if top > 34 else bottom + th + 10
            cv2.rectangle(frame, (left, ly - th - 6), (left + tw + 10, ly + 2), color, -1)
            cv2.putText(
                frame, label, (left + 5, ly - 1),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA,
            )

            # Confidence bar beneath label pill
            bar_w = tw + 10
            bar_h = 3
            filled = int(bar_w * confidence / 100)
            cv2.rectangle(frame, (left, ly + 3), (left + bar_w, ly + 3 + bar_h), (40, 40, 40), -1)
            cv2.rectangle(frame, (left, ly + 3), (left + filled, ly + 3 + bar_h), color, -1)

            # Landmarks
            if result.get("landmarks") and self.show_landmarks:
                draw_landmarks(frame, [result["landmarks"]])

        return frame
