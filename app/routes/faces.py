from flask import Blueprint, jsonify
from app.stores.face_store import list_names, delete_face
from app.services.recognition_service import get_recognizer

faces_bp = Blueprint("faces", __name__)


@faces_bp.route('/faces')
def list_faces():
    return jsonify({"faces": list_names()})


@faces_bp.route('/faces/<name>', methods=['DELETE'])
def remove_face(name):
    success = delete_face(name)
    if not success:
        return jsonify({"error": f"No face found for '{name}'."}), 404
    get_recognizer().refresh_data()
    return jsonify({"message": f"'{name}' removed successfully."})
