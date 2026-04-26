from insightface.app import FaceAnalysis
import threading

_face_app = None
_lock = threading.Lock()


def get_face_app():
    global _face_app

    if _face_app is None:
        with _lock:
            if _face_app is None:
                # No allowed_modules filter — loads all models in buffalo_l
                # including det_10g (detection), w600k_r50 (ArcFace),
                # 2d106det (106-pt 2D landmarks), and 1k3d68 (68-pt 3D landmarks).
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