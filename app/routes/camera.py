from flask import Blueprint, Response
import cv2
from app.services.face_service import detect_faces, match_face
from app.models.face_store import load_data

camera_bp = Blueprint("camera", __name__)
cam = cv2.VideoCapture(0)

def gen_frames():
    while True:
        success, frame = cam.read()
        if not success:
            break
        data = load_data()
        boxes, encoding = detect_faces(frame)

        for (top, right, bottom, left), encoding in zip(boxes, encoding):
            name, confidence = match_face(encoding, data["encodings"], data["names"])

            cv2.rectangle(
                frame, (left, top), (right, bottom), (0, 255, 0), 2, cv2.LINE_AA
            )

            label = f"{name} ({confidence:.2f})"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)

            cv2.rectangle(frame, (left, top - h - 10), (left + w, top), (0, 255, 0), -1)

            cv2.putText(
                frame,
                label,
                (left, top - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
                cv2.LINE_AA,
            )

            _, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()

            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


@camera_bp.route("/video")
def video():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")
