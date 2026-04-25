import cv2
import numpy as np
import face_recognition

COLOR_KNOWN = (34, 197, 94)      # green (BGR)
COLOR_UNKNOWN = (239, 68, 68)    # red   (BGR)
COLOR_LANDMARK = (99, 102, 241)  # indigo (BGR)


def detect_faces(frame):
    """Return (locations, encodings) for a BGR frame."""
    rgb = frame[:, :, ::-1]
    boxes = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, boxes)
    return boxes, encodings


def get_encodings(frame, locations=None):
    return face_recognition.face_encodings(frame[:, :, ::-1], locations)


def get_landmarks(frame, locations=None):
    return face_recognition.face_landmarks(frame[:, :, ::-1], locations)


def draw_landmarks(frame, landmarks_list, color=COLOR_LANDMARK):
    """Draw 68-point facial landmarks on *frame* (in-place, BGR)."""
    closed_features = {"left_eye", "right_eye", "top_lip", "bottom_lip"}
    for lm in landmarks_list:
        for feature, points in lm.items():
            if not points:
                continue
            pts = np.array(points, dtype=np.int32)
            cv2.polylines(frame, [pts], feature in closed_features, color, 1, cv2.LINE_AA)
            for x, y in points:
                cv2.circle(frame, (x, y), 1, color, -1, cv2.LINE_AA)
    return frame


def assess_quality(frame, box) -> int:
    """Return a 0-100 quality score for a face crop (sharpness + brightness)."""
    top, right, bottom, left = box
    crop = frame[top:bottom, left:right]
    if crop.size == 0:
        return 0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur = min(cv2.Laplacian(gray, cv2.CV_64F).var() / 500.0, 1.0)
    bright = 1.0 - abs(gray.mean() - 128) / 128.0
    return int((blur * 0.7 + bright * 0.3) * 100)
