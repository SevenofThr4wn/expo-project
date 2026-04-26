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
    def __init__(self):
        # Threshold = 1 - tolerance. ArcFace (buffalo_l) cosine similarities for
        # the same person in webcam conditions typically range 0.4–0.75, so the
        # default tolerance of 0.6 (threshold 0.4) is intentionally lenient.
        # Raise RECOGNITION_TOLERANCE toward 0.7 to tighten security.
        self.tolerance: float = float(
            __import__("os").getenv("RECOGNITION_TOLERANCE", "0.6")
        )
        self.show_landmarks: bool = True

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
        # Only push a new app context when we are NOT already inside one.
        # Pushing a nested context causes Flask-SQLAlchemy's teardown to call
        # db.session.remove() when the inner context pops, which closes the
        # session mid-request and can leave _known_encodings stale.
        ctx = None
        try:
            from flask import current_app as _cur
            _cur._get_current_object()   # raises RuntimeError if no context
        except RuntimeError:
            if _app:
                ctx = _app.app_context()
                ctx.push()

        try:
            from app.models.face_encoding import FaceEncoding

            rows = FaceEncoding.query.all()

            enc   = [np.array(r.encoding, dtype=np.float32) for r in rows]
            names = [r.name for r in rows]

            with self._data_lock:
                self._known_encodings = enc
                self._known_names     = names

            logger.info(
                "Face data refreshed: %d encodings, %d unique people",
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

        logger.debug(
            "No match: best='%s' score=%.3f threshold=%.3f",
            known_names[best], score, 1 - self.tolerance,
        )
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
            # InsightFace bbox is [x1, y1, x2, y2]
            box = result["box"]
            left, top, right, bottom = int(box[0]), int(box[1]), int(box[2]), int(box[3])

            name = result["name"]
            confidence = result["confidence"]
            color = COLOR_KNOWN if name != "unknown" else COLOR_UNKNOWN

            # Outer bounding box
            cv2.rectangle(frame, (left, top), (right, bottom), color, 1, cv2.LINE_AA)

            # Corner accent marks
            cl, ct = 14, 2
            for ox, oy, hx, vy in [
                (left,  top,    left + cl,  top + cl),
                (right, top,    right - cl, top + cl),
                (left,  bottom, left + cl,  bottom - cl),
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

            # Confidence bar
            bar_w = tw + 10
            filled = int(bar_w * confidence / 100)
            cv2.rectangle(frame, (left, ly + 3), (left + bar_w, ly + 6), (40, 40, 40), -1)
            cv2.rectangle(frame, (left, ly + 3), (left + filled, ly + 6), color, -1)

            # Landmarks (InsightFace 5-point kps)
            if result.get("landmarks") is not None and self.show_landmarks:
                lm = np.array(result["landmarks"], dtype=np.int32)
                for x, y in lm:
                    cv2.circle(frame, (x, y), 2, (255, 200, 0), -1, cv2.LINE_AA)

        return frame