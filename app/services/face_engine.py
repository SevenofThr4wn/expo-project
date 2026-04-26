from insightface.app import FaceAnalysis
import threading

_face_app = None
_lock = threading.Lock()


def get_face_app():
    global _face_app

    if _face_app is None:
        with _lock:
            if _face_app is None:
                app = FaceAnalysis(name="buffalo_l")
                app.prepare(ctx_id=-1, det_size=(320, 320))

                _face_app = app

    return _face_app


def get_faces(frame):
    """
    Runs InsightFace detection + embedding
    Returns raw InsightFace objects
    """
    app = get_face_app()
    return app.get(frame)