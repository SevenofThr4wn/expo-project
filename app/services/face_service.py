import cv2
import numpy as np

COLOR_KNOWN = (34, 197, 94)      # green (BGR)
COLOR_UNKNOWN = (239, 68, 68)    # red   (BGR)
COLOR_LANDMARK = (99, 102, 241)  # indigo (BGR)


# ─────────────────────────────────────────────
# FACE DETECTION + EMBEDDING (InsightFace)
# ─────────────────────────────────────────────

def detect_faces(frame):
    """
    Returns:
        faces: InsightFace detections
    """
    from app.services.face_engine import get_face_app

    app = get_face_app()
    faces = app.get(frame)
    return faces


def get_encodings(frame):
    """
    Returns embeddings + boxes in a clean format
    """
    from app.services.face_engine import get_face_app

    app = get_face_app()
    faces = app.get(frame)

    encodings = []
    boxes = []

    for f in faces:
        encodings.append(f.embedding)
        boxes.append(f.bbox)

    return boxes, encodings


# ─────────────────────────────────────────────
# LANDMARKS (InsightFace version)
# ─────────────────────────────────────────────

def get_landmarks(frame):
    """
    InsightFace returns 5-point landmarks (not 68-point like dlib)
    """
    from app.services.face_engine import get_face_app

    app = get_face_app()
    faces = app.get(frame)

    landmarks = []

    for f in faces:
        if hasattr(f, "landmark"):
            landmarks.append(f.landmark)
        else:
            landmarks.append(None)

    return landmarks


# ─────────────────────────────────────────────
# DRAW LANDMARKS (adapted for InsightFace)
# ─────────────────────────────────────────────

def draw_landmarks(frame, landmarks_list, color=COLOR_LANDMARK):
    """
    InsightFace landmarks are usually 5 points:
    [left_eye, right_eye, nose, mouth_left, mouth_right]
    """

    for lm in landmarks_list:
        if lm is None:
            continue

        lm = np.array(lm, dtype=np.int32)

        for (x, y) in lm:
            cv2.circle(frame, (x, y), 2, color, -1, cv2.LINE_AA)

    return frame


# ─────────────────────────────────────────────
# QUALITY SCORE (unchanged - still useful)
# ─────────────────────────────────────────────

def assess_quality(frame, box) -> int:
    top, right, bottom, left = box

    crop = frame[top:bottom, left:right]
    if crop.size == 0:
        return 0

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    blur = min(cv2.Laplacian(gray, cv2.CV_64F).var() / 500.0, 1.0)
    bright = 1.0 - abs(gray.mean() - 128) / 128.0

    return int((blur * 0.7 + bright * 0.3) * 100)