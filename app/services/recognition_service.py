import cv2
import face_recognition
import numpy as np
import logging
import time

from app.models.face_store import load_data

logger = logging.getLogger(__name__)

_instance = None


def get_recognizer():
    global _instance
    if _instance is None:
        _instance = RecognitionService()
    return _instance


class RecognitionService:
    def __init__(self, tolerance=0.5):
        self.tolerance = tolerance
        self.data = load_data()
        self._last_logged = {}
        self._log_cooldown = 8

    def refresh_data(self):
        self.data = load_data()
        logger.info("Face data reloaded")

    def process_frame(self, frame):
        from app.models.log_store import add_event

        rgb = frame[:, :, ::-1]
        boxes = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, boxes)

        results = []
        now = time.time()

        for box, encoding in zip(boxes, encodings):
            name, confidence = self.match_face(encoding)

            if name != "unknown":
                last = self._last_logged.get(name, 0)
                if now - last > self._log_cooldown:
                    add_event(name, confidence)
                    self._last_logged[name] = now

            results.append({"box": box, "name": name, "confidence": confidence})

        return results

    def match_face(self, encoding):
        known_encodings = self.data["encodings"]
        known_names = self.data["names"]

        if not known_encodings:
            return "unknown", 0

        distances = face_recognition.face_distance(known_encodings, encoding)
        best_idx = np.argmin(distances)

        if distances[best_idx] < self.tolerance:
            confidence = int((1 - distances[best_idx]) * 100)
            return known_names[best_idx], confidence

        return "unknown", int((1 - distances[best_idx]) * 100)

    def draw_results(self, frame, results):
        for result in results:
            top, right, bottom, left = result["box"]
            name = result["name"]
            confidence = result["confidence"]

            is_known = name != "unknown"
            color = (34, 197, 94) if is_known else (239, 68, 68)

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2, cv2.LINE_AA)

            label = f"{name} ({confidence}%)"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)

            cv2.rectangle(frame, (left, top - h - 10), (left + w, top), color, -1)
            cv2.putText(
                frame, label, (left, top - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA
            )

        return frame
