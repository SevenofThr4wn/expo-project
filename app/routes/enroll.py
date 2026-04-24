from flask import Blueprint, request, jsonify
import face_recognition
from app.stores.face_store import add_face
from app.services.recognition_service import get_recognizer

enroll_bp = Blueprint("enroll", __name__)


@enroll_bp.route('/enroll', methods=['POST'])
def enroll():
    file = request.files.get('image')
    name = request.form.get('name', '').strip()

    if not name:
        return jsonify({"error": "Name is required."}), 400
    if not file:
        return jsonify({"error": "Image is required."}), 400

    img = face_recognition.load_image_file(file)
    encodings = face_recognition.face_encodings(img)

    if not encodings:
        return jsonify({"error": "No face detected in the image."}), 400

    add_face(encodings[0], name)
    get_recognizer().refresh_data()

    return jsonify({"message": f"'{name}' enrolled successfully."}), 200
