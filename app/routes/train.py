from flask import Blueprint, request, jsonify
from app.services.training_service import train_from_images, get_training_stats
from app.services.recognition_service import get_recognizer

train_bp = Blueprint("train", __name__)


@train_bp.route('/train', methods=['POST'])
def train():
    name = request.form.get('name', '').strip()
    files = request.files.getlist('images')

    if not name:
        return jsonify({"error": "Name is required."}), 400
    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "At least one image is required."}), 400

    result = train_from_images(name, files)

    if result["added"] == 0:
        return jsonify({"error": "No faces detected in any of the provided images."}), 400

    get_recognizer().refresh_data()

    msg = f"'{name}' trained with {result['added']} encoding(s)."
    if result["skipped"]:
        msg += f" {result['skipped']} image(s) skipped (no face detected)."

    return jsonify({"message": msg, "added": result["added"], "skipped": result["skipped"]})


@train_bp.route('/train/status', methods=['GET'])
def train_status():
    return jsonify({"faces": get_training_stats()})
